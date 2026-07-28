import { describe, expect, it } from 'vitest'
import { LANDMARK_COUNT } from '../lib/events'
import parity from './__fixtures__/arm-angle-parity.json'
import { abduction, armAngle, armAngleFromTuples } from './angles'
import { createArmAngleTracker } from './armAngleTracker'
import type { Landmark } from './skeleton'

/** Tolerância do critério de aceite 4 da SPEC-013. */
const MAX_DELTA_DEGREES = 5

interface ParitySample {
  ts: number
  seq: number
  landmarks: number[][]
  expected_arm_angle: number
}

interface ParityCase {
  case: string
  samples: ParitySample[]
}

const cases = parity.cases as ParityCase[]

function landmark(x: number, y: number): Landmark {
  return { x, y, z: 0, visibility: 1 }
}

function toLandmarks(tuples: number[][]): Landmark[] {
  return tuples.map((t) => ({ x: t[0]!, y: t[1]!, z: t[2]!, visibility: t[3] }))
}

describe('abduction', () => {
  // y cresce para baixo, então braço para baixo = dy positivo.
  it('0° com o braço estendido para baixo', () => {
    expect(abduction(landmark(0.5, 0.3), landmark(0.5, 0.8))).toBeCloseTo(0, 5)
  })

  it('90° com o braço na horizontal', () => {
    expect(abduction(landmark(0.5, 0.3), landmark(0.9, 0.3))).toBeCloseTo(90, 5)
  })

  it('180° com o braço reto acima da cabeça', () => {
    expect(abduction(landmark(0.5, 0.5), landmark(0.5, 0.1))).toBeCloseTo(180, 5)
  })

  it('é simétrico: lado do braço não muda o ângulo', () => {
    expect(abduction(landmark(0.5, 0.5), landmark(0.2, 0.2))).toBeCloseTo(
      abduction(landmark(0.5, 0.5), landmark(0.8, 0.2)),
      10,
    )
  })
})

describe('armAngle', () => {
  it('devolve null com pose incompleta', () => {
    expect(armAngle([])).toBeNull()
    expect(armAngle(Array.from({ length: 12 }, () => landmark(0, 0)))).toBeNull()
  })

  it('faz a média dos dois braços', () => {
    const pose = Array.from({ length: LANDMARK_COUNT }, () => landmark(0.5, 0.5))
    pose[11] = landmark(0.45, 0.4) // ombro esq.
    pose[15] = landmark(0.45, 0.8) // pulso esq. → 0°
    pose[12] = landmark(0.55, 0.4) // ombro dir.
    pose[16] = landmark(0.95, 0.4) // pulso dir. → 90°
    expect(armAngle(pose)).toBeCloseTo(45, 5)
  })

  it('aceita landmarks no formato do contrato', () => {
    const tuples = Array.from({ length: LANDMARK_COUNT }, () => [0.5, 0.5, 0, 1])
    tuples[11] = [0.45, 0.4, 0, 1]
    tuples[15] = [0.45, 0.8, 0, 1]
    tuples[12] = [0.55, 0.4, 0, 1]
    tuples[16] = [0.95, 0.4, 0, 1]
    expect(armAngleFromTuples(tuples)).toBeCloseTo(45, 5)
  })
})

// Critério de aceite 4 da SPEC-013: "ângulo exibido difere < 5° do calculado
// pelo worker para a mesma sequência (fixture de teste)".
//
// A fixture não é um número que eu escolhi: `expected_arm_angle` é a saída do
// JumpingJackAnalyzer real do Agente A rodando sobre os frames normalizados.
describe('paridade com a FSM do worker', () => {
  it('a fixture cobre a amplitude do movimento', () => {
    const angles = cases.flatMap((c) => c.samples.map((s) => s.expected_arm_angle))
    expect(angles.length).toBeGreaterThan(100)
    expect(Math.min(...angles)).toBeLessThan(20)
    expect(Math.max(...angles)).toBeGreaterThan(150)
  })

  it.each(cases.map((c) => c.case))('fica dentro de 5° do worker no caso %s', (caseName) => {
    const found = cases.find((c) => c.case === caseName)!
    // Um tracker por caso: cada caso é uma sessão, e o filtro tem estado de sessão.
    const tracker = createArmAngleTracker()

    const deltas = found.samples.map((sample) => {
      const mine = tracker.push(toLandmarks(sample.landmarks), sample.ts)
      expect(mine).not.toBeNull()
      return Math.abs(mine! - sample.expected_arm_angle)
    })

    expect(Math.max(...deltas)).toBeLessThan(MAX_DELTA_DEGREES)
  })

  it('sem o filtro o erro estoura a tolerância — é por isso que ele existe', () => {
    const found = cases[0]!
    const cru = found.samples.map((s) =>
      Math.abs(armAngleFromTuples(s.landmarks)! - s.expected_arm_angle),
    )
    expect(Math.max(...cru)).toBeGreaterThan(MAX_DELTA_DEGREES)
  })
})

describe('createArmAngleTracker', () => {
  it('devolve null com pose incompleta', () => {
    expect(createArmAngleTracker().push([], 1000)).toBeNull()
  })

  it('reset devolve o tracker ao estado inicial', () => {
    const samples = cases[0]!.samples
    const a = createArmAngleTracker()
    const b = createArmAngleTracker()

    for (const s of samples.slice(0, 10)) a.push(toLandmarks(s.landmarks), s.ts)
    a.reset()

    const first = samples[0]!
    expect(a.push(toLandmarks(first.landmarks), first.ts)).toBeCloseTo(
      b.push(toLandmarks(first.landmarks), first.ts)!,
      10,
    )
  })
})
