import { describe, expect, it, vi } from 'vitest'

import { loadVideoFile, seekTo, shortName } from './videoSource'

/**
 * `<video>` de mentira. Os testes rodam em `environment: 'node'`, então não há elemento de
 * verdade — e o que importa aqui é a **ordem**: carregar, posicionar em zero e NÃO tocar.
 */
function videoFalso(options: { falha?: boolean } = {}) {
  const eventos = new Map<string, Array<() => void>>()
  const video = {
    src: '',
    srcObject: {} as unknown,
    muted: false,
    loop: true,
    playbackRate: 2,
    currentTime: 7,
    readyState: 0,
    HAVE_METADATA: 1,
    HAVE_CURRENT_DATA: 2,
    videoWidth: 0,
    videoHeight: 0,
    duration: Number.NaN,
    played: false,
    play: vi.fn(async () => {
      video.played = true
    }),
    addEventListener(nome: string, fn: () => void) {
      const lista = eventos.get(nome) ?? []
      lista.push(fn)
      eventos.set(nome, lista)
      // O elemento real emite sozinho; aqui o disparo é imediato para o teste não depender
      // de temporizador.
      queueMicrotask(() => {
        if (nome === 'loadedmetadata' && !options.falha) {
          video.readyState = 2
          video.videoWidth = 854
          video.videoHeight = 480
          video.duration = 28.9
          fn()
        }
        if (nome === 'error' && options.falha) fn()
        if (nome === 'seeked' || nome === 'canplay') fn()
      })
    },
    removeEventListener(nome: string, fn: () => void) {
      eventos.set(nome, (eventos.get(nome) ?? []).filter((item) => item !== fn))
    },
  }
  return video as unknown as HTMLVideoElement & { played: boolean; play: ReturnType<typeof vi.fn> }
}

function arquivoFalso(nome = 'jj_01.mp4'): File {
  return { name: nome } as File
}

const urlFalsa = () => {
  const criadas: string[] = []
  const revogadas: string[] = []
  globalThis.URL.createObjectURL = vi.fn(() => {
    const url = `blob:${criadas.length}`
    criadas.push(url)
    return url
  })
  globalThis.URL.revokeObjectURL = vi.fn((url: string) => void revogadas.push(url))
  return { criadas, revogadas }
}

describe('carregar arquivo de vídeo', () => {
  it('devolve as dimensões e a duração lidas do arquivo', async () => {
    urlFalsa()
    const video = videoFalso()

    const carregado = await loadVideoFile(video, arquivoFalso())

    expect(carregado.width).toBe(854)
    expect(carregado.height).toBe(480)
    expect(carregado.durationS).toBeCloseTo(28.9)
  })

  it('NÃO toca o vídeo: quem dá o play é o pipeline, depois do probe', async () => {
    urlFalsa()
    const video = videoFalso()

    await loadVideoFile(video, arquivoFalso())

    // Este é o teste que protege a paridade. Se o vídeo tocasse aqui, os ~2 s do capability
    // probe comeriam o começo do arquivo e a contagem do navegador divergiria da do harness
    // por montagem, não por diferença de implementação.
    expect(video.played).toBe(false)
    expect(video.play).not.toHaveBeenCalled()
    expect(video.currentTime).toBe(0)
  })

  it('larga o MediaStream da câmera e prepara o elemento', async () => {
    urlFalsa()
    const video = videoFalso()

    await loadVideoFile(video, arquivoFalso())

    expect(video.srcObject).toBeNull()
    expect(video.src).toMatch(/^blob:/)
    expect(video.muted).toBe(true) // sem isto o navegador recusa o play() programático
    expect(video.loop).toBe(false) // repetir contaria a mesma série duas vezes
    expect(video.playbackRate).toBe(1) // 2x mudaria a cadência medida
  })

  it('arquivo ilegível não vaza o object URL', async () => {
    const { revogadas } = urlFalsa()
    const video = videoFalso({ falha: true })

    await expect(loadVideoFile(video, arquivoFalso('quebrado.avi'))).rejects.toThrow(/mp4/)
    expect(revogadas).toHaveLength(1)
  })
})

describe('seekTo', () => {
  it('não espera evento quando já está no ponto e com frame decodificado', async () => {
    const video = videoFalso()
    video.currentTime = 3
    ;(video as unknown as { readyState: number }).readyState = 2

    await expect(seekTo(video, 3)).resolves.toBeUndefined()
  })
})

describe('shortName', () => {
  it('tira a extensão para casar com o nome no relatório do harness', () => {
    expect(shortName('jj_frontal_boa_luz.mp4')).toBe('jj_frontal_boa_luz')
  })

  it('nome sem extensão passa inteiro', () => {
    expect(shortName('jj_01')).toBe('jj_01')
  })
})
