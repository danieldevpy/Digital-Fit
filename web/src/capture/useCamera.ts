// Captura de câmera (SPEC-001, Fase Inicial): getUserMedia 640×480 @30fps
// preferidos, com fallback para o que o device entregar.
import { useCallback, useEffect, useRef, type RefObject } from 'react'
import { useSessionStore } from '../store/session'

const PREFERRED_VIDEO: MediaTrackConstraints = {
  width: { ideal: 640 },
  height: { ideal: 480 },
  frameRate: { ideal: 30 },
}

function isPermissionDenied(error: unknown): boolean {
  return error instanceof DOMException && (error.name === 'NotAllowedError' || error.name === 'SecurityError')
}

function isOverconstrained(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'OverconstrainedError'
}

async function requestStream(): Promise<MediaStream> {
  try {
    return await navigator.mediaDevices.getUserMedia({ video: PREFERRED_VIDEO, audio: false })
  } catch (error) {
    if (!isOverconstrained(error)) throw error
    // Device não atende à resolução preferida: aceita o que ele der.
    return navigator.mediaDevices.getUserMedia({ video: true, audio: false })
  }
}

export function useCamera(videoRef: RefObject<HTMLVideoElement | null>) {
  const streamRef = useRef<MediaStream | null>(null)
  const setCameraStatus = useSessionStore((state) => state.setCameraStatus)
  const setVideoResolution = useSessionStore((state) => state.setVideoResolution)
  const setError = useSessionStore((state) => state.setError)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraStatus('idle')
  }, [setCameraStatus, videoRef])

  const start = useCallback(async () => {
    if (streamRef.current) return
    setError(null)
    setCameraStatus('requesting')
    try {
      const stream = await requestStream()
      streamRef.current = stream

      const video = videoRef.current
      if (!video) {
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        setCameraStatus('idle')
        return
      }

      video.srcObject = stream
      await video.play()
      setVideoResolution({ width: video.videoWidth, height: video.videoHeight })
      setCameraStatus('ready')
    } catch (error) {
      streamRef.current = null
      if (isPermissionDenied(error)) {
        setCameraStatus('denied')
        setError('Permissão de câmera negada. Libere o acesso e tente de novo.')
        return
      }
      setCameraStatus('error')
      setError(error instanceof Error ? error.message : 'Falha ao abrir a câmera.')
    }
  }, [setCameraStatus, setError, setVideoResolution, videoRef])

  useEffect(() => stop, [stop])

  return { start, stop }
}
