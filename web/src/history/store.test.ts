import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import type { SessionReport } from '../report/sessionReport'
import { useHistoryStore } from './store'

function sessao(id: string, created_at = '2026-08-05T10:00:00Z', reps = 10) {
  return { session_id: id, created_at, rep_count: reps } as SessionReport
}

beforeEach(() => {
  installStorage()
  useHistoryStore.setState({
    sessions: [],
    status: 'idle',
    source: 'local',
    loadedAt: null,
    loadError: false,
  })
})

afterEach(uninstallStorage)

describe('store do histórico', () => {
  it('a sessão que acabou aparece na hora, sem passar pela rede', () => {
    useHistoryStore.getState().record(sessao('s1'))
    expect(useHistoryStore.getState().sessions.map((s) => s.session_id)).toEqual(['s1'])
    expect(useHistoryStore.getState().status).toBe('ready')
  })

  it('o que foi gravado sobrevive ao boot seguinte (`hydrate` lê o aparelho)', () => {
    useHistoryStore.getState().record(sessao('s1'))
    useHistoryStore.setState({ sessions: [] })
    useHistoryStore.getState().hydrate()
    expect(useHistoryStore.getState().sessions.map((s) => s.session_id)).toEqual(['s1'])
  })

  it('a resposta do servidor absorve o que o aparelho tinha, sem contar duas vezes', () => {
    useHistoryStore.getState().record(sessao('s1', '2026-08-05T10:00:00Z', 8))
    useHistoryStore.getState().applyServer([sessao('s1', '2026-08-05T10:00:00Z', 12)])
    const { sessions, source } = useHistoryStore.getState()
    expect(sessions).toHaveLength(1)
    expect(sessions[0]?.rep_count).toBe(12)
    expect(source).toBe('server')
  })

  // Critério 5: rede fora não pode zerar o progresso de ninguém, nem visualmente.
  it('falha ao revalidar mantém o que estava na tela', () => {
    useHistoryStore.getState().record(sessao('s1'))
    useHistoryStore.getState().startLoad()
    useHistoryStore.getState().failLoad()
    const { sessions, status, loadError } = useHistoryStore.getState()
    expect(sessions).toHaveLength(1)
    expect(status).toBe('ready')
    expect(loadError).toBe(true)
  })

  it('falha com a tela vazia é o único caso em que a falha vira o estado da tela', () => {
    useHistoryStore.getState().startLoad()
    useHistoryStore.getState().failLoad()
    expect(useHistoryStore.getState().status).toBe('error')
  })

  it('revalidar com dado na tela não mostra "carregando" — não pode piscar', () => {
    useHistoryStore.getState().record(sessao('s1'))
    useHistoryStore.getState().startLoad()
    expect(useHistoryStore.getState().status).toBe('ready')
  })

  it('carga bem-sucedida marca a hora — é o relógio do debounce da T-122', () => {
    useHistoryStore.getState().applyServer([sessao('s1')], 1_700_000_000_000)
    expect(useHistoryStore.getState().loadedAt).toBe(1_700_000_000_000)
  })

  it('trocar de identidade devolve o histórico ao que o APARELHO sabe', () => {
    useHistoryStore.getState().record(sessao('meu'))
    useHistoryStore.getState().applyServer([sessao('do-outro', '2026-08-06T10:00:00Z')])
    expect(useHistoryStore.getState().sessions).toHaveLength(2)

    useHistoryStore.getState().reset()
    const { sessions, source, loadedAt } = useHistoryStore.getState()
    expect(sessions.map((s) => s.session_id)).toEqual(['meu'])
    expect(source).toBe('local')
    expect(loadedAt).toBeNull()
  })
})
