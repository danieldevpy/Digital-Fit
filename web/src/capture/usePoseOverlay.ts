// Liga o vídeo ao MediaPipe e desenha o esqueleto sobre ele (T-003).
//
// O loop aqui é um requestAnimationFrame cru, de propósito: o frame clock real
// (requestVideoFrameCallback, decimação por tempo para 15fps, `ts`/`seq`) é a
// T-004 e substitui este loop.
import { useEffect, useRef, type RefObject } from 'react'
import type { PoseLandmarker } from '@mediapipe/tasks-vision'
import { createEdgePoseLandmarker, detectPose } from '../pose/poseLandmarker'
import { clearCanvas, drawSkeleton } from '../pose/skeleton'
import { useSessionStore } from '../store/session'

export function usePoseOverlay(
  videoRef: RefObject<HTMLVideoElement | null>,
  canvasRef: RefObject<HTMLCanvasElement | null>,
  enabled: boolean,
) {
  const landmarkerRef = useRef<PoseLandmarker | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!enabled || !canvas) return

    const { setPoseStatus, setPoseDelegate, setLandmarksDetected, setError } =
      useSessionStore.getState()

    let animationFrame = 0
    let disposed = false
    let lastVideoTime = -1

    const renderLoop = () => {
      animationFrame = requestAnimationFrame(renderLoop)

      const video = videoRef.current
      const landmarker = landmarkerRef.current
      if (!video || !landmarker) return
      if (video.readyState < video.HAVE_CURRENT_DATA || video.videoWidth === 0) return

      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
      }

      // MediaPipe exige timestamps crescentes; repetir o mesmo frame o quebra.
      if (video.currentTime === lastVideoTime) return
      lastVideoTime = video.currentTime

      const context = canvas.getContext('2d')
      if (!context) return

      const landmarks = detectPose(landmarker, video, performance.now())
      drawSkeleton(context, landmarks)
      setLandmarksDetected(landmarks.length)
    }

    setPoseStatus('loading')
    createEdgePoseLandmarker()
      .then(({ landmarker, delegate }) => {
        if (disposed) {
          landmarker.close()
          return
        }
        landmarkerRef.current = landmarker
        setPoseDelegate(delegate)
        setPoseStatus('ready')
        animationFrame = requestAnimationFrame(renderLoop)
      })
      .catch((error: unknown) => {
        if (disposed) return
        setPoseStatus('error')
        setError(
          error instanceof Error
            ? `Falha ao carregar o modelo de pose: ${error.message}`
            : 'Falha ao carregar o modelo de pose.',
        )
      })

    return () => {
      disposed = true
      cancelAnimationFrame(animationFrame)
      landmarkerRef.current?.close()
      landmarkerRef.current = null
      const context = canvas.getContext('2d')
      if (context) clearCanvas(context)
      setLandmarksDetected(0)
      setPoseStatus('idle')
    }
  }, [enabled, videoRef, canvasRef])
}
