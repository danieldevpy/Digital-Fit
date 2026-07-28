import { exerciseSubtitle, getExercise } from '../session/catalog'
import { useCountdown } from '../session/countdown'
import { useSessionStore } from '../store/session'
import { TimerRing } from './TimerRing'

export function ExerciseCard() {
  const exerciseKey = useSessionStore((state) => state.exerciseKey)
  const { secondsLeft, durationS } = useCountdown()
  const exercise = getExercise(exerciseKey)

  return (
    <article className="card card--exercise">
      <div>
        <h2 className="exercise__name">{exercise.display_name}</h2>
        <p className="exercise__category">{exerciseSubtitle(exercise)}</p>
      </div>
      <TimerRing secondsLeft={secondsLeft} secondsTotal={durationS} />
    </article>
  )
}
