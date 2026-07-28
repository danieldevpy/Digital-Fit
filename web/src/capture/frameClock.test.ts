import { describe, expect, it } from 'vitest'
import { CLOUD_TARGET_FPS, EDGE_TARGET_FPS, createFrameClock, type FrameTick } from './frameClock'

/** Simula uma fonte de vídeo de `sourceFps` durante `seconds`, a partir de `startMs`. */
function run(clock: ReturnType<typeof createFrameClock>, sourceFps: number, seconds: number, startMs = 1_700_000_000_000) {
  const step = 1000 / sourceFps
  const ticks: FrameTick[] = []
  const total = Math.round(sourceFps * seconds)
  for (let i = 0; i < total; i++) {
    const tick = clock.tick(startMs + i * step)
    if (tick) ticks.push(tick)
  }
  return ticks
}

describe('createFrameClock', () => {
  it('rejeita fps alvo inválido', () => {
    expect(() => createFrameClock(0)).toThrow()
    expect(() => createFrameClock(-5)).toThrow()
    expect(() => createFrameClock(Number.NaN)).toThrow()
  })

  it('emite o primeiro frame imediatamente', () => {
    const clock = createFrameClock(EDGE_TARGET_FPS)
    expect(clock.tick(1_700_000_000_000)).toEqual({ ts: 1_700_000_000_000, seq: 0 })
  })
})

describe('decimação por tempo', () => {
  // A nota da SPEC-001 pede fps alvo estável com câmeras de 24 a 60fps.
  it.each([24, 30, 60])('mantém ~15fps com fonte de %ifps', (sourceFps) => {
    const ticks = run(createFrameClock(EDGE_TARGET_FPS), sourceFps, 4)
    const fps = ticks.length / 4
    expect(fps).toBeGreaterThanOrEqual(EDGE_TARGET_FPS - 1)
    expect(fps).toBeLessThanOrEqual(EDGE_TARGET_FPS + 1)
  })

  it('mantém ~10fps no alvo cloud', () => {
    const ticks = run(createFrameClock(CLOUD_TARGET_FPS), 30, 4)
    const fps = ticks.length / 4
    expect(fps).toBeGreaterThanOrEqual(CLOUD_TARGET_FPS - 1)
    expect(fps).toBeLessThanOrEqual(CLOUD_TARGET_FPS + 1)
  })

  it('não emite mais frames do que a fonte entrega', () => {
    const ticks = run(createFrameClock(EDGE_TARGET_FPS), 10, 2)
    expect(ticks.length).toBeLessThanOrEqual(20)
  })
})

describe('critério de aceite 3 da SPEC-001', () => {
  it('seq nunca repete nem retrocede', () => {
    const ticks = run(createFrameClock(EDGE_TARGET_FPS), 30, 5)
    const seqs = ticks.map((t) => t.seq)
    expect(new Set(seqs).size).toBe(seqs.length)
    for (let i = 1; i < seqs.length; i++) {
      expect(seqs[i]!).toBeGreaterThan(seqs[i - 1]!)
    }
    expect(seqs[0]).toBe(0)
  })

  it('Δ entre ts fica na faixa de ~66–100ms com fonte de 30fps', () => {
    const ticks = run(createFrameClock(EDGE_TARGET_FPS), 30, 5)
    for (let i = 1; i < ticks.length; i++) {
      const delta = ticks[i]!.ts - ticks[i - 1]!.ts
      expect(delta).toBeGreaterThanOrEqual(66)
      expect(delta).toBeLessThanOrEqual(100)
    }
  })

  it('ts é inteiro em epoch ms', () => {
    const clock = createFrameClock(EDGE_TARGET_FPS)
    const tick = clock.tick(1_700_000_000_123.7)!
    expect(Number.isInteger(tick.ts)).toBe(true)
    expect(tick.ts).toBe(1_700_000_000_124)
  })
})

describe('robustez', () => {
  it('pausa longa não vira rajada de frames', () => {
    const clock = createFrameClock(EDGE_TARGET_FPS)
    const start = 1_700_000_000_000
    clock.tick(start)
    // aba escondida por 3s: volta com um único frame, não com 45 atrasados
    const afterStall = clock.tick(start + 3000)
    expect(afterStall).not.toBeNull()
    expect(clock.tick(start + 3001)).toBeNull()
    expect(clock.emitted).toBe(2)
  })

  it('reset zera seq e o agendamento', () => {
    const clock = createFrameClock(EDGE_TARGET_FPS)
    run(clock, 30, 1)
    expect(clock.emitted).toBeGreaterThan(0)

    clock.reset()
    expect(clock.emitted).toBe(0)
    expect(clock.tick(1_700_000_099_000)).toEqual({ ts: 1_700_000_099_000, seq: 0 })
  })

  it('expõe o fps alvo configurado', () => {
    expect(createFrameClock(EDGE_TARGET_FPS).targetFps).toBe(15)
    expect(createFrameClock(CLOUD_TARGET_FPS).targetFps).toBe(10)
  })
})
