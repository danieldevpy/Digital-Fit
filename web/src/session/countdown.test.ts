import { describe, expect, it } from 'vitest'
import { formatClock, secondsLeft } from './countdown'

const START = 1_700_000_000_000

describe('secondsLeft', () => {
  it('mostra a duração cheia antes da sessão começar', () => {
    expect(secondsLeft(null, 30, START)).toBe(30)
  })

  it('conta para baixo a partir do início', () => {
    expect(secondsLeft(START, 30, START)).toBe(30)
    expect(secondsLeft(START, 30, START + 6000)).toBe(24)
    expect(secondsLeft(START, 30, START + 29_500)).toBe(1)
  })

  it('nunca fica negativo nem passa da duração', () => {
    expect(secondsLeft(START, 30, START + 60_000)).toBe(0)
    // relógio do cliente atrás do servidor não vira 31s na tela
    expect(secondsLeft(START, 30, START - 5000)).toBe(30)
  })

  it('arredonda para cima: 29,2s restantes ainda mostram 30', () => {
    expect(secondsLeft(START, 30, START + 800)).toBe(30)
  })
})

describe('formatClock', () => {
  it('formata mm:ss', () => {
    expect(formatClock(24)).toBe('00:24')
    expect(formatClock(0)).toBe('00:00')
    expect(formatClock(90)).toBe('01:30')
  })

  it('protege contra valor inválido', () => {
    expect(formatClock(-5)).toBe('00:00')
    expect(formatClock(24.9)).toBe('00:24')
  })
})
