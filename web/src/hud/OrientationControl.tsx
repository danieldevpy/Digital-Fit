// Botão de virar a tela (SPEC-027 §F).
//
// Existe porque a detecção automática tem um buraco real e comum: celular com a **rotação de
// tela travada**. Ali virar o aparelho não muda a viewport, a consulta de mídia não dispara, e
// o app segue desenhando retrato para quem está segurando deitado.
//
// E o botão não finge que resolveu tudo. Nesse mesmo aparelho **o quadro da câmera também não
// girou** — o mundo chega deitado, e é a leitura do exercício que sofre (ver
// `shell/orientationChoice.ts`). Por isso, quando o que ele produz é paisagem numa viewport
// que continuou retrato, a mesma superfície que confirma o layout diz que destravar a rotação
// é o caminho que preserva o exercício.
//
// Mora na pré-configuração, ao lado de Espelhar e da troca de câmera: é a mesma família de
// escolhas — "como o celular está" —, e é o instante em que ainda dá para arrumar isso.
import { useT } from '../i18n'
import { useLayoutOrientation } from '../shell/useLayoutOrientation'
import { IconRotate } from '../ui/icons'

export function OrientationControl() {
  const t = useT()
  const { valendo, travada, alternar } = useLayoutOrientation()

  // O rótulo diz o que o toque VAI FAZER, e não o estado atual — ao contrário do controle de
  // câmera, onde o estado é o que a pessoa confere olhando a imagem. Aqui a tela inteira já
  // mostra o estado; o que falta saber é para onde o botão leva.
  const acao = valendo === 'landscape' ? 'session:orientation.to_portrait' : 'session:orientation.to_landscape'

  return (
    <button
      type="button"
      className="prep-cell prep-cell--action"
      onClick={alternar}
      aria-label={t('session:orientation.aria')}
    >
      <span className="prep-cell__mirror">
        <IconRotate className="prep-cell__mirror-icon" />
        <span>{t(acao)}</span>
      </span>
      {travada && <span className="prep-cell__hint">{t('session:orientation.locked')}</span>}
    </button>
  )
}
