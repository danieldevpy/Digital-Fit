// Capability probe da SPEC-001: decide EDGE vs CLOUD.
//
// A decisão é função pura (`decideMode`) para ser testável sem GPU e sem câmera.
// A medição em si (`runCapabilityProbe`) vive em `runProbe.ts`.
import { Mode } from '../lib/events'

/** Abaixo disto o device não sustenta pose no navegador (SPEC-001). */
export const EDGE_FPS_THRESHOLD = 12

/** Duração da medição. O critério 1 da spec exige o probe inteiro em ≤ 3s. */
export const PROBE_DURATION_MS = 2000

export interface CapabilityInput {
  /** fps medido no probe; `null` quando o probe falhou ou nem rodou. */
  probeFps: number | null
  webgl: boolean
  wasmSimd: boolean
  /** O probe lançou exceção (modelo não carregou, contexto perdido, etc.). */
  failed?: boolean
}

/**
 * CLOUD nunca é escolha otimista: só sai daqui quando o device realmente não dá
 * conta. Mesmo assim ainda depende de slot de admission control (SPEC-009) —
 * esta função decide o que *pedir*, não o que a sessão vai usar.
 */
export function decideMode(input: CapabilityInput): Mode {
  if (input.failed) return Mode.CLOUD
  if (!input.webgl || !input.wasmSimd) return Mode.CLOUD
  if (input.probeFps === null || !Number.isFinite(input.probeFps)) return Mode.CLOUD
  return input.probeFps >= EDGE_FPS_THRESHOLD ? Mode.EDGE : Mode.CLOUD
}

/** `?mode=edge|cloud` força o modo para debug (SPEC-001). Valor inválido é ignorado. */
export function parseModeOverride(search: string): Mode | null {
  const raw = new URLSearchParams(search).get('mode')?.trim().toLowerCase()
  if (raw === Mode.EDGE || raw === Mode.CLOUD) return raw
  return null
}

/** WebGL2, com fallback para WebGL1 — é o delegate GPU do MediaPipe. */
export function detectWebgl(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'))
  } catch {
    return false
  }
}

/**
 * Módulo WASM mínimo que usa `v128` (SIMD). Se o motor não validar, o runtime
 * do MediaPipe cai para o build `nosimd`, bem mais lento.
 */
const WASM_SIMD_PROBE = Uint8Array.from([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x05, 0x01, 0x60, 0x00, 0x01, 0x7b, 0x03,
  0x02, 0x01, 0x00, 0x0a, 0x0a, 0x01, 0x08, 0x00, 0x41, 0x00, 0xfd, 0x0f, 0xfd, 0x62, 0x0b,
])

export function detectWasmSimd(): boolean {
  try {
    return WebAssembly.validate(WASM_SIMD_PROBE)
  } catch {
    return false
  }
}
