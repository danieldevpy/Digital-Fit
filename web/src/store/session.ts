// Estado da sessão em um único store (convenções §Código).
// Por ora só o necessário para a T-003: estados de câmera e do modelo de pose.
import { create } from 'zustand'
import type { PoseDelegate } from '../pose/poseLandmarker'

export type CameraStatus = 'idle' | 'requesting' | 'ready' | 'denied' | 'error'
export type PoseStatus = 'idle' | 'loading' | 'ready' | 'error'

export interface SessionState {
  cameraStatus: CameraStatus
  poseStatus: PoseStatus
  poseDelegate: PoseDelegate | null
  /** Resolução realmente entregue pelo device (pode diferir da preferida). */
  videoResolution: { width: number; height: number } | null
  landmarksDetected: number
  error: string | null

  setCameraStatus: (status: CameraStatus) => void
  setPoseStatus: (status: PoseStatus) => void
  setPoseDelegate: (delegate: PoseDelegate) => void
  setVideoResolution: (resolution: { width: number; height: number }) => void
  setLandmarksDetected: (count: number) => void
  setError: (message: string | null) => void
}

export const useSessionStore = create<SessionState>((set) => ({
  cameraStatus: 'idle',
  poseStatus: 'idle',
  poseDelegate: null,
  videoResolution: null,
  landmarksDetected: 0,
  error: null,

  setCameraStatus: (cameraStatus) => set({ cameraStatus }),
  setPoseStatus: (poseStatus) => set({ poseStatus }),
  setPoseDelegate: (poseDelegate) => set({ poseDelegate }),
  setVideoResolution: (videoResolution) => set({ videoResolution }),
  setLandmarksDetected: (landmarksDetected) => set({ landmarksDetected }),
  setError: (error) => set({ error }),
}))
