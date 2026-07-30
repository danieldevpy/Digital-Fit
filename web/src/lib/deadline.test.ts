import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { comPrazo, DeadlineError } from './deadline'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('comPrazo', () => {
  it('entrega o valor quando chega dentro do prazo', async () => {
    const promessa = comPrazo(Promise.resolve('pronto'), 1000, { oQue: 'delegate GPU' })
    await expect(promessa).resolves.toBe('pronto')
  })

  it('propaga a rejeição original — erro de verdade não vira "tempo esgotado"', async () => {
    const promessa = comPrazo(Promise.reject(new Error('WebGL indisponível')), 1000, {
      oQue: 'delegate GPU',
    })
    await expect(promessa).rejects.toThrow('WebGL indisponível')
  })

  it('desiste quando a promessa não volta — é o caso da GPU que trava', async () => {
    const nuncaVolta = new Promise<string>(() => {})
    const promessa = comPrazo(nuncaVolta, 12_000, { oQue: 'delegate GPU' })
    const capturado = promessa.catch((erro: unknown) => erro)
    await vi.advanceTimersByTimeAsync(12_000)
    const erro = await capturado
    expect(erro).toBeInstanceOf(DeadlineError)
    expect((erro as Error).message).toContain('delegate GPU')
  })

  it('entrega ao "chegou tarde" o valor que venceu o prazo — é assim que o recurso órfão fecha', async () => {
    let resolver: (valor: string) => void = () => {}
    const lenta = new Promise<string>((r) => {
      resolver = r
    })
    const tardios: string[] = []
    const promessa = comPrazo(lenta, 1000, {
      oQue: 'delegate GPU',
      aoChegarTarde: (valor) => tardios.push(valor),
    })
    const capturado = promessa.catch(() => 'estourou')

    await vi.advanceTimersByTimeAsync(1000)
    expect(await capturado).toBe('estourou')

    resolver('landmarker que chegou tarde')
    await vi.advanceTimersByTimeAsync(0)
    expect(tardios).toEqual(['landmarker que chegou tarde'])
  })

  it('não chama "chegou tarde" quando o valor chegou em tempo', async () => {
    const tardios: string[] = []
    await comPrazo(Promise.resolve('em tempo'), 1000, {
      oQue: 'delegate GPU',
      aoChegarTarde: (valor) => tardios.push(valor),
    })
    await vi.advanceTimersByTimeAsync(0)
    expect(tardios).toEqual([])
  })
})
