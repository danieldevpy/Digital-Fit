import { beforeEach, describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import { useAccountStore } from './account'

const RELATORIO = { session_id: 's1', rep_count: 20 } as SessionReport

beforeEach(() => {
  useAccountStore.getState().reset()
  useAccountStore.setState({ status: 'unknown' })
})

describe('estado da conta', () => {
  it('começa sem saber quem é — a resposta do `/api/me` é que decide', () => {
    expect(useAccountStore.getState().status).toBe('unknown')
  })

  it('entrar limpa o erro do formulário e destrava o botão', () => {
    const store = useAccountStore.getState()
    store.setFormError('E-mail ou senha inválidos.')
    store.setBusy(true)
    store.setUser({ id: 1, email: 'a@b.com', name: 'Ana', date_joined: '2026-07-29T10:00:00Z' })

    const depois = useAccountStore.getState()
    expect(depois.status).toBe('authenticated')
    expect(depois.formError).toBeNull()
    expect(depois.busy).toBe(false)
  })

  it('quem entrou não vê mais aviso de trial', () => {
    const store = useAccountStore.getState()
    store.setTrial({ used: 3, limit: 3, remaining: 0 })
    store.blockByTrial()
    store.setUser({ id: 1, email: 'a@b.com', name: '', date_joined: '2026-07-29T10:00:00Z' })

    expect(useAccountStore.getState().trial).toBeNull()
    expect(useAccountStore.getState().trialBlocked).toBe(false)
  })

  it('trocar de conta não deixa o histórico da pessoa anterior na tela', () => {
    useAccountStore.getState().applyHistory([RELATORIO])
    useAccountStore
      .getState()
      .setUser({ id: 2, email: 'c@d.com', name: '', date_joined: '2026-07-29T10:00:00Z' })

    expect(useAccountStore.getState().history).toEqual([])
    // De volta a `idle` para a tela buscar de novo — em nome de quem entrou agora.
    expect(useAccountStore.getState().historyStatus).toBe('idle')
  })

  it('sair volta a ser visitante, não "não sei"', () => {
    useAccountStore
      .getState()
      .setUser({ id: 1, email: 'a@b.com', name: 'Ana', date_joined: '2026-07-29T10:00:00Z' })
    useAccountStore.getState().reset()

    const depois = useAccountStore.getState()
    expect(depois.status).toBe('anonymous')
    expect(depois.user).toBeNull()
  })
})

describe('trial', () => {
  it('recusa por trial abre a tela de conta sozinha', () => {
    expect(useAccountStore.getState().sheetOpen).toBe(false)
    useAccountStore.getState().blockByTrial()

    const depois = useAccountStore.getState()
    expect(depois.sheetOpen).toBe(true)
    expect(depois.trialBlocked).toBe(true)
  })

  it('uma sessão que entrou depois do bloqueio desfaz o aviso', () => {
    useAccountStore.getState().blockByTrial()
    useAccountStore.getState().setTrial({ used: 1, limit: 3, remaining: 2 })

    expect(useAccountStore.getState().trialBlocked).toBe(false)
  })

  it('sessão que entrou gastando a última NÃO desfaz o aviso', () => {
    useAccountStore.getState().blockByTrial()
    useAccountStore.getState().setTrial({ used: 3, limit: 3, remaining: 0 })

    expect(useAccountStore.getState().trialBlocked).toBe(true)
  })

  it('fechar a tela não apaga o motivo do bloqueio', () => {
    useAccountStore.getState().blockByTrial()
    useAccountStore.getState().openSheet(false)

    expect(useAccountStore.getState().trialBlocked).toBe(true)
  })
})

describe('histórico', () => {
  it('percorre idle → loading → ready', () => {
    expect(useAccountStore.getState().historyStatus).toBe('idle')
    useAccountStore.getState().startHistory()
    expect(useAccountStore.getState().historyStatus).toBe('loading')
    useAccountStore.getState().applyHistory([RELATORIO])
    expect(useAccountStore.getState().historyStatus).toBe('ready')
    expect(useAccountStore.getState().history).toHaveLength(1)
  })

  it('falha não trava em "carregando"', () => {
    useAccountStore.getState().startHistory()
    useAccountStore.getState().failHistory()
    expect(useAccountStore.getState().historyStatus).toBe('error')
  })
})
