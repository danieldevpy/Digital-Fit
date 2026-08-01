// Conta e histórico (SPEC-011 / T-022). Store separado do de sessão de propósito: o treino
// funciona inteiro sem conta, e misturar os dois faria a tela de exercício depender de um
// estado que ela não usa — exatamente o acoplamento que a spec evita ao dizer que o SaaS é
// "adicionado por fora".
import { create } from 'zustand'
import type { AccountUser } from '../auth/api'
import type { SessionReport } from '../report/sessionReport'
import type { QuotaSnapshot } from '../session/quota'

export type AccountStatus = 'unknown' | 'anonymous' | 'authenticated'
export type HistoryStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface AccountState {
  status: AccountStatus
  user: AccountUser | null
  /** Aberto pela aba Perfil. */
  sheetOpen: boolean
  /** Mensagem de erro do formulário (login/cadastro). */
  formError: string | null
  busy: boolean

  /**
   * Quanto da quota de hoje resta. `null` = o servidor ainda não falou (nunca "sem limite").
   *
   * Vale para as duas identidades desde a T-063: o visitante conta por aparelho, a conta Free
   * conta por conta. Era `trial` e só existia para o anônimo — o campo mudou de nome no dia em
   * que o Free ganhou limite, porque um `trial` guardando a quota de quem tem conta seria o
   * convite a criar o segundo campo, e dois campos do mesmo número divergem.
   */
  quota: QuotaSnapshot | null
  /** A última tentativa foi recusada pelo limite diário — a tela explica e oferece a saída. */
  quotaBlocked: boolean

  history: SessionReport[]
  historyStatus: HistoryStatus

  setUser: (user: AccountUser | null) => void
  openSheet: (open: boolean) => void
  setFormError: (message: string | null) => void
  setBusy: (busy: boolean) => void
  setQuota: (quota: QuotaSnapshot | null) => void
  blockByQuota: (quota?: QuotaSnapshot | null) => void
  startHistory: () => void
  applyHistory: (reports: SessionReport[]) => void
  failHistory: () => void
  reset: () => void
}

const DEFAULTS = {
  status: 'unknown' as AccountStatus,
  user: null,
  sheetOpen: false,
  formError: null,
  busy: false,
  quota: null,
  quotaBlocked: false,
  history: [] as SessionReport[],
  historyStatus: 'idle' as HistoryStatus,
}

export const useAccountStore = create<AccountState>((set) => ({
  ...DEFAULTS,

  setUser: (user) =>
    set({
      user,
      status: user ? 'authenticated' : 'anonymous',
      formError: null,
      busy: false,
      // A quota do aparelho não vale para a conta que acabou de entrar, e vice-versa: quem
      // troca de identidade zera o que sabia e pergunta de novo (`AppShell` refaz o pré-voo).
      // Herdar o contador faria a conta nova nascer esgotada por causa do visitante de antes.
      quota: null,
      quotaBlocked: false,
      // O histórico é de quem está logado. Trocar de conta sem limpar mostraria as sessões
      // da pessoa anterior por um instante — curto, mas errado.
      history: [],
      historyStatus: 'idle' as HistoryStatus,
    }),

  openSheet: (sheetOpen) => set({ sheetOpen, formError: null }),
  setFormError: (formError) => set({ formError, busy: false }),
  setBusy: (busy) => set({ busy }),
  // Contador que voltou a ter folga destrava a tela sozinho: é o caso da virada do dia com o
  // app aberto, e o de quem acabou de assinar. Sem isto o bloqueio só sairia recarregando.
  setQuota: (quota) => set({ quota, ...(quota?.allowed ? { quotaBlocked: false } : {}) }),

  blockByQuota: (quota) => set({ quotaBlocked: true, sheetOpen: true, ...(quota ? { quota } : {}) }),

  startHistory: () => set({ historyStatus: 'loading' }),
  applyHistory: (history) => set({ history, historyStatus: 'ready' }),
  failHistory: () => set({ historyStatus: 'error' }),

  reset: () => set({ ...DEFAULTS, status: 'anonymous' }),
}))
