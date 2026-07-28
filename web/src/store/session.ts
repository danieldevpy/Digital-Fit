// Estado da sessão em um único store (convenções §Código).
import { create } from 'zustand'
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
import type { CoachEntry } from '../session/coachCard'

export type CameraStatus = 'idle' | 'requesting' | 'ready' | 'denied' | 'error'
/**
 * `calibrating` é a preparação (SPEC-004): a câmera já roda e os frames já sobem, mas o
 * exercício ainda não vale. Quem decide a passagem para `running` é o servidor, via
 * `session.calibrated` — o cliente nunca começa a sessão por conta própria.
 */
export type SessionStatus = 'idle' | 'calibrating' | 'running' | 'completed'
export type PoseStatus = 'idle' | 'loading' | 'ready' | 'error'
export type ProbeStatus = 'idle' | 'running' | 'done' | 'error'

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
  cameraControls: { start: () => void; stop: () => void } | null

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
  /** epoch ms do primeiro frame enviado — só para saber há quanto tempo se está calibrando. */
  firstFrameAt: number | null
  sceneEntry: CoachEntry | null
  feedbackEntry: CoachEntry | null

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
  applyCalibrated: (at: number) => void
  applySessionStarted: (data: SessionStartedData, sessionId: string) => void
  applyRepDetected: (data: RepDetectedData) => void
  applyPhase: (phase: Phase) => void
  applySceneWarning: (entry: CoachEntry) => void
  applyFeedback: (entry: CoachEntry) => void
  applySessionCompleted: (data: SessionCompletedData) => void
  resetSession: () => void
  setError: (message: string | null) => void
  resetPipeline: () => void
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
  firstFrameAt: null,
  sceneEntry: null,
  feedbackEntry: null,
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
  gatewayStatus: 'idle',
  ...SESSION_DEFAULTS,
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

  applyCalibrated: (at) => {
    // Idempotente: o servidor emite uma vez, mas um reenvio não pode reiniciar o anel.
    if (get().startedAt !== null) return
    set({ startedAt: at, sessionStatus: 'running' })
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
