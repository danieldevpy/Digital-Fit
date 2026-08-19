import { useEffect, useRef } from 'react'
import { FixtureControls } from '../dev/FixtureControls'
import { VideoSourceControl } from '../dev/VideoSourceControl'
import { useDevTools, useRecordMode } from '../dev/gate'
import { useT, type TKey } from '../i18n'
import { CountdownSetting } from '../hud/CountdownSetting'
import { ExercisePicker } from '../hud/ExercisePicker'
import { GetReady } from '../hud/GetReady'
import { Mode } from '../lib/events'
import { warmupLabel } from '../pose/assetWarmup'
import { useSceneCheck } from '../scene/useSceneCheck'
import { pipelinePhase } from '../session/pipelineGate'
import { useSessionStore } from '../store/session'
import { useCamera } from './useCamera'
import { useEdgePipeline } from './useEdgePipeline'

/**
 * Estado da câmera na capa. Chave = `CameraStatus` (contrato do store); o valor é a chave do
 * dicionário, resolvida no render — congelar o texto aqui, no import do módulo, o prenderia
 * ao idioma detectado naquele instante (mesma lição do `EXERCISE_CATALOG` na T-152).
 */
const CAMERA_LABEL: Record<string, TKey> = {
  idle: 'session:camera.status.idle',
  requesting: 'session:camera.status.requesting',
  ready: 'session:camera.status.ready',
  denied: 'session:camera.status.denied',
  error: 'session:camera.status.error',
}

interface CameraViewProps {
  /**
   * Capa compacta (SPEC-014 §3): dentro da moldura da pré-configuração as escolhas de
   * exercício/preparação já têm casa própria nas colunas — repetir os chips aqui viraria
   * ruído dentro de uma janela estreita.
   */
  compactCover?: boolean
  /**
   * Avaliar luz/nitidez da cena (T-085). Ligado só na pré-configuração: é lá que dá para
   * limpar a lente e acender a luz antes de começar. Durante o treino a instrução de medição
   * manda na tela (T-071) e um aviso a mais disputaria espaço com o que importa.
   */
  checkScene?: boolean
}

export function CameraView({ compactCover = false, checkScene = false }: CameraViewProps) {
  const t = useT()
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
  // Modo gravação (T-129): mesmo direito, sem diagnóstico nenhum na tela — só a origem em
  // arquivo continua acessível. Os dois nunca estão ligados ao mesmo tempo (ver `gate.ts`).
  const recordMode = useRecordMode()

  const { start, stop, startFile, setZoom, switchCamera } = useCamera(videoRef)
  useEdgePipeline(videoRef, canvasRef, cameraStatus === 'ready')
  useSceneCheck(videoRef, checkScene && cameraStatus === 'ready')

  // O FAB da bottom nav aciona a câmera sem conhecer o pipeline.
  useEffect(() => {
    setCameraControls({
      start: () => void start(),
      stop,
      // Só o painel de dev chama (T-040); o FAB da nav nem sabe que existe.
      startFile: (file: File) => void startFile(file),
      setZoom,
      switchCamera: () => void switchCamera(),
    })
    return () => setCameraControls(null)
  }, [setCameraControls, setZoom, start, startFile, stop, switchCamera])

  const isReady = cameraStatus === 'ready'
  const isCloud = capability?.mode === Mode.CLOUD
  const fase = pipelinePhase({ poseStatus, probeStatus })

  return (
    <div className={`stage ${mirrored ? '' : 'stage--unmirrored'}`}>
      {/* video e canvas espelhados juntos: o desenho usa coordenadas cruas. Zoom (quando o
          aparelho suporta) é aplicado no TRACK via `applyConstraints` (useCamera.ts) — o
          frame que chega aqui já vem ampliado/reduzido pelo hardware, sem transform de CSS. */}
      <video ref={videoRef} className="stage__video" playsInline muted autoPlay />
      <canvas ref={canvasRef} className="stage__canvas" />

      {!isReady && (
        <div className="stage__cover">
          <p className="stage__status">{t(CAMERA_LABEL[cameraStatus] ?? CAMERA_LABEL.idle!)}</p>
          {error && <p className="stage__error">{error}</p>}
          <button
            type="button"
            className="stage__start"
            onClick={start}
            disabled={cameraStatus === 'requesting'}
          >
            {cameraStatus === 'requesting'
              ? t('session:camera.waiting')
              : t('session:cta.turn_on_camera')}
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

          {/* Modo gravação (T-129). Aqui dentro da capa de propósito, e também na capa compacta
              da pré-configuração — que é justamente a tela que se quer gravar: escolher o
              arquivo é a alternativa a "Ligar câmera", e é este o momento em que ela existe.
              Carregado o vídeo, `cameraStatus` vira `ready`, a capa inteira sai da tela e não
              sobra nenhum vestígio do modo na imagem gravada. */}
          {recordMode && (
            <div className="stage__dev stage__dev--cover stage__dev--rec">
              <VideoSourceControl variant="record" />
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
          {t('session:warmup.title')}
          <span className="stage__banner-sub">
            {poseDownload
              ? // Com números reais: são ~17 MB no primeiro acesso, e "43% · 7,4 de 17,3 MB"
                // responde a única pergunta que quem espera tem — "está andando?".
                t('session:warmup.downloading', { progress: warmupLabel(poseDownload) })
              : t('session:warmup.first_time')}
          </span>
        </p>
      )}

      {isReady && fase === 'falhou' && (
        <p className="stage__banner stage__banner--offline">
          {error ?? t('session:warmup.failed')}
        </p>
      )}

      {isReady && fase === 'medindo' && (
        <p className="stage__banner">{t('session:warmup.measuring')}</p>
      )}

      {/* "3, 2, 1" entre o corpo medido e a contagem valer (T-049). Quem segura a contagem
          é o worker; isto aqui só desenha o mesmo prazo. */}
      {isReady && <GetReady />}

      {/* Medição (SPEC-004): a câmera roda e os frames já sobem, mas o exercício ainda não
          vale. Quem encerra esta fase é o servidor (`session.calibrated`). */}
      {isReady && sessionStatus === 'calibrating' && (
        <div className="stage__prepare">
          <p className="stage__prepare-title">{t('session:calibrating.title')}</p>
          <p className="stage__prepare-hint">{t('session:calibrating.hint')}</p>
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
              // Diagnóstico, não produto: só quem tem `devTools` lê isto, e o conselho é
              // literalmente um comando de terminal. Fica em português pela mesma razão que o
              // painel admin fica (SPEC-025 §Escopo) — ferramenta de operação não é superfície
              // de quem treina.
              /* eslint-disable i18next/no-literal-string */
              <>
                Sem conexão com o servidor — a contagem não vai avançar. Suba a stack
                (<code>docker compose up</code>) ou aponte <code>VITE_API_URL</code> para a API.
              </>
            ) : (
              /* eslint-enable i18next/no-literal-string */
              t('session:gateway.offline')
            ))}
        </p>
      )}

      {isReady && gatewayStatus === 'connecting' && (
        <p className="stage__banner">{t('session:gateway.connecting')}</p>
      )}

      {/* Sem esqueleto por design: no cloud os landmarks nascem no pose-worker, e `pose.frame`
          não volta ao cliente (CLIENT_PUSH_TYPES). A contagem aparece normalmente — vem de
          `rep.detected`.

          Texto curto (T-071): a versão longa explicava probe, extração no servidor e ausência de
          esqueleto em três linhas, e em aparelho real ela vazava por baixo dos cards do HUD —
          ilegível justamente por querer explicar demais. O "por que" do modo é diagnóstico e
          mora no chip de dev; aqui fica só o que muda para quem treina.

          Escondida durante a medição: naquele instante a instrução "fique em pé, parado" é a
          tela, e um aviso de status não pode disputar espaço com ela. */}
      {isReady && isCloud && sessionStatus !== 'calibrating' && (
        <p className="stage__banner stage__banner--cloud">{t('session:mode.cloud_banner')}</p>
      )}

      {/* Chip de dev — diagnóstico do pipeline, fora da SPEC-013. Não é UI de produto: o
          usuário comum nunca vê isto (T-048). */}
      {/* Chip de dev: mesma exclusão do bloco acima, e pelo mesmo motivo — `pose gpu`,
          `seq 412 · 14,9fps`, `176 lm` e o botão `parar` são instrumentos de medição, não
          produto. Bloco inteiro desligado da regra, com o `enable` logo depois. */}
      {/* eslint-disable i18next/no-literal-string */}
      {isReady && devTools && (
        <div className="stage__dev">
          <span>{poseStatus === 'ready' ? `pose ${poseDelegate}` : poseStatus}</span>
          {/* As DUAS medidas do probe, separadas (T-084): `modelo` é capacidade do aparelho
              (mediana da latência) e decide o modo; `câmera` é cadência da fonte e é sinal de
              cena. Confundir as duas foi o que mandava iPhone bom para cloud. O motivo da
              decisão vem junto porque sem ele "foi para cloud" não tem diagnóstico. */}
          {capability && (
            <span>
              {capability.mode}
              {capability.forced ? '*' : ''} · {capability.reason} · modelo{' '}
              {capability.modelFps?.toFixed(1) ?? '—'}fps
              {capability.inferenceMsP50 !== null &&
                ` (${capability.inferenceMsP50.toFixed(0)}ms)`}{' '}
              · câmera {capability.cameraFpsSource === 'processados' ? '≥' : ''}
              {capability.cameraFps?.toFixed(1) ?? '—'}fps
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
      {/* eslint-enable i18next/no-literal-string */}
    </div>
  )
}
