import { describe, expect, it } from 'vitest'
import { POSE_LANDMARK_COUNT, POSE_LANDMARK_NAMES } from '../pose/landmarks'
import {
  CLIENT_PUSH_TYPES,
  EventType,
  LANDMARK_COUNT,
  LANDMARK_NAMES,
  Mode,
  PROTOCOL_VERSION,
  Source,
  isValidEnvelope,
  makeEnvelope,
  toLandmarkTuples,
} from './events'

const validEnvelope = () =>
  makeEnvelope({
    type: EventType.SESSION_CAPABILITY,
    session_id: 'sess-1',
    ts: 1_700_000_000_000,
    seq: 0,
    source: Source.EDGE,
    data: { mode: Mode.EDGE, probe_fps: 28.4, webgl: true, ua: 'test' },
  })

// Este bloco existe para pegar drift: se o Agente A mudar events.py e o espelho
// não acompanhar, é aqui que quebra primeiro.
describe('espelho do contrato', () => {
  it('mantém a versão de protocolo do contrato', () => {
    expect(PROTOCOL_VERSION).toBe(1)
  })

  it('tem os 33 landmarks na mesma ordem usada no desenho', () => {
    expect(LANDMARK_COUNT).toBe(33)
    expect(LANDMARK_NAMES).toHaveLength(LANDMARK_COUNT)
    expect(POSE_LANDMARK_COUNT).toBe(LANDMARK_COUNT)
    expect([...POSE_LANDMARK_NAMES]).toEqual([...LANDMARK_NAMES])
  })

  it('só empurra ao cliente os tipos previstos no contrato', () => {
    expect([...CLIENT_PUSH_TYPES].sort()).toEqual(
      [
        EventType.EXERCISE_PHASE,
        EventType.REP_DETECTED,
        EventType.SCENE_WARNING,
        EventType.FEEDBACK_ISSUED,
        EventType.SESSION_COMPLETED,
      ].sort(),
    )
  })

  it('não empurra pose.frame nem quality.signal ao cliente', () => {
    expect(CLIENT_PUSH_TYPES).not.toContain(EventType.POSE_FRAME)
    expect(CLIENT_PUSH_TYPES).not.toContain(EventType.QUALITY_SIGNAL)
  })
})

describe('makeEnvelope', () => {
  it('preenche v com a versão do protocolo', () => {
    expect(validEnvelope().v).toBe(PROTOCOL_VERSION)
  })

  it('mantém as chaves do envelope em snake_case', () => {
    expect(Object.keys(validEnvelope()).sort()).toEqual(
      ['v', 'type', 'session_id', 'ts', 'seq', 'source', 'data'].sort(),
    )
  })
})

describe('isValidEnvelope', () => {
  it('aceita envelope bem formado', () => {
    expect(isValidEnvelope(validEnvelope())).toBe(true)
  })

  it.each([
    ['type desconhecido', { type: 'pose.inventado' }],
    ['session_id vazio', { session_id: '' }],
    ['ts zero', { ts: 0 }],
    ['ts negativo', { ts: -1 }],
    ['ts fracionário', { ts: 1_700_000_000_000.5 }],
    ['seq negativo', { seq: -1 }],
    ['source inválido', { source: 'browser' }],
    ['versão errada', { v: 2 }],
    ['data não-objeto', { data: 'x' }],
  ])('rejeita %s', (_label, override) => {
    expect(isValidEnvelope({ ...validEnvelope(), ...override })).toBe(false)
  })

  it('rejeita valores que nem são objeto', () => {
    expect(isValidEnvelope(null)).toBe(false)
    expect(isValidEnvelope('envelope')).toBe(false)
    expect(isValidEnvelope(42)).toBe(false)
  })
})

describe('toLandmarkTuples', () => {
  it('converte para [x, y, z, visibility]', () => {
    expect(toLandmarkTuples([{ x: 0.1, y: 0.2, z: 0.3, visibility: 0.9 }])).toEqual([
      [0.1, 0.2, 0.3, 0.9],
    ])
  })

  it('usa 0 quando o provedor não manda visibility', () => {
    expect(toLandmarkTuples([{ x: 0, y: 0, z: 0 }])).toEqual([[0, 0, 0, 0]])
  })

  it('preserva a ordem dos landmarks', () => {
    const input = Array.from({ length: LANDMARK_COUNT }, (_, i) => ({
      x: i,
      y: 0,
      z: 0,
      visibility: 1,
    }))
    const tuples = toLandmarkTuples(input)
    expect(tuples).toHaveLength(LANDMARK_COUNT)
    expect(tuples.map((t) => t[0])).toEqual(input.map((l) => l.x))
  })
})
