// Índices e conexões do MediaPipe Pose (33 landmarks) — SPEC-005.
// A ordem é a padrão do MediaPipe (0 = nariz … 32 = pé esquerdo) e é a mesma
// usada pelo contrato de eventos (`pose.frame.landmarks`).

export const POSE_LANDMARK_NAMES = [
  'nose',
  'left_eye_inner',
  'left_eye',
  'left_eye_outer',
  'right_eye_inner',
  'right_eye',
  'right_eye_outer',
  'left_ear',
  'right_ear',
  'mouth_left',
  'mouth_right',
  'left_shoulder',
  'right_shoulder',
  'left_elbow',
  'right_elbow',
  'left_wrist',
  'right_wrist',
  'left_pinky',
  'right_pinky',
  'left_index',
  'right_index',
  'left_thumb',
  'right_thumb',
  'left_hip',
  'right_hip',
  'left_knee',
  'right_knee',
  'left_ankle',
  'right_ankle',
  'left_heel',
  'right_heel',
  'left_foot_index',
  'right_foot_index',
] as const

export const POSE_LANDMARK_COUNT = POSE_LANDMARK_NAMES.length

/** Pares de índices ligados por um segmento no desenho do esqueleto. */
export const POSE_CONNECTIONS: readonly (readonly [number, number])[] = [
  // rosto
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 7],
  [0, 4],
  [4, 5],
  [5, 6],
  [6, 8],
  [9, 10],
  // braço esquerdo
  [11, 13],
  [13, 15],
  [15, 17],
  [15, 19],
  [15, 21],
  [17, 19],
  // braço direito
  [12, 14],
  [14, 16],
  [16, 18],
  [16, 20],
  [16, 22],
  [18, 20],
  // tronco
  [11, 12],
  [11, 23],
  [12, 24],
  [23, 24],
  // perna esquerda
  [23, 25],
  [25, 27],
  [27, 29],
  [27, 31],
  [29, 31],
  // perna direita
  [24, 26],
  [26, 28],
  [28, 30],
  [28, 32],
  [30, 32],
] as const

/**
 * Subconjunto usado no desenho do HUD: tronco e membros, sem rosto, mãos e pés.
 * É escolha visual (o esqueleto da referência é limpo), não mudança de contrato —
 * `pose.frame` continua carregando os 33 landmarks.
 */
export const BODY_CONNECTIONS: readonly (readonly [number, number])[] = [
  // braços
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  // tronco
  [11, 12],
  [11, 23],
  [12, 24],
  [23, 24],
  // pernas
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28],
] as const

/** Articulações desenhadas como pontos, na mesma lógica de `BODY_CONNECTIONS`. */
export const BODY_JOINTS: readonly number[] = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
