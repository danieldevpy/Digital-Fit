// Provedor EDGE de pose (SPEC-005): MediaPipe Pose Landmarker, modelo `lite`,
// WASM+SIMD servido localmente, delegate GPU quando disponível.
import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision'
import { comPrazo } from '../lib/deadline'
import type { Landmark } from './skeleton'

/** Assets preparados por `npm run setup` (scripts/setup-mediapipe.mjs). */
const WASM_BASE_PATH = '/wasm'
const MODEL_PATH = '/models/pose_landmarker_lite.task'

/**
 * Prazo de cada tentativa de criar o landmarker (T-069).
 *
 * Generoso de propósito. A inicialização da GPU inclui compilar os shaders do MediaPipe, e num
 * aparelho de cache frio (aba anônima, primeiro acesso) isso passa fácil de 5s — cortar aí
 * empurraria para CPU um aparelho que ia funcionar, e CPU costuma medir menos de 12fps no
 * probe, o que joga a sessão para CLOUD sem necessidade. Depois da T-069 a lentidão deixou de
 * ser fatal (a sessão só abre quando o pipeline está pronto), então este prazo não existe para
 * pegar "devagar": existe para pegar "travado para sempre", que é o que não tinha saída.
 */
export const INIT_TIMEOUT_MS = 12_000

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

/** Cria com prazo, fechando o que chegar depois — dois contextos vivos seria pior que nenhum. */
function createComPrazo(delegate: PoseDelegate): Promise<PoseLandmarker> {
  return comPrazo(createWith(delegate), INIT_TIMEOUT_MS, {
    oQue: `delegate ${delegate}`,
    aoChegarTarde: (landmarker) => landmarker.close(),
  })
}

/**
 * Esta é a MESMA config que o capability probe (SPEC-001) deve usar — medir com
 * outra config faria o probe mentir.
 *
 * O prazo (T-069) fecha um buraco real: a queda para CPU só acontecia quando a GPU REJEITAVA,
 * e uma inicialização de GPU que trava não rejeita — ficava pendente para sempre. O app parava
 * em "preparando", sem erro, sem fallback, e a sessão morria de `no_data` do outro lado.
 */
export async function createEdgePoseLandmarker(): Promise<EdgePoseLandmarker> {
  try {
    return { landmarker: await createComPrazo('GPU'), delegate: 'GPU' }
  } catch (error) {
    console.warn('[pose] delegate GPU indisponível ou travado, caindo para CPU', error)
    // A CPU também ganha prazo: se ela travar, o `catch` de quem chamou mostra o erro na tela
    // em vez de deixar a tela esperando um evento que não vem.
    return { landmarker: await createComPrazo('CPU'), delegate: 'CPU' }
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
