// O dono das sessões conhecidas (SPEC-024 §1 / T-121).
//
// Antes desta task havia três verdades para "quanto eu treinei": Progresso lia o
// `digitalfit.last_report` (UMA sessão), Perfil buscava `?mine` **uma vez por login** e
// Analytics não lia nada. Agora há uma; Progresso, Analytics e Perfil são leituras daqui.
//
// Store separado do de conta de propósito: o histórico existe **sem** conta (é o caso da
// maioria de quem usa), e deixá-lo dentro do `account` faria a tela de progresso do visitante
// depender de um estado de autenticação que ela não tem.
import { create } from 'zustand'
import type { SessionReport } from '../report/sessionReport'
import { loadLocalHistory, recordLocalSession } from './localHistory'
import { mergeSessions } from './merge'

/**
 * De onde veio o que está na tela agora.
 *
 * `local` obriga o rótulo honesto ("neste aparelho"): sem conta, limpar o navegador leva o
 * histórico embora, e uma tela que promete permanência que não tem é pior que uma tela vazia.
 */
export type HistorySource = 'local' | 'server'

/**
 * `loading` só aparece quando **não há nada** para mostrar. Revalidação em cima de dado bom é
 * silenciosa (stale-while-revalidate, SPEC-024 §2) — spinner por cima de número certo faz a
 * tela piscar sem informar ninguém.
 */
export type HistoryStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface HistoryState {
  sessions: SessionReport[]
  status: HistoryStatus
  source: HistorySource
  /** epoch ms da última carga do servidor bem-sucedida. É o relógio do debounce da T-122. */
  loadedAt: number | null
  /**
   * A última tentativa de revalidar falhou, mas há dado na tela.
   *
   * Separado do `status` porque são duas perguntas diferentes: "tenho o que mostrar?" e "o que
   * mostro pode estar velho?". Colapsar as duas obrigaria a escolher entre esvaziar a tela e
   * mentir que está tudo fresco.
   */
  loadError: boolean

  /** Boot: lê o aparelho. Sem rede — o primeiro paint não espera ninguém. */
  hydrate: () => void
  /** Fim de sessão: grava no aparelho e entra na lista na hora (SPEC-024 §2). */
  record: (report: SessionReport) => void
  startLoad: () => void
  applyServer: (reports: SessionReport[], at?: number) => void
  failLoad: () => void
  /** Trocou de identidade: o histórico do servidor era de outra pessoa. */
  reset: () => void
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  sessions: [],
  status: 'idle',
  source: 'local',
  loadedAt: null,
  loadError: false,

  hydrate: () => {
    const locais = loadLocalHistory()
    // Não sobrescreve o que o servidor já trouxe: no boot isto roda antes, mas um `hydrate`
    // chamado fora de ordem não pode fazer a lista andar para trás.
    set({ sessions: mergeSessions(locais, get().sessions) })
  },

  record: (report) => {
    const locais = recordLocalSession(report)
    set({ sessions: mergeSessions(locais, get().sessions), status: 'ready' })
  },

  // `loading` só quando a tela está vazia — ver `HistoryStatus`.
  startLoad: () =>
    set({ status: get().sessions.length > 0 ? 'ready' : 'loading', loadError: false }),

  applyServer: (reports, at = Date.now()) =>
    set({
      sessions: mergeSessions(loadLocalHistory(), reports),
      status: 'ready',
      source: 'server',
      loadedAt: at,
      loadError: false,
    }),

  /**
   * Falha **não destrói**: as sessões continuam na tela (SPEC-024, critério 5). Rede ruim não
   * pode zerar o progresso de ninguém, nem visualmente. Só quando não há nada para mostrar é
   * que a falha vira o estado da tela.
   */
  failLoad: () =>
    set({ status: get().sessions.length > 0 ? 'ready' : 'error', loadError: true }),

  reset: () => {
    const locais = loadLocalHistory()
    set({
      sessions: locais,
      status: 'idle',
      source: 'local',
      loadedAt: null,
      loadError: false,
    })
  },
}))
