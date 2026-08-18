// Controle da preparação (T-049). Um toque cicla 3 → 5 → 10 → sem preparação → 3.
//
// Mora na capa da câmera, e não numa tela de ajustes, por dois motivos: não existe tela de
// ajustes (a aba Perfil é conta e histórico, SPEC-011), e este é o único instante em que a
// escolha importa — logo antes de treinar. Ajuste escondido em menu é ajuste que ninguém
// muda, e a spec pediu explicitamente que desse para estender ou desligar.
//
// Ciclo em vez de select: são quatro opções e a tela é um celular. Um `<select>` abriria a
// roleta nativa por cima da câmera para escolher entre quatro números.
//
// Virou card (mesmo `.prep-cell` do Zoom e do Ângulo) para não destoar da coluna: era o único
// controle em formato de pílula no meio de uma grade de cartões. Os pontinhos por baixo do
// valor mostram as quatro paradas do ciclo — o mesmo toque avança para a próxima, e agora dá
// para ver isso antes mesmo de tocar.
import { useState } from 'react'
import { useT } from '../i18n'
import {
  COUNTDOWN_OPTIONS,
  countdownLabel,
  countdownPreference,
  nextCountdown,
  setCountdownPreference,
} from '../session/preferences'
import { IconTimer } from '../ui/icons'

export function CountdownSetting() {
  const t = useT()
  const [segundos, setSegundos] = useState(() => countdownPreference())
  // Curto porque a célula tem 92 px: "Off" e "3s" cabem, "sem preparação" não. O balde `.zero`
  // do dicionário é que decide qual dos dois sai — a mesma máquina do `countdownLabel`, com
  // outra chave.
  const curto = t('session:countdown.short', { n: segundos })

  return (
    <button
      type="button"
      className="prep-cell prep-cell--action"
      onClick={() => setSegundos(setCountdownPreference(nextCountdown(segundos)))}
      aria-label={t('session:countdown.aria', { value: countdownLabel(segundos) })}
    >
      <p className="v2-label">{t('session:countdown.label')}</p>
      <p className="prep-cell__value prep-cell__value--sm tabular">
        <IconTimer className="prep-cell__hud-icon prep-cell__hud-icon--cyan" /> {curto}
      </p>
      <span className="prep-cell__dots" aria-hidden="true">
        {COUNTDOWN_OPTIONS.map((opcao) => (
          <span key={opcao} className={`prep-cell__dot ${opcao === segundos ? 'prep-cell__dot--on' : ''}`} />
        ))}
      </span>
    </button>
  )
}
