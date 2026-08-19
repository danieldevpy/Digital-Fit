import { describe, expect, it, vi } from 'vitest'

import {
  CONSULTA_PAISAGEM,
  currentOrientation,
  orientationFrom,
  subscribeOrientation,
  type AbrirConsulta,
  type ConsultaMidia,
} from './orientation'

/**
 * `matchMedia` de mentira que REGISTRA o que foi perguntado e quem ficou ouvindo. O registro é
 * o teste: a decisão da SPEC-027 §C não é "descobrir a orientação", é descobrir por qual
 * caminho — e o caminho errado (`resize`) funcionaria o suficiente para passar num teste que
 * só olhasse o valor.
 */
function fakeMatchMedia(paisagem: boolean) {
  const registro = {
    consultas: [] as string[],
    ouvintes: [] as (() => void)[],
    removidos: 0,
  }
  const consulta: ConsultaMidia = {
    matches: paisagem,
    addEventListener: (_tipo, ouvinte) => {
      registro.ouvintes.push(ouvinte)
    },
    removeEventListener: () => {
      registro.removidos += 1
    },
  }
  const abrir: AbrirConsulta = (texto) => {
    registro.consultas.push(texto)
    return consulta
  }
  return { abrir, registro, consulta }
}

describe('orientationFrom', () => {
  it('traduz a resposta da consulta', () => {
    expect(orientationFrom(true)).toBe('landscape')
    expect(orientationFrom(false)).toBe('portrait')
  })
})

describe('a orientação vem da FORMA DA VIEWPORT (SPEC-027 §C)', () => {
  it('pergunta pela largura da caixa, não pelo ângulo do aparelho', () => {
    const { abrir, registro } = fakeMatchMedia(true)

    expect(currentOrientation(abrir)).toBe('landscape')
    // `(orientation: landscape)` e não `screen.orientation.angle`: num celular com a rotação
    // travada os dois discordam, e o layout mora na viewport.
    expect(registro.consultas).toEqual([CONSULTA_PAISAGEM])
  })

  it('viewport em pé responde retrato', () => {
    const { abrir } = fakeMatchMedia(false)
    expect(currentOrientation(abrir)).toBe('portrait')
  })

  // O pré-render (T-159) roda sem `window`, e navegador antigo pode não ter `matchMedia`.
  // Retrato é o layout de sempre: é ele que não pode depender de detecção para existir.
  it('sem `matchMedia` cai em retrato em vez de quebrar', () => {
    expect(currentOrientation(null)).toBe('portrait')
  })
})

describe('assinatura da mudança (SPEC-027 §C)', () => {
  it('ouve a consulta de mídia — nunca `resize`', () => {
    const { abrir, registro } = fakeMatchMedia(false)
    const avisar = vi.fn()

    subscribeOrientation(avisar, abrir)

    expect(registro.ouvintes).toHaveLength(1)
    // A prova pelo outro lado: `resize` dispara a cada entrada e saída da barra do navegador
    // do celular — ou seja, a cada rolagem —, e nada aqui pode estar pendurado nele.
    expect(registro.consultas).toEqual([CONSULTA_PAISAGEM])
  })

  it('o aviso chega quando a consulta muda', () => {
    const { abrir, registro } = fakeMatchMedia(false)
    const avisar = vi.fn()

    subscribeOrientation(avisar, abrir)
    registro.ouvintes.forEach((ouvinte) => ouvinte())

    expect(avisar).toHaveBeenCalledTimes(1)
  })

  it('cancelar solta o ouvinte — girar o aparelho não empilha assinaturas', () => {
    const { abrir, registro } = fakeMatchMedia(false)

    const cancelar = subscribeOrientation(() => {}, abrir)
    cancelar()

    expect(registro.removidos).toBe(1)
  })

  it('sem `matchMedia`, cancelar continua sendo seguro de chamar', () => {
    expect(() => subscribeOrientation(() => {}, null)()).not.toThrow()
  })
})
