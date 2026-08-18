import { describe, expect, it } from 'vitest'
import { useI18nStore } from '../i18n/store'
import { Code, SessionEndReason } from '../lib/events'
import { cadenceBars, improvements, reasonText, windowLabel } from './reportSummary'
import type { SessionReport } from './sessionReport'

// `improvements` passa pelo `textForCode` (T-152: `catalog:code.*`, getter resolvido por
// `t()`) — as fixtures deste arquivo checam texto em pt-BR.
useI18nStore.getState().setLocale('pt-BR')

function relatorio(parcial: Partial<SessionReport> = {}): SessionReport {
  return {
    session_id: 's-1',
    exercise: 'jumping_jack',
    mode: 'edge',
    reason: SessionEndReason.COMPLETED,
    rep_count: 20,
    duration_ms: 30_000,
    cadence_rpm: 40,
    cadence_windows: [3, 4, 3, 4, 3, 3],
    rep_durations_ms: [],
    feedback_counts: {},
    scene_warning_counts: {},
    calibration_samples: 12,
    config_version: 0,
    created_at: '2026-07-28T12:00:00Z',
    ...parcial,
  }
}

describe('improvements', () => {
  it('junta execução e cena numa lista só, do mais frequente ao menos', () => {
    const itens = improvements(
      relatorio({
        feedback_counts: { [Code.ARMS_TOO_LOW]: 2 },
        scene_warning_counts: { [Code.TOO_FAR]: 5 },
      }),
    )

    expect(itens.map((item) => item.code)).toEqual([Code.TOO_FAR, Code.ARMS_TOO_LOW])
    expect(itens[0]).toMatchObject({ count: 5 })
  })

  it('soma o mesmo código vindo das duas origens', () => {
    // `ARMS_TOO_LOW` nasce como sinal de execução, mas nada impede o mesmo código nas duas
    // contagens — e para quem treinou é um aviso só.
    const itens = improvements(
      relatorio({
        feedback_counts: { [Code.ARMS_TOO_LOW]: 2 },
        scene_warning_counts: { [Code.ARMS_TOO_LOW]: 1 },
      }),
    )

    expect(itens).toHaveLength(1)
    expect(itens[0]?.count).toBe(3)
  })

  it('traduz o código para o mesmo texto que o HUD mostrou ao vivo', () => {
    const itens = improvements(relatorio({ feedback_counts: { [Code.OUT_OF_FRAME]: 1 } }))

    expect(itens[0]?.text).toBe('Apareça inteiro no quadro')
  })

  // A regressão que motivou a T-126: enquanto só o polichinelo contava, os dois códigos dele
  // eram o mundo inteiro. Quem terminava um agachamento lia `SQUAT_TOO_SHALLOW` em "o que
  // melhorar" — o nome da constante, na tela, depois de suar.
  it('nenhum código de execução chega à tela como identificador', () => {
    const itens = improvements(
      relatorio({
        feedback_counts: {
          [Code.SQUAT_TOO_SHALLOW]: 3,
          [Code.PUSHUP_TOO_SHALLOW]: 2,
          [Code.CRUNCH_TOO_FAST]: 1,
        },
      }),
    )

    for (const item of itens) expect(item.text).not.toBe(item.code)
    expect(itens[0]?.text).toBe('Desça mais no agachamento')
  })

  it('devolve lista vazia quando não houve aviso nenhum', () => {
    expect(improvements(relatorio())).toEqual([])
  })
})

describe('cadenceBars', () => {
  it('normaliza pelo pico da própria sessão', () => {
    expect(cadenceBars([1, 2, 4])).toEqual([0.25, 0.5, 1])
  })

  it('sessão sem nenhuma rep não vira divisão por zero', () => {
    expect(cadenceBars([0, 0, 0])).toEqual([0, 0, 0])
  })

  it('preserva as janelas vazias — o buraco é a pausa', () => {
    expect(cadenceBars([2, 0, 1])).toEqual([1, 0, 0.5])
  })
})

describe('reasonText', () => {
  it.each([
    [SessionEndReason.COMPLETED, 'Série completa'],
    [SessionEndReason.NO_DATA, 'Encerrada: paramos de te ver na câmera'],
  ])('%s vira %s', (motivo, esperado) => {
    expect(reasonText(motivo)).toBe(esperado)
  })

  it('motivo desconhecido não quebra a tela', () => {
    expect(reasonText('motivo_do_futuro')).toBe('Sessão encerrada')
  })
})

describe('windowLabel', () => {
  it('rotula em segundos a partir do início do exercício', () => {
    expect(windowLabel(0, 5000)).toBe('0s')
    expect(windowLabel(6, 5000)).toBe('30s')
  })
})
