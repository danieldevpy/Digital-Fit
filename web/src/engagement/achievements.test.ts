import { afterEach, describe, expect, it } from 'vitest'

import type { Achievement } from './api'
import { diffDeConquistas, esquecerConquistas, ganhas, novasConquistas } from './achievements'
import { installStorage, uninstallStorage } from '../auth/testStorage'

afterEach(uninstallStorage)

function conquista(slug: string, earned: boolean): Achievement {
  return { slug, name: slug, description: `descrição de ${slug}`, earned }
}

const CATALOGO = [
  conquista('primeira-sessao', true),
  conquista('fogo-7', true),
  conquista('milheiro', false),
]

describe('ganhas', () => {
  it('devolve só as conquistadas, na ordem do catálogo', () => {
    expect(ganhas(CATALOGO)).toEqual(['primeira-sessao', 'fogo-7'])
  })
})

describe('diffDeConquistas', () => {
  it('só o que é novo', () => {
    const novas = diffDeConquistas(CATALOGO, ['primeira-sessao'])

    expect(novas.map((c) => c.slug)).toEqual(['fogo-7'])
  })

  it('bloqueada nunca é novidade', () => {
    expect(diffDeConquistas(CATALOGO, []).map((c) => c.slug)).not.toContain('milheiro')
  })

  it('nada novo é lista vazia', () => {
    expect(diffDeConquistas(CATALOGO, ['primeira-sessao', 'fogo-7'])).toEqual([])
  })
})

describe('novasConquistas', () => {
  it('a PRIMEIRA leitura não avisa nada — marca tudo como visto em silêncio', () => {
    // Quem já treinava antes desta task receberia sete avisos de uma vez, inclusive de
    // conquistas ganhas meses atrás. A marca existe para não repetir, não para celebrar
    // retroativamente (mesma escolha do `guide_seen`).
    installStorage()

    expect(novasConquistas(CATALOGO)).toEqual([])
  })

  it('depois da primeira, conquista nova aparece uma vez só', () => {
    installStorage()
    novasConquistas(CATALOGO)

    const comMilheiro = [...CATALOGO.slice(0, 2), conquista('milheiro', true)]

    expect(novasConquistas(comMilheiro).map((c) => c.slug)).toEqual(['milheiro'])
    expect(novasConquistas(comMilheiro)).toEqual([])
  })

  it('lista vazia não marca nada — senão um erro de rede queimaria os avisos', () => {
    installStorage()

    expect(novasConquistas([])).toEqual([])
    // A primeira leitura de VERDADE ainda está por vir, e continua silenciosa.
    expect(novasConquistas(CATALOGO)).toEqual([])
  })

  it('armazenamento quebrado degrada para "tudo visto", não para "tudo novo"', () => {
    // Sete toasts na primeira abertura por causa de um storage do Safari privado seria pior
    // que aviso nenhum.
    installStorage({ readOnly: true })

    expect(novasConquistas(CATALOGO)).toEqual([])
  })

  it('esquecer devolve a lista ao estado de primeira leitura', () => {
    installStorage()
    novasConquistas(CATALOGO)
    esquecerConquistas()

    expect(novasConquistas(CATALOGO)).toEqual([])
  })
})
