import { describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import type { QuotaSnapshot } from '../session/quota'
import { displayName, historyDate, historyTotals, quotaNotice, renewLabel } from './accountSummary'

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

const AGORA = new Date('2026-07-31T18:00:00Z')

function quota(campos: Partial<QuotaSnapshot> = {}): QuotaSnapshot {
  return {
    used: 1,
    limit: 10,
    remaining: 9,
    unlimited: false,
    allowed: true,
    resets_at: '2026-08-01T00:00:00Z',
    plan: 'free',
    plan_name: 'Free',
    message: 'Você treinou muito hoje 🎉 Suas sessões de hoje acabaram.',
    ...campos,
  }
}

describe('quotaNotice', () => {
  it('esgotado mostra o título da spec, a contagem e quando renova', () => {
    const aviso = quotaNotice(quota({ used: 10, remaining: 0, allowed: false }), true, AGORA)

    expect(aviso?.title).toBe('Você treinou muito hoje 🎉')
    expect(aviso?.count).toBe('10 de 10 sessões de hoje')
    expect(aviso?.renew).toMatch(/^Renova às /)
  })

  it('o texto é o do servidor, não uma cópia local', () => {
    const doPainel = 'Mensagem que alguém escreveu no admin numa terça-feira.'
    const aviso = quotaNotice(quota({ allowed: false, message: doPainel }), false, AGORA)

    expect(aviso?.text).toBe(doPainel)
  })

  it('a contagem acompanha o limite do plano — 15 no painel, 15 na tela', () => {
    const aviso = quotaNotice(quota({ used: 15, limit: 15, remaining: 0, allowed: false }), true, AGORA)

    expect(aviso?.count).toBe('15 de 15 sessões de hoje')
  })

  it('a última sessão do dia avisa', () => {
    const aviso = quotaNotice(quota({ used: 9, remaining: 1 }), false, AGORA)

    expect(aviso?.text).toMatch(/Resta 1 sessão/)
  })

  it('o visitante é convidado à conta e o Free à assinatura — o degrau seguinte de cada um', () => {
    const visitante = quotaNotice(quota({ plan: 'anon', used: 2, limit: 3, remaining: 1 }), false, AGORA)
    const free = quotaNotice(quota({ used: 9, remaining: 1 }), false, AGORA)

    expect(visitante?.text).toMatch(/conta/)
    expect(free?.text).toMatch(/assinatura/)
  })

  it('quem ainda tem folga não é lembrado do limite', () => {
    expect(quotaNotice(quota({ used: 0, remaining: 10 }), false, AGORA)).toBeNull()
    expect(quotaNotice(quota({ used: 8, remaining: 2 }), false, AGORA)).toBeNull()
  })

  it('plano ilimitado não tem o que dizer, nem quando bloqueado por engano', () => {
    expect(quotaNotice(quota({ limit: 0, unlimited: true }), true, AGORA)).toBeNull()
  })

  it('sem resposta do servidor não inventa aviso nenhum', () => {
    expect(quotaNotice(null, true, AGORA)).toBeNull()
  })
})

describe('renewLabel', () => {
  it('perto da virada diz a hora local, não "meia-noite"', () => {
    // O servidor conta o dia em UTC; no Brasil isso é 21 h. Dizer "meia-noite" seria mentira.
    const texto = renewLabel('2026-08-01T00:00:00Z', new Date('2026-07-31T18:00:00Z'))

    expect(texto).toMatch(/^Renova às \d{2}:\d{2}$/)
  })

  it('longe demais vira "amanhã" — hora exata daqui a 20 h não ajuda ninguém', () => {
    const texto = renewLabel('2026-08-01T00:00:00Z', new Date('2026-07-31T02:00:00Z'))

    expect(texto).toMatch(/^Renova amanhã às /)
  })

  it('data podre ou virada já passada não viram texto', () => {
    expect(renewLabel('não é data', AGORA)).toBeNull()
    expect(renewLabel('2026-07-30T00:00:00Z', AGORA)).toBeNull()
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
