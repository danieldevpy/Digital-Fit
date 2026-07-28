// Barra de métricas da SPEC-013 §1.
//
// Fase Inicial: SÉRIE fixo em 1 (circuitos são evolução), REPETIÇÕES sem meta,
// ÂNGULO ao vivo chega na T-044, KCAL exibe "--" (estimativa MET é evolução).
import { useSessionStore } from '../store/session'
import { IconAngle, IconFlame, IconPulse, IconSeries } from '../ui/icons'

/** Placeholder honesto: a célula existe no design, o dado ainda não. */
const NOT_AVAILABLE = '--'

const CURRENT_SERIES = 1

export function StatsBar() {
  const repCount = useSessionStore((state) => state.repCount)

  return (
    <div className="stats">
      <div className="stats__item">
        <IconSeries className="stats__icon" />
        <div>
          <p className="stats__value tabular">{CURRENT_SERIES}</p>
          <p className="stats__label">Série</p>
        </div>
      </div>

      <div className="stats__item">
        <IconPulse className="stats__icon" />
        <div>
          <p className="stats__value tabular">{repCount}</p>
          <p className="stats__label">Repetições</p>
        </div>
      </div>

      <div className="stats__item">
        <IconAngle className="stats__icon" />
        <div>
          <p className="stats__value tabular">{NOT_AVAILABLE}</p>
          <p className="stats__label">Ângulo</p>
        </div>
      </div>

      <div className="stats__item">
        <IconFlame className="stats__icon stats__icon--flame" />
        <div>
          <p className="stats__value tabular">{NOT_AVAILABLE}</p>
          <p className="stats__label">Kcal</p>
        </div>
      </div>
    </div>
  )
}
