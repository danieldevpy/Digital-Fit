import { afterEach, describe, expect, it, vi } from 'vitest'

import { useI18nStore } from '../i18n/store'
import { authedFetch, fetchHistory, fetchMe, login, logout, refreshAccess, register } from './api'
import { deviceId, identityHeaders, rememberDeviceId, storeTokens, storedTokens } from './storage'
import { installStorage, uninstallStorage } from './testStorage'

afterEach(uninstallStorage)

/** Sequência de respostas: cada chamada consome a próxima. */
function fetchSequence(...respostas: Array<{ status?: number; body?: unknown }>) {
  const chamadas: Array<[string, RequestInit | undefined]> = []
  const impl = vi.fn(async (url: string, init?: RequestInit) => {
    chamadas.push([url, init])
    const proxima = respostas.shift() ?? { status: 500, body: {} }
    return new Response(JSON.stringify(proxima.body ?? {}), {
      status: proxima.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  return { impl: impl as unknown as typeof fetch, chamadas }
}

const USUARIO = {
  id: 1,
  email: 'a@b.com',
  name: 'Ana',
  is_admin: false,
  daily_goal: 'casual',
  date_joined: '2026-07-29T10:00:00Z',
}

describe('refreshAccess', () => {
  it('sem refresh guardado nem tenta a rede', async () => {
    installStorage()
    const { impl, chamadas } = fetchSequence()
    expect(await refreshAccess(impl)).toBe(false)
    expect(chamadas).toHaveLength(0)
  })

  it('troca o access e mantém o refresh', async () => {
    installStorage()
    storeTokens({ access: 'velho', refresh: 'r.1' })
    const { impl } = fetchSequence({ body: { access: 'novo' } })

    expect(await refreshAccess(impl)).toBe(true)
    expect(storedTokens()).toEqual({ access: 'novo', refresh: 'r.1' })
  })

  it('refresh recusado apaga os tokens — repetir seria laço', async () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    const { impl } = fetchSequence({ status: 401, body: { detail: 'Token inválido.' } })

    expect(await refreshAccess(impl)).toBe(false)
    expect(storedTokens()).toEqual({ access: undefined, refresh: undefined })
  })

  it('rede fora NÃO apaga o refresh: ele pode estar perfeitamente válido', async () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    const quebrado = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch

    expect(await refreshAccess(quebrado)).toBe(false)
    expect(storedTokens().refresh).toBe('r.1')
  })
})

describe('authedFetch', () => {
  it('manda a identidade em toda chamada', async () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    const { impl, chamadas } = fetchSequence({ body: USUARIO })

    await authedFetch('/api/me', {}, impl)

    const headers = chamadas[0]?.[1]?.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer a.1')
  })

  it('401 renova o access e repete — com o token novo', async () => {
    installStorage()
    storeTokens({ access: 'vencido', refresh: 'r.1' })
    const { impl, chamadas } = fetchSequence(
      { status: 401, body: { detail: 'expired' } },
      { body: { access: 'novo' } },
      { body: USUARIO },
    )

    const resposta = await authedFetch('/api/me', {}, impl)

    expect(resposta.status).toBe(200)
    expect(chamadas).toHaveLength(3)
    expect(chamadas[1]?.[0]).toMatch(/\/api\/auth\/refresh$/)
    const cabecalhoDaRepeticao = chamadas[2]?.[1]?.headers as Record<string, string>
    expect(cabecalhoDaRepeticao.Authorization).toBe('Bearer novo')
  })

  it('renova UMA vez: 401 depois da renovação volta como está', async () => {
    installStorage()
    storeTokens({ access: 'vencido', refresh: 'r.1' })
    const { impl, chamadas } = fetchSequence(
      { status: 401, body: {} },
      { body: { access: 'novo' } },
      { status: 401, body: {} },
    )

    const resposta = await authedFetch('/api/me', {}, impl)

    expect(resposta.status).toBe(401)
    expect(chamadas).toHaveLength(3)
  })

  it('sem refresh, o 401 volta direto sem tentar renovar', async () => {
    installStorage()
    const { impl, chamadas } = fetchSequence({ status: 401, body: {} })

    const resposta = await authedFetch('/api/me', {}, impl)

    expect(resposta.status).toBe(401)
    expect(chamadas).toHaveLength(1)
  })

  it('preserva o que o chamador pediu (método e cabeçalhos próprios)', async () => {
    installStorage()
    const { impl, chamadas } = fetchSequence({ body: {} })

    await authedFetch('/api/me', { method: 'POST', headers: { 'X-Teste': '1' } }, impl)

    expect(chamadas[0]?.[1]?.method).toBe('POST')
    expect((chamadas[0]?.[1]?.headers as Record<string, string>)['X-Teste']).toBe('1')
  })

  // SPEC-025 §3.4 / critério 7 da T-142: o cliente manda o locale JÁ RESOLVIDO, não o bruto do
  // navegador — é o que permite o servidor (T-143, em paralelo) responder `GET /api/config` e
  // `GET /api/engagement` na língua certa sem rota nova nem parâmetro por chamada.
  it('manda Accept-Language com o locale resolvido do cliente, não o do navegador', async () => {
    installStorage()
    useI18nStore.getState().setLocale('pt-BR')
    const { impl, chamadas } = fetchSequence({ body: USUARIO })

    await authedFetch('/api/me', {}, impl)

    const headers = chamadas[0]?.[1]?.headers as Record<string, string>
    expect(headers['Accept-Language']).toBe('pt-BR')
  })

  it('Accept-Language acompanha a troca de idioma, inclusive na chamada repetida após renovar', async () => {
    installStorage()
    storeTokens({ access: 'vencido', refresh: 'r.1' })
    useI18nStore.getState().setLocale('en')
    const { impl, chamadas } = fetchSequence(
      { status: 401, body: {} },
      { body: { access: 'novo' } },
      { body: USUARIO },
    )

    await authedFetch('/api/me', {}, impl)

    const cabecalhoDaRepeticao = chamadas[2]?.[1]?.headers as Record<string, string>
    expect(cabecalhoDaRepeticao['Accept-Language']).toBe('en')
  })
})

describe('login e cadastro', () => {
  it('entrar guarda o par de tokens', async () => {
    installStorage()
    const { impl, chamadas } = fetchSequence({
      body: { user: USUARIO, access: 'a.1', refresh: 'r.1' },
    })

    const sessao = await login('A@B.com', 'segredo', impl)

    expect(sessao.user.email).toBe('a@b.com')
    expect(storedTokens()).toEqual({ access: 'a.1', refresh: 'r.1' })
    expect(chamadas[0]?.[0]).toMatch(/\/api\/auth\/login$/)
  })

  it('cadastro manda o nome junto', async () => {
    installStorage()
    const { impl, chamadas } = fetchSequence({
      status: 201,
      body: { user: USUARIO, access: 'a.1', refresh: 'r.1' },
    })

    await register('a@b.com', 'segredo', 'Ana', impl)

    const corpo = JSON.parse(chamadas[0]?.[1]?.body as string)
    expect(corpo).toEqual({ email: 'a@b.com', password: 'segredo', name: 'Ana' })
  })

  it('cadastro leva o aparelho junto, para o servidor adotar as sessões de visitante', async () => {
    // T-087: sem este cabeçalho o cadastro funciona e o histórico fica para trás — que é
    // exatamente a dor que o CTA de conta promete evitar.
    installStorage()
    rememberDeviceId('dev-abc12345')
    const { impl, chamadas } = fetchSequence({
      status: 201,
      body: { user: USUARIO, access: 'a.1', refresh: 'r.1', adopted_sessions: 4 },
    })

    const sessao = await register('a@b.com', 'segredo', 'Ana', impl)

    const cabecalhos = chamadas[0]?.[1]?.headers as Record<string, string>
    expect(cabecalhos['X-Device-Id']).toBe('dev-abc12345')
    // O access velho NÃO vai junto: quem se cadastra não está logado.
    expect(cabecalhos.Authorization).toBeUndefined()
    expect(sessao.adopted_sessions).toBe(4)
  })

  it('cadastro sem aparelho guardado não inventa cabeçalho', async () => {
    installStorage()
    const { impl, chamadas } = fetchSequence({
      status: 201,
      body: { user: USUARIO, access: 'a.1', refresh: 'r.1' },
    })

    await register('a@b.com', 'segredo', 'Ana', impl)

    const cabecalhos = chamadas[0]?.[1]?.headers as Record<string, string>
    expect(cabecalhos['X-Device-Id']).toBeUndefined()
  })

  it('e-mail já cadastrado vira a mensagem do servidor', async () => {
    installStorage()
    const { impl } = fetchSequence({ status: 409, body: { detail: 'Este e-mail já tem conta.' } })

    await expect(register('a@b.com', 'segredo', '', impl)).rejects.toThrow(/já tem conta/)
  })

  it('senha errada não guarda token nenhum', async () => {
    installStorage()
    const { impl } = fetchSequence({ status: 401, body: { detail: 'E-mail ou senha inválidos.' } })

    await expect(login('a@b.com', 'errada', impl)).rejects.toThrow(/inválidos/)
    expect(storedTokens()).toEqual({ access: undefined, refresh: undefined })
  })

  it('API fora do ar não vaza stack de rede', async () => {
    installStorage()
    const quebrado = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch

    useI18nStore.getState().setLocale('pt-BR')
    await expect(login('a@b.com', 'segredo', quebrado)).rejects.toThrow(/API fora do ar/)
  })

  it('a mesma falha de rede sai em inglês — e da MESMA chave das outras duas (T-151)', async () => {
    installStorage()
    const quebrado = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch

    // `errors:api_down_detail` é a única casa da frase desde esta task: `auth/api`,
    // `session/admission` e `report/sessionReport` liam três cópias iguais.
    useI18nStore.getState().setLocale('en')
    await expect(login('a@b.com', 'segredo', quebrado)).rejects.toThrow(/API is down/)
    useI18nStore.getState().setLocale('pt-BR')
  })
})

describe('fetchMe', () => {
  it('devolve o usuário quando o access vale', async () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    const { impl } = fetchSequence({ body: USUARIO })

    expect(await fetchMe(impl)).toEqual(USUARIO)
  })

  it('ninguém logado é `null`, não erro — é o estado padrão do produto', async () => {
    installStorage()
    const { impl } = fetchSequence({ status: 401, body: {} })

    expect(await fetchMe(impl)).toBeNull()
  })

  it('API fora do ar na abertura do app também é `null`', async () => {
    installStorage()
    const quebrado = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch

    expect(await fetchMe(quebrado)).toBeNull()
  })
})

describe('fetchHistory', () => {
  it('devolve os relatórios da conta', async () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    const { impl, chamadas } = fetchSequence({ body: { results: [{ session_id: 's1' }] } })

    const historico = await fetchHistory(impl)

    expect(historico).toHaveLength(1)
    expect(chamadas[0]?.[0]).toMatch(/\/api\/sessions\?mine$/)
  })

  it('corpo sem `results` vira lista vazia', async () => {
    installStorage()
    const { impl } = fetchSequence({ body: {} })
    expect(await fetchHistory(impl)).toEqual([])
  })

  it('conta que não vale mais levanta erro — a tela precisa saber', async () => {
    installStorage()
    const { impl } = fetchSequence({ status: 401, body: { detail: 'Faça login.' } })

    await expect(fetchHistory(impl)).rejects.toThrow(/Faça login/)
  })
})

describe('logout', () => {
  it('apaga os tokens e mantém o aparelho', async () => {
    installStorage()
    const { impl } = fetchSequence({ body: { user: USUARIO, access: 'a.1', refresh: 'r.1' } })
    await login('a@b.com', 'segredo', impl)
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    ;(globalThis as { window?: { localStorage: Storage } }).window?.localStorage.setItem(
      'digitalfit.device_id',
      'dev-abc12345',
    )

    logout()

    expect(identityHeaders()).toEqual({ 'X-Device-Id': 'dev-abc12345' })
    expect(deviceId()).toBe('dev-abc12345')
  })
})
