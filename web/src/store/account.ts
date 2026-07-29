// Conta e histórico (SPEC-011 / T-022). Store separado do de sessão de propósito: o treino
// funciona inteiro sem conta, e misturar os dois faria a tela de exercício depender de um
// estado que ela não usa — exatamente o acoplamento que a spec evita ao dizer que o SaaS é
// "adicionado por fora".
import { create } from 'zustand'
import type { AccountUser } from '../auth/api'
import type { SessionReport } from '../report/sessionReport'
import type { TrialStatus } from '../session/admission'

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

  /** Quanto do trial anônimo resta hoje; `null` para quem tem conta. */
  trial: TrialStatus | null
  /** A última sessão foi recusada por trial esgotado — a tela convida a criar conta. */
  trialBlocked: boolean

  history: SessionReport[]
  historyStatus: HistoryStatus

  setUser: (user: AccountUser | null) => void
  openSheet: (open: boolean) => void
  setFormError: (message: string | null) => void
  setBusy: (busy: boolean) => void
  setTrial: (trial: TrialStatus | null) => void
  blockByTrial: () => void
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
  trial: null,
  trialBlocked: false,
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
      // Quem entrou não tem trial a exibir: a conta É o upgrade nesta fase.
      ...(user ? { trial: null, trialBlocked: false } : {}),
      // O histórico é de quem está logado. Trocar de conta sem limpar mostraria as sessões
      // da pessoa anterior por um instante — curto, mas errado.
      history: [],
      historyStatus: 'idle' as HistoryStatus,
    }),

  openSheet: (sheetOpen) => set({ sheetOpen, formError: null }),
  setFormError: (formError) => set({ formError, busy: false }),
  setBusy: (busy) => set({ busy }),
  setTrial: (trial) => set({ trial, ...(trial && trial.remaining > 0 ? { trialBlocked: false } : {}) }),

  blockByTrial: () => set({ trialBlocked: true, sheetOpen: true }),

  startHistory: () => set({ historyStatus: 'loading' }),
  applyHistory: (history) => set({ history, historyStatus: 'ready' }),
  failHistory: () => set({ historyStatus: 'error' }),

  reset: () => set({ ...DEFAULTS, status: 'anonymous' }),
}))
