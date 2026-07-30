// Passo do funil da SPEC-015: escolher um exercício decide entre Guia (primeiro acesso
// àquele exercício) e Pré-configuração (repetente). Módulo próprio para o arquivo de
// componente exportar só componente (react-refresh).
import { guideSeen, setExercisePreference } from '../session/preferences'
import { navigate } from '../shell/nav'

export function chooseExercise(key: string): void {
  setExercisePreference(key)
  navigate(guideSeen(key) ? { screen: 'preparar' } : { screen: 'guia', exercise: key })
}
