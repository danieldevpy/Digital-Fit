// O fogo do servidor, guardado (SPEC-019 / T-088).
//
// Store separado do de histórico porque a fonte é outra: o histórico vem de
// `GET /api/sessions?mine` e existe sem conta; isto vem de `GET /api/engagement` e **só existe
// com conta**. Juntar os dois faria o visitante carregar um estado que nunca vai preencher.
//
// O frescor segue o mesmo contrato da SPEC-024 §2 que o histórico já usa (T-122): revalida ao
// entrar na tela, ao a página voltar a ficar visível, e **na hora** que uma sessão termina —
// este último ignorando o debounce, porque ali existe um fato novo e não uma suspeita.
import { create } from 'zustand'
import { useAccountStore } from '../store/account'
import { novasConquistas } from './achievements'
import type { Achievement, Engagement } from './api'
import { fetchEngagement } from './api'

/** Mesma janela do histórico, e pelo mesmo motivo: foco é barato de ganhar. */
export const FRESH_MS = 30_000

export interface EngagementState {
  data: Engagement | null
  loadedAt: number | null
  loading: boolean
  /** Painel aberto pelo toque no chip. Sheet e não rota, como a AccountSheet (SPEC-019). */
  sheetOpen: boolean
  /**
   * Conquistas ganhas que ainda não foram avisadas (T-089).
   *
   * A fila mora **aqui, e não num efeito do toast**, porque o diff pertence ao instante em que
   * o dado chega: o toast pode nem estar montado (o painel fechado, outra tela aberta) e a
   * conquista não pode se perder por causa disso. É também o que a regra `set-state-in-effect`
   * do lint cobra — e ela está certa: escrever no `localStorage` é sincronizar com sistema
   * externo, e isso não é trabalho de renderização.
   */
  novas: Achievement[]
  apply: (data: Engagement, at?: number) => void
  /** O toast consumiu a primeira da fila. */
  dispensarNova: () => void
  start: () => void
  fail: () => void
  openSheet: (open: boolean) => void
  /** Trocou de identidade: o fogo do servidor era de outra pessoa. */
  reset: () => void
}

export const useEngagementStore = create<EngagementState>((set) => ({
  data: null,
  loadedAt: null,
  loading: false,
  sheetOpen: false,
  novas: [],
  apply: (data, at = Date.now()) =>
    set((estado) => ({
      data,
      loadedAt: at,
      loading: false,
      novas: [...estado.novas, ...novasConquistas(data.achievements ?? [])],
    })),
  dispensarNova: () => set((estado) => ({ novas: estado.novas.slice(1) })),
  start: () => set({ loading: true }),
  // Falha mantém o dado anterior: número certo e velho é melhor que tela vazia (SPEC-024 §2).
  fail: () => set({ loading: false }),
  openSheet: (sheetOpen) => set({ sheetOpen }),
  // O painel NÃO fecha aqui: trocar de conta com o painel aberto deve trocar o conteúdo, não
  // sumir com a tela debaixo do dedo de quem acabou de se cadastrar.
  reset: () => set({ data: null, loadedAt: null, loading: false, novas: [] }),
}))

export function engagementIsFresh(agora: number = Date.now()): boolean {
  const { loadedAt } = useEngagementStore.getState()
  return loadedAt !== null && agora - loadedAt < FRESH_MS
}

export interface RefreshOptions {
  /** Ignora o debounce. É o fim de sessão — fato novo, não suspeita. */
  force?: boolean
  now?: number
  fetchImpl?: typeof fetch
}

/**
 * Busca o engajamento se fizer sentido buscar.
 *
 * Sem conta não há o que buscar, e o store é zerado: o visitante vê o fogo fantasma, derivado
 * do histórico local (`engagement/fire.ts`), e um payload de servidor sobrando no store seria o
 * número de outra pessoa esperando para aparecer.
 */
export async function refreshEngagement(options: RefreshOptions = {}): Promise<void> {
  const { force = false, now = Date.now(), fetchImpl = fetch } = options

  if (useAccountStore.getState().user === null) {
    if (useEngagementStore.getState().data !== null) useEngagementStore.getState().reset()
    return
  }
  if (!force && engagementIsFresh(now)) return

  useEngagementStore.getState().start()
  const dados = await fetchEngagement(fetchImpl)
  if (dados === null) {
    useEngagementStore.getState().fail()
    return
  }
  useEngagementStore.getState().apply(dados, now)
}
