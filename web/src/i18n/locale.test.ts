import { afterEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import { DEFAULT_LOCALE, detectLocale, isLocale, matchLocale, persistLocale, resolveLocale } from './locale'

afterEach(uninstallStorage)

describe('matchLocale — casamento por prefixo (SPEC-025 §3.3)', () => {
  it('pt* casa com pt-BR, inclusive variantes que não são do Brasil', () => {
    expect(matchLocale('pt-BR')).toBe('pt-BR')
    expect(matchLocale('pt')).toBe('pt-BR')
    expect(matchLocale('pt-PT')).toBe('pt-BR')
  })

  it('en* casa com en', () => {
    expect(matchLocale('en-US')).toBe('en')
    expect(matchLocale('en')).toBe('en')
    expect(matchLocale('en-GB')).toBe('en')
  })

  it('idioma sem suporte não casa com nada', () => {
    expect(matchLocale('fr-FR')).toBeNull()
    expect(matchLocale('es')).toBeNull()
  })
})

describe('isLocale', () => {
  it('só os dois locales suportados passam', () => {
    expect(isLocale('pt-BR')).toBe(true)
    expect(isLocale('en')).toBe(true)
    expect(isLocale('es')).toBe(false)
    expect(isLocale(null)).toBe(false)
    expect(isLocale(undefined)).toBe(false)
    expect(isLocale(42)).toBe(false)
  })
})

describe('resolveLocale — pura, sem window (critério 4 da T-142)', () => {
  it('escolha explícita no armazenamento vence sempre, mesmo contra o navegador', () => {
    expect(resolveLocale('en', ['pt-BR'])).toBe('en')
    expect(resolveLocale('pt-BR', ['en-US'])).toBe('pt-BR')
  })

  it('sem escolha explícita, cai no primeiro idioma do navegador que casar', () => {
    expect(resolveLocale(null, ['fr-FR', 'pt-BR', 'en-US'])).toBe('pt-BR')
    expect(resolveLocale(null, ['de-DE', 'en-GB'])).toBe('en')
  })

  it('navegador brasileiro cai na regra do navegador, não seria o fallback global', () => {
    // O ponto do §3.3: o fallback é 'en' e NÃO 'pt-BR' de propósito, porque um navegador
    // brasileiro já é resolvido aqui — nunca chega a precisar do fallback.
    expect(resolveLocale(null, ['pt-BR'])).toBe('pt-BR')
  })

  it('nada casa: cai no fallback global en, não pt-BR', () => {
    expect(resolveLocale(null, ['fr-FR', 'de-DE'])).toBe(DEFAULT_LOCALE)
    expect(resolveLocale(null, [])).toBe(DEFAULT_LOCALE)
  })

  it('valor corrompido no armazenamento não é tratado como escolha válida', () => {
    expect(resolveLocale('klingon', ['pt-BR'])).toBe('pt-BR')
  })
})

describe('detectLocale / persistLocale — leitura de armazenamento separada (Safari privado)', () => {
  it('sem escolha guardada, decide pelo navegador exposto em `navigator`', () => {
    installStorage()
    // `navigator.languages` não é mockável por aqui (é global do ambiente, não do storage
    // fake) — o que importa testar é que a ausência de escolha cai para a cadeia, e isso já
    // está coberto por `resolveLocale`. Aqui confirma-se só que não explode sem `navigator`
    // completo (ambiente de teste é Node, `environment: 'node'`).
    expect(() => detectLocale()).not.toThrow()
  })

  it('escolha persistida sobrevive à próxima leitura', () => {
    installStorage()
    persistLocale('pt-BR')
    expect(detectLocale()).toBe('pt-BR')
  })

  it('sem armazenamento (Safari privado) não lança e cai no fallback', () => {
    installStorage({ readOnly: true })
    expect(() => persistLocale('pt-BR')).not.toThrow()
    // `readOnly` só bloqueia ESCRITA (mesma fixture de `preferences.test.ts`) — sem nada
    // gravado antes, a leitura cai na cadeia normal (navegador/fallback).
    expect(() => detectLocale()).not.toThrow()
  })

  it('sem `window` nenhum (SSR/Node puro) a leitura não lança', () => {
    // Sem `installStorage()`: `window` não existe neste ambiente (`environment: 'node'`).
    expect(() => detectLocale()).not.toThrow()
    expect(detectLocale()).toBe(DEFAULT_LOCALE)
  })
})
