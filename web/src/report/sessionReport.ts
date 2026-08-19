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
import { t } from '../i18n'
import { localeHeaders } from '../i18n/http'
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
  /**
   * Como a série terminava (SPEC-023 / T-134): `livre` fecha na janela, `contado` na meta.
   *
   * Estes quatro campos são carimbo do servidor e o `to_report()` os manda desde a T-134 —
   * este espelho é que tinha ficado para trás. É exatamente o drift que o cabeçalho deste
   * arquivo avisa: campo que existe no fio e não no tipo não dá erro, só some da tela.
   *
   * Sem `?`: o servidor tem default para os quatro (`livre`, `0`, `0`, `0`), então eles sempre
   * chegam. Opcional aqui empurraria um `?? 0` para cada leitura sem nenhum ganho.
   */
  set_mode: string
  /** Meta de repetições da série. `0` no modo livre — não havia meta, e não é "meta zero". */
  target_reps: number
  /** Posição desta série no plano, base 1. `0` quando a sessão não veio de um plano. */
  set_index: number
  /** Quantas séries o plano tinha. `0` junto com `set_index` — os dois são o mesmo carimbo. */
  set_total: number
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
      // Idioma junto (T-153): o relatório em si é número, mas a rota pode recusar com `detail`
      // localizado, e o header é o mesmo em todas as chamadas nossas.
      { headers: { ...identityHeaders(), ...localeHeaders() } },
    )
  } catch (erro) {
    throw new ReportError(
      erro instanceof Error
        ? t('errors:api_down_detail', { reason: erro.message })
        : t('errors:api_down'),
    )
  }

  if (resposta.status === 404) return null
  if (!resposta.ok)
    throw new ReportError(t('report:fetch.failed', { status: resposta.status }))
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
