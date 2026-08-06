// Junção das duas origens do histórico (SPEC-024 §1 / T-121). Puro: entram duas listas, sai
// uma. É regra, não desenho — e por isso se testa com dois objetos.
import type { SessionReport } from '../report/sessionReport'
import { HISTORY_CAP } from './localHistory'

/**
 * União por `session_id`, **servidor vencendo** — nunca soma das duas listas.
 *
 * Somar contaria em dobro toda sessão feita com conta: ela existe no aparelho (gravada no fim
 * do treino) *e* no servidor (gravada pelo report-builder). E o erro seria do tipo caro: um
 * total desatualizado a pessoa desconfia, um total dobrado ela acredita.
 *
 * O servidor vence no conflito porque ele é a autoridade da SPEC-010 — o mesmo `session_id`
 * pode ter sido consolidado depois de o cliente guardar a sua cópia.
 *
 * Ordena por `created_at` decrescente e corta no teto: a lista é uma janela das sessões mais
 * recentes, e as duas origens já respeitam o mesmo teto separadamente.
 */
export function mergeSessions(
  local: SessionReport[],
  servidor: SessionReport[],
): SessionReport[] {
  const porId = new Map<string, SessionReport>()
  for (const sessao of local) porId.set(sessao.session_id, sessao)
  for (const sessao of servidor) porId.set(sessao.session_id, sessao)

  return [...porId.values()]
    .sort((a, b) => instante(b) - instante(a))
    .slice(0, HISTORY_CAP)
}

/** `created_at` inválido vai para o fim da lista em vez de embaralhar a ordem com `NaN`. */
function instante(sessao: SessionReport): number {
  const ms = new Date(sessao.created_at).getTime()
  return Number.isNaN(ms) ? 0 : ms
}
