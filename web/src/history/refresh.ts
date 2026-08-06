// Quem manda o histórico ir buscar (SPEC-024 §1 / T-121).
//
// Fica fora do store pelo motivo de sempre nesta base: o store guarda estado, isto conhece
// **identidade e rede**. Sem esta fronteira o store de histórico importaria o de conta e a API,
// e um teste de merge precisaria de `fetch`.
//
// A T-122 acrescenta os gatilhos (foco, `visibilitychange`, fim de sessão) em cima daqui —
// esta função continua sendo a única porta.
import { fetchHistory } from '../auth/api'
import { useAccountStore } from '../store/account'
import { useHistoryStore } from './store'

/**
 * Traz o histórico do servidor quando há conta.
 *
 * Sem conta não há o que buscar: `GET /api/sessions?mine` responde 401 por construção
 * (`server/api/views.py`), e o aparelho já é a fonte. Por isso o visitante sai daqui em
 * `ready` — o `hydrate` do boot já pôs na tela tudo o que existe sobre ele.
 */
export async function refreshHistory(): Promise<void> {
  const { status } = useAccountStore.getState()
  const store = useHistoryStore.getState()

  if (status !== 'authenticated') {
    store.hydrate()
    return
  }

  store.startLoad()
  try {
    const sessoes = await fetchHistory()
    useHistoryStore.getState().applyServer(sessoes)
  } catch {
    // Silencioso de propósito: falhar em atualizar não é um erro na cara de quem só queria ver
    // o próprio progresso. O store guarda o `loadError` e a tela decide o quanto dizer.
    useHistoryStore.getState().failLoad()
  }
}
