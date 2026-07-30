// Tela Progresso (T-068) — aba própria na bottom nav.
//
// Mostra o ÚLTIMO treino, que é o único dado de progresso que existe hoje no aparelho
// (`digitalfit.last_report`, gravado na revisão de 2026-07-30). Série temporal, sequência de
// dias e evolução de peso são a T-065 (SPEC-017): declarados aqui como "em breve" em vez de
// desenhados com número inventado — a régua da SPEC-014 §Desvios vale para telas novas também.
import { reasonText } from '../report/reportSummary'
import { getExercise } from '../session/catalog'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { useSessionStore } from '../store/session'
import { IconChart, IconCounter, IconPlay, IconPulse } from '../ui/icons'

function segundos(ms: number): string {
  return `${(ms / 1000).toFixed(0)}s`
}

export function ProgressScreen() {
  // Do store, não do `localStorage` direto: o store já rehidrata `digitalfit.last_report` no
  // boot, e ler o arquivo duas vezes abriria a porta para duas verdades na mesma tela.
  const report = useSessionStore((state) => state.report)

  return (
    <>
      <div className="panel">
        <header className="panel__head">
          <p className="guide__kicker">Progresso</p>
          <h1 className="panel__title">Seu último treino</h1>
        </header>

        {report ? (
          <>
            <div className="panel__card">
              <p className="panel__card-title">{getExercise(report.exercise).display_name}</p>
              <p className="panel__card-sub">{reasonText(report.reason)}</p>
              <div className="panel__metrics">
                <div className="panel__metric">
                  <IconCounter className="panel__metric-icon" />
                  <p className="panel__metric-value tabular">{report.rep_count}</p>
                  <p className="v2-label">repetições</p>
                </div>
                <div className="panel__metric">
                  <IconPulse className="panel__metric-icon" />
                  <p className="panel__metric-value tabular">{report.cadence_rpm.toFixed(0)}</p>
                  <p className="v2-label">rep/min</p>
                </div>
                <div className="panel__metric">
                  <IconChart className="panel__metric-icon" />
                  <p className="panel__metric-value tabular">{segundos(report.duration_ms)}</p>
                  <p className="v2-label">duração</p>
                </div>
              </div>
            </div>

            <p className="panel__note">
              Histórico completo, evolução por semana e sequência de dias entram com o perfil
              físico (SPEC-017). Este é o treino que ficou guardado neste aparelho.
            </p>
          </>
        ) : (
          <div className="panel__empty">
            <IconChart className="panel__empty-icon" />
            <p className="panel__empty-title">Nenhum treino registrado ainda</p>
            <p className="panel__empty-text">
              Termine uma sessão e o resultado aparece aqui — mesmo sem conta.
            </p>
            <button
              type="button"
              className="v2-cta"
              onClick={() => navigate({ screen: 'preparar' })}
            >
              Treinar agora
              <span className="v2-cta__play">
                <IconPlay className="v2-cta__play-icon" />
              </span>
            </button>
          </div>
        )}
      </div>
      <TabBar />
    </>
  )
}
