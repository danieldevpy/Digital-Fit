// Estado da sessão em um único store (convenções §Código).
import { create } from 'zustand'
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
import type { PoseDelegate } from '../pose/poseLandmarker'
import type { ProbeOutcome } from '../probe/runProbe'
import type { SessionReport } from '../report/sessionReport'
import type { CoachEntry } from '../session/coachCard'

export type CameraStatus = 'idle' | 'requesting' | 'ready' | 'denied' | 'error'
/**
 * `calibrating` é a preparação (SPEC-004): a câmera já roda e os frames já sobem, mas o
 * exercício ainda não vale. Quem decide a passagem para `running` é o servidor, via
 * `session.calibrated` — o cliente nunca começa a sessão por conta própria.
 */
export type SessionStatus = 'idle' | 'calibrating' | 'preparing' | 'running' | 'completed'
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
  } | null
  /**
   * Visão de espelho do palco (SPEC-014 §3, botão Espelhar). `true` é o default do produto:
   * quem treina de frente para a câmera espera se ver como num espelho.
   */
  mirrored: boolean
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
  setProbeStatus: (status: ProbeStatus) => void
  setCapability: (capability: ProbeOutcome | null) => void
  setModeOverride: (mode: Mode | null) => void
  setVideoResolution: (resolution: { width: number; height: number }) => void
  setLandmarksDetected: (count: number) => void
  setLandmarkVisibility: (range: { min: number; max: number } | null) => void
  setFrameStats: (stats: FrameStats | null) => void
  setArmAngleDeg: (angle: number | null) => void
  setRecording: (recording: boolean) => void
  setRecordedFrames: (count: number) => void
  setCameraControls: (controls: SessionState['cameraControls']) => void
  toggleMirrored: () => void
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
  poseDelegate: null,
  probeStatus: 'idle',
  capability: null,
  modeOverride: null,
  videoResolution: null,
  landmarksDetected: 0,
  landmarkVisibility: null,
  frameStats: null,
  armAngleDeg: null,
  recording: false,
  recordedFrames: 0,
  cameraControls: null,
  mirrored: true,
  videoSource: 'camera',
  videoFileName: null,
  gatewayStatus: 'idle',
  ...SESSION_DEFAULTS,
  ...hydrateReport(),
  error: null,

  setCameraStatus: (cameraStatus) => set({ cameraStatus }),
  setPoseStatus: (poseStatus) => set({ poseStatus }),
  setPoseDelegate: (poseDelegate) => set({ poseDelegate }),
  setProbeStatus: (probeStatus) => set({ probeStatus }),
  setCapability: (capability) => set({ capability }),
  setModeOverride: (modeOverride) => set({ modeOverride }),
  setVideoResolution: (videoResolution) => set({ videoResolution }),
  setLandmarksDetected: (landmarksDetected) => set({ landmarksDetected }),
  setLandmarkVisibility: (landmarkVisibility) => set({ landmarkVisibility }),
  setFrameStats: (frameStats) => set({ frameStats }),
  setArmAngleDeg: (armAngleDeg) => set({ armAngleDeg }),
  setRecording: (recording) => set({ recording }),
  setRecordedFrames: (recordedFrames) => set({ recordedFrames }),
  setCameraControls: (cameraControls) => set({ cameraControls }),
  toggleMirrored: () => set({ mirrored: !get().mirrored }),
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
    set({ report, reportStatus: 'ready' })
  },
  failReport: () => set({ reportStatus: 'error' }),
  closeReport: () => {
    markLastReportClosed()
    set({ reportOpen: false })
  },

  resetSession: () => set({ ...SESSION_DEFAULTS }),
  setError: (error) => set({ error }),

  resetPipeline: () =>
    set({
      poseStatus: 'idle',
      poseDelegate: null,
      probeStatus: 'idle',
      capability: null,
      landmarksDetected: 0,
      frameStats: null,
      armAngleDeg: null,
      recording: false,
      recordedFrames: 0,
    }),
}))
