import { describe, expect, it } from 'vitest'
import { Mode } from '../lib/events'
import {
  EDGE_FPS_THRESHOLD,
  PROBE_WARMUP_SAMPLES,
  decideMode,
  detectWasmSimd,
  fpsSustentavel,
  mediana,
  parseModeOverride,
} from './capability'

const capable = { modelFps: 30, webgl: true, wasmSimd: true }

describe('decideMode', () => {
  it('escolhe edge em device capaz', () => {
    expect(decideMode(capable)).toEqual({ mode: Mode.EDGE, reason: 'probe_ok' })
  })

  it('usa 12fps como limiar, inclusive', () => {
    expect(EDGE_FPS_THRESHOLD).toBe(12)
    expect(decideMode({ ...capable, modelFps: 12 }).mode).toBe(Mode.EDGE)
    expect(decideMode({ ...capable, modelFps: 11.9 })).toEqual({
      mode: Mode.CLOUD,
      reason: 'probe_lento',
    })
  })

  // Critério de aceite 2 da SPEC-001.
  it('escolhe cloud sem WebGL', () => {
    expect(decideMode({ ...capable, webgl: false })).toEqual({
      mode: Mode.CLOUD,
      reason: 'sem_webgl',
    })
  })

  it('escolhe cloud sem WASM-SIMD', () => {
    expect(decideMode({ ...capable, wasmSimd: false })).toEqual({
      mode: Mode.CLOUD,
      reason: 'sem_simd',
    })
  })

  it('escolhe cloud quando o probe falhou', () => {
    expect(decideMode({ ...capable, failed: true })).toEqual({
      mode: Mode.CLOUD,
      reason: 'probe_falhou',
    })
  })

  /**
   * Regra invertida na T-084. Ausência de medida não é evidência contra o aparelho, e cloud
   * não conserta o caso: sem frame de câmera não há o que mandar ao servidor tampouco. Cloud
   * tem 3 vagas (SPEC-009) e queimá-las por falta de evidência tirava lugar de quem tem.
   */
  it('sem medição fica em edge, não em cloud', () => {
    expect(decideMode({ ...capable, modelFps: null })).toEqual({
      mode: Mode.EDGE,
      reason: 'sem_medida',
    })
    expect(decideMode({ ...capable, modelFps: Number.NaN }).mode).toBe(Mode.EDGE)
    expect(decideMode({ ...capable, modelFps: Number.POSITIVE_INFINITY }).mode).toBe(Mode.EDGE)
  })

  it('sem medição NÃO salva device sem WebGL ou sem SIMD', () => {
    expect(decideMode({ modelFps: null, webgl: false, wasmSimd: true }).mode).toBe(Mode.CLOUD)
    expect(decideMode({ modelFps: null, webgl: true, wasmSimd: false }).mode).toBe(Mode.CLOUD)
  })

  it('fps alto não salva device sem WebGL', () => {
    expect(decideMode({ modelFps: 120, webgl: false, wasmSimd: true }).mode).toBe(Mode.CLOUD)
  })
})

describe('mediana', () => {
  it('devolve o do meio em lista ímpar', () => {
    expect(mediana([30, 10, 20])).toBe(20)
  })

  it('devolve a média dos dois do meio em lista par', () => {
    expect(mediana([10, 20, 30, 40])).toBe(25)
  })

  it('ignora valores não finitos e devolve null sem amostra', () => {
    expect(mediana([Number.NaN, 10, Number.POSITIVE_INFINITY])).toBe(10)
    expect(mediana([])).toBeNull()
    expect(mediana([Number.NaN])).toBeNull()
  })
})

describe('fpsSustentavel', () => {
  it('converte latência mediana em fps', () => {
    // 3 amostras de aquecimento descartadas + 25ms de regime = 40fps.
    expect(fpsSustentavel([400, 380, 350, 25, 25, 25], 3)).toBeCloseTo(40, 5)
  })

  /**
   * O caso que motivou a T-084, com os dois jeitos de medir lado a lado.
   *
   * Um aparelho que roda a 25ms por inferência (40fps de regime) depois de três inferências
   * caras de compilação de shader. A régua antiga — frames contados sobre tempo de parede —
   * lia 4,9fps e mandava para cloud, porque as três primeiras sozinhas consumiam 1,5s da
   * janela. A régua nova lê 40fps, que é a verdade sobre o aparelho.
   */
  it('a régua antiga afundava com o aquecimento; a nova não', () => {
    const latencias = [500, 500, 500, 25, 25, 25, 25, 25]
    const totalMs = latencias.reduce((soma, ms) => soma + ms, 0)
    const reguaAntiga = (latencias.length * 1000) / totalMs
    expect(reguaAntiga).toBeLessThan(EDGE_FPS_THRESHOLD)
    expect(fpsSustentavel(latencias)).toBeCloseTo(40, 5)
  })

  it('um pico isolado não afunda a medida (mediana, não média)', () => {
    const latencias = [...Array<number>(PROBE_WARMUP_SAMPLES).fill(300), 25, 25, 900, 25, 25]
    expect(fpsSustentavel(latencias)).toBeCloseTo(40, 5)
  })

  it('devolve null quando não sobra amostra depois do aquecimento', () => {
    expect(fpsSustentavel([300, 300])).toBeNull()
    expect(fpsSustentavel([])).toBeNull()
  })

  it('devolve null com latência zero (relógio sem resolução)', () => {
    expect(fpsSustentavel([0, 0, 0, 0, 0, 0])).toBeNull()
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
