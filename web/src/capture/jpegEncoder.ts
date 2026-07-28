// Redução + codificação JPEG do modo cloud (SPEC-005 / T-015).
//
// O servidor recusa frame com o maior lado acima de FRAME_RAW_MAX_SIDE — reduzir aqui não é
// otimização, é o contrato. O motivo é de orçamento: o pose-worker roda com 1 vCPU (SPEC-005,
// critério 2: ≤80ms por frame), então mandar 640×480 empurraria o resize para o lado mais
// caro do sistema.
import { FRAME_RAW_MAX_SIDE, FRAME_RAW_QUALITY, type FrameRawData } from '../lib/events'

/**
 * Dimensão de destino preservando a proporção, com o maior lado em `maxSide`.
 *
 * Nunca amplia: fonte menor que o alvo passa como está. Ampliar gastaria banda para inventar
 * pixel que o modelo não tem como usar.
 */
export function scaledSize(
  width: number,
  height: number,
  maxSide: number = FRAME_RAW_MAX_SIDE,
): { width: number; height: number } {
  const maior = Math.max(width, height)
  if (maior <= 0) return { width: 0, height: 0 }
  if (maior <= maxSide) return { width, height }

  const fator = maxSide / maior
  // `max(1, …)`: um vídeo muito alongado poderia arredondar o lado menor para 0, e canvas
  // com dimensão 0 lança em vez de devolver imagem vazia.
  return {
    width: Math.max(1, Math.round(width * fator)),
    height: Math.max(1, Math.round(height * fator)),
  }
}

/** Canvas de trabalho reaproveitado entre frames — alocar 10×/s viraria pressão de GC. */
let scratch: HTMLCanvasElement | null = null

function scratchCanvas(width: number, height: number): HTMLCanvasElement {
  scratch ??= document.createElement('canvas')
  if (scratch.width !== width || scratch.height !== height) {
    scratch.width = width
    scratch.height = height
  }
  return scratch
}

/**
 * Codifica o frame atual do vídeo como JPEG reduzido.
 *
 * `null` quando o vídeo ainda não tem dimensão — acontece nos primeiros frames depois do
 * `getUserMedia`, e é esperado, não erro.
 */
export async function encodeFrame(
  video: HTMLVideoElement,
  { maxSide = FRAME_RAW_MAX_SIDE, quality = FRAME_RAW_QUALITY } = {},
): Promise<FrameRawData | null> {
  const origem = { width: video.videoWidth, height: video.videoHeight }
  if (origem.width === 0 || origem.height === 0) return null

  const alvo = scaledSize(origem.width, origem.height, maxSide)
  const canvas = scratchCanvas(alvo.width, alvo.height)
  const contexto = canvas.getContext('2d')
  if (!contexto) return null

  contexto.drawImage(video, 0, 0, alvo.width, alvo.height)

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, 'image/jpeg', quality)
  })
  if (!blob) return null

  return {
    jpeg: new Uint8Array(await blob.arrayBuffer()),
    width: alvo.width,
    height: alvo.height,
  }
}

/** Só para teste: descarta o canvas reaproveitado. */
export function resetScratchCanvas(): void {
  scratch = null
}
