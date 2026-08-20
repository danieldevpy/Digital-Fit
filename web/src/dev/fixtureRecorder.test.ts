import { describe, expect, it } from 'vitest'
import type { FrameTick } from '../capture/frameClock'
import { LANDMARK_COUNT, Mode } from '../lib/events'
import type { Landmark } from '../pose/skeleton'
import { FIXTURE_SCHEMA, createFixtureRecorder, fixtureFileName } from './fixtureRecorder'

const META = { label: 'polichinelo' }

function pose(seed = 0): Landmark[] {
  return Array.from({ length: LANDMARK_COUNT }, (_, i) => ({
    x: (i + seed) / 100,
    y: i / 100,
    z: 0,
    visibility: 0.9,
  }))
}

function tick(seq: number): FrameTick {
  return { ts: 1_700_000_000_000 + seq * 67, seq }
}

function record(frameCount: number) {
  const recorder = createFixtureRecorder('sess-fixture')
  recorder.start()
  for (let i = 0; i < frameCount; i++) recorder.addFrame(tick(i), pose(i))
  return recorder
}

describe('gravação', () => {
  it('não grava nada antes de start', () => {
    const recorder = createFixtureRecorder('sess-1')
    recorder.addFrame(tick(0), pose())
    expect(recorder.frameCount).toBe(0)
    expect(recorder.isRecording).toBe(false)
  })

  it('grava frames entre start e stop', () => {
    const recorder = record(3)
    expect(recorder.frameCount).toBe(3)

    recorder.stop()
    recorder.addFrame(tick(99), pose())
    expect(recorder.frameCount).toBe(3)
  })

  it('descarta frame sem pose detectada', () => {
    const recorder = createFixtureRecorder('sess-1')
    recorder.start()
    recorder.addFrame(tick(0), [])
    expect(recorder.frameCount).toBe(0)
  })

  it('clear zera tudo e para a gravação', () => {
    const recorder = record(5)
    recorder.clear()
    expect(recorder.frameCount).toBe(0)
    expect(recorder.isRecording).toBe(false)
  })
})

// O schema é o de `workers/shared/keypoints.py`. Se algum campo sumir daqui,
// `load_fixture()` do lado Python quebra.
describe('schema de workers/shared/keypoints.py', () => {
  it('declara schema 1 e os campos de topo esperados', () => {
    const fixture = record(2).build(META)
    expect(fixture.schema).toBe(FIXTURE_SCHEMA)
    expect(Object.keys(fixture).sort()).toEqual(
      [
        'schema',
        'label',
        'exercise',
        'expected_reps',
        'source',
        'fps',
        'notes',
        // T-110: sem elas a normalização mede no espaço anisotrópico, e o gate do corpus
        // (`test_toda_fixture_declara_as_dimensoes_do_frame`) recusa a fixture.
        'width',
        'height',
        'conditions',
        'frames',
      ].sort(),
    )
  })

  it('leva as dimensões do vídeo para o topo, não só para conditions (T-110)', () => {
    const recorder = record(2)
    recorder.setContext({ video: { width: 576, height: 1024 } })

    const fixture = recorder.build(META)

    expect(fixture.width).toBe(576)
    expect(fixture.height).toBe(1024)
  })

  it('sem contexto de vídeo, declara null em vez de inventar dimensão', () => {
    const fixture = record(2).build(META)

    expect(fixture.width).toBeNull()
    expect(fixture.height).toBeNull()
  })

  it('cada frame é {ts, seq, landmarks} — nada de envelope', () => {
    const [first] = record(1).build(META).frames
    expect(Object.keys(first!).sort()).toEqual(['ts', 'seq', 'landmarks'].sort())
    expect(first!.landmarks).toHaveLength(LANDMARK_COUNT)
    for (const tuple of first!.landmarks) {
      expect(tuple).toHaveLength(4)
    }
  })

  it('grava landmarks CRUS com 5 casas decimais', () => {
    const recorder = createFixtureRecorder('sess-1')
    recorder.start()
    recorder.addFrame(tick(0), [
      ...Array.from({ length: LANDMARK_COUNT - 1 }, () => ({ x: 0, y: 0, z: 0, visibility: 1 })),
      { x: 0.123456789, y: 0.987654321, z: -0.5000004, visibility: 0.9123456 },
    ])
    const last = recorder.build(META).frames[0]!.landmarks[LANDMARK_COUNT - 1]!
    expect(last).toEqual([0.12346, 0.98765, -0.5, 0.91235])
  })

  it('preserva ts e seq do frame clock', () => {
    const { frames } = record(6).build(META)
    expect(frames.map((f) => f.seq)).toEqual([0, 1, 2, 3, 4, 5])
    for (let i = 1; i < frames.length; i++) {
      expect(frames[i]!.ts).toBeGreaterThan(frames[i - 1]!.ts)
    }
  })

  it('sobrevive a JSON.stringify sem perder nada', () => {
    const fixture = record(3).build(META)
    expect(JSON.parse(JSON.stringify(fixture))).toEqual(fixture)
  })
})

describe('metadados', () => {
  it('guarda contexto do device em conditions (campo livre do schema)', () => {
    const recorder = record(2)
    recorder.setContext({
      capability: {
        mode: Mode.EDGE,
        probe_fps: 27.5,
        webgl: true,
        ua: 'test-ua',
        facing: '',
        orientation: '',
      },
      video: { width: 640, height: 480 },
      fps: 15,
    })
    const fixture = recorder.build({ label: 'com-contexto', notes: 'luz baixa', expected_reps: 20 })

    expect(fixture.fps).toBe(15)
    expect(fixture.notes).toBe('luz baixa')
    expect(fixture.expected_reps).toBe(20)
    expect(fixture.source).toBe('camera')
    expect(fixture.conditions).toMatchObject({
      session_id: 'sess-fixture',
      video: { width: 640, height: 480 },
    })
  })

  it('usa nulos quando nada foi informado', () => {
    const fixture = record(1).build(META)
    expect(fixture.fps).toBeNull()
    expect(fixture.notes).toBeNull()
    expect(fixture.expected_reps).toBeNull()
  })

  it('rótulo vazio vira "sem-rotulo", igual ao default do Python', () => {
    expect(record(1).build({ label: '   ' }).label).toBe('sem-rotulo')
  })
})

describe('fixtureFileName', () => {
  it('usa rótulo e timestamp ordenável', () => {
    const fixture = record(1).build({ label: 'Polichinelo Limpo' })
    expect(fixtureFileName(fixture)).toMatch(
      /^polichinelo-limpo-\d{4}-\d{2}-\d{2}T[\d-]+\.json$/,
    )
  })
})
