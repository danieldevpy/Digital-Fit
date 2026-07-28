import { describe, expect, it } from 'vitest'
import { createClientSequencer } from './clientSequencer'
import { MAX_QUEUED_FRAMES } from './gateway'

describe('createClientSequencer', () => {
  // Contrato: "contador monotônico por sessão (nunca repete nem retrocede)".
  it('começa em 0 e não repete', () => {
    const seq = createClientSequencer()
    expect([seq.next(), seq.next(), seq.next()]).toEqual([0, 1, 2])
  })

  it('nunca retrocede', () => {
    const seq = createClientSequencer()
    const valores = Array.from({ length: 200 }, () => seq.next())
    expect(new Set(valores).size).toBe(valores.length)
    for (let i = 1; i < valores.length; i++) {
      expect(valores[i]!).toBeGreaterThan(valores[i - 1]!)
    }
  })

  it('é compartilhado entre tipos de evento: capability e frames não colidem', () => {
    const seq = createClientSequencer()
    const capability = seq.next()
    const frames = [seq.next(), seq.next(), seq.next()]
    expect(frames).not.toContain(capability)
    expect(Math.min(...frames)).toBeGreaterThan(capability)
  })

  it('expõe o próximo valor sem consumir', () => {
    const seq = createClientSequencer()
    seq.next()
    expect(seq.current).toBe(1)
    expect(seq.current).toBe(1)
  })

  it('reset recomeça a sessão do zero', () => {
    const seq = createClientSequencer()
    seq.next()
    seq.next()
    seq.reset()
    expect(seq.next()).toBe(0)
  })
})

describe('backpressure', () => {
  it('o limite é o da SPEC-002: 3 frames', () => {
    expect(MAX_QUEUED_FRAMES).toBe(3)
  })
})
