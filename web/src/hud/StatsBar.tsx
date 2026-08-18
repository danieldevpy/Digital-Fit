// Barra de métricas da SPEC-013 §1.
//
// `translate="no"` nos VALORES, e não na barra inteira (T-162, SPEC-026 §Escopo). Quem abre o
// app numa língua não curada pode pedir a tradução da página ao navegador — e aí duas coisas
// ruins acontecem de uma vez. A primeira é de produto: "12" não se traduz, e um número passado
// por tradução de máquina é ruído com risco. A segunda é técnica: o Google Translate embrulha
// cada nó de texto num `<font>`, o React continua tratando o nó como filho direto do elemento,
// e uma tela que redesenha texto a cada repetição é a mais exposta do app a essa classe de
// falha. Os RÓTULOS ficam de fora do atributo de propósito — "Repetições"/"Reps" é exatamente
// o que alguém que traduziu a página quer ler na própria língua, e eles só mudam quando o
// locale muda.
//
// Fase Inicial: SÉRIE fixo em 1 (circuitos são evolução), REPETIÇÕES sem meta,
// ÂNGULO ao vivo vem do cliente (T-044), KCAL exibe "--" (MET é evolução).
import { useT } from '../i18n'
import { getExercise } from '../session/catalog'
import { useSessionStore } from '../store/session'
import { IconAngle, IconFlame, IconPulse, IconSeries } from '../ui/icons'

/** Placeholder honesto: a célula existe no design, o dado ainda não. */
const NOT_AVAILABLE = '--'

const CURRENT_SERIES = 1

export function StatsBar() {
  const t = useT()
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
          <p className="stats__value tabular" translate="no">
            {CURRENT_SERIES}
          </p>
          <p className="stats__label">{t('session:label.series')}</p>
        </div>
      </div>

      <div className="stats__item">
        <IconPulse className="stats__icon" />
        <div>
          <p className="stats__value tabular" translate="no">
            {repCount}
          </p>
          <p className="stats__label">{t('session:label.reps')}</p>
        </div>
      </div>

      <div className="stats__item">
        <IconAngle className="stats__icon" />
        <div>
          <p className="stats__value tabular" translate="no">
            {angulo}
          </p>
          <p className="stats__label">{t('session:label.angle')}</p>
        </div>
      </div>

      <div className="stats__item">
        <IconFlame className="stats__icon stats__icon--flame" />
        <div>
          <p className="stats__value tabular" translate="no">
            {NOT_AVAILABLE}
          </p>
          <p className="stats__label">{t('session:label.kcal_short')}</p>
        </div>
      </div>
    </div>
  )
}
