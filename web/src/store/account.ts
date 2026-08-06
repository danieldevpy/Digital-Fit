// Conta e histórico (SPEC-011 / T-022). Store separado do de sessão de propósito: o treino
// funciona inteiro sem conta, e misturar os dois faria a tela de exercício depender de um
// estado que ela não usa — exatamente o acoplamento que a spec evita ao dizer que o SaaS é
// "adicionado por fora".
//
// **O histórico não mora mais aqui** (T-121): ele existe sem conta, e guardá-lo neste store
// obrigava a tela de progresso do visitante a depender de um estado de autenticação que ela
// não usa. O dono passou a ser o `history/store.ts`; o que sobrou aqui é identidade e quota.
import { create } from 'zustand'
import { useHistoryStore } from '../history/store'
import type { AccountUser } from '../auth/api'
import type { QuotaSnapshot } from '../session/quota'

export type AccountStatus = 'unknown' | 'anonymous' | 'authenticated'

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

  setUser: (user: AccountUser | null) => void
  openSheet: (open: boolean) => void
  setFormError: (message: string | null) => void
  setBusy: (busy: boolean) => void
  setQuota: (quota: QuotaSnapshot | null) => void
  blockByQuota: (quota?: QuotaSnapshot | null) => void
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
}

export const useAccountStore = create<AccountState>((set) => ({
  ...DEFAULTS,

  setUser: (user) => {
    // O histórico do servidor era de quem estava antes. Trocar de identidade sem devolvê-lo ao
    // que o APARELHO sabe mostraria as sessões da pessoa anterior por um instante — curto, mas
    // errado. `reset` do histórico não apaga nada: ele recai no local, que é de todo mundo que
    // usou este aparelho, e o `refreshHistory` traz as do servidor logo em seguida.
    useHistoryStore.getState().reset()
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
    })
  },

  openSheet: (sheetOpen) => set({ sheetOpen, formError: null }),
  setFormError: (formError) => set({ formError, busy: false }),
  setBusy: (busy) => set({ busy }),
  // Contador que voltou a ter folga destrava a tela sozinho: é o caso da virada do dia com o
  // app aberto, e o de quem acabou de assinar. Sem isto o bloqueio só sairia recarregando.
  setQuota: (quota) => set({ quota, ...(quota?.allowed ? { quotaBlocked: false } : {}) }),

  blockByQuota: (quota) => set({ quotaBlocked: true, sheetOpen: true, ...(quota ? { quota } : {}) }),

  reset: () => {
    useHistoryStore.getState().reset()
    set({ ...DEFAULTS, status: 'anonymous' })
  },
}))
