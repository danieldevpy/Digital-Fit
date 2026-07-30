import { describe, expect, it } from 'vitest'
import { parseHash, routeHash, type Route } from './nav'

describe('parseHash', () => {
  it('abrir o app sem rota cai na pré-configuração (a tela "Início")', () => {
    expect(parseHash('')).toEqual({ screen: 'preparar' })
    expect(parseHash('#/')).toEqual({ screen: 'preparar' })
    // O `#/` da landing antiga: quem tinha o app favoritado na raiz continua treinando.
    expect(parseHash('#/index')).toEqual({ screen: 'preparar' })
  })

  it('reconhece as telas do app', () => {
    expect(parseHash('#/exercicios')).toEqual({ screen: 'exercicios' })
    expect(parseHash('#/treino')).toEqual({ screen: 'treino' })
    expect(parseHash('#/progresso')).toEqual({ screen: 'progresso' })
    expect(parseHash('#/analytics')).toEqual({ screen: 'analytics' })
    expect(parseHash('#/entrar')).toEqual({ screen: 'entrar' })
  })

  it('guia e ponte do site carregam o slug validado contra o catálogo', () => {
    expect(parseHash('#/guia/jumping_jack')).toEqual({
      screen: 'guia',
      exercise: 'jumping_jack',
    })
    expect(parseHash('#/ex/jumping_jack')).toEqual({
      screen: 'abrirExercicio',
      exercise: 'jumping_jack',
    })
  })

  it('slug inexistente não é erro de rota: cai na escolha, onde dá para se orientar', () => {
    expect(parseHash('#/guia/flexao_marciana')).toEqual({ screen: 'exercicios' })
    expect(parseHash('#/ex/flexao_marciana')).toEqual({ screen: 'exercicios' })
  })
})

describe('routeHash', () => {
  it('ida e volta: toda rota sobrevive ao próprio hash', () => {
    const rotas: Route[] = [
      { screen: 'exercicios' },
      { screen: 'preparar' },
      { screen: 'treino' },
      { screen: 'progresso' },
      { screen: 'analytics' },
      { screen: 'entrar' },
      { screen: 'guia', exercise: 'jumping_jack' },
      { screen: 'abrirExercicio', exercise: 'jumping_jack' },
    ]
    for (const rota of rotas) {
      expect(parseHash(routeHash(rota))).toEqual(rota)
    }
  })
})
