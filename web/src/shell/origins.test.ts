import { describe, expect, it } from 'vitest'
import { hrefFrom, normalizeBase } from './origins'

describe('normalizeBase', () => {
  it('cai no fallback quando a variável não veio ou veio vazia', () => {
    expect(normalizeBase(undefined, '/app/')).toBe('/app/')
    expect(normalizeBase('', '/app/')).toBe('/app/')
    expect(normalizeBase('   ', '/app/')).toBe('/app/')
  })

  it('garante a barra final — é ela que faz o hash colar sem virar caminho novo', () => {
    expect(normalizeBase('https://app.exemplo.com', '/app/')).toBe('https://app.exemplo.com/')
    expect(normalizeBase('https://app.exemplo.com/', '/app/')).toBe('https://app.exemplo.com/')
    expect(normalizeBase('/app', '/app/')).toBe('/app/')
  })
})

describe('hrefFrom', () => {
  it('sem hash devolve a base pura', () => {
    expect(hrefFrom('/app/', '')).toBe('/app/')
    expect(hrefFrom('/app/', '#')).toBe('/app/')
  })

  it('monta a rota no host do outro lado', () => {
    expect(hrefFrom('https://app.exemplo.com/', '#/preparar')).toBe(
      'https://app.exemplo.com/#/preparar',
    )
    expect(hrefFrom('/app/', '#/exercicios')).toBe('/app/#/exercicios')
  })

  it('aceita hash sem "#" — quem chama não deveria ter de lembrar', () => {
    expect(hrefFrom('/app/', '/preparar')).toBe('/app/#/preparar')
  })
})
