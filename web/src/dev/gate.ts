// Quem pode ver as ferramentas de diagnóstico (T-048).
//
// Este arquivo é o ÚNICO lugar que decide. Antes não havia decisão nenhuma: o chip de dev e o
// gravador de fixtures estavam atrás de `isReady` no `CameraView`, ou seja, qualquer pessoa
// que abrisse o app e ligasse a câmera os via — em produção, no domínio público. O comentário
// no topo do `FixtureControls` já dizia "não faz parte da UI de produto"; o código é que não
// fazia valer.
//
// Duas fontes de direito, nesta ordem:
//
//   1. Build de desenvolvimento (`npm run dev`) — sempre ligado, sem login. Trocar o fluxo
//      local por "crie conta e se promova" seria atrito diário para resolver um problema que
//      só existe em produção.
//   2. Conta com `is_admin` (`GET /api/me`) — é assim que se inspeciona o servidor de
//      produção com o que está de pé lá. Quem concede é o `manage.py admin_tools`, que exige
//      shell na máquina: nenhuma rota da API aceita o campo, então não há como se promover
//      pela web.
//
// O `?dev=` só MODIFICA um direito que já existe; nunca concede. `?dev=0` desliga (é como o
// admin vê a tela exatamente como o usuário comum a vê, sem deslogar), e `?dev=1` sozinho não
// faz nada para quem não é admin — senão o gate seria decoração.
//
// `?record=1` (T-129) é a TERCEIRA posição, e existe porque as duas anteriores não serviam para
// gravar material do produto: com as ferramentas ligadas dá para entrar com um vídeo em arquivo
// (T-040), mas a tela ganha o chip de diagnóstico, o gravador de fixtures e o texto de erro que
// manda subir a stack — nada disso pode aparecer numa gravação. Com elas desligadas (`?dev=0`) a
// tela é a do produto, mas só a câmera entra. O modo gravação separa as duas coisas que estavam
// coladas: **a origem de vídeo continua liberada, o diagnóstico não**. Vale a mesma regra de
// sempre — modifica um direito, nunca concede: `?record=1` na mão de quem não é admin é inerte.
import { useAccountStore } from '../store/account'

/** `?dev=0` desliga, `?dev=1` liga (para quem já teria direito), ausente não opina. */
function override(search: string): boolean | null {
  const valor = new URLSearchParams(search).get('dev')
  if (valor === null) return null
  return valor !== '0' && valor !== 'false'
}

/** `?record=1` pedido na URL. Pedido, não direito: quem concede continua sendo o `is_admin`. */
function recordPedido(search: string): boolean {
  const valor = new URLSearchParams(search).get('record')
  if (valor === null) return false
  return valor !== '0' && valor !== 'false'
}

export interface GateInput {
  /** Build de desenvolvimento (`import.meta.env.DEV`). */
  isDevBuild: boolean
  /** A conta logada tem as ferramentas liberadas. */
  isAdmin: boolean
  /** A query string da URL, incluindo o `?`. */
  search: string
}

/** Puro, para ser testável sem navegador nem store. */
export function devToolsAllowed({ isDevBuild, isAdmin, search }: GateInput): boolean {
  const direito = isDevBuild || isAdmin
  if (override(search) === false) return false
  // Gravando, o diagnóstico sai de cena — é o ponto do modo. Aqui, e não em cada componente:
  // esconder o chip mas deixar o texto de erro de dev vazar seria a mesma tela vazando por
  // outro buraco.
  if (recordPedido(search)) return false
  return direito
}

/**
 * Modo gravação: a interface do usuário comum, com a origem de vídeo em arquivo liberada.
 *
 * Mesmo direito das ferramentas de dev (build local ou `is_admin`), e o `?dev=0` continua sendo
 * o desligador geral — quem pede a tela limpa de verdade não quer nem o botão de escolher o
 * arquivo no meio dela.
 */
export function recordModeAllowed({ isDevBuild, isAdmin, search }: GateInput): boolean {
  if (!recordPedido(search)) return false
  if (override(search) === false) return false
  return isDevBuild || isAdmin
}

function ambiente(isAdmin: boolean): GateInput {
  return {
    isDevBuild: import.meta.env.DEV,
    isAdmin,
    search: typeof window === 'undefined' ? '' : window.location.search,
  }
}

/** A decisão, para quem não está num componente. */
export function devToolsEnabled(): boolean {
  return devToolsAllowed(ambiente(useAccountStore.getState().user?.is_admin === true))
}

/**
 * Versão reativa: o `GET /api/me` responde DEPOIS do primeiro render, então um valor lido uma
 * vez só deixaria o admin sem ferramentas até recarregar a página.
 */
export function useDevTools(): boolean {
  const isAdmin = useAccountStore((state) => state.user?.is_admin === true)
  return devToolsAllowed(ambiente(isAdmin))
}

/** Idem para o modo gravação — o `is_admin` chega tarde do mesmo jeito. */
export function useRecordMode(): boolean {
  const isAdmin = useAccountStore((state) => state.user?.is_admin === true)
  return recordModeAllowed(ambiente(isAdmin))
}
