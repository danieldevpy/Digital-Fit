// Controle de zoom da câmera. Só a direção PARA MENOS tem utilidade (feedback pós-teste
// real): ampliar não ajuda quem precisa caber o corpo inteiro mais perto da câmera — pelo
// contrário, obriga a ficar mais longe ainda. Por isso o slider só existe quando o aparelho
// expõe `zoom.min < 1` (PTZ da Media Capture and Streams, `useCamera.ts`) e o teto é sempre 1
// (neutro), nunca o `max` que o hardware relata.
//
// Muda o frame de verdade que a câmera captura (`applyConstraints`), não é recorte visual —
// mas isso não afeta a análise: o MediaPipe lê ângulos/landmarks relativos ao corpo, e
// continua funcionando desde que o corpo caiba no enquadramento.
//
// Mora na pré-configuração, ao lado de Espelhar: mesma lógica de mostrar só onde a escolha
// importa, e travar depois que o exercício começa.
import { useSessionStore } from '../store/session'
import { IconZoom } from '../ui/icons'

function formatZoom(value: number): string {
  return `${value.toFixed(1)}x`
}

export function ZoomControl() {
  const zoomCapabilities = useSessionStore((state) => state.zoomCapabilities)
  const zoomValue = useSessionStore((state) => state.zoomValue)
  const cameraControls = useSessionStore((state) => state.cameraControls)

  // Sem capacidade de abrir o campo de visão, o controle não tem o que oferecer — melhor
  // escondido do que um slider que só atrapalha.
  if (!zoomCapabilities) return null

  return (
    <div className="prep-cell prep-cell--zoom">
      <p className="v2-label">Zoom</p>
      <p className="prep-cell__value prep-cell__value--sm tabular">
        <IconZoom className="prep-cell__hud-icon prep-cell__hud-icon--blue" /> {formatZoom(zoomValue)}
      </p>
      <input
        type="range"
        className="zoom-slider"
        min={zoomCapabilities.min}
        max={zoomCapabilities.max}
        step={zoomCapabilities.step}
        value={zoomValue}
        onChange={(event) => cameraControls?.setZoom(Number(event.target.value))}
        aria-label={`Zoom da câmera: ${formatZoom(zoomValue)}. Arraste para menos e caiba mais perto da câmera.`}
      />
      <p className="prep-cell__hint">Arraste para menos e caiba mais perto da câmera.</p>
    </div>
  )
}
