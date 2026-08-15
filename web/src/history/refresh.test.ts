import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import type { SessionReport } from '../report/sessionReport'
import { useAccountStore } from '../store/account'
import { FRESH_MS, historyIsFresh, refreshHistory, resetRefreshForTests } from './refresh'
import { useHistoryStore } from './store'

const AGORA = 1_800_000_000_000

function sessao(id: string, created_at = '2026-08-05T10:00:00Z', reps = 10) {
  return { session_id: id, created_at, rep_count: reps } as SessionReport
}

/** `fetch` de mentira que devolve o histórico pedido. Conta quantas vezes foi chamado. */
function servidor(reports: SessionReport[]) {
  const impl = vi.fn(
    async () =>
      new Response(JSON.stringify({ results: reports }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
  )
  return impl as unknown as typeof fetch & { mock: { calls: unknown[] } }
}

function logar() {
  useAccountStore.setState({
    status: 'authenticated',
    user: { id: 1, email: 'a@b.com', name: 'Ana', is_admin: false, daily_goal: 'casual', date_joined: '2026-07-01' },
  })
}

beforeEach(() => {
  installStorage()
  resetRefreshForTests()
  useHistoryStore.setState({
    sessions: [],
    status: 'idle',
    source: 'local',
    loadedAt: null,
    loadError: false,
  })
  useAccountStore.setState({ status: 'anonymous', user: null })
})

afterEach(uninstallStorage)

describe('sem conta', () => {
  it('não chama a rede — `?mine` responde 401 por construção', async () => {
    const impl = servidor([])
    await refreshHistory({ fetchImpl: impl, now: AGORA })
    expect(impl).not.toHaveBeenCalled()
  })

  it('relê o aparelho, que é a única fonte que o visitante tem', async () => {
    useHistoryStore.getState().record(sessao('s1'))
    useHistoryStore.setState({ sessions: [] })
    await refreshHistory({ fetchImpl: servidor([]), now: AGORA })
    expect(useHistoryStore.getState().sessions.map((s) => s.session_id)).toEqual(['s1'])
  })
})

describe('debounce de 30 s (critérios 2 e 3)', () => {
  it('foco novo logo depois de uma carga boa não gasta requisição', async () => {
    logar()
    const impl = servidor([sessao('s1')])

    await refreshHistory({ fetchImpl: impl, now: AGORA })
    await refreshHistory({ fetchImpl: impl, now: AGORA + 5_000 })

    expect(impl).toHaveBeenCalledTimes(1)
  })

  it('passados os 30 s, o foco vale uma requisição', async () => {
    logar()
    const impl = servidor([sessao('s1')])

    await refreshHistory({ fetchImpl: impl, now: AGORA })
    await refreshHistory({ fetchImpl: impl, now: AGORA + FRESH_MS + 1 })

    expect(impl).toHaveBeenCalledTimes(2)
  })

  // O fim de sessão é fato novo, não suspeita: esperar 30 s para mostrá-lo é a queixa que
  // originou a spec.
  it('`force` ignora o debounce', async () => {
    logar()
    const impl = servidor([sessao('s1')])

    await refreshHistory({ fetchImpl: impl, now: AGORA })
    await refreshHistory({ fetchImpl: impl, now: AGORA + 1_000, force: true })

    expect(impl).toHaveBeenCalledTimes(2)
  })

  it('sem carga nenhuma ainda, nada está fresco', () => {
    expect(historyIsFresh(AGORA)).toBe(false)
  })
})

describe('resposta que chega', () => {
  it('aplica o que veio do servidor e marca a hora', async () => {
    logar()
    await refreshHistory({ fetchImpl: servidor([sessao('s1')]), now: AGORA })

    const { sessions, source, loadedAt } = useHistoryStore.getState()
    expect(sessions.map((s) => s.session_id)).toEqual(['s1'])
    expect(source).toBe('server')
    expect(loadedAt).toBe(AGORA)
  })

  it('revalidar não faz a tela piscar: nunca passa por "carregando" com dado bom', async () => {
    logar()
    useHistoryStore.getState().record(sessao('s1'))

    const vistos: string[] = []
    const parar = useHistoryStore.subscribe((estado) => vistos.push(estado.status))
    await refreshHistory({ fetchImpl: servidor([sessao('s1')]), now: AGORA })
    parar()

    expect(vistos).not.toContain('loading')
  })
})

describe('falha (critério 5)', () => {
  it('rede fora mantém o que estava na tela e acende o aviso', async () => {
    logar()
    useHistoryStore.getState().record(sessao('s1'))

    const impl = vi.fn(async () => {
      throw new Error('rede fora')
    }) as unknown as typeof fetch
    await refreshHistory({ fetchImpl: impl, now: AGORA })

    const { sessions, status, loadError } = useHistoryStore.getState()
    expect(sessions).toHaveLength(1)
    expect(status).toBe('ready')
    expect(loadError).toBe(true)
  })
})

describe('resposta velha não pousa por cima da nova (`AbortController`)', () => {
  it('o pedido substituído é abortado e não escreve na tela', async () => {
    logar()

    // Num objeto, e não numa variável solta: o controle de fluxo do TS reduz a variável a
    // `never` depois do executor da Promise, e a propriedade escapa dessa análise.
    const controle: { liberar: () => void } = { liberar: () => {} }
    const lenta = new Promise<void>((resolve) => {
      controle.liberar = resolve
    })

    let chamada = 0
    const impl = vi.fn(async (_url: string, init?: RequestInit) => {
      chamada += 1
      if (chamada === 1) {
        await lenta
        // A primeira só termina depois de a segunda ter abortado.
        if (init?.signal?.aborted) throw new DOMException('Aborted', 'AbortError')
        return new Response(JSON.stringify({ results: [sessao('velha')] }), { status: 200 })
      }
      return new Response(JSON.stringify({ results: [sessao('nova')] }), { status: 200 })
    }) as unknown as typeof fetch

    const primeira = refreshHistory({ fetchImpl: impl, now: AGORA })
    const segunda = refreshHistory({ fetchImpl: impl, now: AGORA, force: true })
    await segunda
    controle.liberar()
    await primeira

    expect(useHistoryStore.getState().sessions.map((s) => s.session_id)).toEqual(['nova'])
    // Abortar não é falhar: o aviso de "pode estar velho" não pode acender aqui.
    expect(useHistoryStore.getState().loadError).toBe(false)
  })
})
