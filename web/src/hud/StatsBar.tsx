import { IconAngle, IconFlame, IconPulse, IconSeries } from '../ui/icons'
import { PLACEHOLDER_STATS } from './placeholders'

export function StatsBar() {
  const { series, reps, repsTarget, angle, kcal } = PLACEHOLDER_STATS

  return (
    <div className="stats">
      <div className="stats__item">
        <IconSeries className="stats__icon" />
        <div>
          <p className="stats__value tabular">{series}</p>
          <p className="stats__label">Série</p>
        </div>
      </div>

      <div className="stats__item">
        <IconPulse className="stats__icon" />
        <div>
          <p className="stats__value tabular">
            {reps}
            <span className="stats__value--muted">/{repsTarget}</span>
          </p>
          <p className="stats__label">Repetições</p>
        </div>
      </div>

      <div className="stats__item">
        <IconAngle className="stats__icon" />
        <div>
          <p className="stats__value tabular">{angle}°</p>
          <p className="stats__label">Ângulo</p>
        </div>
      </div>

      <div className="stats__item">
        <IconFlame className="stats__icon stats__icon--flame" />
        <div>
          <p className="stats__value tabular">{kcal}</p>
          <p className="stats__label">Kcal</p>
        </div>
      </div>
    </div>
  )
}
