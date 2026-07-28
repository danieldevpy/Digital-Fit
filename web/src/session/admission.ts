// Admissão da sessão (SPEC-009 / T-011): `POST /api/sessions` devolve o ticket, e é dele que
// saem `session_id`, `token` e `ws_url`. O cliente NÃO inventa nenhum dos três — antes da
// T-011 existir ele inventava, e isso agora seria uma sessão que o servidor não conhece.
//
// O `ws_url` vem pronto (já com o token na query) e é usado como veio: montar a URL de novo
// aqui seria uma segunda implementação do mesmo contrato, pronta para divergir.
import type { Mode } from '../lib/events'
import { Mode as ModeValues } from '../lib/events'
import { toCapabilityData, type ProbeOutcome } from '../probe/runProbe'

/** Resposta do `POST /api/sessions` — espelho de `SessionTicket` em `server/api/sessions.py`. */
export interface SessionTicket {
  session_id: string
  token: string
  ws_url: string
  mode: string
  exercise: string
  duration_s: number
  expires_at: number
}

/**
 * Pedido de cloud sem vaga no semáforo (`slots:cloud = 3`, SPEC-009) volta com este `mode`,
 * e a sessão não chega a nascer. É condição temporária — três vagas ocupadas agora —, não
 * ausência de recurso: a mesma tentativa daqui a 30s tende a passar.
 */
export const DENIED_CLOUD = 'denied_cloud'

export class AdmissionError extends Error {
  readonly status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'AdmissionError'
    this.status = status
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
    // Mesmos campos do `session.capability` — o servidor monta o evento a partir daqui.
    probe_result: probe ? toCapabilityData(probe) : null,
  })

  let resposta: Response
  try {
    resposta = await fetchImpl(`${apiBaseUrl()}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: corpo,
    })
  } catch (erro) {
    throw new AdmissionError(
      erro instanceof Error ? `API fora do ar: ${erro.message}` : 'API fora do ar',
    )
  }

  if (!resposta.ok) {
    throw new AdmissionError(await mensagemDeErro(resposta), resposta.status)
  }

  const ticket = (await resposta.json()) as SessionTicket
  if (ticket.mode === DENIED_CLOUD) {
    // Não é erro de programação: o servidor recusou o modo, a sessão não nasceu.
    throw new AdmissionError('Modo cloud indisponível agora — tente em modo edge.', 200)
  }
  if (!ticket.ws_url || !ticket.session_id) {
    throw new AdmissionError('Ticket de sessão incompleto (sem ws_url).')
  }
  return ticket
}

async function mensagemDeErro(resposta: Response): Promise<string> {
  try {
    const corpo = (await resposta.json()) as { error?: string; detail?: string }
    const texto = corpo.error ?? corpo.detail
    if (texto) return texto
  } catch {
    // corpo não-JSON: cai no genérico
  }
  return resposta.status === 503
    ? 'Servidor sem Redis — sessão não pode ser aberta.'
    : `Falha ao abrir a sessão (HTTP ${resposta.status}).`
}

/** O modo que o cliente pede: o override de `?mode=` vence o probe (SPEC-001). */
export function modeToRequest(override: Mode | null, probe: ProbeOutcome | null): Mode {
  return override ?? probe?.mode ?? ModeValues.EDGE
}
