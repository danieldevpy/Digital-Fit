// Estado da sessão em um único store (convenções §Código).
import { create } from 'zustand'
import { refreshHistory } from '../history/refresh'
import { useHistoryStore } from '../history/store'
import { loadLastReport, markLastReportClosed, saveLastReport } from '../report/lastReport'
import type {
  Mode,
  Phase,
  RepDetectedData,
  SessionCompletedData,
  SessionEndReason,
  SessionStartedData,
} from '../lib/events'
import type { GatewayStatus } from '../lib/gateway'
import type { AssetProgress } from '../pose/assetWarmup'
import type { PoseDelegate } from '../pose/poseLandmarker'
import type { ProbeOutcome } from '../probe/runProbe'
import type { SceneAdvice } from '../scene/sceneQuality'
import type { SessionReport } from '../report/sessionReport'
import type { CoachEntry } from '../session/coachCard'
import { FACING_DEFAULT, type Facing } from '../capture/facing'

export type CameraStatus = 'idle' | 'requesting' | 'ready' | 'denied' | 'error'

/**
 * Faixa de zoom NATIVO que o track da câmera expõe (`MediaTrackCapabilities.zoom`, PTZ da
 * Media Capture and Streams). `null` quando o aparelho/navegador não suporta — nesse caso o
 * zoom vira recorte por CSS (`cssZoomValue`), só cosmético.
 */
export interface ZoomCapabilities {
  min: number
  max: number
  step: number
}
/**
 * `calibrating` é a preparação (SPEC-004): a câmera já roda e os frames já sobem, mas o
 * exercício ainda não vale. Quem decide a passagem para `running` é o servidor, via
 * `session.calibrated` — o cliente nunca começa a sessão por conta própria.
 */
export type SessionStatus = 'idle' | 'calibrating' | 'preparing' | 'running' | 'completed'

/**
 * A captura ainda deve subir frames neste estado? (T-077)
 *
 * `completed` é o estado em que a resposta é NÃO, e essa é toda a razão desta função existir.
 * Quando o servidor encerra a sessão, a câmera aqui continua rodando — a tela do relatório
 * ainda está subindo, o `sessionId` continua no store — e o loop de captura seguia mandando
 * `pose.frame` por vários segundos. Medido em produção: 4,7 s de frames depois do fim, que o
 * servidor lia como uma sessão nova com o MESMO id e usava para sobrescrever o relatório bom.
 *
 * O servidor passou a se defender disso sozinho (`ENDED_MEMORY_MS` no analysis-worker), e é lá
 * que mora a garantia — o cliente é forjável. Aqui é economia: nem CPU de inferência, nem
 * bateria, nem banda para frames que ninguém vai ler.
 */
export function streamsFrames(status: SessionStatus): boolean {
  return status === 'calibrating' || status === 'preparing' || status === 'running'
}
export type PoseStatus = 'idle' | 'loading' | 'ready' | 'error'
export type ProbeStatus = 'idle' | 'running' | 'done' | 'error'
/**
 * `loading` é o intervalo entre o fim da sessão e o relatório existir no banco — o
 * report-builder ainda está consolidando (SPEC-010). Estado normal, não erro: por isso a tela
 * mostra "consolidando" em vez de uma falha.
 */
export type ReportStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface FrameStats {
  /** Último `seq` emitido pelo frame clock — monotônico por sessão. */
  seq: number
  /** Último `ts` emitido, em epoch ms. */
  ts: number
  /** fps efetivo medido na janela recente (só diagnóstico). */
  fps: number
}

export interface SessionState {
  cameraStatus: CameraStatus
  poseStatus: PoseStatus
  poseDelegate: PoseDelegate | null
  /**
   * Quanto dos assets de pose já baixou (T-070). `null` quando não há download em curso —
   * inclusive na segunda visita, em que tudo vem do cache e ninguém precisa ver barra alguma.
   */
  poseDownload: AssetProgress | null
  probeStatus: ProbeStatus
  capability: ProbeOutcome | null
  /** `?mode=` da URL; `null` quando o probe decide sozinho. */
  modeOverride: Mode | null
  /** Resolução realmente entregue pelo device (pode diferir da preferida). */
  videoResolution: { width: number; height: number } | null
  landmarksDetected: number
  /**
   * Faixa de `visibility` do último frame. Existe porque a visibilidade é o que decide o
   * desenho do esqueleto (limiar 0.5) **e** a validação de cena no worker: se o provedor não
   * preencher o campo, os dois falham em silêncio, e nenhum log diz o motivo.
   */
  landmarkVisibility: { min: number; max: number } | null
  frameStats: FrameStats | null
  /**
   * Conselho de cena da pré-configuração (T-085): luz fraca, contraluz, falta de nitidez.
   *
   * Não confundir com `sceneEntry`, que é o `scene.warning` do SERVIDOR sobre enquadramento
   * (SPEC-003 Fase Inicial). Este aqui nasce no cliente, olhando pixels que nunca sobem, e só
   * existe na tela de Início — durante o treino a instrução de medição manda na tela (T-071).
   */
  sceneAdvice: SceneAdvice | null
  /** Ângulo articular ao vivo, calculado no cliente (T-044) — cosmético. */
  armAngleDeg: number | null
  /** Gravador de fixtures (T-007) — ferramenta de dev, não faz parte da sessão real. */
  recording: boolean
  recordedFrames: number
  /**
   * Controles da câmera, registrados pela CameraView. Existe para o FAB da
   * bottom nav iniciar a sessão sem que a nav precise conhecer o pipeline.
   */
  cameraControls: {
    start: () => void
    stop: () => void
    /** Fonte de arquivo (T-040) — só chamada pela superfície de dev. */
    startFile: (file: File) => void
    /**
     * Zoom NATIVO do track (só existe função quando `zoomCapabilities` não é `null`).
     * Aplica via `applyConstraints` — muda o frame de verdade que a pose lê, não só a tela.
     */
    setZoom: (value: number) => void
    /**
     * Troca frontal ⇄ traseira (SPEC-027 §A). Só existe onde há escolha — quem decide se o
     * controle aparece é `hasCameraChoice`, não esta função.
     */
    switchCamera: () => void
  } | null
  /**
   * Visão de espelho do palco (SPEC-014 §3, botão Espelhar). `true` é o default do produto:
   * quem treina de frente para a câmera espera se ver como num espelho.
   */
  mirrored: boolean
  /**
   * Qual câmera está no ar AGORA (SPEC-027 §A) — o valor que o track relatou, não o que foi
   * pedido. Aparelho que ignora a restrição sem erro existe, e é por isso que este campo não
   * é a preferência salva: a preferência é intenção, este é fato.
   */
  facing: Facing
  /**
   * O aparelho tem mais de uma câmera? Contado por `enumerateDevices()` DEPOIS de o stream
   * abrir (antes da permissão o navegador não conta direito). `false` esconde o controle,
   * mesmo precedente do `zoomCapabilities: null` — controle que não faz nada ensina que o app
   * está quebrado.
   */
  hasCameraChoice: boolean
  /**
   * A troca falhou, e por quê. Hoje só existe um motivo: o aparelho não tem a câmera pedida
   * (`OverconstrainedError` do `exact`). É código e não frase para o texto ser resolvido no
   * render — congelar a frase aqui a prenderia ao idioma do instante (lição da T-152).
   */
  cameraNotice: 'single_camera' | null
  /**
   * Faixa de zoom nativo do track atual — `null` sem câmera ligada ou sem o aparelho expor
   * `min < 1` (zoom "para menos", o único com utilidade aqui). Um aparelho que só amplia
   * (`min >= 1`) cai no mesmo `null`: o controle correspondente fica escondido, porque ampliar
   * não ajuda quem precisa caber o corpo inteiro mais perto da câmera — só atrapalha.
   */
  zoomCapabilities: ZoomCapabilities | null
  /** Zoom nativo aplicado agora (só significa algo quando `zoomCapabilities` não é `null`). */
  zoomValue: number
  /**
   * De onde vem a imagem (T-040). `file` faz o pipeline rebobinar o vídeo depois do probe,
   * para o começo do arquivo não ser comido pela medição — ver `dev/videoSource.ts`.
   */
  videoSource: 'camera' | 'file'
  /** Nome do arquivo em uso, para o painel de dev e para o JSON de paridade. */
  videoFileName: string | null

  // ---- sessão (eventos vindos do gateway) ----
  gatewayStatus: GatewayStatus
  sessionId: string | null
  exerciseKey: string | null
  sessionStatus: SessionStatus
  endReason: SessionEndReason | null
  /** Contador autoritativo: vem de `rep.detected.rep_count`, não é somado aqui. */
  repCount: number
  phase: Phase | null
  durationS: number
  /**
   * epoch ms em que o exercício passou a valer (chegada do `session.calibrated`) — base do
   * countdown cosmético. Fica `null` durante a preparação, e por isso o anel mostra a
   * duração cheia: não há tempo a descontar de uma sessão que não começou.
   */
  startedAt: number | null
  /**
   * Instante em que a contagem passa a valer (T-049). Durante a preparação fica no FUTURO —
   * é dele que sai o "3, 2, 1" na tela.
   *
   * O anel dos 30 s ancora aqui, e não no `session.calibrated`: quem segura a contagem é o
   * worker, e o anel tem de andar junto com ele, não com a medição.
   */
  countingFrom: number | null
  /** Quanto durou a preparação pedida, em ms — denominador do anel do "3, 2, 1" (T-049). */
  countdownMs: number
  /** epoch ms do primeiro frame enviado — só para saber há quanto tempo se está calibrando. */
  firstFrameAt: number | null
  sceneEntry: CoachEntry | null
  feedbackEntry: CoachEntry | null

  /** Relatório consolidado (SPEC-010). Só existe depois do fim da sessão. */
  report: SessionReport | null
  reportStatus: ReportStatus
  /** Tela de relatório visível. Fechar não apaga o relatório — só sai da frente. */
  reportOpen: boolean

  error: string | null

  setCameraStatus: (status: CameraStatus) => void
  setPoseStatus: (status: PoseStatus) => void
  setPoseDelegate: (delegate: PoseDelegate) => void
  setPoseDownload: (progresso: AssetProgress | null) => void
  setProbeStatus: (status: ProbeStatus) => void
  setCapability: (capability: ProbeOutcome | null) => void
  setModeOverride: (mode: Mode | null) => void
  setVideoResolution: (resolution: { width: number; height: number }) => void
  setLandmarksDetected: (count: number) => void
  setLandmarkVisibility: (range: { min: number; max: number } | null) => void
  setFrameStats: (stats: FrameStats | null) => void
  setSceneAdvice: (advice: SceneAdvice | null) => void
  setArmAngleDeg: (angle: number | null) => void
  setRecording: (recording: boolean) => void
  setRecordedFrames: (count: number) => void
  setCameraControls: (controls: SessionState['cameraControls']) => void
  toggleMirrored: () => void
  setMirrored: (mirrored: boolean) => void
  setFacing: (facing: Facing) => void
  setHasCameraChoice: (hasCameraChoice: boolean) => void
  setCameraNotice: (cameraNotice: 'single_camera' | null) => void
  setZoomCapabilities: (capabilities: ZoomCapabilities | null) => void
  setZoomValue: (value: number) => void
  setVideoSource: (source: 'camera' | 'file', fileName?: string | null) => void
  setGatewayStatus: (status: GatewayStatus) => void
  /**
   * Sessão admitida (`POST /api/sessions`). É **daqui** que vem o `session_id` no caminho
   * real: `session.started` não está nos `CLIENT_PUSH_TYPES`, então o gateway nunca o
   * empurra — o mock mandava, e era só por isso que o cliente funcionava contra ele.
   */
  applyTicket: (ticket: { sessionId: string; exercise: string; durationS: number }) => void
  /** Primeiro frame enviado: marca o início da preparação, não o do exercício. */
  markFirstFrame: (at: number) => void
  /** `session.calibrated`: o servidor mediu o corpo e começou a contar os 30 s. */
  applyCalibrated: (at: number, countdownMs?: number) => void
  startCounting: () => void
  applySessionStarted: (data: SessionStartedData, sessionId: string) => void
  applyRepDetected: (data: RepDetectedData) => void
  applyPhase: (phase: Phase) => void
  applySceneWarning: (entry: CoachEntry) => void
  applyFeedback: (entry: CoachEntry) => void
  applySessionCompleted: (data: SessionCompletedData) => void
  /** Começou a buscar o relatório — a tela abre já mostrando "consolidando". */
  startReport: () => void
  applyReport: (report: SessionReport) => void
  failReport: () => void
  closeReport: () => void
  /** Reabre a folha do último relatório (aba Analytics, T-068). */
  reopenReport: () => void
  resetSession: () => void
  setError: (message: string | null) => void
  resetPipeline: () => void
}

/**
 * Rehidrata o último relatório do aparelho (F5 depois do treino não pode apagar o
 * resultado). Se a folha estava aberta quando a página morreu, reabre.
 */
function hydrateReport() {
  const stored = loadLastReport()
  if (!stored) return {}
  return {
    report: stored.report,
    reportStatus: 'ready' as ReportStatus,
    reportOpen: stored.open,
  }
}

const SESSION_DEFAULTS = {
  sessionId: null,
  exerciseKey: null,
  sessionStatus: 'idle' as SessionStatus,
  endReason: null,
  repCount: 0,
  phase: null,
  durationS: 30,
  startedAt: null,
  countingFrom: null,
  countdownMs: 0,
  firstFrameAt: null,
  sceneEntry: null,
  feedbackEntry: null,
  report: null,
  reportStatus: 'idle' as ReportStatus,
  reportOpen: false,
}

export const useSessionStore = create<SessionState>((set, get) => ({
  cameraStatus: 'idle',
  poseStatus: 'idle',
  poseDownload: null,
  poseDelegate: null,
  probeStatus: 'idle',
  capability: null,
  modeOverride: null,
  videoResolution: null,
  landmarksDetected: 0,
  landmarkVisibility: null,
  frameStats: null,
  sceneAdvice: null,
  armAngleDeg: null,
  recording: false,
  recordedFrames: 0,
  cameraControls: null,
  mirrored: true,
  facing: FACING_DEFAULT,
  hasCameraChoice: false,
  cameraNotice: null,
  zoomCapabilities: null,
  zoomValue: 1,
  videoSource: 'camera',
  videoFileName: null,
  gatewayStatus: 'idle',
  ...SESSION_DEFAULTS,
  ...hydrateReport(),
  error: null,

  setCameraStatus: (cameraStatus) => set({ cameraStatus }),
  setPoseStatus: (poseStatus) => set({ poseStatus }),
  setPoseDelegate: (poseDelegate) => set({ poseDelegate }),
  setPoseDownload: (poseDownload) => set({ poseDownload }),
  setProbeStatus: (probeStatus) => set({ probeStatus }),
  setCapability: (capability) => set({ capability }),
  setModeOverride: (modeOverride) => set({ modeOverride }),
  setVideoResolution: (videoResolution) => set({ videoResolution }),
  setLandmarksDetected: (landmarksDetected) => set({ landmarksDetected }),
  setLandmarkVisibility: (landmarkVisibility) => set({ landmarkVisibility }),
  setFrameStats: (frameStats) => set({ frameStats }),
  setSceneAdvice: (sceneAdvice) => set({ sceneAdvice }),
  setArmAngleDeg: (armAngleDeg) => set({ armAngleDeg }),
  setRecording: (recording) => set({ recording }),
  setRecordedFrames: (recordedFrames) => set({ recordedFrames }),
  setCameraControls: (cameraControls) => set({ cameraControls }),
  toggleMirrored: () => set({ mirrored: !get().mirrored }),
  setMirrored: (mirrored) => set({ mirrored }),
  setFacing: (facing) => set({ facing }),
  setHasCameraChoice: (hasCameraChoice) => set({ hasCameraChoice }),
  setCameraNotice: (cameraNotice) => set({ cameraNotice }),
  setZoomCapabilities: (zoomCapabilities) => set({ zoomCapabilities }),
  setZoomValue: (zoomValue) => set({ zoomValue }),
  setVideoSource: (videoSource, videoFileName = null) => set({ videoSource, videoFileName }),
  setGatewayStatus: (gatewayStatus) => set({ gatewayStatus }),

  applyTicket: ({ sessionId, exercise, durationS }) =>
    set({
      sessionId,
      exerciseKey: exercise,
      durationS,
      // Admitida ≠ começada: a sessão entra em preparação e só vira `running` quando o
      // servidor confirma a calibração (SPEC-004).
      sessionStatus: 'calibrating',
      endReason: null,
      repCount: 0,
      phase: null,
      startedAt: null,
      firstFrameAt: null,
      sceneEntry: null,
      feedbackEntry: null,
    }),

  markFirstFrame: (at) => {
    if (get().firstFrameAt !== null) return
    set({ firstFrameAt: at })
  },

  applyCalibrated: (at, countdownMs = 0) => {
    // Idempotente: o servidor emite uma vez, mas um reenvio não pode reiniciar o anel.
    if (get().startedAt !== null) return
    const valeEm = at + Math.max(0, countdownMs)
    set({
      startedAt: valeEm,
      countingFrom: valeEm,
      countdownMs: Math.max(0, countdownMs),
      // Sem preparação o estado vai direto a `running`, como antes da T-049.
      sessionStatus: countdownMs > 0 ? 'preparing' : 'running',
    })
  },

  /** Fim do "3, 2, 1": chamado pelo próprio cliente quando o prazo vence. */
  startCounting: () => {
    if (get().sessionStatus !== 'preparing') return
    set({ sessionStatus: 'running' })
  },

  applySessionStarted: (data, sessionId) =>
    set({
      sessionId,
      exerciseKey: data.exercise,
      durationS: data.duration_s,
      sessionStatus: 'running',
      endReason: null,
      repCount: 0,
      phase: null,
      startedAt: Date.now(),
      firstFrameAt: null,
      sceneEntry: null,
      feedbackEntry: null,
    }),

  applyRepDetected: (data) => set({ repCount: data.rep_count, phase: data.phase }),
  applyPhase: (phase) => set({ phase }),
  applySceneWarning: (sceneEntry) => set({ sceneEntry }),
  applyFeedback: (feedbackEntry) => set({ feedbackEntry }),

  applySessionCompleted: (data) =>
    set({ sessionStatus: 'completed', endReason: data.reason, repCount: data.rep_count }),

  startReport: () => {
    // Idempotente: o `session.completed` e o `session.report.ready` chamam os dois, e o
    // segundo não pode reabrir uma tela que o usuário acabou de fechar.
    if (get().reportStatus !== 'idle') return
    set({ reportStatus: 'loading', reportOpen: true })
  },
  applyReport: (report) => {
    // Persistido com a folha aberta: quem der F5 com o relatório na tela o reencontra.
    saveLastReport(report, get().reportOpen)
    // A sessão que acabou entra no histórico AQUI, e não numa tela (T-121). É o único lugar
    // por onde todo relatório consolidado passa — o `session.report.ready` e o repique do
    // `waitForReport` chegam os dois neste método —, e é o que faz o Progresso do visitante
    // existir sem conta. O `record` é idempotente por `session_id`.
    useHistoryStore.getState().record(report)
    // Terceiro gatilho do contrato de frescor (T-122): fim de sessão invalida o histórico NA
    // HORA, sem esperar foco e **ignorando o debounce** — aqui houve um fato novo, não uma
    // suspeita. É o caso que originou a spec: treinou, foi no Perfil, viu o número de antes.
    // Sem conta isto só relê o aparelho, que o `record` acabou de atualizar.
    void refreshHistory({ force: true })
    set({ report, reportStatus: 'ready' })
  },
  failReport: () => set({ reportStatus: 'error' }),
  closeReport: () => {
    markLastReportClosed()
    set({ reportOpen: false })
  },
  /**
   * A aba Analytics reabre a análise da última sessão. Escreve `open: true` no aparelho pelo
   * mesmo motivo que `applyReport`: um F5 com a folha na tela tem de reencontrá-la aberta.
   * Sem relatório não faz nada — abrir folha vazia seria pior que não abrir.
   */
  reopenReport: () => {
    const { report } = get()
    if (!report) return
    saveLastReport(report, true)
    set({ reportOpen: true, reportStatus: 'ready' })
  },

  resetSession: () => set({ ...SESSION_DEFAULTS }),
  setError: (error) => set({ error }),

  resetPipeline: () =>
    set({
      poseStatus: 'idle',
      poseDelegate: null,
      poseDownload: null,
      probeStatus: 'idle',
      capability: null,
      landmarksDetected: 0,
      frameStats: null,
      sceneAdvice: null,
      armAngleDeg: null,
      recording: false,
      recordedFrames: 0,
    }),
}))
