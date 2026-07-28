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
export type SessionStatus = 'idle' | 'running' | 'completed'
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
  frameStats: FrameStats | null
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
  /** epoch ms do `session.started` — base do countdown cosmético. */
  startedAt: number | null
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
  setFrameStats: (stats: FrameStats | null) => void
  setRecording: (recording: boolean) => void
  setRecordedFrames: (count: number) => void
  setCameraControls: (controls: SessionState['cameraControls']) => void
  setGatewayStatus: (status: GatewayStatus) => void
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
  sceneEntry: null,
  feedbackEntry: null,
}

export const useSessionStore = create<SessionState>((set) => ({
  cameraStatus: 'idle',
  poseStatus: 'idle',
  poseDelegate: null,
  probeStatus: 'idle',
  capability: null,
  modeOverride: null,
  videoResolution: null,
  landmarksDetected: 0,
  frameStats: null,
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
  setFrameStats: (frameStats) => set({ frameStats }),
  setRecording: (recording) => set({ recording }),
  setRecordedFrames: (recordedFrames) => set({ recordedFrames }),
  setCameraControls: (cameraControls) => set({ cameraControls }),
  setGatewayStatus: (gatewayStatus) => set({ gatewayStatus }),

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
      recording: false,
      recordedFrames: 0,
    }),
}))
