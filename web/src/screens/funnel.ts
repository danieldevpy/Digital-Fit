// Passo do funil da SPEC-015: trocar de exercício decide entre Guia e Pré-configuração.
// Módulo próprio para o arquivo de componente exportar só componente (react-refresh).
//
// **Quem decide não é mais o `guide_seen`, é a identidade** — o porquê está inteiro no
// `session/guideGate.ts`. Aqui fica só a navegação.
import { estadoDoExemplo, temConta } from '../session/guideGate'
import { guideSeen, setExercisePreference } from '../session/preferences'
import { navigate } from '../shell/nav'
import { useAccountStore } from '../store/account'

/**
 * `replace` serve à ponte `#/ex/<slug>` do site (T-067): ali a escolha não foi um toque
 * nesta tela, e a ponte não deve sobrar no histórico.
 */
export function chooseExercise(key: string, { replace = false }: { replace?: boolean } = {}): void {
  setExercisePreference(key)
  // `getState()` e não hook: isto é chamado de dentro de um `onClick` e de um efeito de boot,
  // não durante render.
  const { abrirAgora } = estadoDoExemplo({
    temConta: temConta(useAccountStore.getState().status),
    jaViu: guideSeen(key),
  })
  navigate(abrirAgora ? { screen: 'guia', exercise: key } : { screen: 'preparar' }, { replace })
}
