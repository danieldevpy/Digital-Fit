import { describe, expect, it } from 'vitest'

import { resolveLocale } from '../i18n/locale'
import { idiomaASugerir } from './sugestaoDeIdioma'

describe('idiomaASugerir (T-161, SPEC-026 — camada "Chegar certo")', () => {
  it('não sugere nada quando a página já está na língua da pessoa', () => {
    expect(idiomaASugerir('pt-BR', 'pt-BR', false)).toBeNull()
    expect(idiomaASugerir('en', 'en', false)).toBeNull()
  })

  it('sugere a outra quando discordam', () => {
    expect(idiomaASugerir('en', 'pt-BR', false)).toBe('en')
    expect(idiomaASugerir('pt-BR', 'en', false)).toBe('pt-BR')
  })

  it('dispensou, acabou — em qualquer combinação', () => {
    // Sem isto o aviso vira faixa de cookie: aparece toda visita e ninguém lê.
    expect(idiomaASugerir('en', 'pt-BR', true)).toBeNull()
    expect(idiomaASugerir('pt-BR', 'en', true)).toBeNull()
  })
})

describe('o caso que motivou a frente: o estrangeiro que não fala nenhuma das duas', () => {
  it('francês em `/` recebe sugestão de INGLÊS, não de português', () => {
    // `matchLocale('fr')` é `null`, a cadeia cai em `DEFAULT_LOCALE` — e o destino é o mesmo
    // do `x-default` da T-160. Funciona por construção, sem regra especial para francês.
    const preferido = resolveLocale(null, ['fr-FR', 'fr'])

    expect(preferido).toBe('en')
    expect(idiomaASugerir(preferido, 'pt-BR', false)).toBe('en')
  })

  it('francês que já está em `/en/` não recebe aviso nenhum', () => {
    const preferido = resolveLocale(null, ['fr-FR', 'fr'])

    expect(idiomaASugerir(preferido, 'en', false)).toBeNull()
  })

  it('escolha explícita no app vence: quem escolheu pt-BR não é empurrado para o inglês', () => {
    // `detectLocale()` lê `localStorage` primeiro, e é ele que alimenta esta decisão — então a
    // preferência explícita da SPEC-025 continua vencendo também aqui.
    const preferido = resolveLocale('pt-BR', ['en-US', 'en'])

    expect(idiomaASugerir(preferido, 'pt-BR', false)).toBeNull()
  })

  it('brasileiro que cai em `/en/` por um link compartilhado recebe sugestão de português', () => {
    const preferido = resolveLocale(null, ['pt-BR', 'pt'])

    expect(idiomaASugerir(preferido, 'en', false)).toBe('pt-BR')
  })
})
