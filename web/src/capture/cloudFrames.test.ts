import { describe, expect, it, vi } from 'vitest'

import type { FrameRawData } from '../lib/events'
import { createCloudSender } from './cloudFrames'
import { CLOUD_TARGET_FPS, createFrameClock } from './frameClock'

/** Vídeo mínimo: só o que o sender lê. `currentTime` avança a cada frame novo. */
function videoFalso(): HTMLVideoElement & { currentTime: number } {
  return {
    readyState: 2,
    HAVE_CURRENT_DATA: 2,
    videoWidth: 640,
    videoHeight: 480,
    currentTime: 0,
  } as unknown as HTMLVideoElement & { currentTime: number }
}

const JPEG: FrameRawData = { jpeg: new Uint8Array([0xff, 0xd8, 0xff, 0x00]), width: 320, height: 240 }

/** Codificação controlada pelo teste: resolve quando o teste mandar. */
function encodeManual() {
  const pendentes: ((valor: FrameRawData | null) => void)[] = []
  return {
    encode: () => new Promise<FrameRawData | null>((resolve) => pendentes.push(resolve)),
    concluir: (valor: FrameRawData | null = JPEG) => {
      const resolver = pendentes.shift()
      resolver?.(valor)
    },
    get emAndamento() {
      return pendentes.length
    },
  }
}

describe('envio de frame.raw no modo cloud', () => {
  it('envia um frame codificado com o tick do relógio', async () => {
    const video = videoFalso()
    const send = vi.fn()
    const sender = createCloudSender(video, {
      clock: createFrameClock(CLOUD_TARGET_FPS),
      encode: () => Promise.resolve(JPEG),
      send,
    })

    video.currentTime = 0.1
    await sender.onFrame(1_000)

    expect(send).toHaveBeenCalledTimes(1)
    const [frame, tick] = send.mock.calls[0]!
    expect(frame).toBe(JPEG)
    expect(tick.seq).toBe(0)
    expect(sender.sent).toBe(1)
  })

  it('NÃO empilha frames enquanto a codificação anterior não termina', async () => {
    // O risco real do caminho cloud: `toBlob` mais lento que os 100ms do alvo de 10fps.
    // Sem esta trava a fila cresceria indefinidamente enquanto a pessoa treina.
    const video = videoFalso()
    const send = vi.fn()
    const manual = encodeManual()
    const sender = createCloudSender(video, {
      clock: createFrameClock(CLOUD_TARGET_FPS),
      encode: manual.encode,
      send,
    })

    video.currentTime = 0.1
    const primeiro = sender.onFrame(1_000)
    expect(manual.emAndamento).toBe(1)

    // Três frames chegam durante a codificação: todos devem ser descartados.
    for (const [i, t] of [1_100, 1_200, 1_300].entries()) {
      video.currentTime = 0.2 + i * 0.1
      await sender.onFrame(t)
    }

    expect(sender.droppedWhileBusy).toBe(3)
    expect(manual.emAndamento).toBe(1)
    expect(send).not.toHaveBeenCalled()

    manual.concluir()
    await primeiro
    expect(send).toHaveBeenCalledTimes(1)
  })

  it('descartar não consome o relógio: o frame seguinte sai no ritmo', async () => {
    // Se a trava viesse depois do `tick`, o agendamento avançaria sem envio e o fps
    // efetivo cairia abaixo do alvo mesmo com a codificação já livre.
    const video = videoFalso()
    const send = vi.fn()
    const manual = encodeManual()
    const sender = createCloudSender(video, {
      clock: createFrameClock(CLOUD_TARGET_FPS),
      encode: manual.encode,
      send,
    })

    video.currentTime = 0.1
    const primeiro = sender.onFrame(1_000)
    video.currentTime = 0.2
    await sender.onFrame(1_030) // descartado: ocupado
    manual.concluir()
    await primeiro

    video.currentTime = 0.3
    const segundo = sender.onFrame(1_060)
    manual.concluir()
    await segundo

    // 1_060 já passou o intervalo de 100ms? Não — mas o relógio não foi consumido pelo
    // descarte, então o tick de 1_060 é avaliado contra o agendamento original.
    expect(send).toHaveBeenCalledTimes(1)

    video.currentTime = 0.4
    const terceiro = sender.onFrame(1_100)
    manual.concluir()
    await terceiro
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('ignora frame repetido do vídeo', async () => {
    const video = videoFalso()
    const send = vi.fn()
    const sender = createCloudSender(video, {
      clock: createFrameClock(CLOUD_TARGET_FPS),
      encode: () => Promise.resolve(JPEG),
      send,
    })

    video.currentTime = 0.5
    await sender.onFrame(1_000)
    await sender.onFrame(1_200) // mesmo currentTime: nada novo para enviar

    expect(send).toHaveBeenCalledTimes(1)
  })

  it('vídeo sem dimensão ainda não envia nada', async () => {
    const video = videoFalso()
    Object.assign(video, { videoWidth: 0 })
    const send = vi.fn()
    const sender = createCloudSender(video, {
      clock: createFrameClock(CLOUD_TARGET_FPS),
      encode: () => Promise.resolve(JPEG),
      send,
    })

    await sender.onFrame(1_000)

    expect(send).not.toHaveBeenCalled()
  })

  it('codificação que falha não conta como envio nem trava o sender', async () => {
    const video = videoFalso()
    const send = vi.fn()
    const sender = createCloudSender(video, {
      clock: createFrameClock(CLOUD_TARGET_FPS),
      encode: () => Promise.resolve(null),
      send,
    })

    video.currentTime = 0.1
    await sender.onFrame(1_000)
    expect(send).not.toHaveBeenCalled()

    // A trava tem de ter sido liberada, senão o modo cloud morreria no primeiro erro.
    video.currentTime = 0.2
    await sender.onFrame(1_200)
    expect(sender.droppedWhileBusy).toBe(0)
  })
})
