// Critério 3 da SPEC-016: "kcal ao vivo aparece na sessão para todos; nenhuma tela do Free
// soma kcal entre sessões". A primeira metade é esta função; a segunda é uma propriedade da
// arquitetura — este módulo não tem estado nenhum, então não há onde somar.
import { describe, expect, it } from 'vitest'

import { DEFAULT_WEIGHT_KG, formatKcal, liveKcal } from './kcal'

describe('liveKcal', () => {
  it('30 s de polichinelo (MET 8) a 70 kg dão ~4,1 kcal', () => {
    // Conferência à mão da fórmula do Compendium: 8 × 3,5 × 70 / 200 = 9,8 kcal/min; em meio
    // minuto, 4,9. O número existe aqui escrito para que uma "otimização" da fórmula precise
    // explicar por que mudou.
    expect(liveKcal(8, 30)).toBeCloseTo(4.9, 2)
  })

  it('o gasto acompanha o MET do exercício — é o que faz o número não ser decorativo', () => {
    // Se o MET não entrasse na conta, alongamento e polichinelo dariam a mesma caloria e
    // ninguém notaria. É exatamente o defeito que um "MET médio" chutado produziria.
    expect(liveKcal(8, 30)).toBeGreaterThan(liveKcal(2.5, 30) as number)
  })

  it('sem MET não há número: o catálogo embutido não sabe, e o servidor é quem sabe', () => {
    expect(liveKcal(undefined, 30)).toBeNull()
    expect(liveKcal(0, 30)).toBeNull()
    expect(liveKcal(Number.NaN, 30)).toBeNull()
  })

  it('antes de começar o gasto é zero, não `null` — a diferença é "ainda não" x "não sei"', () => {
    expect(liveKcal(8, 0)).toBe(0)
    expect(liveKcal(8, -5)).toBe(0)
  })

  it('o peso é premissa e entra como parâmetro, para a T-065 poder passar o real', () => {
    expect(liveKcal(8, 60, 100)).toBeCloseTo((liveKcal(8, 60) as number) * (100 / 70), 4)
    expect(DEFAULT_WEIGHT_KG).toBe(70)
  })

  it('cada instante da sessão dá o mesmo número — derivação, não acumulador', () => {
    // Chamar duas vezes com o mesmo tempo não pode somar: se somasse, a caloria dependeria de
    // quantas vezes o React renderizou.
    expect(liveKcal(8, 17)).toBe(liveKcal(8, 17))
  })
})

describe('formatKcal', () => {
  it('sem número, `--` — a regra da SPEC-014 vale aqui como vale para FC', () => {
    expect(formatKcal(null)).toBe('--')
  })

  it('uma casa decimal com vírgula: em 30 s o inteiro ficaria parado na tela', () => {
    expect(formatKcal(4.9)).toBe('4,9')
    expect(formatKcal(0)).toBe('0,0')
  })
})
