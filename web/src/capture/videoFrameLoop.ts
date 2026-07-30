// Loop de frames do vídeo (SPEC-001): `requestVideoFrameCallback` quando existe,
// `requestAnimationFrame` como fallback.
//
// rVFC dispara uma vez por frame REAL do vídeo; o rAF dispara por repaint da tela
// e pode repetir o mesmo frame — quem filtra repetição é o chamador.

/** Instante atual em epoch ms com precisão sub-ms (o `ts` do contrato). */
export function epochNow(): number {
  return performance.timeOrigin + performance.now()
}

/**
 * Metadados que o rVFC entrega junto do frame. Só o que usamos está declarado.
 *
 * `presentedFrames` é contado pelo COMPOSITOR, não pelo nosso callback: ele continua andando
 * quando pulamos frames porque a inferência demorou. É por isso que ele é a única forma
 * honesta de saber a cadência real da câmera (T-084) — contar chamadas do loop mede o
 * gargalo, que quase sempre somos nós.
 */
export interface VideoFrameMetadata {
  presentedFrames?: number
}

type VideoWithFrameCallback = HTMLVideoElement & {
  requestVideoFrameCallback?: (
    callback: (now: number, metadata: VideoFrameMetadata) => void,
  ) => number
  cancelVideoFrameCallback?: (handle: number) => void
}

/** Devolve a função de cancelamento. */
export function createVideoFrameLoop(
  video: HTMLVideoElement,
  onFrame: (epochMs: number, metadata?: VideoFrameMetadata) => void,
): () => void {
  const target = video as VideoWithFrameCallback
  let cancelled = false

  if (typeof target.requestVideoFrameCallback === 'function') {
    let handle = 0
    const step = (_now: number, metadata: VideoFrameMetadata) => {
      if (cancelled) return
      onFrame(epochNow(), metadata)
      handle = target.requestVideoFrameCallback!(step)
    }
    handle = target.requestVideoFrameCallback(step)
    return () => {
      cancelled = true
      target.cancelVideoFrameCallback?.(handle)
    }
  }

  let animationFrame = 0
  const step = () => {
    if (cancelled) return
    onFrame(epochNow())
    animationFrame = requestAnimationFrame(step)
  }
  animationFrame = requestAnimationFrame(step)
  return () => {
    cancelled = true
    cancelAnimationFrame(animationFrame)
  }
}

export function hasVideoFrameCallback(video: HTMLVideoElement): boolean {
  return typeof (video as VideoWithFrameCallback).requestVideoFrameCallback === 'function'
}
