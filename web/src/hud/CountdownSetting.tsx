// Controle da preparação (T-049). Um toque cicla 3 → 5 → 10 → sem preparação → 3.
//
// Mora na capa da câmera, e não numa tela de ajustes, por dois motivos: não existe tela de
// ajustes (a aba Perfil é conta e histórico, SPEC-011), e este é o único instante em que a
// escolha importa — logo antes de treinar. Ajuste escondido em menu é ajuste que ninguém
// muda, e a spec pediu explicitamente que desse para estender ou desligar.
//
// Ciclo em vez de select: são quatro opções e a tela é um celular. Um `<select>` abriria a
// roleta nativa por cima da câmera para escolher entre quatro números.
import { useState } from 'react'
import {
  countdownLabel,
  countdownPreference,
  nextCountdown,
  setCountdownPreference,
} from '../session/preferences'

export function CountdownSetting() {
  const [segundos, setSegundos] = useState(() => countdownPreference())

  return (
    <button
      type="button"
      className="prep-setting"
      onClick={() => setSegundos(setCountdownPreference(nextCountdown(segundos)))}
      aria-label={`Preparação antes de contar: ${countdownLabel(segundos)}. Tocar para mudar.`}
    >
      {countdownLabel(segundos)}
    </button>
  )
}
