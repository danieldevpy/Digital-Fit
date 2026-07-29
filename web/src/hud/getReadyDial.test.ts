import { describe, expect, it } from 'vitest'

import { fracaoRestante, segundosRestantes } from './getReadyDial'

describe('segundosRestantes', () => {
  it('arredonda para cima: 2,4 s restantes ainda são "3"', () => {
    // O número na tela é o que a pessoa vai contar em voz alta. Arredondar para baixo faria
    // o "1" aparecer e o VAI! chegar antes de o segundo terminar.
    expect(segundosRestantes(10_000, 7_600)).toBe(3)
  })

  it('chega a zero no instante exato', () => {
    expect(segundosRestantes(10_000, 10_000)).toBe(0)
  })

  it('nunca fica negativo se o relógio passar do prazo', () => {
    expect(segundosRestantes(10_000, 12_000)).toBe(0)
  })
})

describe('fracaoRestante', () => {
  it('começa cheia e termina vazia', () => {
    expect(fracaoRestante(3_000, 0, 3_000)).toBe(1)
    expect(fracaoRestante(3_000, 3_000, 3_000)).toBe(0)
  })

  it('é contínua, não em degraus de um segundo', () => {
    // Meio segundo depois do início de uma preparação de 3 s: 5/6 do anel.
    expect(fracaoRestante(3_000, 500, 3_000)).toBeCloseTo(0.8333, 3)
  })

  it('não estoura os limites quando o relógio atrasa ou adianta', () => {
    expect(fracaoRestante(3_000, -1_000, 3_000)).toBe(1)
    expect(fracaoRestante(3_000, 9_000, 3_000)).toBe(0)
  })

  it('total zero não vira divisão por zero', () => {
    expect(fracaoRestante(0, 0, 0)).toBe(0)
  })
})
