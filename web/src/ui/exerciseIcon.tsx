// A figura do exercício selecionado, para as telas (T-082).
//
// O registro de qual pose pertence a qual slug — e as instruções para adicionar exercício —
// está em `exerciseFigures.ts`. Este arquivo é só a ponte entre ele e o JSX.
import { EXERCISE_FIGURES, FIGURA_PADRAO } from './exerciseFigures'

interface ExerciseIconProps {
  /** Slug do exercício (`session.started.exercise`). `null` cai na figura padrão. */
  exercise: string | null
  className?: string
}

/**
 * Slug sem figura cai na neutra em pé, sem barulho: quem cobra a figura faltando é o teste,
 * em desenvolvimento. Em produção um desenho ausente não pode abrir buraco no card nem
 * derrubar a pré-configuração.
 */
export function ExerciseIcon({ exercise, className }: ExerciseIconProps) {
  // `Object.hasOwn` e não indexação direta, pela mesma razão do `isExerciseKey` do catálogo:
  // um slug herdado do protótipo (`toString`) devolveria uma função que não é componente, e o
  // React quebraria no meio da tela em vez de cair no padrão.
  const Figura =
    exercise !== null && Object.hasOwn(EXERCISE_FIGURES, exercise)
      ? EXERCISE_FIGURES[exercise]!
      : FIGURA_PADRAO

  return <Figura className={className} />
}
