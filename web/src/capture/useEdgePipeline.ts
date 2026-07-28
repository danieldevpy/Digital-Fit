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
import { getGatewayClient, getSequencer } from '../session/gatewayInstance'
import { createArmAngleTracker } from '../pose/armAngleTracker'
import { createEdgePoseLandmarker, detectPose } from '../pose/poseLandmarker'
import { clearCanvas, drawSkeleton } from '../pose/skeleton'
import { parseModeOverride } from '../probe/capability'
import { runCapabilityProbe } from '../probe/runProbe'
import { getFixtureRecorder } from '../dev/recorder'
import { useSessionStore } from '../store/session'
import { EDGE_TARGET_FPS, createFrameClock } from './frameClock'
import { createVideoFrameLoop } from './videoFrameLoop'

/** Janela do fps efetivo mostrado no diagnóstico. */
const FPS_WINDOW_MS = 1000

/** SPEC-013: ângulo atualiza no máximo a 10Hz para não piscar. */
const ANGLE_MIN_INTERVAL_MS = 100

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
        const sessionId = useSessionStore.getState().sessionId
        if (sessionId) {
          gateway.send(
            makeEnvelope({
              type: EventType.POSE_FRAME,
              session_id: sessionId,
              ts: tick.ts,
              seq: getSequencer().next(),
              source: Source.EDGE,
              data: { landmarks: toLandmarkTuples(landmarks) },
            }),
          )
        }
      }

      // Ângulo ao vivo (T-044): calculado a cada frame para o filtro não perder
      // amostra, mas publicado no máximo a 10Hz — a spec não quer número piscando.
      const angle = angleTracker.push(landmarks, tick.ts)
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

      const { setLandmarksDetected, setFrameStats, setRecordedFrames, frameStats } =
        useSessionStore.getState()
      setLandmarksDetected(landmarks.length)
      setFrameStats({ seq: tick.seq, ts: tick.ts, fps: fps ?? frameStats?.fps ?? 0 })
      if (recorder.isRecording) setRecordedFrames(recorder.frameCount)
    }

    const startPipeline = async () => {
      store.setPoseStatus('loading')
      const { landmarker, delegate } = await createEdgePoseLandmarker()
      if (disposed) {
        landmarker.close()
        return
      }
      landmarkerRef.current = landmarker
      store.setPoseDelegate(delegate)
      store.setPoseStatus('ready')

      store.setProbeStatus('running')
      const capability = await runCapabilityProbe(landmarker, video, modeOverride)
      if (disposed) return
      store.setCapability(capability)
      store.setProbeStatus(capability.failed ? 'error' : 'done')

      // Sem slot de admission control e sem `frame.raw` na Fase 0, cloud é só
      // uma decisão registrada — não há o que rodar localmente.
      if (capability.mode === Mode.CLOUD) return

      clock.reset()
      stopLoop = createVideoFrameLoop(video, renderFrame)
    }

    startPipeline().catch((error: unknown) => {
      if (disposed) return
      store.setPoseStatus('error')
      store.setError(
        error instanceof Error
          ? `Falha ao iniciar o pipeline de pose: ${error.message}`
          : 'Falha ao iniciar o pipeline de pose.',
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
