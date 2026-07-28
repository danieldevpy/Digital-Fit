// VALORES DE FACHADA — nada aqui é calculado.
//
// O HUD real é a T-012 e consome os eventos do contrato:
//   reps        ← `rep.detected`      (FSM do analysis-worker, T-008/T-009)
//   tempo       ← timer autoritativo da sessão (T-011)
//   ângulo      ← derivado dos keypoints normalizados (T-006)
//   kcal, série ← ainda não existem em nenhuma spec (ver Descobertas no BACKLOG)
//
// Enquanto isso, este arquivo é o único lugar com números inventados: quando os
// eventos chegarem, ele some e cada card passa a ler do store.

export const PLACEHOLDER_STATS = {
  series: 2,
  reps: 11,
  repsTarget: 20,
  angle: 128,
  kcal: 420,
} as const

export const PLACEHOLDER_EXERCISE = {
  name: 'Polichinelo',
  category: 'Cardio • Corpo inteiro',
  secondsLeft: 24,
  secondsTotal: 30,
} as const

export const PLACEHOLDER_TIP = {
  title: 'Dica do treinador',
  text: 'Mantenha o core contraído e movimentos controlados.',
} as const
