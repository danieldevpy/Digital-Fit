// Relatório da sessão (SPEC-010 / T-020): busca no `GET /api/sessions/{id}/report`.
//
// O relatório NÃO existe no instante em que a sessão termina: o `session.completed` vai para o
// barramento, o report-builder consome, consolida e só então grava. Por isso a busca aqui
// tolera "ainda não" — e por isso a API responde 404 com `pending: true` em vez de um 404 seco:
// o cliente precisa distinguir "não existe ainda" de "não existe".
//
// Espelho de `SessionResult.to_report()` em `server/api/models.py`. Chaves em snake_case pelo
// mesmo motivo do contrato de eventos: é o formato que trafega, e traduzir na fronteira só
// criaria uma chance a mais de drift.
import { identityHeaders } from '../auth/storage'
import { apiBaseUrl } from '../session/admission'

/** Corpo do `GET /api/sessions/{id}/report`. */
export interface SessionReport {
  session_id: string
  exercise: string
  mode: string
  reason: string
  rep_count: number
  /** Duração **efetiva**: da calibração ao fim. Não inclui a preparação. */
  duration_ms: number
  cadence_rpm: number
  /** Repetições por janela de 5 s, inclusive as vazias — o buraco é a pausa. */
  cadence_windows: number[]
  rep_durations_ms: number[]
  feedback_counts: Record<string, number>
  scene_warning_counts: Record<string, number>
  calibration_samples: number
  /**
   * Versão da configuração (SPEC-018) sob a qual a sessão foi admitida; `0` = não registrada.
   * Nenhuma tela mostra este número — quem pergunta é o suporte, no painel. Está aqui porque
   * este tipo é o espelho do `to_report()`, e espelho com campo faltando é drift esperando
   * acontecer (a lição do `[A/T-051]`).
   */
  config_version: number
  created_at: string
  /**
   * Decomposição do XP desta sessão (SPEC-019 §XP / T-088).
   *
   * **Opcional porque só existe para quem tem conta**: XP não se aplica ao visitante (§Planos),
   * e a view omite a chave em vez de mandar zeros — zero seria lido como "não valeu nada", que
   * é uma afirmação, e falsa.
   *
   * Vem do servidor e não é recalculado aqui de propósito: a fórmula é versionada, um espelho
   * em TypeScript ficaria para trás no dia em que ela mudasse, e nenhum teste compara as duas
   * linguagens. Ver `engagement/XpLine.tsx`.
   */
  xp?: XpBreakdown
}

export interface XpBreakdown {
  total: number
  session: number
  reps: number
  clean: number
  /** Versão da fórmula que produziu estes números (`XP_FORMULA_V`). */
  formula_v: number
}

export class ReportError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ReportError'
  }
}

/**
 * Uma tentativa. `null` significa **ainda não pronto** (404), que é um estado normal logo
 * depois do fim da sessão — não um erro.
 */
export async function fetchReport(
  sessionId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<SessionReport | null> {
  let resposta: Response
  try {
    resposta = await fetchImpl(
      `${apiBaseUrl()}/api/sessions/${encodeURIComponent(sessionId)}/report`,
      // Sem o `Authorization`, o relatório de uma sessão COM DONO responde 404 (SPEC-011,
      // critério 2) — e o cliente ficaria repetindo para sempre por não conseguir ler o que
      // é dele. A identidade tem de acompanhar a busca, não só a admissão.
      { headers: identityHeaders() },
    )
  } catch (erro) {
    throw new ReportError(
      erro instanceof Error ? `API fora do ar: ${erro.message}` : 'API fora do ar',
    )
  }

  if (resposta.status === 404) return null
  if (!resposta.ok) throw new ReportError(`Falha ao buscar o relatório (HTTP ${resposta.status}).`)
  return (await resposta.json()) as SessionReport
}

/** Espera entre tentativas. A SPEC-010 promete o relatório em ≤ 2 s. */
export const RETRY_DELAY_MS = 400
export const MAX_ATTEMPTS = 12

export interface WaitOptions {
  attempts?: number
  delayMs?: number
  fetchImpl?: typeof fetch
  sleep?: (ms: number) => Promise<void>
}

/**
 * Tenta até o relatório existir. Existe porque o aviso `session.report.ready` pode não chegar
 * — WS caído, cliente que reconectou depois do fim — e sem isto a tela ficaria eternamente em
 * "consolidando". O caminho feliz continua sendo o evento: ele dispara a primeira tentativa
 * imediatamente, e estas repetições são a rede de segurança.
 */
export async function waitForReport(
  sessionId: string,
  options: WaitOptions = {},
): Promise<SessionReport | null> {
  const tentativas = options.attempts ?? MAX_ATTEMPTS
  const espera = options.delayMs ?? RETRY_DELAY_MS
  const dormir = options.sleep ?? ((ms: number) => new Promise((r) => setTimeout(r, ms)))

  for (let tentativa = 0; tentativa < tentativas; tentativa += 1) {
    const relatorio = await fetchReport(sessionId, options.fetchImpl)
    if (relatorio) return relatorio
    if (tentativa < tentativas - 1) await dormir(espera)
  }
  return null
}

/** Duração efetiva em `m:ss`, para o cabeçalho do relatório. */
export function formatDuration(durationMs: number): string {
  const total = Math.max(0, Math.round(durationMs / 1000))
  const minutos = Math.floor(total / 60)
  const segundos = total % 60
  return `${minutos}:${String(segundos).padStart(2, '0')}`
}
