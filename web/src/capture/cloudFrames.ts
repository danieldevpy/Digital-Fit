// Envio de `frame.raw` no modo cloud (SPEC-005 / T-015).
//
// Separado do hook de propósito: o interessante aqui é a decisão de descarte, e ela precisa
// ser testável sem câmera, sem React e sem canvas.
//
// A diferença em relação ao caminho edge é que a codificação é ASSÍNCRONA. Um JPEG que
// demore mais que os 100ms do alvo de 10fps faria os frames se empilharem, e a fila cresceria
// sem limite enquanto a pessoa treina. Por isso existe uma trava de "um por vez": frame que
// chega com codificação em andamento é descartado, não enfileirado — frame novo vale mais
// que frame velho, a mesma regra do backpressure do gateway (SPEC-002).
import type { FrameRawData } from '../lib/events'
import type { FrameClock, FrameTick } from './frameClock'

export interface CloudSenderDeps {
  clock: FrameClock
  encode: (video: HTMLVideoElement) => Promise<FrameRawData | null>
  send: (frame: FrameRawData, tick: FrameTick) => void
  /** Chamado a cada envio — só diagnóstico. */
  onSent?: (info: { tick: FrameTick; bytes: number }) => void
}

export interface CloudSender {
  /** Liga no loop de vídeo: recebe o instante do frame e decide o que fazer. */
  onFrame(epochMs: number): Promise<void>
  /** Frames pulados por já haver codificação em andamento. */
  readonly droppedWhileBusy: number
  /** Frames enviados. */
  readonly sent: number
}

export function createCloudSender(video: HTMLVideoElement, deps: CloudSenderDeps): CloudSender {
  let inFlight = false
  let dropped = 0
  let sent = 0
  let lastVideoTime = -1

  return {
    get droppedWhileBusy() {
      return dropped
    },
    get sent() {
      return sent
    },

    async onFrame(epochMs: number): Promise<void> {
      if (video.readyState < video.HAVE_CURRENT_DATA || video.videoWidth === 0) return

      // Com o fallback de `requestAnimationFrame`, o mesmo frame do vídeo pode chegar duas
      // vezes; enviá-lo de novo gastaria banda e `seq` por nada.
      if (video.currentTime === lastVideoTime) return

      // A trava vem ANTES do relógio: consumir o tick e depois descartar deixaria o próximo
      // frame fora do agendamento, derrubando o fps efetivo abaixo do alvo.
      if (inFlight) {
        dropped += 1
        return
      }

      const tick = deps.clock.tick(epochMs)
      if (!tick) return

      lastVideoTime = video.currentTime
      inFlight = true
      try {
        const frame = await deps.encode(video)
        if (!frame) return
        deps.send(frame, tick)
        sent += 1
        deps.onSent?.({ tick, bytes: frame.jpeg.byteLength })
      } finally {
        inFlight = false
      }
    },
  }
}
