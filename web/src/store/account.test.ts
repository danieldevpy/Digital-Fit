import { beforeEach, describe, expect, it } from 'vitest'

import { useHistoryStore } from '../history/store'
import type { SessionReport } from '../report/sessionReport'
import type { QuotaSnapshot } from '../session/quota'
import { useAccountStore } from './account'

/** Quota de conta Free com folga; os testes sobrescrevem o que interessa a cada um. */
function quota(campos: Partial<QuotaSnapshot> = {}): QuotaSnapshot {
  return {
    used: 1,
    limit: 10,
    remaining: 9,
    unlimited: false,
    allowed: true,
    resets_at: '2026-08-01T00:00:00Z',
    plan: 'free',
    plan_name: 'Free',
    message: 'Você treinou muito hoje 🎉',
    ...campos,
  }
}

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
    store.setUser({ id: 1, email: 'a@b.com', name: 'Ana', is_admin: false, date_joined: '2026-07-29T10:00:00Z' })

    const depois = useAccountStore.getState()
    expect(depois.status).toBe('authenticated')
    expect(depois.formError).toBeNull()
    expect(depois.busy).toBe(false)
  })

  it('entrar não herda a quota do visitante — nem o número, nem o bloqueio', () => {
    const store = useAccountStore.getState()
    store.setQuota(quota({ plan: 'anon', used: 3, limit: 3, remaining: 0, allowed: false }))
    store.blockByQuota()
    store.setUser({ id: 1, email: 'a@b.com', name: '', is_admin: false, date_joined: '2026-07-29T10:00:00Z' })

    // A conta nova nasceria esgotada por causa do visitante de antes — e a conta é justamente
    // o upgrade que se oferece a ele.
    expect(useAccountStore.getState().quota).toBeNull()
    expect(useAccountStore.getState().quotaBlocked).toBe(false)
  })

  it('trocar de conta não deixa o histórico da pessoa anterior na tela', () => {
    // O histórico mudou de dono na T-121 (`history/store.ts`), mas a regra continua sendo do
    // store de conta: quem troca de identidade não pode ver as sessões de quem estava antes.
    useHistoryStore.getState().applyServer([RELATORIO])
    useAccountStore
      .getState()
      .setUser({ id: 2, email: 'c@d.com', name: '', is_admin: false, date_joined: '2026-07-29T10:00:00Z' })

    expect(useHistoryStore.getState().sessions).toEqual([])
    // De volta a `idle` para a tela buscar de novo — em nome de quem entrou agora.
    expect(useHistoryStore.getState().status).toBe('idle')
    expect(useHistoryStore.getState().source).toBe('local')
  })

  it('sair volta a ser visitante, não "não sei"', () => {
    useAccountStore
      .getState()
      .setUser({ id: 1, email: 'a@b.com', name: 'Ana', is_admin: false, date_joined: '2026-07-29T10:00:00Z' })
    useAccountStore.getState().reset()

    const depois = useAccountStore.getState()
    expect(depois.status).toBe('anonymous')
    expect(depois.user).toBeNull()
  })
})

describe('quota diária', () => {
  it('recusa por limite abre a tela de conta sozinha', () => {
    expect(useAccountStore.getState().sheetOpen).toBe(false)
    useAccountStore.getState().blockByQuota()

    const depois = useAccountStore.getState()
    expect(depois.sheetOpen).toBe(true)
    expect(depois.quotaBlocked).toBe(true)
  })

  it('a recusa traz o contador junto, para o sheet não precisar perguntar de novo', () => {
    useAccountStore.getState().blockByQuota(quota({ used: 10, remaining: 0, allowed: false }))

    expect(useAccountStore.getState().quota?.used).toBe(10)
  })

  it('contador com folga destrava a tela — é a virada do dia com o app aberto', () => {
    useAccountStore.getState().blockByQuota()
    useAccountStore.getState().setQuota(quota({ used: 1, remaining: 9, allowed: true }))

    expect(useAccountStore.getState().quotaBlocked).toBe(false)
  })

  it('sessão que gastou a última NÃO destrava', () => {
    useAccountStore.getState().blockByQuota()
    useAccountStore.getState().setQuota(quota({ used: 10, remaining: 0, allowed: false }))

    expect(useAccountStore.getState().quotaBlocked).toBe(true)
  })

  it('plano ilimitado nunca bloqueia', () => {
    useAccountStore.getState().blockByQuota()
    useAccountStore.getState().setQuota(quota({ plan: 'subscriber', limit: 0, unlimited: true }))

    expect(useAccountStore.getState().quotaBlocked).toBe(false)
  })

  it('fechar a tela não apaga o motivo do bloqueio', () => {
    useAccountStore.getState().blockByQuota()
    useAccountStore.getState().openSheet(false)

    expect(useAccountStore.getState().quotaBlocked).toBe(true)
  })
})

describe('histórico', () => {
  // A máquina de estados do histórico mudou de arquivo na T-121 e é testada em
  // `history/store.test.ts`. O que ficou sendo responsabilidade DESTE store é só a linha
  // acima ("trocar de conta não deixa o histórico da pessoa anterior na tela"): o histórico
  // existe sem conta, e por isso não mora mais aqui.
  it('sair da conta devolve o histórico ao que o aparelho sabe', () => {
    useHistoryStore.getState().applyServer([RELATORIO])
    useAccountStore.getState().reset()
    expect(useHistoryStore.getState().sessions).toEqual([])
    expect(useHistoryStore.getState().source).toBe('local')
  })
})
