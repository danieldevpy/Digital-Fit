// Quando o histórico vai buscar (SPEC-024 §2 / T-121, T-122).
//
// Fica fora do store pelo motivo de sempre nesta base: o store guarda estado, isto conhece
// **identidade e rede**. Sem essa fronteira um teste de merge precisaria de `fetch`.
//
// O contrato de frescor da spec em uma frase: **toda tela de dado acumulado revalida ao ganhar
// foco**, e "ganhar foco" é entrar na tela, a página voltar a ficar visível, ou uma sessão
// terminar. Os dois primeiros passam pelo debounce; o terceiro não, porque ali existe um fato
// novo e não uma suspeita.
import { fetchHistory } from '../auth/api'
import { useAccountStore } from '../store/account'
import { useHistoryStore } from './store'

/**
 * Janela em que um foco novo não vale uma requisição.
 *
 * Existe porque foco é barato de ganhar: quem alterna entre abas, ou entre Progresso e
 * Analytics, ganharia foco várias vezes por minuto e viraria rajada em cima de um dado que só
 * muda quando a própria pessoa treina — e esse caso tem gatilho próprio, que ignora esta
 * janela. 30 s é curto o bastante para ninguém ver número velho e longo o bastante para o
 * vai-e-vem entre abas não custar nada.
 */
export const FRESH_MS = 30_000

/** Requisição em voo. Módulo, não store: é detalhe de rede, não estado de tela. */
let emVoo: AbortController | null = null

/** O que está na tela foi carregado agora há pouco? */
export function historyIsFresh(agora: number = Date.now()): boolean {
  const { loadedAt } = useHistoryStore.getState()
  return loadedAt !== null && agora - loadedAt < FRESH_MS
}

export interface RefreshOptions {
  /**
   * Ignora o debounce. É o fim de sessão (SPEC-024 §2): ali houve um fato novo, e esperar 30 s
   * para mostrá-lo é exatamente a queixa que originou a spec.
   */
  force?: boolean
  now?: number
  fetchImpl?: typeof fetch
}

/**
 * Traz o histórico do servidor quando há conta.
 *
 * Sem conta não há o que buscar: `GET /api/sessions?mine` responde 401 por construção
 * (`server/api/views.py`), e o aparelho já é a fonte. Por isso o visitante sai daqui pelo
 * `hydrate` — o que existe sobre ele já está no `localStorage`.
 */
export async function refreshHistory(options: RefreshOptions = {}): Promise<void> {
  const agora = options.now ?? Date.now()
  const { status } = useAccountStore.getState()

  if (status !== 'authenticated') {
    useHistoryStore.getState().hydrate()
    return
  }
  if (!options.force && historyIsFresh(agora)) return

  // Um pedido novo cancela o anterior. Não é economia: é o que impede a resposta lenta de
  // pousar por cima da recente e fazer a tela voltar no tempo.
  emVoo?.abort()
  const controlador = new AbortController()
  emVoo = controlador

  useHistoryStore.getState().startLoad()
  try {
    const sessoes = await fetchHistory(options.fetchImpl ?? fetch, controlador.signal)
    // Abortado enquanto a resposta vinha: quem manda na tela é o pedido que o substituiu.
    if (controlador.signal.aborted) return
    useHistoryStore.getState().applyServer(sessoes, agora)
  } catch {
    // Pedido substituído não é falha — marcar `loadError` aqui acenderia o aviso de "pode
    // estar velho" justamente no instante em que um dado mais novo está a caminho.
    if (controlador.signal.aborted) return
    useHistoryStore.getState().failLoad()
  } finally {
    if (emVoo === controlador) emVoo = null
  }
}

/** Só os testes precisam disto: o controlador em voo é estado de módulo. */
export function resetRefreshForTests(): void {
  emVoo = null
}
