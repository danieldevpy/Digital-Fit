import { describe, expect, it } from 'vitest'

import { swapCamera, type SwapDeps } from './cameraSwap'
import type { Facing } from './facing'

/** Erro que só o `exact` produz: a restrição não pode ser satisfeita por este aparelho. */
class RestricaoImpossivel extends Error {}

interface Registro {
  pedidos: { facing: Facing; precisao: 'ideal' | 'exact' }[]
  adotados: Facing[]
  soltou: number
}

/**
 * `cameras` é o que o aparelho TEM. Um pedido `exact` fora dessa lista falha, que é
 * exatamente o comportamento do navegador; um pedido `ideal` fora dela devolve a primeira
 * câmera disponível **sem erro nenhum** — o silêncio que motiva a regra do `exact`.
 */
function deps(cameras: Facing[], opcoes: { voltaFalha?: boolean } = {}) {
  const registro: Registro = { pedidos: [], adotados: [], soltou: 0 }
  const swap: SwapDeps = {
    abrir: async (facing, precisao) => {
      registro.pedidos.push({ facing, precisao })
      if (precisao === 'exact' && !cameras.includes(facing)) {
        throw new RestricaoImpossivel('OverconstrainedError')
      }
      if (opcoes.voltaFalha && precisao === 'ideal') throw new Error('câmera sumiu')
      return {} as MediaStream
    },
    adotar: async (_stream, pedido) => {
      registro.adotados.push(pedido)
    },
    soltar: () => {
      registro.soltou += 1
    },
    ehRestricaoImpossivel: (erro) => erro instanceof RestricaoImpossivel,
  }
  return { swap, registro }
}

describe('troca de câmera (SPEC-027 §A)', () => {
  // Critério 1: o caminho feliz.
  it('aparelho com as duas: troca e adota a de destino', async () => {
    const { swap, registro } = deps(['user', 'environment'])

    expect(await swapCamera('user', swap)).toEqual({ estado: 'trocou', facing: 'environment' })
    expect(registro.pedidos).toEqual([{ facing: 'environment', precisao: 'exact' }])
    expect(registro.adotados).toEqual(['environment'])
  })

  it('e volta no sentido contrário', async () => {
    const { swap } = deps(['user', 'environment'])
    expect(await swapCamera('environment', swap)).toEqual({ estado: 'trocou', facing: 'user' })
  })

  // Critério 3 da SPEC-027, que é a razão de esta função existir separada do hook.
  it('aparelho sem traseira: volta para a anterior e diz por quê', async () => {
    const { swap, registro } = deps(['user'])

    expect(await swapCamera('user', swap)).toEqual({
      estado: 'voltou',
      facing: 'user',
      notice: 'single_camera',
    })
    // O rótulo da tela vem daqui: continua `user`. Nunca a câmera que não abriu.
    expect(registro.adotados).toEqual(['user'])
  })

  it('a volta é `ideal`, não `exact` — falhar a volta seria deixar a tela sem imagem', async () => {
    const { swap, registro } = deps(['user'])
    await swapCamera('user', swap)

    expect(registro.pedidos).toEqual([
      { facing: 'environment', precisao: 'exact' },
      { facing: 'user', precisao: 'ideal' },
    ])
  })

  it('solta a câmera atual antes de pedir a outra (aparelho que não abre duas)', async () => {
    const { swap, registro } = deps(['user', 'environment'])
    await swapCamera('user', swap)

    expect(registro.soltou).toBe(1)
  })

  it('falha que não é de restrição volta igual, mas sem afirmar o motivo', async () => {
    const { swap } = deps(['user', 'environment'])
    const comFalhaGenerica: SwapDeps = {
      ...swap,
      abrir: async (_facing, precisao) => {
        if (precisao === 'exact') throw new Error('NotReadableError: câmera ocupada')
        return {} as MediaStream
      },
    }

    // Sem `notice`: "só tem uma câmera" seria uma causa inventada — a câmera existe e está
    // ocupada por outro app, que é outra história e outra frase.
    expect(await swapCamera('user', comFalhaGenerica)).toEqual({
      estado: 'voltou',
      facing: 'user',
      notice: null,
    })
  })

  it('perdendo a de ida e a de volta, o estado é sem câmera — não "trocou"', async () => {
    const { swap } = deps(['user'], { voltaFalha: true })
    const resultado = await swapCamera('user', swap)

    expect(resultado.estado).toBe('sem_camera')
  })
})
