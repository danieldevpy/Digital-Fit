// Catálogo de exercícios do cliente (SPEC-013 §Notas técnicas).
//
// Vive no cliente porque é conteúdo de apresentação: nome exibido, categoria,
// grupo muscular, dica padrão e qual ângulo mostrar. A chave (`jumping_jack`) é
// a mesma que o contrato usa em `session.started.exercise`.
export interface ExerciseInfo {
  display_name: string
  category: string
  muscle_group: string
  /** Estado vazio do card do treinador — ele nunca fica sem texto. */
  default_tip: string
  /** Qual ângulo articular a barra de métricas exibe (usado pela T-044). */
  main_angle: 'arm_abduction'
}

export const EXERCISE_CATALOG: Record<string, ExerciseInfo> = {
  jumping_jack: {
    display_name: 'Polichinelo',
    category: 'Cardio',
    muscle_group: 'Corpo inteiro',
    default_tip: 'Mantenha o core contraído e movimentos controlados.',
    main_angle: 'arm_abduction',
  },
}

export const DEFAULT_EXERCISE = 'jumping_jack'

export function getExercise(key: string | null): ExerciseInfo {
  return EXERCISE_CATALOG[key ?? DEFAULT_EXERCISE] ?? EXERCISE_CATALOG[DEFAULT_EXERCISE]!
}

/** "CARDIO • CORPO INTEIRO" da referência. */
export function exerciseSubtitle(exercise: ExerciseInfo): string {
  return `${exercise.category} • ${exercise.muscle_group}`
}
