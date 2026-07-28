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

const POSE_LABEL: Record<string, string> = {
  idle: 'Pose parada',
  loading: 'Carregando modelo…',
  ready: 'Pose ativa',
  error: 'Erro no modelo',
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

  const isOn = cameraStatus === 'ready' || cameraStatus === 'requesting'

  return (
    <section className="camera">
      {/* video e canvas espelhados juntos: o desenho usa coordenadas cruas. */}
      <div className="stage">
        <video ref={videoRef} className="stage__video" playsInline muted autoPlay />
        <canvas ref={canvasRef} className="stage__canvas" />
        {cameraStatus !== 'ready' && (
          <p className="stage__placeholder">{CAMERA_LABEL[cameraStatus]}</p>
        )}
      </div>

      <div className="controls">
        <button type="button" onClick={isOn ? stop : start} disabled={cameraStatus === 'requesting'}>
          {isOn ? 'Parar câmera' : 'Ligar câmera'}
        </button>

        <ul className="status">
          <li>
            <span className={`dot dot--${cameraStatus}`} /> {CAMERA_LABEL[cameraStatus]}
          </li>
          <li>
            <span className={`dot dot--${poseStatus}`} /> {POSE_LABEL[poseStatus]}
            {poseDelegate && ` (${poseDelegate})`}
          </li>
          {videoResolution && (
            <li>
              {videoResolution.width}×{videoResolution.height}
            </li>
          )}
          <li>{landmarksDetected} landmarks</li>
        </ul>
      </div>

      {error && <p className="error">{error}</p>}
    </section>
  )
}
