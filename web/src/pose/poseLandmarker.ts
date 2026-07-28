// Provedor EDGE de pose (SPEC-005): MediaPipe Pose Landmarker, modelo `lite`,
// WASM+SIMD servido localmente, delegate GPU quando disponível.
import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision'
import type { Landmark } from './skeleton'

/** Assets preparados por `npm run setup` (scripts/setup-mediapipe.mjs). */
const WASM_BASE_PATH = '/wasm'
const MODEL_PATH = '/models/pose_landmarker_lite.task'

export type PoseDelegate = 'GPU' | 'CPU'

export interface EdgePoseLandmarker {
  landmarker: PoseLandmarker
  delegate: PoseDelegate
}

async function createWith(delegate: PoseDelegate): Promise<PoseLandmarker> {
  const fileset = await FilesetResolver.forVisionTasks(WASM_BASE_PATH)
  return PoseLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: MODEL_PATH, delegate },
    runningMode: 'VIDEO',
    numPoses: 1,
  })
}

/**
 * Esta é a MESMA config que o capability probe (SPEC-001) deve usar — medir com
 * outra config faria o probe mentir.
 */
export async function createEdgePoseLandmarker(): Promise<EdgePoseLandmarker> {
  try {
    return { landmarker: await createWith('GPU'), delegate: 'GPU' }
  } catch (error) {
    console.warn('[pose] delegate GPU indisponível, caindo para CPU', error)
    return { landmarker: await createWith('CPU'), delegate: 'CPU' }
  }
}

/**
 * Extrai a pose da pessoa dominante. Múltiplas pessoas ficam para a Fase
 * Evolução da SPEC-005 — aqui `numPoses: 1` já resolve.
 */
export function detectPose(
  landmarker: PoseLandmarker,
  video: HTMLVideoElement,
  timestampMs: number,
): Landmark[] {
  const result = landmarker.detectForVideo(video, timestampMs)
  return result.landmarks[0] ?? []
}
