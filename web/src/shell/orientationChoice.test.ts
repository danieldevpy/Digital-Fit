import { describe, expect, it } from 'vitest'

import {
  escolherOutra,
  orientationLabel,
  resolveOrientation,
  rotacaoTravada,
  type EscolhaDeOrientacao,
} from './orientationChoice'

describe('sem escolha manual, quem manda é a viewport', () => {
  it('retrato e paisagem passam direto', () => {
    expect(resolveOrientation('portrait', null)).toBe('portrait')
    expect(resolveOrientation('landscape', null)).toBe('landscape')
  })
})

describe('a escolha manual vale até a viewport girar de verdade (SPEC-027 §F)', () => {
  const forcouPaisagem: EscolhaDeOrientacao = {
    quer: 'landscape',
    quandoViewportEra: 'portrait',
  }

  it('enquanto a viewport continua como estava, a escolha vence', () => {
    expect(resolveOrientation('portrait', forcouPaisagem)).toBe('landscape')
  })

  // O caso do celular com a rotação travada que a pessoa DESTRAVA no meio: a viewport gira, e
  // a escolha morre sozinha. Sem isto ela sobreviveria ao giro real — e uma escolha que
  // sobrevive a um giro real é uma escolha que ninguém consegue desfazer: a pessoa gira o
  // aparelho, nada acontece, e não há nada na tela explicando por quê.
  it('a viewport girando de verdade mata a escolha', () => {
    expect(resolveOrientation('landscape', forcouPaisagem)).toBe('landscape')

    const forcouRetrato: EscolhaDeOrientacao = {
      quer: 'portrait',
      quandoViewportEra: 'portrait',
    }
    expect(resolveOrientation('landscape', forcouRetrato)).toBe('landscape')
  })
})

describe('o botão', () => {
  it('sem escolha anterior, pede o oposto do que a viewport diz', () => {
    expect(escolherOutra('portrait', null)).toEqual({
      quer: 'landscape',
      quandoViewportEra: 'portrait',
    })
    expect(escolherOutra('landscape', null)).toEqual({
      quer: 'portrait',
      quandoViewportEra: 'landscape',
    })
  })

  it('tocar duas vezes volta ao que era — não fica preso na escolha', () => {
    const primeira = escolherOutra('portrait', null)
    const segunda = escolherOutra('portrait', primeira)

    expect(resolveOrientation('portrait', primeira)).toBe('landscape')
    expect(resolveOrientation('portrait', segunda)).toBe('portrait')
  })

  it('parte do que está VALENDO, não do que a viewport diz', () => {
    // Viewport girou de verdade e matou a escolha velha: o próximo toque tem de sair de
    // `landscape` (o que está na tela), não de `portrait` (o que a escolha morta pedia).
    const morta: EscolhaDeOrientacao = { quer: 'portrait', quandoViewportEra: 'portrait' }
    expect(escolherOutra('landscape', morta).quer).toBe('portrait')
  })
})

describe('o aviso de rotação travada (SPEC-027 §F)', () => {
  it('avisa quando o layout é paisagem e a viewport continuou retrato', () => {
    expect(rotacaoTravada('portrait', 'landscape')).toBe(true)
  })

  it('não avisa quando a viewport girou junto — não há nada travado', () => {
    expect(rotacaoTravada('landscape', 'landscape')).toBe(false)
  })

  // Assimetria deliberada: com retrato forçado numa viewport deitada, o quadro da câmera está
  // em pé com o mundo em pé. O layout é só mais estreito do que precisaria, e não há nada
  // sobre o EXERCÍCIO a corrigir — avisar ali seria alarme sem consequência.
  it('não avisa no caso espelhado, porque ele não machuca a leitura', () => {
    expect(rotacaoTravada('landscape', 'portrait')).toBe(false)
  })
})

describe('o rótulo que vai para o dataset (SPEC-027 §Eventos)', () => {
  it('os dois casos honestos saem com o próprio nome', () => {
    expect(orientationLabel('portrait', 'portrait')).toBe('portrait')
    expect(orientationLabel('landscape', 'landscape')).toBe('landscape')
  })

  // É este rótulo que permite EXCLUIR depois as sessões de quadro girado de qualquer
  // calibração. Sem ele viram ruído não explicado no corpus, indistinguíveis de gente que
  // simplesmente se enquadrou mal.
  it('paisagem forçada em viewport retrato é `landscape_forced`, e não `landscape`', () => {
    expect(orientationLabel('portrait', 'landscape')).toBe('landscape_forced')
  })

  it('retrato forçado não inventa rótulo novo', () => {
    expect(orientationLabel('landscape', 'portrait')).toBe('portrait')
  })
})
