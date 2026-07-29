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

/**
 * Os exercícios oferecidos, em ordem de exibição.
 *
 * A autoridade sobre o que existe é o servidor (`EXERCISES` em
 * `workers/analysis_worker/exercises/`), que rejeita slug desconhecido no `POST /sessions`
 * dizendo quais aceita. Este catálogo é a face visível dela — quem adicionar exercício aqui
 * sem adicionar lá vai receber a recusa da admissão, que é alta e explica o motivo.
 */
export const EXERCISE_KEYS = Object.keys(EXERCISE_CATALOG)

export function isExerciseKey(key: unknown): key is string {
  // `Object.hasOwn` e não `in`: `in` percorre o protótipo, e `'toString' in EXERCISE_CATALOG`
  // é `true`. Um `toString` guardado no aparelho passaria por exercício válido, iria parar no
  // `POST /sessions` e faria `getExercise` devolver uma função no lugar do card.
  return typeof key === 'string' && Object.hasOwn(EXERCISE_CATALOG, key)
}

/**
 * Há escolha a oferecer? Com um exercício só, não — e a tela não desenha nada (T-051).
 *
 * Regra e não `&&` solto no componente porque é a decisão de produto desta task: o caminho da
 * escolha existe desde já, a superfície aparece quando houver o que escolher.
 */
export function offersChoice(): boolean {
  return EXERCISE_KEYS.length > 1
}

export function getExercise(key: string | null): ExerciseInfo {
  // Passa por `isExerciseKey` em vez de indexar direto: com chave herdada (`toString`) o
  // acesso devolveria uma função, o `??` não dispararia, e quem chamasse `.display_name`
  // receberia `undefined` no meio da tela.
  return isExerciseKey(key) ? EXERCISE_CATALOG[key]! : EXERCISE_CATALOG[DEFAULT_EXERCISE]!
}

/** "CARDIO • CORPO INTEIRO" da referência. */
export function exerciseSubtitle(exercise: ExerciseInfo): string {
  return `${exercise.category} • ${exercise.muscle_group}`
}
