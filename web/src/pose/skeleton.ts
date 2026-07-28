// Geometria do esqueleto: funções puras (testáveis sem câmera) + o desenho no
// canvas, que é a única parte imperativa.
import { POSE_CONNECTIONS } from './landmarks'

/** Landmark normalizado 0–1 relativo ao frame (convenções §Unidades). */
export interface Landmark {
  x: number
  y: number
  z: number
  visibility?: number
}

export interface CanvasSize {
  width: number
  height: number
}

export interface CanvasPoint {
  x: number
  y: number
}

export interface Segment {
  from: CanvasPoint
  to: CanvasPoint
}

/** Limiar padrão de visibilidade (convenções §Unidades e medidas). */
export const DEFAULT_MIN_VISIBILITY = 0.5

/**
 * Landmark sem `visibility` conta como visível: nem todo provedor preenche o
 * campo, e esconder o esqueleto inteiro seria pior que desenhar demais.
 */
export function isVisible(landmark: Landmark, minVisibility = DEFAULT_MIN_VISIBILITY): boolean {
  return (landmark.visibility ?? 1) >= minVisibility
}

/** Normalizado 0–1 → pixels do canvas. */
export function toCanvasPoint(landmark: Landmark, size: CanvasSize): CanvasPoint {
  return { x: landmark.x * size.width, y: landmark.y * size.height }
}

export function visiblePoints(
  landmarks: readonly Landmark[],
  size: CanvasSize,
  minVisibility = DEFAULT_MIN_VISIBILITY,
): CanvasPoint[] {
  return landmarks.filter((l) => isVisible(l, minVisibility)).map((l) => toCanvasPoint(l, size))
}

/** Só entram segmentos cujas DUAS pontas existem e estão visíveis. */
export function visibleSegments(
  landmarks: readonly Landmark[],
  size: CanvasSize,
  minVisibility = DEFAULT_MIN_VISIBILITY,
): Segment[] {
  const segments: Segment[] = []
  for (const [fromIndex, toIndex] of POSE_CONNECTIONS) {
    const from = landmarks[fromIndex]
    const to = landmarks[toIndex]
    if (!from || !to) continue
    if (!isVisible(from, minVisibility) || !isVisible(to, minVisibility)) continue
    segments.push({ from: toCanvasPoint(from, size), to: toCanvasPoint(to, size) })
  }
  return segments
}

export interface DrawSkeletonOptions {
  minVisibility?: number
  lineColor?: string
  jointColor?: string
  lineWidth?: number
  jointRadius?: number
}

export function drawSkeleton(
  ctx: CanvasRenderingContext2D,
  landmarks: readonly Landmark[],
  options: DrawSkeletonOptions = {},
): void {
  const {
    minVisibility = DEFAULT_MIN_VISIBILITY,
    lineColor = '#22d3ee',
    jointColor = '#f8fafc',
    lineWidth = 4,
    jointRadius = 5,
  } = options

  const size: CanvasSize = { width: ctx.canvas.width, height: ctx.canvas.height }
  ctx.clearRect(0, 0, size.width, size.height)
  if (landmarks.length === 0) return

  ctx.lineWidth = lineWidth
  ctx.strokeStyle = lineColor
  ctx.lineCap = 'round'
  ctx.beginPath()
  for (const { from, to } of visibleSegments(landmarks, size, minVisibility)) {
    ctx.moveTo(from.x, from.y)
    ctx.lineTo(to.x, to.y)
  }
  ctx.stroke()

  ctx.fillStyle = jointColor
  for (const point of visiblePoints(landmarks, size, minVisibility)) {
    ctx.beginPath()
    ctx.arc(point.x, point.y, jointRadius, 0, Math.PI * 2)
    ctx.fill()
  }
}

export function clearCanvas(ctx: CanvasRenderingContext2D): void {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
}
