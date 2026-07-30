import { describe, expect, it } from 'vitest'
import { parseSiteHash, siteRouteHash } from './nav'

describe('parseSiteHash', () => {
  it('a raiz é a landing', () => {
    expect(parseSiteHash('')).toEqual({ screen: 'index' })
    expect(parseSiteHash('#/')).toEqual({ screen: 'index' })
  })

  it('reconhece o sobre, com ou sem barra final', () => {
    expect(parseSiteHash('#/sobre')).toEqual({ screen: 'sobre' })
    expect(parseSiteHash('#/sobre/')).toEqual({ screen: 'sobre' })
  })

  it('rota do app pedida ao site não quebra: cai na landing, que sabe levar ao app', () => {
    expect(parseSiteHash('#/treino')).toEqual({ screen: 'index' })
  })

  it('ida e volta', () => {
    expect(parseSiteHash(siteRouteHash({ screen: 'index' }))).toEqual({ screen: 'index' })
    expect(parseSiteHash(siteRouteHash({ screen: 'sobre' }))).toEqual({ screen: 'sobre' })
  })
})
