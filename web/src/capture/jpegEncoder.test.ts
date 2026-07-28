import { describe, expect, it } from 'vitest'

import { FRAME_RAW_MAX_SIDE } from '../lib/events'
import { scaledSize } from './jpegEncoder'

describe('redução para o modo cloud', () => {
  it('encaixa o maior lado no limite do contrato preservando a proporção', () => {
    // 640×480 é a resolução preferida da SPEC-001; 4:3 tem de sobreviver à redução, senão a
    // pose sai distorcida e os ângulos da FSM mudam.
    const { width, height } = scaledSize(640, 480)

    expect(Math.max(width, height)).toBe(FRAME_RAW_MAX_SIDE)
    expect(width / height).toBeCloseTo(640 / 480, 2)
  })

  it('reduz pelo lado maior também no retrato', () => {
    const { width, height } = scaledSize(480, 640)

    expect(height).toBe(FRAME_RAW_MAX_SIDE)
    expect(width).toBe(240)
  })

  it('nunca amplia — banda gasta para inventar pixel', () => {
    expect(scaledSize(160, 120)).toEqual({ width: 160, height: 120 })
  })

  it('respeita o teto que o servidor valida', () => {
    // O contrato recusa maior lado acima de FRAME_RAW_MAX_SIDE; qualquer resolução de
    // câmera plausível tem de passar depois desta função.
    for (const [w, h] of [
      [1920, 1080],
      [1280, 720],
      [640, 480],
      [3840, 2160],
    ]) {
      const alvo = scaledSize(w!, h!)
      expect(Math.max(alvo.width, alvo.height)).toBeLessThanOrEqual(FRAME_RAW_MAX_SIDE)
    }
  })

  it('não gera lado zero em proporção extrema', () => {
    // Canvas com dimensão 0 lança; arredondar 2000×3 para baixo daria altura 0.
    const { width, height } = scaledSize(2000, 3)

    expect(width).toBe(FRAME_RAW_MAX_SIDE)
    expect(height).toBeGreaterThanOrEqual(1)
  })

  it('vídeo sem dimensão devolve zero em vez de dividir por zero', () => {
    expect(scaledSize(0, 0)).toEqual({ width: 0, height: 0 })
  })
})
