import { describe, expect, it } from 'vitest'

import { fireAriaLabel, fireLabel, parcelasDeXp } from './format'
import type { EngagementView } from './useEngagement'

const BASE: EngagementView = {
  source: 'server',
  streak: 3,
  bestStreak: 9,
  todayActive: true,
  sessionsToday: 1,
  goalTarget: 2,
  goalDone: false,
  xp: 120,
  level: 2,
  protections: { used: 0, total: 1 },
  pending: false,
}

describe('fireLabel', () => {
  it('mostra o número quando ele existe', () => {
    expect(fireLabel(BASE)).toBe('3')
  })

  it('mostra `--` enquanto o servidor não respondeu — "não sei" não é zero', () => {
    expect(fireLabel({ ...BASE, pending: true })).toBe('--')
  })

  it('zero de verdade é zero, e não `--`', () => {
    expect(fireLabel({ ...BASE, streak: 0 })).toBe('0')
  })
})

describe('fireAriaLabel', () => {
  it('diz a sequência e a meta', () => {
    expect(fireAriaLabel(BASE)).toBe('3 dias seguidos, meta do dia 1 de 2')
  })

  it('singulariza um dia só', () => {
    expect(fireAriaLabel({ ...BASE, streak: 1 })).toMatch(/^1 dia seguido,/)
  })

  it('avisa em palavras quando o fogo vive só neste aparelho', () => {
    // O ponto cinza do chip não existe para quem não vê a tela — o rótulo honesto do
    // §Anônimo tem de estar aqui também.
    expect(fireAriaLabel({ ...BASE, source: 'local' })).toMatch(/guardado só neste aparelho$/)
  })

  it('carregando não afirma número nenhum', () => {
    expect(fireAriaLabel({ ...BASE, pending: true })).toBe('Sequência ainda carregando')
  })
})

describe('parcelasDeXp', () => {
  it('mostra as três quando todas valem', () => {
    const lista = parcelasDeXp({ total: 38, session: 10, reps: 18, clean: 10, formula_v: 1 })

    expect(lista.map((p) => p.rotulo)).toEqual(['sessão', 'reps', 'limpa'])
  })

  it('parcela zerada some — "limpa +0" é repreensão, não informação', () => {
    const lista = parcelasDeXp({ total: 28, session: 10, reps: 18, clean: 0, formula_v: 1 })

    expect(lista.map((p) => p.rotulo)).toEqual(['sessão', 'reps'])
  })

  it('sessão inválida não tem parcela nenhuma', () => {
    expect(parcelasDeXp({ total: 0, session: 0, reps: 0, clean: 0, formula_v: 1 })).toEqual([])
  })
})
