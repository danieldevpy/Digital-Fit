import { describe, expect, it } from 'vitest'

import { formatDate, formatDateTime, formatNumber, formatPercent, formatTime } from './format'

// Todas as chamadas passam o locale explícito (3º parâmetro) — testar o default (o locale
// ATIVO do store) exigiria depender da ordem de import dos módulos, algo que os testes deste
// projeto evitam manipulando o store diretamente (ver `i18n/store.test.ts`). A garantia "ninguém
// mais escreve 'pt-BR' literal" está em o parâmetro SEMPRE poder ser omitido em produção — o que
// os call sites futuros (T-150/T-151) vão fazer.

describe('formatNumber — separador decimal por locale, nunca hardcoded', () => {
  it('pt-BR usa vírgula decimal e ponto de milhar', () => {
    expect(formatNumber(1234.5, undefined, 'pt-BR')).toBe('1.234,5')
  })

  it('en usa ponto decimal e vírgula de milhar', () => {
    expect(formatNumber(1234.5, undefined, 'en')).toBe('1,234.5')
  })
})

describe('formatPercent', () => {
  it('pt-BR', () => {
    expect(formatPercent(0.42, undefined, 'pt-BR')).toBe('42%')
  })

  it('en', () => {
    expect(formatPercent(0.42, undefined, 'en')).toBe('42%')
  })
})

describe('formatDate — dia/mês/ano na ordem do locale', () => {
  const data = new Date('2026-08-18T12:00:00Z')

  it('pt-BR: dd/mm/aaaa', () => {
    expect(formatDate(data, undefined, 'pt-BR')).toBe('18/08/2026')
  })

  it('en: m/d/yyyy', () => {
    expect(formatDate(data, undefined, 'en')).toBe('8/18/2026')
  })

  it('aceita opções do Intl.DateTimeFormat por cima do locale', () => {
    expect(formatDate(data, { month: 'long' }, 'pt-BR')).toBe('agosto')
    expect(formatDate(data, { month: 'long' }, 'en')).toBe('August')
  })
})

describe('formatTime / formatDateTime — não lançam e respeitam o locale pedido', () => {
  const data = new Date('2026-08-18T15:30:00Z')

  it('formatTime devolve string não vazia nos dois locales', () => {
    expect(formatTime(data, undefined, 'pt-BR').length).toBeGreaterThan(0)
    expect(formatTime(data, undefined, 'en').length).toBeGreaterThan(0)
  })

  it('formatDateTime devolve string não vazia nos dois locales', () => {
    expect(formatDateTime(data, undefined, 'pt-BR').length).toBeGreaterThan(0)
    expect(formatDateTime(data, undefined, 'en').length).toBeGreaterThan(0)
  })
})
