import { afterEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import {
  DEFAULT_COUNTDOWN_S,
  clampCountdown,
  countdownLabel,
  countdownPreference,
  nextCountdown,
  setCountdownPreference,
} from './preferences'

afterEach(uninstallStorage)

describe('preferência de preparação', () => {
  it('quem nunca escolheu recebe o default do produto, não zero', () => {
    installStorage()
    expect(countdownPreference()).toBe(DEFAULT_COUNTDOWN_S)
  })

  it('a escolha sobrevive à próxima sessão', () => {
    installStorage()
    setCountdownPreference(5)
    expect(countdownPreference()).toBe(5)
  })

  it('desligar é uma escolha válida e persiste como zero', () => {
    installStorage()
    setCountdownPreference(0)
    // O ponto sutil: `0` não pode cair no default na leitura seguinte, senão desligar não
    // desligaria nada.
    expect(countdownPreference()).toBe(0)
  })

  it('sem armazenamento (Safari privado) o app segue com o default', () => {
    installStorage({ readOnly: true })
    expect(() => setCountdownPreference(5)).not.toThrow()
    expect(countdownPreference()).toBe(DEFAULT_COUNTDOWN_S)
  })

  it('valor corrompido no armazenamento não quebra a admissão', () => {
    const fake = installStorage()
    fake.store.set('digitalfit.countdown_s', 'três')
    expect(countdownPreference()).toBe(DEFAULT_COUNTDOWN_S)
  })
})

describe('clampCountdown', () => {
  it('respeita o teto de 10 s — preparação longa seguraria a vaga da sessão', () => {
    expect(clampCountdown(60)).toBe(10)
  })

  it('negativo vira zero, não erro', () => {
    expect(clampCountdown(-5)).toBe(0)
  })

  it('fração arredonda', () => {
    expect(clampCountdown(3.4)).toBe(3)
  })
})

describe('ciclo do controle', () => {
  it('avança 3 → 5 → 10 → desligado → 3', () => {
    expect(nextCountdown(3)).toBe(5)
    expect(nextCountdown(5)).toBe(10)
    expect(nextCountdown(10)).toBe(0)
    expect(nextCountdown(0)).toBe(3)
  })

  it('valor fora do ciclo volta ao default em vez de travar', () => {
    expect(nextCountdown(7)).toBe(DEFAULT_COUNTDOWN_S)
  })
})

describe('rótulo', () => {
  it('zero fala em português, não em número', () => {
    expect(countdownLabel(0)).toBe('sem preparação')
  })

  it('os demais dizem os segundos', () => {
    expect(countdownLabel(3)).toBe('3s de preparação')
  })
})
