// Card "Dica do Treinador" — superfície do feedback engine (SPEC-013 §4).
//
// `translate="no"` no corpo (T-162, SPEC-026 §Escopo). É o texto que MAIS muda durante a sessão
// — troca a cada `feedback.issued` —, e é por isso a superfície mais exposta à classe de falha
// que a tradução de página introduz: o Google Translate embrulha cada nó de texto num `<font>`
// e o React segue tratando o nó como filho direto do elemento.
//
// A escolha custa alguma coisa e é bom dizer qual: quem traduziu a página perde justamente a
// frase do treinador. Foi decidido assim porque o app já existe em duas línguas curadas, e
// perder a dica é melhor que perder a sessão no meio do treino. O botão de detalhes fica FORA
// do atributo — é rótulo de interface, não conteúdo ao vivo.
import { useState } from 'react'
import { useT } from '../i18n'
import { getExercise } from '../session/catalog'
import { resolveCoachCard } from '../session/coachCard'
import { useNow } from '../session/useNow'
import { useSessionStore } from '../store/session'
import { IconUser } from '../ui/icons'

export function CoachTip() {
  const t = useT()
  const exerciseKey = useSessionStore((state) => state.exerciseKey)
  const sceneEntry = useSessionStore((state) => state.sceneEntry)
  const feedbackEntry = useSessionStore((state) => state.feedbackEntry)
  const [showHint, setShowHint] = useState(false)

  // Só tiquetaqueia enquanto há aviso ativo para expirar.
  const now = useNow(sceneEntry !== null || feedbackEntry !== null)

  const exercise = getExercise(exerciseKey)
  const card = resolveCoachCard({
    scene: sceneEntry,
    feedback: feedbackEntry,
    defaultTip: exercise.default_tip,
    now,
  })

  return (
    <article className={`card card--tip card--tip-${card.tone}`}>
      <div className="tip__avatar">
        <IconUser className="tip__avatar-icon" />
      </div>
      <div className="tip__body" translate="no">
        <p className="tip__title">{card.title}</p>
        <p className="tip__text">{card.text}</p>
        {showHint && card.hint && <p className="tip__hint">{card.hint}</p>}
      </div>
      <button
        type="button"
        className="tip__action"
        onClick={() => setShowHint((value) => !value)}
        disabled={!card.hint}
        title={card.hint ? undefined : t('session:coach.no_details')}
      >
        {showHint ? t('session:coach.hide') : t('session:coach.details')}
      </button>
    </article>
  )
}
