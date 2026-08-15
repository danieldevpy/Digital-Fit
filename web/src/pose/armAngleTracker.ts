// Ângulo do braço ao vivo, com o MESMO pré-processamento do worker.
//
// Espelha a ordem de `Normalizer.push` (workers/shared/normalize.py):
//   aspecto → torso_raw → escala suavizada → recentragem no quadril → One Euro → ângulo
//
// O passo do aspecto é a T-110: `x` vem dividido pela largura do frame e `y` pela altura, e
// sem pôr os dois na mesma moeda o ângulo herda o formato do vídeo. A ordem importa — o
// aspecto entra ANTES do torso, senão a escala sairia medida no espaço errado.
//
// Só as 4 articulações que a fórmula usa passam pelo filtro. Isso não é um
// atalho: o One Euro tem estado independente por canal, então filtrar 12
// coordenadas dá exatamente o mesmo resultado que filtrar as 99 e descartar o
// resto.
import { armAngle } from './angles'
import { OneEuroFilter } from './oneEuro'
import type { Landmark } from './skeleton'

const LEFT_SHOULDER = 11
const RIGHT_SHOULDER = 12
const LEFT_WRIST = 15
const RIGHT_WRIST = 16
const LEFT_HIP = 23
const RIGHT_HIP = 24

/** `NormParams` do contrato de normalização (SPEC-006) — não ajustar por gosto. */
export const NORM_PARAMS = {
  mincutoff: 0.4,
  beta: 1.5,
  dcutoff: 1.0,
  scaleMincutoff: 0.4,
  scaleBeta: 0.0,
} as const

/** `_MIN_TORSO` do lado Python. */
const MIN_TORSO = 1e-3

export interface ArmAngleTracker {
  /**
   * `tsMs` em epoch ms; devolve o ângulo em graus ou `null` se a pose não serve.
   *
   * `aspect` é largura ÷ altura do frame de onde os landmarks saíram (T-110). Omitido, o
   * espaço é tratado como isotrópico — o comportamento anterior à task, e o que mantém a
   * fixture de paridade sintética válida.
   */
  push(landmarks: readonly Landmark[], tsMs: number, aspect?: number): number | null
  reset(): void
}

export function createArmAngleTracker(): ArmAngleTracker {
  const pointsFilter = new OneEuroFilter({
    mincutoff: NORM_PARAMS.mincutoff,
    beta: NORM_PARAMS.beta,
    dcutoff: NORM_PARAMS.dcutoff,
  })
  const scaleFilter = new OneEuroFilter({
    mincutoff: NORM_PARAMS.scaleMincutoff,
    beta: NORM_PARAMS.scaleBeta,
    dcutoff: NORM_PARAMS.dcutoff,
  })

  return {
    push(landmarks, tsMs, aspect = 1) {
      const raw = {
        leftShoulder: landmarks[LEFT_SHOULDER],
        rightShoulder: landmarks[RIGHT_SHOULDER],
        leftWrist: landmarks[LEFT_WRIST],
        rightWrist: landmarks[RIGHT_WRIST],
        leftHip: landmarks[LEFT_HIP],
        rightHip: landmarks[RIGHT_HIP],
      }
      if (
        !raw.leftShoulder ||
        !raw.rightShoulder ||
        !raw.leftWrist ||
        !raw.rightWrist ||
        !raw.leftHip ||
        !raw.rightHip
      ) {
        return null
      }

      // Isotropia (T-110), antes de qualquer medida — igual ao `Normalizer.push` do worker.
      const iso = (p: Landmark): Landmark => ({ ...p, x: p.x * aspect })
      const leftShoulder = iso(raw.leftShoulder)
      const rightShoulder = iso(raw.rightShoulder)
      const leftWrist = iso(raw.leftWrist)
      const rightWrist = iso(raw.rightWrist)
      const leftHip = iso(raw.leftHip)
      const rightHip = iso(raw.rightHip)

      const t = tsMs / 1000

      const hipMidX = (leftHip.x + rightHip.x) / 2
      const hipMidY = (leftHip.y + rightHip.y) / 2
      const shoulderMidX = (leftShoulder.x + rightShoulder.x) / 2
      const shoulderMidY = (leftShoulder.y + rightShoulder.y) / 2

      const torsoRaw = Math.hypot(shoulderMidX - hipMidX, shoulderMidY - hipMidY)
      const torso = Math.max(scaleFilter.filterScalar(Math.max(torsoRaw, MIN_TORSO), t), MIN_TORSO)

      // Recentragem + escala, na mesma ordem do worker.
      const centered = [
        (leftShoulder.x - hipMidX) / torso,
        (leftShoulder.y - hipMidY) / torso,
        (rightShoulder.x - hipMidX) / torso,
        (rightShoulder.y - hipMidY) / torso,
        (leftWrist.x - hipMidX) / torso,
        (leftWrist.y - hipMidY) / torso,
        (rightWrist.x - hipMidX) / torso,
        (rightWrist.y - hipMidY) / torso,
      ]

      const s = pointsFilter.filter(centered, t)
      const asLandmark = (x: number, y: number): Landmark => ({ x, y, z: 0, visibility: 1 })

      const filtered: Landmark[] = []
      filtered[LEFT_SHOULDER] = asLandmark(s[0]!, s[1]!)
      filtered[RIGHT_SHOULDER] = asLandmark(s[2]!, s[3]!)
      filtered[LEFT_WRIST] = asLandmark(s[4]!, s[5]!)
      filtered[RIGHT_WRIST] = asLandmark(s[6]!, s[7]!)

      return armAngle(filtered)
    },

    reset() {
      pointsFilter.reset()
      scaleFilter.reset()
    },
  }
}
