import { describe, expect, it } from 'vitest'
import { warmAssets, warmupLabel, type AssetProgress } from './assetWarmup'

/** `fetch` de mentira: HEAD devolve o tamanho, GET devolve o corpo em pedaços. */
function fakeFetch(
  arquivos: Record<string, { tamanho: number | null; pedacos: number[]; encoding?: string }>,
  registro: string[] = [],
): typeof fetch {
  return ((url: string, init?: RequestInit) => {
    const arquivo = arquivos[url]
    if (!arquivo) return Promise.resolve({ ok: false, body: null, headers: new Headers() } as Response)

    if (init?.method === 'HEAD') {
      const headers = new Headers()
      if (arquivo.tamanho !== null) headers.set('content-length', String(arquivo.tamanho))
      if (arquivo.encoding) headers.set('content-encoding', arquivo.encoding)
      return Promise.resolve({ ok: true, body: null, headers } as Response)
    }

    registro.push(url)
    let i = 0
    const body = {
      getReader: () => ({
        read: () =>
          Promise.resolve(
            i < arquivo.pedacos.length
              ? { done: false, value: new Uint8Array(arquivo.pedacos[i++]!) }
              : { done: true, value: undefined },
          ),
      }),
    }
    return Promise.resolve({ ok: true, body, headers: new Headers() } as unknown as Response)
  }) as unknown as typeof fetch
}

describe('warmAssets', () => {
  it('baixa cada asset UMA vez — é o conserto do download duplicado', async () => {
    const registro: string[] = []
    const fetchImpl = fakeFetch(
      {
        '/wasm/a.wasm': { tamanho: 300, pedacos: [100, 200] },
        '/models/m.task': { tamanho: 100, pedacos: [100] },
      },
      registro,
    )
    await warmAssets(['/wasm/a.wasm', '/models/m.task'], () => {}, fetchImpl)
    expect(registro).toEqual(['/wasm/a.wasm', '/models/m.task'])
  })

  it('relata progresso somando os pedaços de todos os assets', async () => {
    const vistos: AssetProgress[] = []
    const fetchImpl = fakeFetch({
      '/wasm/a.wasm': { tamanho: 300, pedacos: [100, 200] },
      '/models/m.task': { tamanho: 100, pedacos: [100] },
    })
    await warmAssets(['/wasm/a.wasm', '/models/m.task'], (p) => vistos.push(p), fetchImpl)
    expect(vistos).toEqual([
      { recebidos: 0, total: 400 },
      { recebidos: 100, total: 400 },
      { recebidos: 300, total: 400 },
      { recebidos: 400, total: 400 },
    ])
  })

  it('sem Content-Length em algum asset, o total é null — melhor nada que porcentagem errada', async () => {
    const vistos: AssetProgress[] = []
    const fetchImpl = fakeFetch({
      '/wasm/a.wasm': { tamanho: null, pedacos: [100] },
    })
    await warmAssets(['/wasm/a.wasm'], (p) => vistos.push(p), fetchImpl)
    expect(vistos.every((p) => p.total === null)).toBe(true)
  })

  it('resposta comprimida zera o total: Content-Length é da rede, os bytes lidos são do stream', async () => {
    const vistos: AssetProgress[] = []
    const fetchImpl = fakeFetch({
      '/wasm/a.wasm': { tamanho: 300, pedacos: [1000], encoding: 'gzip' },
    })
    await warmAssets(['/wasm/a.wasm'], (p) => vistos.push(p), fetchImpl)
    expect(vistos.every((p) => p.total === null)).toBe(true)
  })

  it('falha de rede não sobe: o MediaPipe ainda baixa por conta própria', async () => {
    const explode = (() => Promise.reject(new Error('rede caiu'))) as unknown as typeof fetch
    await expect(warmAssets(['/wasm/a.wasm'], () => {}, explode)).resolves.toBeUndefined()
  })

  it('asset que responde erro é pulado sem interromper os outros', async () => {
    const registro: string[] = []
    const fetchImpl = fakeFetch({ '/models/m.task': { tamanho: 100, pedacos: [100] } }, registro)
    await warmAssets(['/nao/existe.wasm', '/models/m.task'], () => {}, fetchImpl)
    expect(registro).toEqual(['/models/m.task'])
  })
})

describe('warmupLabel', () => {
  it('mostra porcentagem e MB quando o total é conhecido', () => {
    expect(warmupLabel({ recebidos: 4_404_019, total: 10_485_760 })).toBe('42% · 4,2 de 10,0 MB')
  })

  it('sem total, mostra só o que já veio', () => {
    expect(warmupLabel({ recebidos: 2_097_152, total: null })).toBe('2,0 MB')
  })

  it('total menor que o recebido não vira porcentagem: o total é que está errado', () => {
    // É o caso do `.wasm` gzipado: 11,0 MB lidos contra 3,2 MB anunciados na rede.
    expect(warmupLabel({ recebidos: 11_534_336, total: 3_355_443 })).toBe('11,0 MB')
  })
})
