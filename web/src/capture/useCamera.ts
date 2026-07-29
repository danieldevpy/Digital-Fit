// Captura de câmera (SPEC-001, Fase Inicial): getUserMedia 640×480 @30fps
// preferidos, com fallback para o que o device entregar.
//
// Desde a T-040 a mesma origem aceita um ARQUIVO de vídeo (`startFile`), para medir o
// pipeline edge do navegador contra o corpus rotulado. É superfície de dev, atrás do gate da
// T-048 — quem chama é o painel, nunca a UI de produto.
import { useCallback, useEffect, useRef, type RefObject } from 'react'
import { loadVideoFile } from '../dev/videoSource'
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
  const releaseFileRef = useRef<(() => void) | null>(null)
  const setCameraStatus = useSessionStore((state) => state.setCameraStatus)
  const setVideoResolution = useSessionStore((state) => state.setVideoResolution)
  const setVideoSource = useSessionStore((state) => state.setVideoSource)
  const setError = useSessionStore((state) => state.setError)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    // O object URL segura o blob do arquivo até ser revogado: sem isto, cada vídeo aberto
    // ficaria na memória da aba até o reload.
    releaseFileRef.current?.()
    releaseFileRef.current = null
    const video = videoRef.current
    if (video) {
      video.srcObject = null
      video.removeAttribute('src')
      video.load()
    }
    setVideoSource('camera')
    setCameraStatus('idle')
  }, [setCameraStatus, setVideoSource, videoRef])

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

  /**
   * Arquivo no lugar da câmera (T-040). O vídeo fica **parado** no frame 0: quem dá o play é
   * o pipeline, depois do capability probe — senão os 2 s da medição comeriam o começo do
   * arquivo, que é justamente o trecho parado que a calibração consome (SPEC-004).
   */
  const startFile = useCallback(
    async (file: File) => {
      const video = videoRef.current
      if (!video) return
      stop()
      setError(null)
      setCameraStatus('requesting')
      try {
        const carregado = await loadVideoFile(video, file)
        releaseFileRef.current = carregado.release
        // Fim do arquivo encerra a captura, como soltar o botão encerraria a da câmera. O
        // servidor fecha a sessão pelo mesmo caminho de sempre (sem frames → `no_data`), que
        // é o comportamento que a T-011 já definiu — nada de rota nova para o modo dev.
        video.addEventListener('ended', () => stop(), { once: true })
        setVideoResolution({ width: carregado.width, height: carregado.height })
        setVideoSource('file', file.name)
        setCameraStatus('ready')
      } catch (error) {
        releaseFileRef.current = null
        setCameraStatus('error')
        setError(error instanceof Error ? error.message : 'Falha ao abrir o vídeo.')
      }
    },
    [setCameraStatus, setError, setVideoResolution, setVideoSource, stop, videoRef],
  )

  useEffect(() => stop, [stop])

  return { start, stop, startFile }
}
