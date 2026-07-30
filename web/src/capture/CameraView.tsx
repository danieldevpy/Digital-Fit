import { useEffect, useRef } from 'react'
import { FixtureControls } from '../dev/FixtureControls'
import { VideoSourceControl } from '../dev/VideoSourceControl'
import { useDevTools } from '../dev/gate'
import { CountdownSetting } from '../hud/CountdownSetting'
import { ExercisePicker } from '../hud/ExercisePicker'
import { GetReady } from '../hud/GetReady'
import { Mode } from '../lib/events'
import { warmupLabel } from '../pose/assetWarmup'
import { pipelinePhase } from '../session/pipelineGate'
import { useSessionStore } from '../store/session'
import { useCamera } from './useCamera'
import { useEdgePipeline } from './useEdgePipeline'

const CAMERA_LABEL: Record<string, string> = {
  idle: 'Câmera desligada',
  requesting: 'Pedindo permissão…',
  ready: 'Câmera pronta',
  denied: 'Permissão negada',
  error: 'Erro na câmera',
}

interface CameraViewProps {
  /**
   * Capa compacta (SPEC-014 §3): dentro da moldura da pré-configuração as escolhas de
   * exercício/preparação já têm casa própria nas colunas — repetir os chips aqui viraria
   * ruído dentro de uma janela de 180px.
   */
  compactCover?: boolean
}

export function CameraView({ compactCover = false }: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const cameraStatus = useSessionStore((state) => state.cameraStatus)
  const sessionStatus = useSessionStore((state) => state.sessionStatus)
  const poseStatus = useSessionStore((state) => state.poseStatus)
  const poseDelegate = useSessionStore((state) => state.poseDelegate)
  const poseDownload = useSessionStore((state) => state.poseDownload)
  const probeStatus = useSessionStore((state) => state.probeStatus)
  const capability = useSessionStore((state) => state.capability)
  const videoResolution = useSessionStore((state) => state.videoResolution)
  const landmarksDetected = useSessionStore((state) => state.landmarksDetected)
  const landmarkVisibility = useSessionStore((state) => state.landmarkVisibility)
  const frameStats = useSessionStore((state) => state.frameStats)
  const gatewayStatus = useSessionStore((state) => state.gatewayStatus)
  const error = useSessionStore((state) => state.error)
  const mirrored = useSessionStore((state) => state.mirrored)

  const setCameraControls = useSessionStore((state) => state.setCameraControls)
  // Ferramentas de diagnóstico: build de dev, ou conta com `is_admin` (T-048).
  const devTools = useDevTools()

  const { start, stop, startFile } = useCamera(videoRef)
  useEdgePipeline(videoRef, canvasRef, cameraStatus === 'ready')

  // O FAB da bottom nav aciona a câmera sem conhecer o pipeline.
  useEffect(() => {
    setCameraControls({
      start: () => void start(),
      stop,
      // Só o painel de dev chama (T-040); o FAB da nav nem sabe que existe.
      startFile: (file: File) => void startFile(file),
    })
    return () => setCameraControls(null)
  }, [setCameraControls, start, startFile, stop])

  const isReady = cameraStatus === 'ready'
  const isCloud = capability?.mode === Mode.CLOUD
  const fase = pipelinePhase({ poseStatus, probeStatus })

  return (
    <div className={`stage ${mirrored ? '' : 'stage--unmirrored'}`}>
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

          {/* As escolhas só importam aqui, logo antes de treinar: o que fazer (T-051) e
              quanto tempo para se preparar (T-049). Na capa compacta da pré-config (SPEC-014)
              elas saem: exercício e ajustes moram nas colunas ao redor da moldura. */}
          {!compactCover && <ExercisePicker />}
          {!compactCover && <CountdownSetting />}

          {/* A fonte de arquivo precisa estar acessível ANTES da câmera (T-040): ela existe
              justamente para medir o pipeline sem câmera — em máquina sem webcam, ou sem
              gastar a permissão. Deixá-la só dentro do chip de diagnóstico, que exige
              `isReady`, obrigaria a ligar a câmera para não usá-la. */}
          {devTools && !compactCover && (
            <div className="stage__dev stage__dev--cover">
              <VideoSourceControl />
            </div>
          )}
        </div>
      )}

      {/* Aquecimento do pipeline (T-069). Antes disto a tela ficava MUDA entre a câmera abrir e
          o primeiro frame sair — que é justamente a janela onde o primeiro acesso passa vários
          segundos baixando ~17 MB de WASM e modelo. Quem esperava não tinha como saber se
          estava carregando, travado, ou se o app não o via. */}
      {isReady && fase === 'carregando' && (
        <p className="stage__banner">
          Preparando a análise neste aparelho…
          <span className="stage__banner-sub">
            {poseDownload
              ? // Com números reais: são ~17 MB no primeiro acesso, e "43% · 7,4 de 17,3 MB"
                // responde a única pergunta que quem espera tem — "está andando?".
                `Baixando o modelo de pose · ${warmupLabel(poseDownload)} (só na primeira vez)`
              : 'No primeiro acesso o modelo de pose é baixado; depois fica no aparelho.'}
          </span>
        </p>
      )}

      {isReady && fase === 'falhou' && (
        <p className="stage__banner stage__banner--offline">
          {error ?? 'Não foi possível preparar a análise de pose neste aparelho.'}
        </p>
      )}

      {isReady && fase === 'medindo' && <p className="stage__banner">Calibrando o dispositivo…</p>}

      {/* "3, 2, 1" entre o corpo medido e a contagem valer (T-049). Quem segura a contagem
          é o worker; isto aqui só desenha o mesmo prazo. */}
      {isReady && <GetReady />}

      {/* Medição (SPEC-004): a câmera roda e os frames já sobem, mas o exercício ainda não
          vale. Quem encerra esta fase é o servidor (`session.calibrated`). */}
      {isReady && sessionStatus === 'calibrating' && (
        <div className="stage__prepare">
          <p className="stage__prepare-title">Fique em pé, parado</p>
          <p className="stage__prepare-hint">
            Braços ao lado do corpo e pés juntos. Estamos medindo você — a contagem começa em
            seguida.
          </p>
        </div>
      )}

      {isReady && (gatewayStatus === 'closed' || gatewayStatus === 'error') && (
        <p className="stage__banner stage__banner--offline">
          {/* A admissão (T-011) explica a falha quando sabe o motivo; o genérico cobre
              queda de WS no meio da sessão, que não tem mensagem do servidor. A instrução de
              subir a stack é diagnóstico, não produto: mandar quem só quer treinar rodar
              `docker compose up` não ajuda ninguém (T-048). */}
          {error ??
            (devTools ? (
              <>
                Sem conexão com o servidor — a contagem não vai avançar. Suba a stack
                (<code>docker compose up</code>) ou aponte <code>VITE_API_URL</code> para a API.
              </>
            ) : (
              'Sem conexão com o servidor — a contagem não vai avançar. Verifique sua internet e tente de novo.'
            ))}
        </p>
      )}

      {isReady && gatewayStatus === 'connecting' && (
        <p className="stage__banner">Conectando ao servidor…</p>
      )}

      {isReady && isCloud && (
        <p className="stage__banner stage__banner--cloud">
          {/* Sem esqueleto por design: no cloud os landmarks nascem no pose-worker, e
              `pose.frame` não volta ao cliente (CLIENT_PUSH_TYPES). A contagem aparece
              normalmente — ela vem de `rep.detected`. */}
          Modo cloud {capability?.forced ? '(forçado por ?mode=)' : 'escolhido pelo probe'} — a pose
          é extraída no servidor, então não há esqueleto sobre a imagem.
        </p>
      )}

      {/* Chip de dev — diagnóstico do pipeline, fora da SPEC-013. Não é UI de produto: o
          usuário comum nunca vê isto (T-048). */}
      {isReady && devTools && (
        <div className="stage__dev">
          <span>{poseStatus === 'ready' ? `pose ${poseDelegate}` : poseStatus}</span>
          {capability && (
            <span>
              {capability.mode}
              {capability.forced ? '*' : ''} · probe {capability.probeFps?.toFixed(1) ?? '—'}fps
            </span>
          )}
          {frameStats && (
            <span>
              seq {frameStats.seq} · {frameStats.fps.toFixed(1)}fps
            </span>
          )}
          <span>
            {landmarksDetected} lm
            {landmarkVisibility &&
              ` · vis ${landmarkVisibility.min.toFixed(2)}–${landmarkVisibility.max.toFixed(2)}`}
          </span>
          {videoResolution && (
            <span>
              {videoResolution.width}×{videoResolution.height}
            </span>
          )}
          <FixtureControls />
          <VideoSourceControl />
          <button type="button" className="stage__dev-stop" onClick={stop}>
            parar
          </button>
        </div>
      )}
    </div>
  )
}
