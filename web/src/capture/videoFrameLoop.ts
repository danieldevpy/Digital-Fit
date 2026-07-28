// Loop de frames do vídeo (SPEC-001): `requestVideoFrameCallback` quando existe,
// `requestAnimationFrame` como fallback.
//
// rVFC dispara uma vez por frame REAL do vídeo; o rAF dispara por repaint da tela
// e pode repetir o mesmo frame — quem filtra repetição é o chamador.

/** Instante atual em epoch ms com precisão sub-ms (o `ts` do contrato). */
export function epochNow(): number {
  return performance.timeOrigin + performance.now()
}

type VideoWithFrameCallback = HTMLVideoElement & {
  requestVideoFrameCallback?: (callback: (now: number) => void) => number
  cancelVideoFrameCallback?: (handle: number) => void
}

/** Devolve a função de cancelamento. */
export function createVideoFrameLoop(
  video: HTMLVideoElement,
  onFrame: (epochMs: number) => void,
): () => void {
  const target = video as VideoWithFrameCallback
  let cancelled = false

  if (typeof target.requestVideoFrameCallback === 'function') {
    let handle = 0
    const step = () => {
      if (cancelled) return
      onFrame(epochNow())
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
