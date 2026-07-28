import { useRef } from 'react'
import { useSessionStore } from '../store/session'
import { useCamera } from './useCamera'
import { usePoseOverlay } from './usePoseOverlay'

const CAMERA_LABEL: Record<string, string> = {
  idle: 'Câmera desligada',
  requesting: 'Pedindo permissão…',
  ready: 'Câmera pronta',
  denied: 'Permissão negada',
  error: 'Erro na câmera',
}

export function CameraView() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const cameraStatus = useSessionStore((state) => state.cameraStatus)
  const poseStatus = useSessionStore((state) => state.poseStatus)
  const poseDelegate = useSessionStore((state) => state.poseDelegate)
  const videoResolution = useSessionStore((state) => state.videoResolution)
  const landmarksDetected = useSessionStore((state) => state.landmarksDetected)
  const error = useSessionStore((state) => state.error)

  const { start, stop } = useCamera(videoRef)
  usePoseOverlay(videoRef, canvasRef, cameraStatus === 'ready')

  const isReady = cameraStatus === 'ready'

  return (
    <div className="stage">
      {/* video e canvas espelhados juntos: o desenho usa coordenadas cruas. */}
      <video ref={videoRef} className="stage__video" playsInline muted autoPlay />
      <canvas ref={canvasRef} className="stage__canvas" />

      {!isReady && (
        <div className="stage__cover">
          <p className="stage__status">{CAMERA_LABEL[cameraStatus]}</p>
          {error && <p className="stage__error">{error}</p>}
          <button
            type="button"
            className="stage__start"
            onClick={start}
            disabled={cameraStatus === 'requesting'}
          >
            {cameraStatus === 'requesting' ? 'Aguardando…' : 'Ligar câmera'}
          </button>
        </div>
      )}

      {/* Chip de dev — a T-003 é validação visual; sai quando o HUD real (T-012) entrar. */}
      {isReady && (
        <div className="stage__dev">
          <span>{poseStatus === 'ready' ? `pose ${poseDelegate}` : poseStatus}</span>
          <span>{landmarksDetected} lm</span>
          {videoResolution && (
            <span>
              {videoResolution.width}×{videoResolution.height}
            </span>
          )}
          <button type="button" className="stage__dev-stop" onClick={stop}>
            parar
          </button>
        </div>
      )}
    </div>
  )
}
