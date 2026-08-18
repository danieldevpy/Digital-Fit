import { describe, expect, it } from 'vitest'
import { hrefFrom, normalizeBase, siteLocaleHref } from './origins'

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

describe('siteLocaleHref — o idioma do SITE mora na URL (T-153)', () => {
  it('pt-BR é a raiz e en é `/en/` — as mesmas URLs dos `hreflang`', () => {
    expect(siteLocaleHref('pt-BR')).toBe('/')
    expect(siteLocaleHref('en')).toBe('/en/')
  })

  it('a tela atual viaja junto: quem está em Sobre continua em Sobre', () => {
    // Perder a tela na troca seria mandar a pessoa para a home como preço de escolher o idioma.
    expect(siteLocaleHref('en', '#/sobre')).toBe('/en/#/sobre')
    expect(siteLocaleHref('pt-BR', '#/sobre')).toBe('/#/sobre')
  })
})
