// Geometria do esqueleto: funções puras (testáveis sem câmera) + o desenho no
// canvas, que é a única parte imperativa.
import { BODY_CONNECTIONS, BODY_JOINTS, POSE_CONNECTIONS } from './landmarks'

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

/** Token `--skeleton` da SPEC-013 (o canvas não enxerga variáveis CSS). */
export const SKELETON_COLOR = '#eaf2ff'
export const SKELETON_GLOW = 'rgba(124, 92, 255, 0.85)'

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

/** `indices` limita quais landmarks entram (ex.: só o corpo, sem rosto). */
export function visiblePoints(
  landmarks: readonly Landmark[],
  size: CanvasSize,
  minVisibility = DEFAULT_MIN_VISIBILITY,
  indices?: readonly number[],
): CanvasPoint[] {
  const selected = indices
    ? indices.map((index) => landmarks[index]).filter((l): l is Landmark => l !== undefined)
    : landmarks
  return selected.filter((l) => isVisible(l, minVisibility)).map((l) => toCanvasPoint(l, size))
}

/** Só entram segmentos cujas DUAS pontas existem e estão visíveis. */
export function visibleSegments(
  landmarks: readonly Landmark[],
  size: CanvasSize,
  minVisibility = DEFAULT_MIN_VISIBILITY,
  connections: readonly (readonly [number, number])[] = POSE_CONNECTIONS,
): Segment[] {
  const segments: Segment[] = []
  for (const [fromIndex, toIndex] of connections) {
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
  connections?: readonly (readonly [number, number])[]
  joints?: readonly number[]
  lineColor?: string
  jointColor?: string
  glowColor?: string
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
    connections = BODY_CONNECTIONS,
    joints = BODY_JOINTS,
    // `--skeleton` da SPEC-013. O canvas está em pixels de VÍDEO (640px), não de
    // CSS (~430px no celular), então 3 aqui é o "~2px" que a spec pede na tela.
    lineColor = SKELETON_COLOR,
    jointColor = SKELETON_COLOR,
    glowColor = SKELETON_GLOW,
    lineWidth = 3,
    jointRadius = 6,
  } = options

  const size: CanvasSize = { width: ctx.canvas.width, height: ctx.canvas.height }
  ctx.clearRect(0, 0, size.width, size.height)
  if (landmarks.length === 0) return

  ctx.save()
  ctx.shadowColor = glowColor
  ctx.shadowBlur = 12

  ctx.lineWidth = lineWidth
  ctx.strokeStyle = lineColor
  ctx.lineCap = 'round'
  ctx.beginPath()
  for (const { from, to } of visibleSegments(landmarks, size, minVisibility, connections)) {
    ctx.moveTo(from.x, from.y)
    ctx.lineTo(to.x, to.y)
  }
  ctx.stroke()

  // Articulações com halo mais forte que os segmentos.
  ctx.shadowBlur = 18
  ctx.fillStyle = jointColor
  for (const point of visiblePoints(landmarks, size, minVisibility, joints)) {
    ctx.beginPath()
    ctx.arc(point.x, point.y, jointRadius, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.restore()
}

export function clearCanvas(ctx: CanvasRenderingContext2D): void {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
}
