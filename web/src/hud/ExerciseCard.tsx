import { PLACEHOLDER_EXERCISE } from './placeholders'
import { TimerRing } from './TimerRing'

export function ExerciseCard() {
  const { name, category, secondsLeft, secondsTotal } = PLACEHOLDER_EXERCISE

  return (
    <article className="card card--exercise">
      <div>
        <h2 className="exercise__name">{name}</h2>
        <p className="exercise__category">{category}</p>
      </div>
      <TimerRing secondsLeft={secondsLeft} secondsTotal={secondsTotal} />
    </article>
  )
}
