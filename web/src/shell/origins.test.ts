import { describe, expect, it } from 'vitest'
import { hrefFrom, normalizeBase, siteRouteHref } from './origins'

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

describe('siteRouteHref — a tela E o idioma moram na URL (T-158)', () => {
  it('a landing de cada idioma é a raiz e `/en/`', () => {
    expect(siteRouteHref('index', 'pt-BR')).toBe('/')
    expect(siteRouteHref('index', 'en')).toBe('/en/')
  })

  it('a tela viaja junto na troca de idioma — e agora por caminho, não por fragmento', () => {
    // Perder a tela na troca seria mandar a pessoa para a home como preço de escolher o idioma.
    // A diferença da T-153 para cá é que existe uma URL para o buscador ver.
    expect(siteRouteHref('sobre', 'pt-BR')).toBe('/sobre/')
    expect(siteRouteHref('sobre', 'en')).toBe('/en/about/')
  })
})
