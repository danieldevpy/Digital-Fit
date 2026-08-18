// Pipeline edge do cliente (SPEC-001 + SPEC-005), em três etapas:
//
//   1. carrega o PoseLandmarker (delegate GPU, fallback CPU)
//   2. roda o capability probe por 2s NO MESMO landmarker e decide edge/cloud
//   3. se edge: loop de frames com decimação por tempo a 15fps, desenhando o esqueleto
//
// Modo cloud não envia nada aqui: `frame.raw` é a T-015 (Fase 1). Na Fase 0 o
// cliente apenas informa a decisão.
import { useEffect, useRef, type RefObject } from 'react'
import type { PoseLandmarker } from '@mediapipe/tasks-vision'
import {
  EventType,
  LANDMARK_COUNT,
  Mode,
  Source,
  makeEnvelope,
  toLandmarkTuples,
} from '../lib/events'
import { t } from '../i18n'
import { getGatewayClient, getSequencer } from '../session/gatewayInstance'
import { createArmAngleTracker } from '../pose/armAngleTracker'
import { createEdgePoseLandmarker, detectPose } from '../pose/poseLandmarker'
import { clearCanvas, drawSkeleton } from '../pose/skeleton'
import { parseModeOverride } from '../probe/capability'
import { runCapabilityProbe } from '../probe/runProbe'
import { getFixtureRecorder } from '../dev/recorder'
import { rewindAndPlay } from '../dev/videoSource'
import { streamsFrames, useSessionStore } from '../store/session'
import { createCloudSender } from './cloudFrames'
import { CLOUD_TARGET_FPS, EDGE_TARGET_FPS, createFrameClock } from './frameClock'
import { encodeFrame } from './jpegEncoder'
import { createVideoFrameLoop } from './videoFrameLoop'

/** Janela do fps efetivo mostrado no diagnóstico. */
const FPS_WINDOW_MS = 1000

/** SPEC-013: ângulo atualiza no máximo a 10Hz para não piscar. */
const ANGLE_MIN_INTERVAL_MS = 100

/**
 * Faixa de `visibility` do frame, para o chip de diagnóstico.
 *
 * Não é enfeite: visibilidade abaixo de 0.5 apaga o esqueleto na tela **e** faz o worker
 * acusar `OUT_OF_FRAME`. Quando isso acontece, a tela fica muda e o log não explica — este
 * número é a única forma de distinguir "o modelo não te viu" de "o campo não veio preenchido".
 */
function visibilityRange(
  landmarks: readonly { visibility?: number }[],
): { min: number; max: number } | null {
  if (landmarks.length === 0) return null
  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY
  for (const { visibility } of landmarks) {
    const valor = visibility ?? 1
    if (valor < min) min = valor
    if (valor > max) max = valor
  }
  return { min, max }
}

export function useEdgePipeline(
  videoRef: RefObject<HTMLVideoElement | null>,
  canvasRef: RefObject<HTMLCanvasElement | null>,
  enabled: boolean,
) {
  const landmarkerRef = useRef<PoseLandmarker | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const video = videoRef.current
    if (!enabled || !canvas || !video) return

    const store = useSessionStore.getState()
    const modeOverride = parseModeOverride(window.location.search)
    store.setModeOverride(modeOverride)

    const clock = createFrameClock(EDGE_TARGET_FPS)
    const angleTracker = createArmAngleTracker()
    let lastAngleAt = 0
    let disposed = false
    let stopLoop: (() => void) | null = null
    let lastVideoTime = -1
    let windowStart = 0
    let windowFrames = 0

    const renderFrame = (epochMs: number) => {
      const landmarker = landmarkerRef.current
      if (!landmarker) return
      if (video.readyState < video.HAVE_CURRENT_DATA || video.videoWidth === 0) return

      // Frame repetido não vira evento: `seq` contaria duas vezes o mesmo instante.
      if (video.currentTime === lastVideoTime) return
      lastVideoTime = video.currentTime

      const tick = clock.tick(epochMs)
      if (!tick) return

      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
      }
      const context = canvas.getContext('2d')
      if (!context) return

      const landmarks = detectPose(landmarker, video, performance.now())
      drawSkeleton(context, landmarks)

      const recorder = getFixtureRecorder()
      recorder.addFrame(tick, landmarks)

      // Envio ao gateway. O `seq` do envelope vem do sequenciador da sessão, não
      // do frame clock: o contrato diz "monotônico por SESSÃO", e a capability
      // também consome desse contador. O backpressure (descartar o frame mais
      // velho) é do cliente de gateway.
      const gateway = getGatewayClient()
      if (gateway && landmarks.length === LANDMARK_COUNT) {
        const { sessionId, sessionStatus, markFirstFrame } = useSessionStore.getState()
        // `streamsFrames` e não `sessionId !== null`: o id sobrevive ao fim da sessão (a tela
        // do relatório precisa dele), e mandar frame depois do fim já custou um relatório.
        if (sessionId && streamsFrames(sessionStatus)) {
          gateway.send(
            makeEnvelope({
              type: EventType.POSE_FRAME,
              session_id: sessionId,
              ts: tick.ts,
              seq: getSequencer().next(),
              source: Source.EDGE,
              // `videoWidth`/`videoHeight` são as dimensões do frame que o landmarker
              // acabou de ver — o mesmo `video` que entrou em `detectPose`. É por elas que
              // o MediaPipe dividiu `x` e `y`, e sem elas o servidor não consegue pôr os
              // dois eixos na mesma moeda (T-110). Vão em todo frame porque o aparelho
              // pode girar no meio do treino.
              data: {
                landmarks: toLandmarkTuples(landmarks),
                width: video.videoWidth,
                height: video.videoHeight,
              },
            }),
          )
          // O countdown da tela ancora no primeiro frame porque é aí que o timer
          // autoritativo do servidor começa (SPEC-009) — não na admissão.
          markFirstFrame(tick.ts)
        }
      }

      // Ângulo ao vivo (T-044): calculado a cada frame para o filtro não perder
      // amostra, mas publicado no máximo a 10Hz — a spec não quer número piscando.
      // O mesmo aspecto que viajou no `pose.frame`: se o HUD medisse no espaço distorcido
      // enquanto o servidor mede no corrigido, os dois números divergiriam na tela de quem
      // filma em retrato — e o ângulo do HUD é justamente o espelho do worker (T-044/T-110).
      const angle = angleTracker.push(
        landmarks,
        tick.ts,
        video.videoHeight > 0 ? video.videoWidth / video.videoHeight : 1,
      )
      if (angle !== null && tick.ts - lastAngleAt >= ANGLE_MIN_INTERVAL_MS) {
        lastAngleAt = tick.ts
        useSessionStore.getState().setArmAngleDeg(angle)
      }

      windowFrames += 1
      if (windowStart === 0) windowStart = tick.ts
      const elapsed = tick.ts - windowStart
      const fps = elapsed >= FPS_WINDOW_MS ? (windowFrames * 1000) / elapsed : null
      if (fps !== null) {
        windowStart = tick.ts
        windowFrames = 0
      }

      const {
        setLandmarksDetected,
        setLandmarkVisibility,
        setFrameStats,
        setRecordedFrames,
        frameStats,
      } = useSessionStore.getState()
      setLandmarksDetected(landmarks.length)
      setLandmarkVisibility(visibilityRange(landmarks))
      setFrameStats({ seq: tick.seq, ts: tick.ts, fps: fps ?? frameStats?.fps ?? 0 })
      if (recorder.isRecording) setRecordedFrames(recorder.frameCount)
    }

    /**
     * Modo cloud (T-015): 10fps de JPEG 320px pelo mesmo WebSocket.
     *
     * Sem esqueleto na tela — os landmarks só existem depois que o pose-worker responde, e o
     * push de `pose.frame` de volta ao cliente não está no contrato (`CLIENT_PUSH_TYPES`).
     * O HUD segue vivo pelos eventos de análise; a imagem fica sem overlay.
     */
    const startCloudLoop = (video: HTMLVideoElement) => {
      const cloudClock = createFrameClock(CLOUD_TARGET_FPS)
      const sender = createCloudSender(video, {
        clock: cloudClock,
        encode: (alvo) => encodeFrame(alvo),
        send: (frame, tick) => {
          const gateway = getGatewayClient()
          const { sessionId, sessionStatus, markFirstFrame } = useSessionStore.getState()
          // Mesma regra do caminho edge, e aqui o desperdício é maior: cada frame é um JPEG.
          if (!gateway || !sessionId || !streamsFrames(sessionStatus)) return
          gateway.send(
            makeEnvelope({
              type: EventType.FRAME_RAW,
              session_id: sessionId,
              ts: tick.ts,
              seq: getSequencer().next(),
              source: Source.CLOUD,
              data: { jpeg: frame.jpeg, width: frame.width, height: frame.height },
            }),
          )
          markFirstFrame(tick.ts)
        },
        onSent: ({ tick }) => {
          const { setFrameStats, frameStats } = useSessionStore.getState()
          setFrameStats({ seq: tick.seq, ts: tick.ts, fps: frameStats?.fps ?? 0 })
        },
      })

      return createVideoFrameLoop(video, (epochMs) => {
        void sender.onFrame(epochMs)
      })
    }

    const startPipeline = async () => {
      store.setPoseStatus('loading')
      // O progresso do download (T-070) vai para o store porque é informação de PRODUTO: são
      // ~17 MB no primeiro acesso, e quem espera precisa saber que está baixando, não travado.
      const { landmarker, delegate } = await createEdgePoseLandmarker((progresso) => {
        if (!disposed) useSessionStore.getState().setPoseDownload(progresso)
      })
      if (disposed) {
        landmarker.close()
        return
      }
      landmarkerRef.current = landmarker
      store.setPoseDelegate(delegate)
      store.setPoseDownload(null)
      store.setPoseStatus('ready')

      store.setProbeStatus('running')
      const capability = await runCapabilityProbe(landmarker, video, modeOverride)
      if (disposed) return
      store.setCapability(capability)
      store.setProbeStatus(capability.failed ? 'error' : 'done')

      // Cloud não roda pose localmente: manda JPEG e o pose-worker extrai (SPEC-005).
      if (capability.mode === Mode.CLOUD) {
        stopLoop = startCloudLoop(video)
        return
      }

      // Fonte de arquivo (T-040): o probe acabou de gastar ~2 s tocando o vídeo, e esses 2 s
      // são o trecho parado em que a calibração mede o corpo. Rebobinar aqui é o que faz o
      // navegador ler o MESMO material que o harness lê — sem isto a paridade compararia
      // arquivos diferentes e chamaria a diferença de "divergência JS × Python".
      if (useSessionStore.getState().videoSource === 'file') {
        await rewindAndPlay(video)
        if (disposed) return
      }

      clock.reset()
      stopLoop = createVideoFrameLoop(video, renderFrame)
    }

    startPipeline().catch((error: unknown) => {
      if (disposed) return
      store.setPoseStatus('error')
      store.setError(
        error instanceof Error
          ? t('session:pipeline.start_failed_detail', { reason: error.message })
          : t('session:pipeline.start_failed'),
      )
    })

    return () => {
      disposed = true
      stopLoop?.()
      landmarkerRef.current?.close()
      landmarkerRef.current = null
      const context = canvas.getContext('2d')
      if (context) clearCanvas(context)
      useSessionStore.getState().resetPipeline()
    }
  }, [enabled, videoRef, canvasRef])
}
