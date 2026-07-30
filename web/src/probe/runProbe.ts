// Medição do capability probe (SPEC-001): roda o modelo de pose em frames REAIS e mede
// quanto CADA inferência custa.
//
// Nota da spec: o probe usa o MESMO landmarker/config da sessão — por isso ele
// recebe a instância pronta em vez de criar a sua.
//
// Duas medidas saem daqui, e misturá-las foi o defeito que a T-084 corrigiu:
//
//   capacidade do aparelho → mediana de ms por inferência   → decide edge × cloud
//   cadência da câmera     → frames apresentados por segundo → sinal de CENA (SPEC-003)
//
// A segunda cai de graça do mesmo loop e não decide modo nenhum: câmera lenta é quase sempre
// pouca luz, e trocar para cloud por causa de pouca luz piora a imagem (JPEG 320px a 10fps).
import type { PoseLandmarker } from '@mediapipe/tasks-vision'
import { createVideoFrameLoop, type VideoFrameMetadata } from '../capture/videoFrameLoop'
import type { Mode, SessionCapabilityData } from '../lib/events'
import { detectPose } from '../pose/poseLandmarker'
import {
  PROBE_DURATION_MS,
  PROBE_MAX_MS,
  PROBE_MIN_SAMPLES,
  PROBE_WARMUP_SAMPLES,
  decideMode,
  detectWasmSimd,
  detectWebgl,
  fpsSustentavel,
  mediana,
  type ModeReason,
} from './capability'

export interface ProbeMeasurement {
  /** fps que o MODELO sustenta (1000 / mediana da latência). É o número da decisão. */
  modelFps: number | null
  /** Mediana de ms por inferência, já sem o aquecimento — o número cru, para diagnóstico. */
  inferenceMsP50: number | null
  /** fps que a CÂMERA entregou durante a medição. Sinal de cena, não de capacidade. */
  cameraFps: number | null
  /**
   * De onde saiu o `cameraFps`.
   *
   * `apresentados` é a taxa REAL da fonte (contador do compositor, via rVFC). `processados` é
   * um PISO: são os frames que nós conseguimos tratar, então num aparelho lento ele mede o
   * nosso gargalo e não a câmera. Quem for concluir "está escuro" a partir deste número
   * precisa checar isto antes — senão acusa luz fraca em aparelho devagar.
   */
  cameraFpsSource: 'apresentados' | 'processados'
  /** Inferências cronometradas (incluindo as de aquecimento, descartadas na conta). */
  samples: number
  durationMs: number
  failed: boolean
  error?: string
}

export interface ProbeOutcome extends ProbeMeasurement {
  mode: Mode
  reason: ModeReason
  webgl: boolean
  wasmSimd: boolean
  /** Modo veio de `?mode=` em vez da medição. */
  forced: boolean
}

/**
 * Cronometra inferências em frames reais da câmera.
 *
 * Fecha na janela nominal quando já tem amostra suficiente; se a câmera estiver lenta, estica
 * até o teto — antes de estimar capacidade com quatro amostras, é melhor esperar mais 1s.
 *
 * O laço é o mesmo `createVideoFrameLoop` do pipeline real (rVFC, como a spec pede), e não um
 * `requestAnimationFrame` próprio: rAF é cadência de REPAINT e compete com o que a tela está
 * animando — e a tela onde o probe roda é a pré-configuração, que tem grade, varredura e
 * quatro painéis de desfoque sobre vídeo ao vivo. Medir o modelo através do compositor era
 * medir a animação junto.
 *
 * O `setTimeout` não é redundância: se a câmera não entregar frame nenhum, o rVFC nunca dispara
 * e sem ele esta promessa jamais resolveria — o app ficaria presoem "calibrando o dispositivo".
 * Sem amostra a decisão é `sem_medida`, que hoje vale EDGE.
 */
export async function measureProbe(
  landmarker: PoseLandmarker,
  video: HTMLVideoElement,
  durationMs = PROBE_DURATION_MS,
  maxMs = PROBE_MAX_MS,
): Promise<ProbeMeasurement> {
  return new Promise<ProbeMeasurement>((resolve) => {
    const startedAt = performance.now()
    const latencias: number[] = []
    let lastVideoTime = -1
    let apresentadosInicio: number | null = null
    let apresentadosFim: number | null = null
    let processados = 0
    let stop: (() => void) | null = null
    let encerrado = false

    const finish = (failed: boolean, error?: string) => {
      if (encerrado) return
      encerrado = true
      clearTimeout(watchdog)
      stop?.()

      const elapsed = performance.now() - startedAt
      // Frames APRESENTADOS pelo compositor quando o navegador os conta; onde não houver
      // rVFC, sobra contar os que processamos — que é um piso, não a taxa da câmera.
      const temApresentados = apresentadosInicio !== null && apresentadosFim !== null
      const apresentados = temApresentados
        ? (apresentadosFim ?? 0) - (apresentadosInicio ?? 0)
        : processados

      resolve({
        modelFps: failed ? null : fpsSustentavel(latencias),
        inferenceMsP50: failed ? null : mediana(latencias.slice(PROBE_WARMUP_SAMPLES)),
        cameraFps: failed || elapsed <= 0 ? null : (apresentados * 1000) / elapsed,
        cameraFpsSource: temApresentados ? 'apresentados' : 'processados',
        samples: latencias.length,
        durationMs: Math.round(elapsed),
        failed,
        error,
      })
    }

    const onFrame = (_epochMs: number, metadata?: VideoFrameMetadata) => {
      if (encerrado) return

      if (typeof metadata?.presentedFrames === 'number') {
        if (apresentadosInicio === null) apresentadosInicio = metadata.presentedFrames
        apresentadosFim = metadata.presentedFrames
      }

      const elapsed = performance.now() - startedAt
      if (video.readyState >= video.HAVE_CURRENT_DATA && video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime
        const t0 = performance.now()
        try {
          detectPose(landmarker, video, performance.now())
        } catch (error) {
          finish(true, error instanceof Error ? error.message : String(error))
          return
        }
        latencias.push(performance.now() - t0)
        processados += 1
      }

      const suficiente = latencias.length >= PROBE_WARMUP_SAMPLES + PROBE_MIN_SAMPLES
      if ((elapsed >= durationMs && suficiente) || elapsed >= maxMs) finish(false)
    }

    // Folga sobre o teto: o loop fecha sozinho quando há frame; isto cobre o caso de não haver.
    // Armado ANTES do laço, para não existir instante em que uma medição está de pé sem rede.
    const watchdog = setTimeout(() => finish(false), maxMs + 250)
    stop = createVideoFrameLoop(video, onFrame)
  })
}

export async function runCapabilityProbe(
  landmarker: PoseLandmarker,
  video: HTMLVideoElement,
  modeOverride: Mode | null,
  durationMs = PROBE_DURATION_MS,
): Promise<ProbeOutcome> {
  const webgl = detectWebgl()
  const wasmSimd = detectWasmSimd()
  const measurement = await measureProbe(landmarker, video, durationMs)

  // O override é de debug: mede assim mesmo, para o número medido continuar
  // aparecendo, mas manda o modo pedido.
  const decidido = decideMode({
    modelFps: measurement.modelFps,
    webgl,
    wasmSimd,
    failed: measurement.failed,
  })

  return {
    ...measurement,
    webgl,
    wasmSimd,
    forced: modeOverride !== null,
    mode: modeOverride ?? decidido.mode,
    reason: decidido.reason,
  }
}

/** Payload `session.capability` do contrato, pronto para o WS (espelho em lib/events.ts). */
export function toCapabilityData(outcome: ProbeOutcome): SessionCapabilityData {
  return {
    mode: outcome.mode,
    // O contrato tem um campo de fps só, e o que interessa ao servidor é o da DECISÃO. O fps
    // da câmera é assunto de cena e não sobe: levá-lo junto pede campo novo no evento, o que
    // começa em `workers/shared/events.py` (registrado em Descobertas do BACKLOG).
    probe_fps: Number((outcome.modelFps ?? 0).toFixed(2)),
    webgl: outcome.webgl,
    ua: navigator.userAgent,
  }
}
