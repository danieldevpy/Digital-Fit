// Como o relatório é lido em português (SPEC-010). Puro: só entra dado, só sai texto.
//
// Separado do componente porque é regra, não desenho: "o que melhorar" ordena por frequência,
// junta feedbacks de execução com avisos de cena e sabe o que dizer quando não há nada a
// corrigir. Isso se testa com um objeto; testar através do React seria testar o React.
import { t, type TKey } from '../i18n'
import { SessionEndReason } from '../lib/events'
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
}

export function reasonText(reason: string): string {
  return t(REASON_KEY[reason] ?? 'report:reason.unknown')
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
