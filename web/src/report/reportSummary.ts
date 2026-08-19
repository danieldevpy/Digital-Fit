// Como o relatório é lido em português (SPEC-010). Puro: só entra dado, só sai texto.
//
// Separado do componente porque é regra, não desenho: "o que melhorar" ordena por frequência,
// junta feedbacks de execução com avisos de cena e sabe o que dizer quando não há nada a
// corrigir. Isso se testa com um objeto; testar através do React seria testar o React.
import { t, type TKey } from '../i18n'
import { SessionEndReason, SetMode } from '../lib/events'
import { textForCode } from '../session/coachCard'
import type { SessionReport } from './sessionReport'

/**
 * Por que a sessão terminou, na voz do produto. A chave é o `SessionEndReason` — contrato do
 * `workers/shared/events.py` —, e o valor é a CHAVE do dicionário, não a frase: resolvida na
 * chamada, o texto acompanha quem troca de idioma sem reimportar o módulo (T-150).
 */
const REASON_KEY: Record<string, TKey> = {
  [SessionEndReason.COMPLETED]: 'report:reason.completed',
  [SessionEndReason.TIMEOUT]: 'report:reason.timeout',
  [SessionEndReason.ABORTED]: 'report:reason.aborted',
  [SessionEndReason.NO_DATA]: 'report:reason.no_data',
  [SessionEndReason.TARGET_REACHED]: 'report:reason.target_reached',
}

export function reasonText(reason: string): string {
  return t(REASON_KEY[reason] ?? 'report:reason.unknown')
}

/**
 * A série foi contada (meta de repetições) ou livre (janela de tempo)? — SPEC-023 §6, T-139.
 *
 * Compara com o vocabulário do contrato (`SetMode`) e não com uma string solta: o valor viaja
 * do `events.py` até aqui, e o dia em que um terceiro modo existir esta linha aponta para o
 * lugar onde ele foi declarado.
 *
 * Relatório antigo — gravado antes da T-134 — chega com `set_mode` no default `livre`, que é
 * exatamente o que ele era. Nada a migrar.
 */
export function isContado(report: SessionReport): boolean {
  return report.set_mode === SetMode.CONTADO
}

/**
 * O rótulo da duração, que muda de SIGNIFICADO com o modo — e é o ponto do §6 da SPEC-023.
 *
 * No modo livre a janela é fixa e a duração é só "quanto tempo valeu"; no contado a meta é fixa
 * e o mesmo número passa a ser **quanto se levou para chegar lá**, que é o número que mede
 * evolução: 15 repetições em 40 s e 15 em 3 min são treinos diferentes.
 *
 * Um rótulo, e não uma quarta estatística: o dado é o mesmo `duration_ms` (a spec promete
 * "nenhuma coluna nova"), e mostrar as duas leituras lado a lado seria repetir o número com
 * dois nomes.
 */
export function durationLabel(report: SessionReport): string {
  return t(isContado(report) ? 'report:stat.time_to_target' : 'report:stat.valid_time')
}

/**
 * "série 2 de 3", quando o carimbo do plano existe (SPEC-023 §Fase Inicial).
 *
 * `null` quando não veio de um plano: `set_index`/`set_total` valem `0` e "série 0 de 0" seria
 * inventar um plano que ninguém montou. Mesma régua do `--` da SPEC-014.
 */
export function setLabel(report: SessionReport): string | null {
  if (report.set_index < 1 || report.set_total < 1) return null
  return t('report:set_of', { n: report.set_index, total: report.set_total })
}

export interface ImprovementItem {
  code: string
  text: string
  count: number
}

/**
 * O que melhorar, do mais frequente para o menos. Execução e cena entram na MESMA lista: para
 * quem treinou, "suba mais os braços" e "você saiu do quadro" são a mesma pergunta — o que eu
 * faço diferente da próxima vez. A origem do aviso é detalhe de arquitetura, não do usuário.
 */
export function improvements(report: SessionReport): ImprovementItem[] {
  const total = new Map<string, number>()
  for (const fonte of [report.feedback_counts, report.scene_warning_counts]) {
    for (const [code, count] of Object.entries(fonte ?? {})) {
      total.set(code, (total.get(code) ?? 0) + count)
    }
  }

  return [...total.entries()]
    .map(([code, count]) => ({ code, text: textForCode(code), count }))
    .sort((a, b) => b.count - a.count || a.code.localeCompare(b.code))
}

/**
 * Altura relativa de cada barra do gráfico, 0–1. A escala é o pico da própria sessão: um
 * gráfico com escala fixa achataria toda sessão lenta até virar uma linha reta, escondendo
 * justamente a variação de ritmo que ele existe para mostrar.
 */
export function cadenceBars(windows: number[]): number[] {
  const pico = Math.max(0, ...windows)
  if (pico === 0) return windows.map(() => 0)
  return windows.map((reps) => reps / pico)
}

/** Rótulo do eixo: início de cada janela em segundos (0s, 5s, 10s…). */
export function windowLabel(index: number, windowMs: number): string {
  return t('report:window_label', { s: (index * windowMs) / 1000 })
}
