// Chamadas de conta e histórico (SPEC-011): `/api/auth/*`, `/api/me`, `/api/sessions?mine`.
//
// O centro deste arquivo é o `authedFetch`: uma chamada que toma 401 tenta renovar o access
// **uma vez** e repete. É o critério 3 da spec do lado do cliente — e a razão de ele ser
// suficiente está do outro lado: o WebSocket do treino não usa JWT nenhum (é o token HMAC do
// ticket, SPEC-009), então a renovação nunca acontece no meio de nada que possa cair.

import type { SessionReport } from '../report/sessionReport'
import { apiBaseUrl } from '../session/admission'
import { clearTokens, identityHeaders, storeTokens, storedTokens } from './storage'

export interface AccountUser {
  id: number
  email: string
  name: string
  /** Vê as ferramentas de diagnóstico, inclusive em produção (T-048). */
  is_admin: boolean
  date_joined: string
}

export interface AuthSession {
  user: AccountUser
  access: string
  refresh: string
}

export class AuthError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'AuthError'
    this.status = status
  }
}

async function detalhe(resposta: Response, padrao: string): Promise<string> {
  try {
    const corpo = (await resposta.json()) as { detail?: string }
    if (corpo.detail) return corpo.detail
  } catch {
    // corpo não-JSON
  }
  return padrao
}

/** Renova o access com o refresh guardado. `false` quando não há como — hora de logar. */
export async function refreshAccess(fetchImpl: typeof fetch = fetch): Promise<boolean> {
  const { refresh } = storedTokens()
  if (!refresh) return false

  let resposta: Response
  try {
    resposta = await fetchImpl(`${apiBaseUrl()}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
  } catch {
    // Rede fora: não é motivo para apagar o refresh — ele pode estar perfeitamente válido.
    return false
  }

  if (!resposta.ok) {
    // Refresh vencido ou adulterado: apagar aqui evita o cliente tentar para sempre.
    clearTokens()
    return false
  }
  const { access } = (await resposta.json()) as { access: string }
  storeTokens({ access })
  return true
}

/**
 * `fetch` com identidade, que renova o access uma vez se tomar 401.
 *
 * Uma vez só de propósito: se a segunda também der 401, o problema não é o access — é a conta.
 * Repetir mais viraria laço em cima de um servidor que já disse não.
 */
export async function authedFetch(
  caminho: string,
  init: RequestInit = {},
  fetchImpl: typeof fetch = fetch,
): Promise<Response> {
  const chamar = () =>
    fetchImpl(`${apiBaseUrl()}${caminho}`, {
      ...init,
      headers: { ...(init.headers as Record<string, string> | undefined), ...identityHeaders() },
    })

  const resposta = await chamar()
  if (resposta.status !== 401) return resposta
  if (!(await refreshAccess(fetchImpl))) return resposta
  return chamar()
}

async function autenticar(
  caminho: string,
  corpo: Record<string, string>,
  fetchImpl: typeof fetch,
): Promise<AuthSession> {
  let resposta: Response
  try {
    resposta = await fetchImpl(`${apiBaseUrl()}${caminho}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
    })
  } catch (erro) {
    throw new AuthError(
      erro instanceof Error ? `API fora do ar: ${erro.message}` : 'API fora do ar',
      0,
    )
  }

  if (!resposta.ok) {
    throw new AuthError(await detalhe(resposta, 'Não foi possível entrar.'), resposta.status)
  }

  const sessao = (await resposta.json()) as AuthSession
  storeTokens({ access: sessao.access, refresh: sessao.refresh })
  return sessao
}

export function login(
  email: string,
  password: string,
  fetchImpl: typeof fetch = fetch,
): Promise<AuthSession> {
  return autenticar('/api/auth/login', { email, password }, fetchImpl)
}

export function register(
  email: string,
  password: string,
  name: string,
  fetchImpl: typeof fetch = fetch,
): Promise<AuthSession> {
  return autenticar('/api/auth/register', { email, password, name }, fetchImpl)
}

/** Quem está logado. `null` quando ninguém — inclusive quando o refresh já não vale. */
export async function fetchMe(fetchImpl: typeof fetch = fetch): Promise<AccountUser | null> {
  let resposta: Response
  try {
    resposta = await authedFetch('/api/me', {}, fetchImpl)
  } catch {
    return null
  }
  if (!resposta.ok) return null
  return (await resposta.json()) as AccountUser
}

/** Histórico do usuário (`GET /api/sessions?mine`). Lança se a conta não valer mais. */
export async function fetchHistory(fetchImpl: typeof fetch = fetch): Promise<SessionReport[]> {
  const resposta = await authedFetch('/api/sessions?mine', {}, fetchImpl)
  if (!resposta.ok) {
    throw new AuthError(
      await detalhe(resposta, 'Não foi possível carregar o histórico.'),
      resposta.status,
    )
  }
  const corpo = (await resposta.json()) as { results: SessionReport[] }
  return corpo.results ?? []
}

export function logout(): void {
  clearTokens()
}
