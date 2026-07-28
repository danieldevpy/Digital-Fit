// Medição do capability probe (SPEC-001): roda o modelo de pose em frames REAIS
// por 2s e mede o fps efetivo.
//
// Nota da spec: o probe usa o MESMO landmarker/config da sessão — por isso ele
// recebe a instância pronta em vez de criar a sua.
import type { PoseLandmarker } from '@mediapipe/tasks-vision'
import type { Mode, SessionCapabilityData } from '../lib/events'
import { detectPose } from '../pose/poseLandmarker'
import { PROBE_DURATION_MS, decideMode, detectWasmSimd, detectWebgl } from './capability'

export interface ProbeMeasurement {
  probeFps: number | null
  frames: number
  durationMs: number
  failed: boolean
  error?: string
}

export interface ProbeOutcome extends ProbeMeasurement {
  mode: Mode
  webgl: boolean
  wasmSimd: boolean
  /** Modo veio de `?mode=` em vez da medição. */
  forced: boolean
}

/**
 * Conta quantos frames de vídeo distintos o modelo consegue processar na janela.
 * Frames repetidos não contam: mediriam a taxa da câmera, não a do modelo.
 */
export async function measureProbeFps(
  landmarker: PoseLandmarker,
  video: HTMLVideoElement,
  durationMs = PROBE_DURATION_MS,
): Promise<ProbeMeasurement> {
  return new Promise<ProbeMeasurement>((resolve) => {
    const startedAt = performance.now()
    let frames = 0
    let lastVideoTime = -1
    let animationFrame = 0

    const finish = (failed: boolean, error?: string) => {
      cancelAnimationFrame(animationFrame)
      const elapsed = performance.now() - startedAt
      resolve({
        frames,
        durationMs: Math.round(elapsed),
        failed,
        error,
        probeFps: failed || elapsed <= 0 ? null : (frames * 1000) / elapsed,
      })
    }

    const step = () => {
      const elapsed = performance.now() - startedAt
      if (elapsed >= durationMs) {
        finish(false)
        return
      }

      if (video.readyState >= video.HAVE_CURRENT_DATA && video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime
        try {
          detectPose(landmarker, video, performance.now())
          frames += 1
        } catch (error) {
          finish(true, error instanceof Error ? error.message : String(error))
          return
        }
      }

      animationFrame = requestAnimationFrame(step)
    }

    animationFrame = requestAnimationFrame(step)
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
  const measurement = await measureProbeFps(landmarker, video, durationMs)

  // O override é de debug: mede assim mesmo, para o número medido continuar
  // aparecendo, mas manda o modo pedido.
  const decided = decideMode({
    probeFps: measurement.probeFps,
    webgl,
    wasmSimd,
    failed: measurement.failed,
  })

  return {
    ...measurement,
    webgl,
    wasmSimd,
    forced: modeOverride !== null,
    mode: modeOverride ?? decided,
  }
}

/** Payload `session.capability` do contrato, pronto para o WS (espelho em lib/events.ts). */
export function toCapabilityData(outcome: ProbeOutcome): SessionCapabilityData {
  return {
    mode: outcome.mode,
    probe_fps: Number((outcome.probeFps ?? 0).toFixed(2)),
    webgl: outcome.webgl,
    ua: navigator.userAgent,
  }
}
