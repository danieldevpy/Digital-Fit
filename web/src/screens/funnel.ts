// Passo do funil da SPEC-015: escolher um exercício decide entre Guia (primeiro acesso
// àquele exercício) e Pré-configuração (repetente). Módulo próprio para o arquivo de
// componente exportar só componente (react-refresh).
import { guideSeen, setExercisePreference } from '../session/preferences'
import { navigate } from '../shell/nav'

/**
 * `replace` serve à ponte `#/ex/<slug>` do site (T-067): ali a escolha não foi um toque
 * nesta tela, e a ponte não deve sobrar no histórico.
 */
export function chooseExercise(key: string, { replace = false }: { replace?: boolean } = {}): void {
  setExercisePreference(key)
  navigate(guideSeen(key) ? { screen: 'preparar' } : { screen: 'guia', exercise: key }, { replace })
}
