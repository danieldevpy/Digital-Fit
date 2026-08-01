// Admissão da sessão (SPEC-009 / T-011): `POST /api/sessions` devolve o ticket, e é dele que
// saem `session_id`, `token` e `ws_url`. O cliente NÃO inventa nenhum dos três — antes da
// T-011 existir ele inventava, e isso agora seria uma sessão que o servidor não conhece.
//
// O `ws_url` vem pronto (já com o token na query) e é usado como veio: montar a URL de novo
// aqui seria uma segunda implementação do mesmo contrato, pronta para divergir.
import { identityHeaders, rememberDeviceId } from '../auth/storage'
import { countdownPreference } from './preferences'
import type { Mode } from '../lib/events'
import { Mode as ModeValues } from '../lib/events'
import { toCapabilityData, type ProbeOutcome } from '../probe/runProbe'
import type { QuotaSnapshot } from './quota'

/** Resposta do `POST /api/sessions` — espelho de `SessionTicket` em `server/api/sessions.py`. */
export interface SessionTicket {
  session_id: string
  token: string
  ws_url: string
  mode: string
  exercise: string
  duration_s: number
  expires_at: number
  /** Id do aparelho: na primeira visita quem o gera é o servidor (SPEC-011). */
  device_id?: string
  /**
   * Quanto da quota de hoje já foi gasto. Vem SEMPRE, inclusive em plano ilimitado (com
   * `unlimited: true`) — um campo que sumisse obrigaria o cliente a ler ausência como
   * permissão, e ausência também é o que ele veria num corpo truncado ou num bug.
   */
  quota: QuotaSnapshot
}

/**
 * Códigos da recusa por quota (HTTP 429). O cliente distingue isto de "servidor com problema"
 * porque a ação é outra: aqui não adianta tentar de novo.
 *
 * São dois porque a ação de quem lê é diferente. `trial_exhausted`: o visitante cria conta, e a
 * conta resolve hoje mesmo. `quota_exceeded`: a conta já existe e é ela que chegou ao limite —
 * o convite a criar conta seria um conselho impossível de seguir.
 */
export const TRIAL_EXHAUSTED = 'trial_exhausted'
export const QUOTA_EXCEEDED = 'quota_exceeded'

/** Se este código é uma recusa por limite diário (qualquer das duas identidades). */
export function isQuotaRefusal(code: string | undefined): boolean {
  return code === TRIAL_EXHAUSTED || code === QUOTA_EXCEEDED
}

/**
 * Pedido de cloud sem vaga no semáforo (`slots:cloud = 3`, SPEC-009) volta com este `mode`,
 * e a sessão não chega a nascer. É condição temporária — três vagas ocupadas agora —, não
 * ausência de recurso: a mesma tentativa daqui a 30s tende a passar.
 */
export const DENIED_CLOUD = 'denied_cloud'

export class AdmissionError extends Error {
  readonly status?: number
  /** `trial_exhausted` ou `quota_exceeded` quando a recusa é o limite diário (SPEC-016). */
  readonly code?: string
  /**
   * O contador no instante da recusa. Vem junto do erro para o sheet dizer "10 de 10" e "renova
   * às 21:00" sem uma segunda chamada — e sem o cliente estimar nada por conta própria.
   */
  readonly quota?: QuotaSnapshot

  constructor(message: string, status?: number, code?: string, quota?: QuotaSnapshot) {
    super(message)
    this.name = 'AdmissionError'
    this.status = status
    this.code = code
    this.quota = quota
  }
}

export function apiBaseUrl(): string {
  const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
  return base.replace(/\/$/, '')
}

export interface AdmissionRequest {
  exercise: string
  requestedMode: Mode
  probe: ProbeOutcome | null
}

/**
 * Pede a sessão à API. `probe_result` vai junto: é o que faz o servidor publicar
 * `session.capability` (SPEC-001) sem o cliente precisar de um segundo evento pelo WS.
 */
export async function requestSession(
  { exercise, requestedMode, probe }: AdmissionRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<SessionTicket> {
  // Montar o corpo fora do `try`: erro aqui é bug meu, não rede fora do ar.
  const corpo = JSON.stringify({
    exercise,
    requested_mode: requestedMode,
    // Preparação escolhida por quem treina (T-049). Vai na admissão porque quem SEGURA a
    // contagem é o analysis-worker — no cliente seria só animação, e a rep feita durante o
    // "3, 2, 1" entraria no total.
    countdown_s: countdownPreference(),
    // Mesmos campos do `session.capability` — o servidor monta o evento a partir daqui.
    probe_result: probe ? toCapabilityData(probe) : null,
  })

  let resposta: Response
  try {
    resposta = await fetchImpl(`${apiBaseUrl()}/api/sessions`, {
      method: 'POST',
      // `identityHeaders` traz o aparelho (trial) e o `Authorization` quando há conta. A
      // admissão NÃO passa pelo `authedFetch`: com o access vencido ela cai no trial anônimo
      // em vez de falhar, e negar o treino de alguém por um token velho seria pior do que
      // contar a sessão como visitante.
      headers: { 'Content-Type': 'application/json', ...identityHeaders() },
      body: corpo,
    })
  } catch (erro) {
    throw new AdmissionError(
      erro instanceof Error ? `API fora do ar: ${erro.message}` : 'API fora do ar',
    )
  }

  if (!resposta.ok) {
    const { detail, code, device_id, quota } = await corpoDeErro(resposta)
    rememberDeviceId(device_id)
    throw new AdmissionError(detail ?? mensagemPadrao(resposta), resposta.status, code, quota)
  }

  const ticket = (await resposta.json()) as SessionTicket
  // Primeira visita: o id veio do servidor e precisa ser o MESMO na próxima sessão, senão o
  // trial nunca chega ao limite e o funil não existe.
  rememberDeviceId(ticket.device_id)
  if (ticket.mode === DENIED_CLOUD) {
    // Não é erro de programação: o servidor recusou o modo, a sessão não nasceu.
    throw new AdmissionError('Modo cloud indisponível agora — tente em modo edge.', 200)
  }
  if (!ticket.ws_url || !ticket.session_id) {
    throw new AdmissionError('Ticket de sessão incompleto (sem ws_url).')
  }
  return ticket
}

interface ErroDaAdmissao {
  detail?: string
  code?: string
  device_id?: string
  quota?: QuotaSnapshot
}

async function corpoDeErro(resposta: Response): Promise<ErroDaAdmissao> {
  try {
    const corpo = (await resposta.json()) as ErroDaAdmissao & { error?: string }
    return { ...corpo, detail: corpo.error ?? corpo.detail }
  } catch {
    return {}
  }
}

function mensagemPadrao(resposta: Response): string {
  return resposta.status === 503
    ? 'Servidor sem Redis — sessão não pode ser aberta.'
    : `Falha ao abrir a sessão (HTTP ${resposta.status}).`
}

/** O modo que o cliente pede: o override de `?mode=` vence o probe (SPEC-001). */
export function modeToRequest(override: Mode | null, probe: ProbeOutcome | null): Mode {
  return override ?? probe?.mode ?? ModeValues.EDGE
}
