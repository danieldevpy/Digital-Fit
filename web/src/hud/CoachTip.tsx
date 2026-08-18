// Card "Dica do Treinador" — superfície do feedback engine (SPEC-013 §4).
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
      <div className="tip__body">
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
