// Tela de relatório (SPEC-010). Sobe sobre a sessão quando ela termina.
//
// A SPEC-013 não define esta tela — ela é da SPEC-010. O visual segue os tokens da 013
// mesmo assim (glass, accent, tabular-nums), porque um relatório com outra linguagem visual
// pareceria outro aplicativo.
import { getExercise } from '../session/catalog'
import { useSessionStore } from '../store/session'
import { BrandMark } from '../ui/BrandMark'
import { cadenceBars, improvements, reasonText, windowLabel } from './reportSummary'
import { formatDuration } from './sessionReport'

/** Igual a `CADENCE_WINDOW_MS` no builder — o rótulo do eixo tem de casar com o dado. */
const WINDOW_MS = 5000

export function ReportSheet() {
  const report = useSessionStore((state) => state.report)
  const status = useSessionStore((state) => state.reportStatus)
  const open = useSessionStore((state) => state.reportOpen)
  const repCount = useSessionStore((state) => state.repCount)
  const closeReport = useSessionStore((state) => state.closeReport)

  if (!open) return null

  return (
    <div className="report" role="dialog" aria-label="Relatório da sessão">
      <div className="report__card">
        <BrandMark center />

        {status === 'loading' && (
          <>
            <p className="report__title">Consolidando o treino…</p>
            {/* O número que a pessoa acabou de ver ao vivo, para a tela não ficar vazia
                enquanto o relatório não chega. */}
            <p className="report__reps tabular">{repCount}</p>
            <p className="report__hint">Repetições contadas. Buscando o detalhamento…</p>
          </>
        )}

        {status === 'error' && (
          <>
            <p className="report__title">Treino concluído</p>
            <p className="report__reps tabular">{repCount}</p>
            <p className="report__hint">
              Não consegui carregar o detalhamento desta sessão. A contagem acima é a do
              servidor e está correta.
            </p>
          </>
        )}

        {status === 'ready' && report && (
          <>
            {/* Qual exercício foi feito (T-055). Era óbvio enquanto o polichinelo era o único
                que contava; com quatro no ar, e com o relatório podendo ser reaberto do
                Progresso e do Analytics, "Série completa · 12 repetições" não diz de quê. */}
            <p className="report__ex">{getExercise(report.exercise).display_name}</p>
            <p className="report__title">{reasonText(report.reason)}</p>
            <p className="report__reps tabular">{report.rep_count}</p>
            <p className="report__hint">repetições</p>

            <div className="report__stats">
              <div className="report__stat">
                <p className="report__stat-value tabular">{report.cadence_rpm.toFixed(0)}</p>
                <p className="report__stat-label">rep/min</p>
              </div>
              <div className="report__stat">
                <p className="report__stat-value tabular">{formatDuration(report.duration_ms)}</p>
                <p className="report__stat-label">tempo válido</p>
              </div>
              <div className="report__stat">
                <p className="report__stat-value">{report.mode}</p>
                <p className="report__stat-label">modo</p>
              </div>
            </div>

            {report.cadence_windows.length > 0 && (
              <div className="report__section">
                <p className="report__section-title">Ritmo ao longo da série</p>
                <div className="report__chart" aria-hidden="true">
                  {cadenceBars(report.cadence_windows).map((altura, indice) => (
                    <div className="report__bar-slot" key={indice}>
                      <div
                        className="report__bar"
                        style={{ height: `${Math.max(altura * 100, 3)}%` }}
                      />
                    </div>
                  ))}
                </div>
                <div className="report__axis">
                  <span>{windowLabel(0, WINDOW_MS)}</span>
                  <span>{windowLabel(report.cadence_windows.length, WINDOW_MS)}</span>
                </div>
              </div>
            )}

            <div className="report__section">
              <p className="report__section-title">O que melhorar</p>
              {improvements(report).length === 0 ? (
                <p className="report__clean">Nenhum aviso nesta série. Execução limpa.</p>
              ) : (
                <ul className="report__list">
                  {improvements(report).map((item) => (
                    <li className="report__item" key={item.code}>
                      <span>{item.text}</span>
                      <span className="report__count tabular">{item.count}×</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        <button type="button" className="report__close" onClick={closeReport}>
          Fechar
        </button>
      </div>
    </div>
  )
}
