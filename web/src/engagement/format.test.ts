import { beforeEach, describe, expect, it } from 'vitest'

import { useI18nStore } from '../i18n/store'
import { fireAriaLabel, fireLabel, parcelasDeXp } from './format'
import type { EngagementView } from './useEngagement'

// Os rótulos saem do dicionário desde a T-151 — o teste fixa a língua antes de cobrar a frase.
beforeEach(() => useI18nStore.getState().setLocale('pt-BR'))

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
  achievements: [],
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

describe('o rótulo do fogo nas duas línguas (T-151)', () => {
  it('o plural de dias sai do Intl, não de um ternário', () => {
    useI18nStore.getState().setLocale('en')
    expect(fireAriaLabel({ ...BASE, streak: 1 })).toMatch(/^1 day in a row,/)
    expect(fireAriaLabel({ ...BASE, streak: 4 })).toMatch(/^4 days in a row,/)
    expect(fireAriaLabel({ ...BASE, pending: true })).toBe('Streak still loading')
  })

  it('o aviso de fogo local também é palavra, e traduz', () => {
    useI18nStore.getState().setLocale('en')
    expect(fireAriaLabel({ ...BASE, source: 'local' })).toContain('saved on this device only')
  })

  it('as parcelas de XP têm `id` estável e rótulo traduzido', () => {
    // O `id` é o que vira `key` no React: se o `key` fosse o texto, trocar de idioma remontaria
    // a lista inteira — e duas línguas com a mesma palavra colidiriam.
    const xp = { total: 38, session: 10, reps: 18, clean: 10, formula_v: 1 }
    useI18nStore.getState().setLocale('en')
    const lista = parcelasDeXp(xp)
    expect(lista.map((p) => p.id)).toEqual(['session', 'reps', 'clean'])
    expect(lista.map((p) => p.rotulo)).toEqual(['session', 'reps', 'clean'])

    useI18nStore.getState().setLocale('pt-BR')
    expect(parcelasDeXp(xp).map((p) => p.id)).toEqual(['session', 'reps', 'clean'])
    expect(parcelasDeXp(xp).map((p) => p.rotulo)).toEqual(['sessão', 'reps', 'limpa'])
  })
})
