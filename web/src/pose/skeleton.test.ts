import { describe, expect, it } from 'vitest'
import { POSE_CONNECTIONS, POSE_LANDMARK_COUNT } from './landmarks'
import {
  DEFAULT_MIN_VISIBILITY,
  isVisible,
  toCanvasPoint,
  visiblePoints,
  visibleSegments,
  type Landmark,
} from './skeleton'

const SIZE = { width: 640, height: 480 }

function landmark(overrides: Partial<Landmark> = {}): Landmark {
  return { x: 0.5, y: 0.5, z: 0, visibility: 1, ...overrides }
}

/** Pose completa e visível: 33 landmarks espalhados de forma determinística. */
function fullPose(visibility = 1): Landmark[] {
  return Array.from({ length: POSE_LANDMARK_COUNT }, (_, i) =>
    landmark({ x: i / POSE_LANDMARK_COUNT, y: 1 - i / POSE_LANDMARK_COUNT, visibility }),
  )
}

describe('POSE_CONNECTIONS', () => {
  it('só referencia índices dentro dos 33 landmarks do MediaPipe', () => {
    for (const [from, to] of POSE_CONNECTIONS) {
      expect(from).toBeGreaterThanOrEqual(0)
      expect(to).toBeGreaterThanOrEqual(0)
      expect(from).toBeLessThan(POSE_LANDMARK_COUNT)
      expect(to).toBeLessThan(POSE_LANDMARK_COUNT)
      expect(from).not.toBe(to)
    }
  })

  it('não tem conexões duplicadas', () => {
    const keys = POSE_CONNECTIONS.map(([a, b]) => [a, b].sort((x, y) => x - y).join('-'))
    expect(new Set(keys).size).toBe(keys.length)
  })
})

describe('isVisible', () => {
  it('usa 0.5 como limiar padrão', () => {
    expect(DEFAULT_MIN_VISIBILITY).toBe(0.5)
    expect(isVisible(landmark({ visibility: 0.5 }))).toBe(true)
    expect(isVisible(landmark({ visibility: 0.49 }))).toBe(false)
  })

  it('trata landmark sem visibility como visível', () => {
    expect(isVisible({ x: 0, y: 0, z: 0 })).toBe(true)
  })

  it('respeita limiar customizado', () => {
    expect(isVisible(landmark({ visibility: 0.7 }), 0.8)).toBe(false)
    expect(isVisible(landmark({ visibility: 0.9 }), 0.8)).toBe(true)
  })
})

describe('toCanvasPoint', () => {
  it('converte normalizado 0–1 para pixels', () => {
    expect(toCanvasPoint(landmark({ x: 0, y: 0 }), SIZE)).toEqual({ x: 0, y: 0 })
    expect(toCanvasPoint(landmark({ x: 1, y: 1 }), SIZE)).toEqual({ x: 640, y: 480 })
    expect(toCanvasPoint(landmark({ x: 0.25, y: 0.5 }), SIZE)).toEqual({ x: 160, y: 240 })
  })
})

describe('visibleSegments', () => {
  it('desenha todas as conexões quando a pose está inteira', () => {
    expect(visibleSegments(fullPose(), SIZE)).toHaveLength(POSE_CONNECTIONS.length)
  })

  it('não desenha nada quando tudo está abaixo do limiar', () => {
    expect(visibleSegments(fullPose(0.2), SIZE)).toHaveLength(0)
  })

  it('descarta o segmento se qualquer uma das pontas estiver invisível', () => {
    const pose = fullPose()
    // 11 = ombro esquerdo, presente em [11,12], [11,13] e [11,23].
    pose[11] = landmark({ visibility: 0.1 })
    const segments = visibleSegments(pose, SIZE)
    expect(segments).toHaveLength(POSE_CONNECTIONS.length - 3)
  })

  it('ignora conexões com índice ausente (pose parcial)', () => {
    const pose = fullPose().slice(0, 12)
    const expected = POSE_CONNECTIONS.filter(([a, b]) => a < 12 && b < 12).length
    expect(visibleSegments(pose, SIZE)).toHaveLength(expected)
  })

  it('devolve pontos já em pixels', () => {
    const pose = fullPose()
    const [segment] = visibleSegments(pose, SIZE)
    expect(segment).toBeDefined()
    expect(segment!.from.x).toBeGreaterThanOrEqual(0)
    expect(segment!.from.x).toBeLessThanOrEqual(SIZE.width)
    expect(segment!.to.y).toBeLessThanOrEqual(SIZE.height)
  })
})

describe('visiblePoints', () => {
  it('filtra pelo limiar de visibilidade', () => {
    const pose = fullPose()
    pose[0] = landmark({ visibility: 0.1 })
    pose[1] = landmark({ visibility: 0.1 })
    expect(visiblePoints(pose, SIZE)).toHaveLength(POSE_LANDMARK_COUNT - 2)
  })

  it('devolve vazio para pose vazia', () => {
    expect(visiblePoints([], SIZE)).toEqual([])
  })
})
