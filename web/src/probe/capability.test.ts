import { describe, expect, it } from 'vitest'
import { Mode } from '../lib/events'
import { EDGE_FPS_THRESHOLD, decideMode, detectWasmSimd, parseModeOverride } from './capability'

const capable = { probeFps: 30, webgl: true, wasmSimd: true }

describe('decideMode', () => {
  it('escolhe edge em device capaz', () => {
    expect(decideMode(capable)).toBe(Mode.EDGE)
  })

  it('usa 12fps como limiar, inclusive', () => {
    expect(EDGE_FPS_THRESHOLD).toBe(12)
    expect(decideMode({ ...capable, probeFps: 12 })).toBe(Mode.EDGE)
    expect(decideMode({ ...capable, probeFps: 11.9 })).toBe(Mode.CLOUD)
  })

  // Critério de aceite 2 da SPEC-001.
  it('escolhe cloud sem WebGL', () => {
    expect(decideMode({ ...capable, webgl: false })).toBe(Mode.CLOUD)
  })

  it('escolhe cloud sem WASM-SIMD', () => {
    expect(decideMode({ ...capable, wasmSimd: false })).toBe(Mode.CLOUD)
  })

  it('escolhe cloud quando o probe falhou', () => {
    expect(decideMode({ ...capable, failed: true })).toBe(Mode.CLOUD)
  })

  it('escolhe cloud quando não houve medição', () => {
    expect(decideMode({ ...capable, probeFps: null })).toBe(Mode.CLOUD)
    expect(decideMode({ ...capable, probeFps: Number.NaN })).toBe(Mode.CLOUD)
    expect(decideMode({ ...capable, probeFps: Number.POSITIVE_INFINITY })).toBe(Mode.CLOUD)
  })

  it('fps alto não salva device sem WebGL', () => {
    expect(decideMode({ probeFps: 120, webgl: false, wasmSimd: true })).toBe(Mode.CLOUD)
  })
})

describe('parseModeOverride', () => {
  // Critério de aceite 4 da SPEC-001.
  it('lê ?mode=cloud e ?mode=edge', () => {
    expect(parseModeOverride('?mode=cloud')).toBe(Mode.CLOUD)
    expect(parseModeOverride('?mode=edge')).toBe(Mode.EDGE)
  })

  it('aceita caixa alta e espaços', () => {
    expect(parseModeOverride('?mode=CLOUD')).toBe(Mode.CLOUD)
    expect(parseModeOverride('?mode=%20edge%20')).toBe(Mode.EDGE)
  })

  it('ignora valor inválido ou ausente', () => {
    expect(parseModeOverride('?mode=turbo')).toBeNull()
    expect(parseModeOverride('?mode=')).toBeNull()
    expect(parseModeOverride('')).toBeNull()
    expect(parseModeOverride('?outro=cloud')).toBeNull()
  })

  it('convive com outros parâmetros', () => {
    expect(parseModeOverride('?debug=1&mode=cloud&x=2')).toBe(Mode.CLOUD)
  })
})

describe('detectWasmSimd', () => {
  it('não lança e devolve booleano', () => {
    expect(typeof detectWasmSimd()).toBe('boolean')
  })

  it('reconhece SIMD no runtime de teste (Node moderno tem)', () => {
    expect(detectWasmSimd()).toBe(true)
  })
})
