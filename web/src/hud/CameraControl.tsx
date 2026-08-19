// Trocar entre a câmera frontal e a traseira (SPEC-027 §A).
//
// Existe para o arranjo em que uma pessoa filma a outra: a traseira é a câmera boa do
// aparelho, e quem segura enquadra melhor que um celular apoiado. O espelho vai junto e não é
// escolha desta tela — traseira abre sem espelho (`mirrorDefaultFor`), porque quem filma não
// está se vendo, está vendo outra pessoa de fora.
//
// Mora na pré-configuração, ao lado de Espelhar e Zoom: mesma lógica dos dois — mostrar só
// onde a escolha importa, e sumir depois que o exercício começa. Trocar de câmera no meio da
// sessão mudaria resolução, faixa de zoom e o corpo de lugar no quadro, e o worker não tem
// evento para "o enquadramento mudou" (SPEC-027 §A, alternativa rejeitada).
import { useT } from '../i18n'
import { useSessionStore } from '../store/session'
import { IconCameraSwitch } from '../ui/icons'

export function CameraControl() {
  const t = useT()
  const hasChoice = useSessionStore((state) => state.hasCameraChoice)
  const facing = useSessionStore((state) => state.facing)
  const notice = useSessionStore((state) => state.cameraNotice)
  const cameraControls = useSessionStore((state) => state.cameraControls)

  // Aparelho com uma câmera só não tem escolha a oferecer — mesmo precedente do `ZoomControl`,
  // que some quando o hardware não expõe zoom para menos. Um botão que não faz nada não é
  // neutro: ele ensina que o app está quebrado.
  if (!hasChoice) return null

  const atual = facing === 'environment' ? t('session:camera.rear') : t('session:camera.front')

  return (
    <button
      type="button"
      className="prep-cell prep-cell--action"
      onClick={() => cameraControls?.switchCamera()}
      aria-label={t('session:camera.switch_aria', { current: atual })}
    >
      <span className="prep-cell__mirror">
        <IconCameraSwitch className="prep-cell__mirror-icon" />
        <span>{atual}</span>
      </span>
      {/* A troca falhou porque o aparelho não tem a outra câmera. O aviso fica no próprio
          controle: é onde a pessoa acabou de tocar, e some no próximo toque que der certo. */}
      {notice === 'single_camera' && (
        <span className="prep-cell__hint">{t('session:camera.single')}</span>
      )}
    </button>
  )
}
