// Barra de métricas da SPEC-013 §1.
//
// Fase Inicial: SÉRIE fixo em 1 (circuitos são evolução), REPETIÇÕES sem meta,
// ÂNGULO ao vivo vem do cliente (T-044), KCAL exibe "--" (MET é evolução).
import { getExercise } from '../session/catalog'
import { useSessionStore } from '../store/session'
import { IconAngle, IconFlame, IconPulse, IconSeries } from '../ui/icons'

/** Placeholder honesto: a célula existe no design, o dado ainda não. */
const NOT_AVAILABLE = '--'

const CURRENT_SERIES = 1

export function StatsBar() {
  const repCount = useSessionStore((state) => state.repCount)
  const armAngleDeg = useSessionStore((state) => state.armAngleDeg)
  const exerciseKey = useSessionStore((state) => state.exerciseKey)

  // O ângulo do braço só significa alguma coisa em quem move o braço (T-032). No agachamento
  // ele fica parado em ~12° o treino inteiro: um número imóvel enquanto a pessoa se esforça
  // lê como "não está me vendo", que é pior que a célula vazia.
  const mostraAngulo = getExercise(exerciseKey).main_angle === 'arm_abduction'
  const angulo = mostraAngulo && armAngleDeg !== null ? `${Math.round(armAngleDeg)}°` : NOT_AVAILABLE

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
          <p className="stats__value tabular">{angulo}</p>
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
