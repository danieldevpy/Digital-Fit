// Captura de câmera (SPEC-001, Fase Inicial): getUserMedia 640×480 @30fps
// preferidos, com fallback para o que o device entregar.
//
// Desde a T-040 a mesma origem aceita um ARQUIVO de vídeo (`startFile`), para medir o
// pipeline edge do navegador contra o corpus rotulado. É superfície de dev, atrás do gate da
// T-048 — quem chama é o painel, nunca a UI de produto.
import { useCallback, useEffect, useRef, type RefObject } from 'react'
import { loadVideoFile } from '../dev/videoSource'
import { t } from '../i18n'
import { useSessionStore } from '../store/session'
import { setZoomPreference, zoomPreference } from './zoomPrefs'

const PREFERRED_VIDEO: MediaTrackConstraints = {
  width: { ideal: 640 },
  height: { ideal: 480 },
  frameRate: { ideal: 30 },
}

/**
 * `zoom` é PTZ (Pan-Tilt-Zoom) da Media Capture and Streams — nem `lib.dom.d.ts` nem
 * `MediaTrackConstraintSet` o declaram, mas é o campo que Chrome/Android expõem de verdade
 * (mesmo padrão dos exemplos oficiais do Chrome para zoom de câmera via web).
 */
interface ZoomTrackCapabilities extends MediaTrackCapabilities {
  zoom?: { min: number; max: number; step: number }
}
interface ZoomConstraintSet extends MediaTrackConstraintSet {
  zoom?: number
}

/**
 * Só a direção PARA MENOS tem utilidade aqui (feedback pós-teste real): ampliar (zoom > 1)
 * não ajuda quem precisa se afastar menos — pelo contrário, obriga a ficar mais longe ainda.
 * Por isso o teto do controle é sempre 1 (neutro), nunca o `max` que o hardware relata.
 */
const ZOOM_UI_MAX = 1

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
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
  /** Track ativo da câmera — só ele sabe aplicar zoom nativo (`applyConstraints`). */
  const trackRef = useRef<MediaStreamTrack | null>(null)
  const setCameraStatus = useSessionStore((state) => state.setCameraStatus)
  const setVideoResolution = useSessionStore((state) => state.setVideoResolution)
  const setVideoSource = useSessionStore((state) => state.setVideoSource)
  const setError = useSessionStore((state) => state.setError)
  const setZoomCapabilities = useSessionStore((state) => state.setZoomCapabilities)
  const setZoomValue = useSessionStore((state) => state.setZoomValue)

  /**
   * Lê a preferência salva e liga o zoom nativo — só quando o aparelho expõe `min < 1`
   * (capacidade de VERDADE de abrir o campo de visão). Sem isso o controle fica escondido:
   * um slider que só amplia (`min >= 1`, ou nenhum suporte) não ajuda ninguém a caber mais
   * perto da câmera, e oferecê-lo só confundiria. Chamada tanto na câmera quanto no arquivo
   * (T-040) — sem track, cai direto no "sem suporte".
   */
  const applyZoomFromTrack = useCallback(
    (track: MediaStreamTrack | undefined) => {
      const caps = track?.getCapabilities?.() as ZoomTrackCapabilities | undefined
      const zoom = caps?.zoom

      if (track && zoom && zoom.min < ZOOM_UI_MAX) {
        setZoomCapabilities({ min: zoom.min, max: ZOOM_UI_MAX, step: zoom.step || 0.1 })
        const alvo = clamp(zoomPreference(), zoom.min, ZOOM_UI_MAX)
        setZoomValue(alvo)
        track
          .applyConstraints({ advanced: [{ zoom: alvo } as ZoomConstraintSet] })
          .catch(() => {
            // Alguns navegadores recusam applyConstraints logo após abrir o stream — o valor
            // salvo fica pronto para a próxima tentativa (slider ou reabertura da câmera).
          })
        return
      }

      setZoomCapabilities(null)
      setZoomValue(1)
    },
    [setZoomCapabilities, setZoomValue],
  )

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    trackRef.current = null
    setZoomCapabilities(null)
    setZoomValue(1)
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
  }, [setCameraStatus, setVideoSource, setZoomCapabilities, setZoomValue, videoRef])

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
      const track = stream.getVideoTracks()[0]
      trackRef.current = track ?? null
      applyZoomFromTrack(track)
      setCameraStatus('ready')
    } catch (error) {
      streamRef.current = null
      if (isPermissionDenied(error)) {
        setCameraStatus('denied')
        setError(t('session:camera.denied_detail'))
        return
      }
      setCameraStatus('error')
      setError(error instanceof Error ? error.message : t('session:camera.open_failed'))
    }
  }, [applyZoomFromTrack, setCameraStatus, setError, setVideoResolution, videoRef])

  /**
   * Zoom nativo, chamado pelo slider (hud/ZoomControl.tsx). Sem track ou sem capacidade, não
   * faz nada — o controle fica escondido nesse caso (ver `applyZoomFromTrack`).
   */
  const setZoom = useCallback(
    (value: number) => {
      const track = trackRef.current
      const caps = useSessionStore.getState().zoomCapabilities
      if (!track || !caps) return
      const alvo = clamp(value, caps.min, ZOOM_UI_MAX)
      setZoomValue(alvo)
      setZoomPreference(alvo)
      track.applyConstraints({ advanced: [{ zoom: alvo } as ZoomConstraintSet] }).catch(() => {
        // Recusa silenciosa: o slider já mostra o valor pedido, e uma falha aqui não pode
        // travar a tela com um erro — zoom é conforto, não requisito do exercício.
      })
    },
    [setZoomValue],
  )

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
        // Arquivo não tem MediaStreamTrack: sem zoom nativo possível, o controle some.
        applyZoomFromTrack(undefined)
        setCameraStatus('ready')
      } catch (error) {
        releaseFileRef.current = null
        setCameraStatus('error')
        setError(error instanceof Error ? error.message : t('session:camera.video_failed'))
      }
    },
    [applyZoomFromTrack, setCameraStatus, setError, setVideoResolution, setVideoSource, stop, videoRef],
  )

  useEffect(() => stop, [stop])

  return { start, stop, startFile, setZoom }
}
