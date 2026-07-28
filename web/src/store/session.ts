// Estado da sessão em um único store (convenções §Código).
import { create } from 'zustand'
import type { Mode } from '../lib/events'
import type { PoseDelegate } from '../pose/poseLandmarker'
import type { ProbeOutcome } from '../probe/runProbe'

export type CameraStatus = 'idle' | 'requesting' | 'ready' | 'denied' | 'error'
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
  setError: (message: string | null) => void
  resetPipeline: () => void
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
  setError: (error) => set({ error }),

  resetPipeline: () =>
    set({
      poseStatus: 'idle',
      poseDelegate: null,
      probeStatus: 'idle',
      capability: null,
      landmarksDetected: 0,
      frameStats: null,
    }),
}))
