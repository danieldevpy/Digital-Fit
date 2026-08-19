// Tela de relatório (SPEC-010). Sobe sobre a sessão quando ela termina.
//
// `translate="no"` nos NÚMEROS (T-162, SPEC-026 §Escopo): contagem, cadência, duração e o modo
// da sessão. Mesma regra do HUD — número não se traduz, e é o texto que o React reescreve
// quando o relatório chega. Título, rótulo e a lista de melhorias ficam de fora: são frases, e
// são o que alguém que ligou a tradução da página quer ler na própria língua.
//
// A SPEC-013 não define esta tela — ela é da SPEC-010. O visual segue os tokens da 013
// mesmo assim (glass, accent, tabular-nums), porque um relatório com outra linguagem visual
// pareceria outro aplicativo.
import { useT } from '../i18n'
import { getExercise } from '../session/catalog'
import { useSessionStore } from '../store/session'
import { BrandMark } from '../ui/BrandMark'
import { XpLine } from '../engagement/XpLine'
import {
  cadenceBars,
  durationLabel,
  improvements,
  reasonText,
  setLabel,
  windowLabel,
} from './reportSummary'
import { formatDuration } from './sessionReport'

/** Igual a `CADENCE_WINDOW_MS` no builder — o rótulo do eixo tem de casar com o dado. */
const WINDOW_MS = 5000

export function ReportSheet() {
  const t = useT()
  const report = useSessionStore((state) => state.report)
  const status = useSessionStore((state) => state.reportStatus)
  const open = useSessionStore((state) => state.reportOpen)
  const repCount = useSessionStore((state) => state.repCount)
  const closeReport = useSessionStore((state) => state.closeReport)

  if (!open) return null

  return (
    <div className="report" role="dialog" aria-label={t('report:sheet.aria_label')}>
      <div className="report__card">
        <BrandMark center />

        {status === 'loading' && (
          <>
            <p className="report__title">{t('report:loading.title')}</p>
            {/* O número que a pessoa acabou de ver ao vivo, para a tela não ficar vazia
                enquanto o relatório não chega. */}
            <p className="report__reps tabular" translate="no">
              {repCount}
            </p>
            <p className="report__hint">{t('report:loading.hint')}</p>
          </>
        )}

        {status === 'error' && (
          <>
            <p className="report__title">{t('report:error.title')}</p>
            <p className="report__reps tabular" translate="no">
              {repCount}
            </p>
            <p className="report__hint">{t('report:error.hint')}</p>
          </>
        )}

        {status === 'ready' && report && (
          <>
            {/* Qual exercício foi feito (T-055). Era óbvio enquanto o polichinelo era o único
                que contava; com quatro no ar, e com o relatório podendo ser reaberto do
                Progresso e do Analytics, "Série completa · 12 repetições" não diz de quê. */}
            <p className="report__ex">
              {getExercise(report.exercise).display_name}
              {/* "série 2 de 3", só quando o plano carimbou (SPEC-023 §Fase Inicial). Sem
                  carimbo não há série — e "série 0 de 0" seria inventar um plano que ninguém
                  montou. O número é `translate="no"` pela mesma regra do resto da tela. */}
              {setLabel(report) !== null && (
                <span className="report__set tabular" translate="no">
                  {setLabel(report)}
                </span>
              )}
            </p>
            <p className="report__title">{reasonText(report.reason)}</p>
            <p className="report__reps tabular" translate="no">
              {report.rep_count}
            </p>
            <p className="report__hint">{t('report:reps_label')}</p>

            <XpLine xp={report.xp} />

            <div className="report__stats">
              <div className="report__stat">
                <p className="report__stat-value tabular" translate="no">
                  {report.cadence_rpm.toFixed(0)}
                </p>
                <p className="report__stat-label">{t('report:stat.rpm')}</p>
              </div>
              <div className="report__stat">
                <p className="report__stat-value tabular" translate="no">
                  {formatDuration(report.duration_ms)}
                </p>
                {/* O rótulo muda com o modo, o número não (SPEC-023 §6: "nenhuma coluna
                    nova"). Com meta fixa, `duration_ms` passa a ser o tempo até a meta — que é
                    o número que mede evolução quando a duração deixa de ser fixa. */}
                <p className="report__stat-label">{durationLabel(report)}</p>
              </div>
              <div className="report__stat">
                {/* `edge`/`cloud` é vocabulário de contrato (SPEC-025 §Entidade), não frase:
                    continua em inglês no fio e não passa por tradução de máquina. */}
                <p className="report__stat-value" translate="no">
                  {report.mode}
                </p>
                <p className="report__stat-label">{t('report:stat.mode')}</p>
              </div>
            </div>

            {report.cadence_windows.length > 0 && (
              <div className="report__section">
                <p className="report__section-title">{t('report:section.pace')}</p>
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
              <p className="report__section-title">{t('report:section.improve')}</p>
              {improvements(report).length === 0 ? (
                <p className="report__clean">{t('report:clean')}</p>
              ) : (
                <ul className="report__list">
                  {improvements(report).map((item) => (
                    <li className="report__item" key={item.code}>
                      <span>{item.text}</span>
                      <span className="report__count tabular" translate="no">
                        {t('report:count_suffix', { n: item.count })}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        <button type="button" className="report__close" onClick={closeReport}>
          {t('report:close')}
        </button>
      </div>
    </div>
  )
}
