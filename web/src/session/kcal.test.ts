// Critério 3 da SPEC-016 e os dois sub-critérios que a T-128 acrescentou:
//
//   3.1 o número não anda sem repetição;
//   3.2 ritmo acima da referência rende mais por repetição, dentro de uma faixa travada.
//
// A segunda metade do critério 3 ("nenhuma tela do Free soma kcal entre sessões") é uma
// propriedade da arquitetura, não desta função: o módulo não tem estado, então não há onde
// somar. O teste `mesmo estado, mesmo número` é o que cobra isso aqui.
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useI18nStore } from '../i18n/store'
import {
  DEFAULT_WEIGHT_KG,
  formatKcal,
  intensityMultiplier,
  kcalPerRep,
  liveCadenceRpm,
  liveKcal,
} from './kcal'

/** Polichinelo como o servidor o serve: MET 8,0 a 50 rep/min. */
const POLICHINELO = { met: 8, refCadenceRpm: 50 }

describe('kcalPerRep', () => {
  it('converte MET (por minuto) em caloria por repetição pela cadência de referência', () => {
    // 8 × 3,5 × 70 / 200 = 9,8 kcal/min; a 50 rep/min, 0,196 kcal por polichinelo.
    expect(kcalPerRep(8, 50)).toBeCloseTo(0.196, 4)
  })

  it('sem MET ou sem cadência não há conversão — e é aí que o card vira `--`', () => {
    expect(kcalPerRep(undefined, 50)).toBeNull()
    expect(kcalPerRep(8, undefined)).toBeNull()
    expect(kcalPerRep(8, 0)).toBeNull()
    expect(kcalPerRep(0, 50)).toBeNull()
    expect(kcalPerRep(Number.NaN, 50)).toBeNull()
  })

  it('cadência de referência maior barateia a repetição — os dois campos andam em par', () => {
    // É a armadilha que o texto do painel avisa: dobrar a cadência com o mesmo MET corta o
    // gasto por repetição pela metade.
    expect(kcalPerRep(8, 100)).toBeCloseTo((kcalPerRep(8, 50) as number) / 2, 6)
  })
})

describe('liveKcal — o total sai das repetições', () => {
  it('no ritmo de referência dá exatamente o mesmo número da fórmula por tempo', () => {
    // A propriedade que amarra a T-128 à T-063: 25 reps em 30 s são 50 rep/min, o ritmo que o
    // MET pressupõe — e 25 × 0,196 = 4,9 kcal, que é o que `MET × minutos` dava. A mudança não
    // reescala o produto, ela faz o número responder a quem está treinando.
    expect(liveKcal({ ...POLICHINELO, reps: 25, elapsedS: 30 })).toBeCloseTo(4.9, 2)
  })

  it('sessão parada não gasta caloria nenhuma — o defeito que esta task veio corrigir', () => {
    // Antes da T-128 estes 30 s davam 4,9 kcal sem ninguém ter se mexido.
    expect(liveKcal({ ...POLICHINELO, reps: 0, elapsedS: 30 })).toBe(0)
  })

  it('mesma duração, contagens diferentes: calorias diferentes (critério 3.1)', () => {
    const preguicoso = liveKcal({ ...POLICHINELO, reps: 10, elapsedS: 30 }) as number
    const aplicado = liveKcal({ ...POLICHINELO, reps: 40, elapsedS: 30 }) as number

    expect(aplicado).toBeGreaterThan(preguicoso * 2)
  })

  it('o gasto acompanha o MET do exercício — é o que faz o número não ser decorativo', () => {
    // Mesmas 20 repetições, exercícios diferentes: agachamento (MET 5 a 20 rpm) custa mais por
    // repetição que polichinelo. Se o catálogo não entrasse na conta, ninguém notaria.
    const polichinelos = liveKcal({ ...POLICHINELO, reps: 20, elapsedS: 30 }) as number
    const agachamentos = liveKcal({ met: 5, refCadenceRpm: 20, reps: 20, elapsedS: 30 }) as number

    expect(agachamentos).toBeGreaterThan(polichinelos)
  })

  it('sem MET ou sem cadência não há número: o embutido não sabe, o servidor é quem sabe', () => {
    expect(liveKcal({ met: undefined, refCadenceRpm: 50, reps: 20, elapsedS: 30 })).toBeNull()
    expect(liveKcal({ met: 8, refCadenceRpm: undefined, reps: 20, elapsedS: 30 })).toBeNull()
  })

  it('sem MET, `null` vence o zero — "não sei" não pode virar "não gastou"', () => {
    expect(liveKcal({ met: undefined, refCadenceRpm: 50, reps: 0, elapsedS: 0 })).toBeNull()
  })

  it('o peso é premissa e entra como parâmetro, para a T-065 poder passar o real', () => {
    const base = liveKcal({ ...POLICHINELO, reps: 25, elapsedS: 30 }) as number
    const pesado = liveKcal({ ...POLICHINELO, reps: 25, elapsedS: 30, weightKg: 100 }) as number

    expect(pesado).toBeCloseTo(base * (100 / 70), 4)
    expect(DEFAULT_WEIGHT_KG).toBe(70)
  })

  it('mesmo estado, mesmo número — derivação, não acumulador', () => {
    // Se somasse, a caloria dependeria de quantas vezes o React renderizou.
    const um = liveKcal({ ...POLICHINELO, reps: 17, elapsedS: 22 })
    const dois = liveKcal({ ...POLICHINELO, reps: 17, elapsedS: 22 })

    expect(um).toBe(dois)
  })
})

describe('multiplicador de ritmo (critério 3.2)', () => {
  it('no ritmo de referência o multiplicador é neutro', () => {
    expect(intensityMultiplier(50, 50)).toBe(1)
  })

  it('acelerar encarece a repetição, e desacelerar barateia', () => {
    expect(intensityMultiplier(100, 50)).toBeGreaterThan(1)
    expect(intensityMultiplier(30, 50)).toBeLessThan(1)
  })

  it('o extra por velocidade é modesto: o ganho principal já está nas repetições', () => {
    // Dobrar a cadência dobra as repetições (isso já conta linearmente). O multiplicador é só
    // a perda de economia de movimento — um valor alto aqui contaria a velocidade duas vezes.
    expect(intensityMultiplier(100, 50)).toBeCloseTo(1.25, 4)
  })

  it('um pico de cadência não produz número absurdo — a trava é defesa, não elegância', () => {
    expect(intensityMultiplier(10_000, 50)).toBeLessThanOrEqual(1.3)
    expect(intensityMultiplier(0.1, 50)).toBeGreaterThanOrEqual(0.9)
  })

  it('cadência só vale depois da janela: antes disso o card não fica piscando', () => {
    // Com 3 s decorridos uma repetição a mais move a cadência em 20 rpm, e o multiplicador
    // saltaria entre os extremos justamente enquanto a pessoa se ajusta.
    expect(liveCadenceRpm(3, 3)).toBeNull()
    expect(liveCadenceRpm(6, 6)).toBeCloseTo(60, 4)
  })

  it('dentro da janela o total é linear nas repetições, sem multiplicador nenhum', () => {
    const dobro = liveKcal({ ...POLICHINELO, reps: 4, elapsedS: 3 }) as number
    const simples = liveKcal({ ...POLICHINELO, reps: 2, elapsedS: 3 }) as number

    expect(dobro).toBeCloseTo(simples * 2, 6)
  })

  it('sessão intensa rende mais que a soma das repetições sozinha', () => {
    // 40 reps em 30 s são 80 rep/min contra 50 de referência: 1,15 de multiplicador.
    const porRep = kcalPerRep(8, 50) as number
    const total = liveKcal({ ...POLICHINELO, reps: 40, elapsedS: 30 }) as number

    expect(total).toBeCloseTo(40 * porRep * 1.15, 4)
    expect(total).toBeGreaterThan(40 * porRep)
  })
})

describe('formatKcal', () => {
  beforeEach(() => useI18nStore.getState().setLocale('pt-BR'))
  afterEach(() => useI18nStore.getState().setLocale('pt-BR'))

  it('sem número, `--` — a regra da SPEC-014 vale aqui como vale para FC', () => {
    expect(formatKcal(null)).toBe('--')
  })

  it('uma casa decimal com vírgula: uma repetição custa ~0,2 kcal', () => {
    expect(formatKcal(4.9)).toBe('4,9')
    expect(formatKcal(0)).toBe('0,0')
  })

  it('a casa decimal continua uma; o SEPARADOR é do idioma (T-150)', () => {
    // Ponto e vírgula trocados de lugar não são detalhe de estilo: "4,9 kcal" numa tela em
    // inglês é o mesmo tipo de erro que uma frase não traduzida — só que ninguém o reporta.
    useI18nStore.getState().setLocale('en')
    expect(formatKcal(4.9)).toBe('4.9')
    expect(formatKcal(0)).toBe('0.0')
    // O `--` não é texto e não muda de língua.
    expect(formatKcal(null)).toBe('--')
  })
})
