import { describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import { displayName, historyDate, historyTotals, trialMessage } from './accountSummary'

const RELATORIO: SessionReport = {
  session_id: 's1',
  exercise: 'jumping_jack',
  mode: 'edge',
  reason: 'timeout',
  rep_count: 20,
  duration_ms: 30_000,
  cadence_rpm: 40,
  cadence_windows: [],
  rep_durations_ms: [],
  feedback_counts: {},
  scene_warning_counts: {},
  calibration_samples: 12,
  config_version: 0,
  created_at: '2026-07-29T10:00:00Z',
}

describe('trialMessage', () => {
  it('recusado por trial diz o que fazer, não só o que aconteceu', () => {
    const texto = trialMessage(null, true)
    expect(texto).toMatch(/Crie uma conta/)
  })

  it('a última sessão do dia avisa', () => {
    expect(trialMessage({ used: 2, limit: 3, remaining: 1 }, false)).toMatch(/Resta 1 sessão/)
  })

  it('quem ainda tem folga não é lembrado do limite', () => {
    expect(trialMessage({ used: 0, limit: 3, remaining: 3 }, false)).toBeNull()
    expect(trialMessage({ used: 1, limit: 3, remaining: 2 }, false)).toBeNull()
  })

  it('zerado sem ter sido recusado ainda também avisa', () => {
    expect(trialMessage({ used: 3, limit: 3, remaining: 0 }, false)).toMatch(/usou suas 3/)
  })

  it('quem tem conta não vê nada sobre trial', () => {
    expect(trialMessage(null, false)).toBeNull()
  })
})

describe('historyDate', () => {
  const agora = new Date(2026, 6, 29, 8, 0) // 29 jul 2026, 08:00 local

  it('hoje é "hoje"', () => {
    expect(historyDate(new Date(2026, 6, 29, 7, 30).toISOString(), agora)).toMatch(/^hoje /)
  })

  it('ontem é "ontem" mesmo cabendo em 24 h', () => {
    // 23:50 de ontem para 00:30 de hoje: 40 minutos de diferença, dia diferente.
    const meiaNoiteEMeia = new Date(2026, 6, 29, 0, 30)
    const ontemTarde = new Date(2026, 6, 28, 23, 50)
    expect(historyDate(ontemTarde.toISOString(), meiaNoiteEMeia)).toMatch(/^ontem /)
  })

  it('mais velho que isso vira data curta', () => {
    expect(historyDate(new Date(2026, 6, 24, 7, 55).toISOString(), agora)).toMatch(/^24 de jul/)
  })

  it('data inválida não quebra a lista', () => {
    expect(historyDate('nada disso', agora)).toBe('—')
  })
})

describe('historyTotals', () => {
  it('soma sessões e reps e guarda a melhor cadência', () => {
    const totais = historyTotals([
      RELATORIO,
      { ...RELATORIO, session_id: 's2', rep_count: 25, cadence_rpm: 52.4 },
      { ...RELATORIO, session_id: 's3', rep_count: 18, cadence_rpm: 33 },
    ])
    expect(totais).toEqual({ sessions: 3, reps: 63, bestCadence: 52.4 })
  })

  it('histórico vazio dá zeros, não NaN', () => {
    expect(historyTotals([])).toEqual({ sessions: 0, reps: 0, bestCadence: 0 })
  })
})

describe('displayName', () => {
  it('cumprimenta pelo primeiro nome', () => {
    expect(displayName({ name: 'Ana Maria Souza', email: 'a@b.com' })).toBe('Ana')
  })

  it('sem nome, cai no e-mail sem o domínio', () => {
    expect(displayName({ name: '   ', email: 'daniel@example.com' })).toBe('daniel')
  })

  it('sem usuário, texto vazio', () => {
    expect(displayName(null)).toBe('')
  })
})
