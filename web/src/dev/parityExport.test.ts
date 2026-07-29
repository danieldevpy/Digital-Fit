import { describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import { buildParityResult, parityFileName } from './parityExport'

const RELATORIO: SessionReport = {
  session_id: 's1',
  exercise: 'jumping_jack',
  mode: 'edge',
  reason: 'timeout',
  rep_count: 19,
  duration_ms: 28_412,
  cadence_rpm: 40.1,
  cadence_windows: [3, 4, 3],
  rep_durations_ms: [1000, 980],
  feedback_counts: { ARMS_TOO_LOW: 2 },
  scene_warning_counts: { OUT_OF_FRAME: 1 },
  calibration_samples: 15,
  created_at: '2026-07-29T10:00:00Z',
}

describe('resultado do navegador para a bancada', () => {
  it('sai no formato que o `VideoResult` do harness lê', () => {
    const saida = buildParityResult({ report: RELATORIO, videoName: 'jj_01', frames: 412 })

    expect(saida.name).toBe('jj_01')
    expect(saida.exercise).toBe('jumping_jack')
    expect(saida.reps).toBe(19)
    expect(saida.frames).toBe(412)
    expect(saida.rep_durations_ms).toEqual([1000, 980])
    expect(saida.quality_signals).toEqual({ OUT_OF_FRAME: 1 })
  })

  it('marca a perna — sem isso o arquivo seria indistinguível de um do harness', () => {
    expect(buildParityResult({ report: RELATORIO, videoName: 'jj_01' }).source).toBe(
      'browser-edge',
    )
  })

  it('a duração vai em segundos, como a bancada mede', () => {
    expect(buildParityResult({ report: RELATORIO, videoName: 'jj_01' }).duration_s).toBe(28.41)
  })

  it('carrega o delegate: `gpu` e `cpu` dão resultados diferentes', () => {
    const saida = buildParityResult({
      report: RELATORIO,
      videoName: 'jj_01',
      delegate: 'gpu',
      userAgent: 'Mozilla/5.0',
    })

    expect(saida.delegate).toBe('gpu')
    expect(saida.user_agent).toBe('Mozilla/5.0')
  })

  it('sem rótulo, `expected_reps` é nulo — não zero, que significaria "esperava nenhuma"', () => {
    expect(buildParityResult({ report: RELATORIO, videoName: 'jj_01' }).expected_reps).toBeNull()
  })

  it('com rótulo, ele viaja junto para o harness calcular o erro', () => {
    const saida = buildParityResult({
      report: RELATORIO,
      videoName: 'jj_01',
      expectedReps: 20,
    })

    expect(saida.expected_reps).toBe(20)
  })
})

describe('nome do arquivo baixado', () => {
  it('casa com o nome do vídeo, para parear com o relatório do harness', () => {
    expect(parityFileName('jj_frontal_boa_luz')).toBe('jj_frontal_boa_luz.browser.json')
  })

  it('espaço e acento não viram nome de arquivo quebrado', () => {
    expect(parityFileName('vídeo do daniel (2)')).toBe('v_deo_do_daniel_2_.browser.json')
  })

  it('nome vazio ainda gera um arquivo válido', () => {
    expect(parityFileName('')).toBe('sessao.browser.json')
  })
})
