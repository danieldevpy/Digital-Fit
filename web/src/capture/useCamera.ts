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
import { facingPreference, setFacingPreference } from './cameraPrefs'
import { swapCamera } from './cameraSwap'
import {
  facingConstraint,
  facingFromSettings,
  hasCameraChoice,
  mirrorDefaultFor,
  type Facing,
} from './facing'
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

/**
 * Abre o stream na câmera pedida (SPEC-027 §A).
 *
 * O fallback de RESOLUÇÃO continua sendo o da SPEC-001 — só que ele preserva o `facingMode`:
 * cair para `video: true` porque o aparelho não faz 640×480 não pode, de quebra, trocar a
 * câmera que a pessoa escolheu.
 *
 * Com `precisao: 'exact'` o `OverconstrainedError` da CÂMERA não é tratado aqui: ele sobe
 * para quem chamou (`switchCamera`), que é quem sabe para onde voltar. Distinguir os dois
 * casos é o motivo de a segunda tentativa manter a restrição de câmera — se ela cair junto, o
 * erro vira "resolução" e a troca falha em silêncio.
 */
async function requestStream(facing: Facing, precisao: 'ideal' | 'exact'): Promise<MediaStream> {
  const camera = facingConstraint(facing, precisao)
  try {
    return await navigator.mediaDevices.getUserMedia({
      video: { ...PREFERRED_VIDEO, ...camera },
      audio: false,
    })
  } catch (error) {
    if (!isOverconstrained(error)) throw error
    // Device não atende à resolução preferida: aceita o que ele der, na MESMA câmera.
    return navigator.mediaDevices.getUserMedia({ video: { ...camera }, audio: false })
  }
}

/**
 * Há mais de uma câmera? Só depois de o stream abrir (a permissão já existe) — antes disso o
 * navegador devolve entradas sem `label` e, em parte deles, sem contagem confiável.
 *
 * Falha aqui não é erro de produto: sem a resposta, o controle simplesmente não aparece.
 */
async function contarCameras(): Promise<boolean> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices?.()
    return hasCameraChoice(devices ?? [])
  } catch {
    return false
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
  const setMirrored = useSessionStore((state) => state.setMirrored)
  const setFacing = useSessionStore((state) => state.setFacing)
  const setHasCameraChoice = useSessionStore((state) => state.setHasCameraChoice)
  const setCameraNotice = useSessionStore((state) => state.setCameraNotice)

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

  /**
   * Adota um stream recém-aberto: pendura no `<video>`, e resolve as três coisas que caem da
   * câmera — rótulo, espelho e zoom (SPEC-027 §A/§B).
   *
   * O espelho é reaplicado a CADA abertura de câmera, e é isso que dá o comportamento escrito
   * na spec: a câmera define o default, a escolha explícita do botão Espelhar sobrepõe, e a
   * sobreposição vale até a câmera mudar de novo.
   *
   * Devolve o facing REAL (o que o track relatou), que é o que a preferência guarda — guardar
   * o pedido faria a próxima carga repetir um pedido que este aparelho já recusou uma vez.
   */
  const adotarStream = useCallback(
    async (stream: MediaStream, video: HTMLVideoElement, pedido: Facing): Promise<Facing> => {
      streamRef.current = stream
      video.srcObject = stream
      await video.play()
      setVideoResolution({ width: video.videoWidth, height: video.videoHeight })

      const track = stream.getVideoTracks()[0]
      trackRef.current = track ?? null
      const real = facingFromSettings(track?.getSettings?.(), pedido)
      setFacing(real)
      setFacingPreference(real)
      setMirrored(mirrorDefaultFor(real))
      applyZoomFromTrack(track)
      setHasCameraChoice(await contarCameras())
      return real
    },
    [applyZoomFromTrack, setFacing, setHasCameraChoice, setMirrored, setVideoResolution],
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
    // Sem câmera no ar não há troca a oferecer, e um aviso de troca sobrevivente seria um
    // aviso sobre uma câmera que não existe mais.
    setHasCameraChoice(false)
    setCameraNotice(null)
  }, [
    setCameraNotice,
    setCameraStatus,
    setHasCameraChoice,
    setVideoSource,
    setZoomCapabilities,
    setZoomValue,
    videoRef,
  ])

  const start = useCallback(async () => {
    if (streamRef.current) return
    setError(null)
    setCameraStatus('requesting')
    setCameraNotice(null)
    try {
      // Abrir usa `ideal`: se a câmera preferida sumiu (fone desconectado, lente escondida por
      // outro app), abrir na outra é melhor que tela preta — e `adotarStream` corrige o rótulo.
      const pedido = facingPreference()
      const stream = await requestStream(pedido, 'ideal')
      streamRef.current = stream

      const video = videoRef.current
      if (!video) {
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        setCameraStatus('idle')
        return
      }

      await adotarStream(stream, video, pedido)
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
  }, [adotarStream, setCameraNotice, setCameraStatus, setError, videoRef])

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
   * Troca frontal ⇄ traseira (SPEC-027 §A), chamada pelo controle da pré-configuração.
   *
   * **Não mexe em `cameraStatus`.** O `useEdgePipeline` liga e desliga por ele, e um
   * `requesting` no meio da troca derrubaria o landmarker e faria o capability probe rodar de
   * novo (2–3 s) — a cada toque no botão, com risco de a medição nova cair do outro lado do
   * limiar e mandar para cloud um aparelho que estava em edge. O `<video>` é o mesmo nó, o
   * laço de rVFC continua nele: o que troca por baixo é só o `srcObject`.
   *
   * A SEQUÊNCIA da troca (soltar, pedir com `exact`, voltar quando falha) mora em
   * `cameraSwap.ts`, com as dependências injetadas: é a parte cuja falha só aparece em
   * aparelho de câmera única, que é justamente o aparelho que ninguém tem na mesa na hora de
   * escrever o código. Aqui fica a fiação com o store.
   */
  const switchCamera = useCallback(async () => {
    const video = videoRef.current
    const stream = streamRef.current
    if (!video || !stream) return
    // Origem em arquivo (T-040) não tem câmera para trocar.
    if (useSessionStore.getState().videoSource === 'file') return

    setCameraNotice(null)
    const resultado = await swapCamera(useSessionStore.getState().facing, {
      abrir: (facing, precisao) => requestStream(facing, precisao),
      adotar: async (novoStream, pedido) => {
        await adotarStream(novoStream, video, pedido)
      },
      soltar: () => {
        stream.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        trackRef.current = null
      },
      ehRestricaoImpossivel: isOverconstrained,
    })

    if (resultado.estado === 'voltou' && resultado.notice) setCameraNotice(resultado.notice)
    if (resultado.estado === 'sem_camera') {
      // Perdeu a câmera de ida E a de volta: aqui não há mais imagem, e o estado de erro é a
      // verdade da tela.
      streamRef.current = null
      setCameraStatus('error')
      setError(
        resultado.erro instanceof Error ? resultado.erro.message : t('session:camera.open_failed'),
      )
    }
  }, [adotarStream, setCameraNotice, setCameraStatus, setError, videoRef])

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
        // Arquivo não tem MediaStreamTrack: sem zoom nativo possível, o controle some — e
        // pelo mesmo motivo não há frontal/traseira a oferecer (SPEC-027 §A).
        applyZoomFromTrack(undefined)
        setHasCameraChoice(false)
        setCameraNotice(null)
        setCameraStatus('ready')
      } catch (error) {
        releaseFileRef.current = null
        setCameraStatus('error')
        setError(error instanceof Error ? error.message : t('session:camera.video_failed'))
      }
    },
    [
      applyZoomFromTrack,
      setCameraNotice,
      setCameraStatus,
      setError,
      setHasCameraChoice,
      setVideoResolution,
      setVideoSource,
      stop,
      videoRef,
    ],
  )

  useEffect(() => stop, [stop])

  return { start, stop, startFile, setZoom, switchCamera }
}
