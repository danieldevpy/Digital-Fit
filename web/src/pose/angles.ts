// Ângulo articular ao vivo (SPEC-013 Fase Inicial, T-044).
//
// ESPELHO da fórmula `_abduction` da FSM do polichinelo
// (`workers/analysis_worker/exercises/jumping_jack.py`). É **cosmético**: a
// autoridade de contagem e de qualidade continua no worker. Se a fórmula mudar
// lá, o teste de paridade (`angles.test.ts`) quebra aqui — é para isso que ele
// existe.
//
// O worker calcula sobre keypoints normalizados; aqui o cálculo é sobre os
// crus. Dá no mesmo: recentragem e escala uniforme não mudam o ângulo entre
// dois pontos, só o filtro de suavização introduz diferença — e ela cabe
// folgada nos 5° que a spec tolera.
import type { Landmark } from './skeleton'

const LEFT_SHOULDER = 11
const RIGHT_SHOULDER = 12
const LEFT_WRIST = 15
const RIGHT_WRIST = 16

/**
 * Ângulo ombro→pulso contra a vertical: 0° = braço para baixo, 180° = acima da
 * cabeça. `y` cresce para baixo (padrão MediaPipe).
 */
export function abduction(shoulder: Landmark, wrist: Landmark): number {
  const dx = wrist.x - shoulder.x
  const dy = wrist.y - shoulder.y
  return (Math.atan2(Math.abs(dx), dy) * 180) / Math.PI
}

/** Média dos dois braços — a feature `arm_angle` da FSM. */
export function armAngle(landmarks: readonly Landmark[]): number | null {
  const leftShoulder = landmarks[LEFT_SHOULDER]
  const rightShoulder = landmarks[RIGHT_SHOULDER]
  const leftWrist = landmarks[LEFT_WRIST]
  const rightWrist = landmarks[RIGHT_WRIST]
  if (!leftShoulder || !rightShoulder || !leftWrist || !rightWrist) return null

  return (abduction(leftShoulder, leftWrist) + abduction(rightShoulder, rightWrist)) / 2
}

/** Landmarks vindos do contrato (`[x, y, z, visibility]`). */
export function armAngleFromTuples(tuples: readonly (readonly number[])[]): number | null {
  return armAngle(
    tuples.map((t) => ({ x: t[0] ?? 0, y: t[1] ?? 0, z: t[2] ?? 0, visibility: t[3] })),
  )
}
