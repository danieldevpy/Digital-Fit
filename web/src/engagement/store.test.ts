import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAccountStore } from '../store/account'
import type { Engagement } from './api'
import { engagementIsFresh, FRESH_MS, refreshEngagement, useEngagementStore } from './store'

const PAYLOAD: Engagement = {
  streak: 3,
  best_streak: 9,
  protections_used_month: 1,
  protections_month: 2,
  today_active: true,
  sessions_today: 1,
  goal: 'casual',
  goal_target: 1,
  goal_done_today: true,
  xp: 120,
  xp_formula_v: 1,
  level: { number: 2, xp_min: 100, xp_next: 300, progress: 0.1 },
}

const USUARIO = {
  id: 1,
  email: 'a@b.com',
  name: 'Ana',
  is_admin: false,
  daily_goal: 'casual',
  date_joined: '2026-07-01',
}

function fetchQueResponde(corpo: unknown, status = 200) {
  const chamadas: string[] = []
  const impl = vi.fn(async (url: string) => {
    chamadas.push(url)
    return new Response(JSON.stringify(corpo), {
      status,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  return { impl: impl as unknown as typeof fetch, chamadas }
}

beforeEach(() => {
  useEngagementStore.setState({ data: null, loadedAt: null, loading: false, sheetOpen: false })
  useAccountStore.setState({ user: null, status: 'anonymous' })
})

describe('refreshEngagement', () => {
  it('sem conta não busca nada — o visitante tem fogo fantasma, não payload', async () => {
    const { impl, chamadas } = fetchQueResponde(PAYLOAD)

    await refreshEngagement({ fetchImpl: impl })

    expect(chamadas).toHaveLength(0)
    expect(useEngagementStore.getState().data).toBeNull()
  })

  it('sair da conta zera o fogo do servidor — era o número de outra pessoa', async () => {
    useEngagementStore.setState({ data: PAYLOAD, loadedAt: Date.now() })
    const { impl } = fetchQueResponde(PAYLOAD)

    await refreshEngagement({ fetchImpl: impl })

    expect(useEngagementStore.getState().data).toBeNull()
  })

  it('com conta, busca e guarda', async () => {
    useAccountStore.setState({ user: USUARIO, status: 'authenticated' })
    const { impl, chamadas } = fetchQueResponde(PAYLOAD)

    await refreshEngagement({ fetchImpl: impl, now: 1_000 })

    expect(chamadas[0]).toMatch(/\/api\/engagement$/)
    expect(useEngagementStore.getState().data?.streak).toBe(3)
    expect(useEngagementStore.getState().loadedAt).toBe(1_000)
  })

  it('dado fresco não vira requisição — foco é barato de ganhar', async () => {
    useAccountStore.setState({ user: USUARIO, status: 'authenticated' })
    useEngagementStore.setState({ data: PAYLOAD, loadedAt: 1_000 })
    const { impl, chamadas } = fetchQueResponde(PAYLOAD)

    await refreshEngagement({ fetchImpl: impl, now: 1_000 + FRESH_MS - 1 })

    expect(chamadas).toHaveLength(0)
  })

  it('`force` ignora o debounce — é o fim de sessão, fato novo e não suspeita', async () => {
    useAccountStore.setState({ user: USUARIO, status: 'authenticated' })
    useEngagementStore.setState({ data: PAYLOAD, loadedAt: 1_000 })
    const { impl, chamadas } = fetchQueResponde(PAYLOAD)

    await refreshEngagement({ fetchImpl: impl, now: 1_001, force: true })

    expect(chamadas).toHaveLength(1)
  })

  it('falha mantém o que já estava na tela', async () => {
    useAccountStore.setState({ user: USUARIO, status: 'authenticated' })
    useEngagementStore.setState({ data: PAYLOAD, loadedAt: 1 })
    const { impl } = fetchQueResponde({ detail: 'fora do ar' }, 503)

    await refreshEngagement({ fetchImpl: impl, force: true })

    expect(useEngagementStore.getState().data?.streak).toBe(3)
    expect(useEngagementStore.getState().loading).toBe(false)
  })
})

describe('engagementIsFresh', () => {
  it('nunca carregado não é fresco', () => {
    expect(engagementIsFresh()).toBe(false)
  })

  it('a janela é a mesma do histórico', () => {
    useEngagementStore.setState({ loadedAt: 1_000 })

    expect(engagementIsFresh(1_000 + FRESH_MS - 1)).toBe(true)
    expect(engagementIsFresh(1_000 + FRESH_MS)).toBe(false)
  })
})
