import { describe, expect, it } from 'vitest'
import type { FrameTick } from '../capture/frameClock'
import { EventType, LANDMARK_COUNT, Mode, Source, isValidEnvelope } from '../lib/events'
import type { Landmark } from '../pose/skeleton'
import {
  FIXTURE_FORMAT,
  FIXTURE_VERSION,
  createFixtureRecorder,
  fixtureFileName,
} from './fixtureRecorder'

const META = { label: 'polichinelo', notes: '' }

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

describe('formato do contrato', () => {
  it('gera envelopes pose.frame válidos', () => {
    const { events } = record(4).build(META)
    expect(events).toHaveLength(4)
    for (const envelope of events) {
      expect(isValidEnvelope(envelope)).toBe(true)
      expect(envelope.type).toBe(EventType.POSE_FRAME)
      expect(envelope.source).toBe(Source.EDGE)
      expect(envelope.session_id).toBe('sess-fixture')
    }
  })

  it('cada frame carrega os 33 landmarks como [x, y, z, visibility]', () => {
    const [first] = record(1).build(META).events
    expect(first!.data.landmarks).toHaveLength(LANDMARK_COUNT)
    for (const tuple of first!.data.landmarks) {
      expect(tuple).toHaveLength(4)
      expect(tuple.every((value) => typeof value === 'number')).toBe(true)
    }
  })

  it('preserva ts e seq do frame clock — é o que vira RawFrame no Python', () => {
    const { events } = record(6).build(META)
    expect(events.map((e) => e.seq)).toEqual([0, 1, 2, 3, 4, 5])
    for (let i = 1; i < events.length; i++) {
      expect(events[i]!.seq).toBeGreaterThan(events[i - 1]!.seq)
      expect(events[i]!.ts).toBeGreaterThan(events[i - 1]!.ts)
    }
  })

  it('sobrevive a JSON.stringify sem perder nada', () => {
    const fixture = record(3).build(META)
    expect(JSON.parse(JSON.stringify(fixture))).toEqual(fixture)
  })
})

describe('embalagem da fixture', () => {
  it('marca formato e versão', () => {
    const fixture = record(1).build(META)
    expect(fixture.format).toBe(FIXTURE_FORMAT)
    expect(fixture.version).toBe(FIXTURE_VERSION)
    expect(() => new Date(fixture.recorded_at).toISOString()).not.toThrow()
  })

  it('guarda contexto do device fora dos envelopes', () => {
    const recorder = record(2)
    recorder.setContext({
      capability: { mode: Mode.EDGE, probe_fps: 27.5, webgl: true, ua: 'test-ua' },
      video: { width: 640, height: 480 },
      target_fps: 15,
    })
    const fixture = recorder.build({ label: 'com-contexto', notes: 'luz baixa' })

    expect(fixture.capability?.probe_fps).toBe(27.5)
    expect(fixture.video).toEqual({ width: 640, height: 480 })
    expect(fixture.target_fps).toBe(15)
    expect(fixture.notes).toBe('luz baixa')
    // O contexto não contamina os envelopes.
    expect(Object.keys(fixture.events[0]!.data)).toEqual(['landmarks'])
  })

  it('começa sem contexto quando nada foi informado', () => {
    const fixture = record(1).build(META)
    expect(fixture.capability).toBeNull()
    expect(fixture.video).toBeNull()
    expect(fixture.target_fps).toBeNull()
  })
})

describe('fixtureFileName', () => {
  it('usa rótulo e timestamp ordenável', () => {
    const fixture = record(1).build({ label: 'Polichinelo Limpo', notes: '' })
    const name = fixtureFileName(fixture)
    expect(name).toMatch(/^polichinelo-limpo-\d{4}-\d{2}-\d{2}T[\d-]+\.json$/)
  })

  it('cai para um nome genérico se o rótulo estiver vazio', () => {
    const fixture = record(1).build({ label: '   ', notes: '' })
    expect(fixtureFileName(fixture)).toMatch(/^fixture-/)
  })
})
