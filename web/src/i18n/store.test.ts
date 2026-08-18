import { afterEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import { isLocale } from './locale'
import { useI18nStore } from './store'

afterEach(uninstallStorage)

describe('useI18nStore (SPEC-025 §3.1, critério 6 da T-142 — padrão de store/config.ts)', () => {
  it('nasce com um locale válido — a detecção roda na criação, não some em "ainda não sei"', () => {
    // Ao contrário do `store/config.ts` (que espera uma resposta de rede), o locale é
    // derivável 100% do aparelho: não há estado `null`/`unknown` de boot aqui.
    expect(isLocale(useI18nStore.getState().locale)).toBe(true)
  })

  it('setLocale troca o estado', () => {
    installStorage()
    useI18nStore.getState().setLocale('pt-BR')
    expect(useI18nStore.getState().locale).toBe('pt-BR')

    useI18nStore.getState().setLocale('en')
    expect(useI18nStore.getState().locale).toBe('en')
  })

  it('setLocale persiste a escolha para o próximo boot', () => {
    const fake = installStorage()
    useI18nStore.getState().setLocale('pt-BR')
    expect(fake.store.get('digitalfit.locale')).toBe('pt-BR')
  })

  it('setLocale sem armazenamento (Safari privado) não lança — a troca ainda vale na sessão', () => {
    installStorage({ readOnly: true })
    expect(() => useI18nStore.getState().setLocale('en')).not.toThrow()
    expect(useI18nStore.getState().locale).toBe('en')
  })
})
