import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useI18nStore } from '../i18n/store'
import { fetchReport, formatDuration, waitForReport, type SessionReport } from './sessionReport'

const RELATORIO: SessionReport = {
  session_id: 's-1',
  exercise: 'jumping_jack',
  mode: 'edge',
  reason: 'completed',
  rep_count: 20,
  duration_ms: 30_000,
  cadence_rpm: 40,
  cadence_windows: [3, 4, 3, 4, 3, 3],
  rep_durations_ms: [1400],
  feedback_counts: { ARMS_TOO_LOW: 2 },
  scene_warning_counts: {},
  calibration_samples: 12,
  config_version: 0,
  set_mode: 'livre',
  target_reps: 0,
  set_index: 0,
  set_total: 0,
  created_at: '2026-07-28T12:00:00Z',
}

function resposta(status: number, corpo: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  } as Response
}

describe('fetchReport', () => {
  // A mensagem de falha sai do dicionário desde a T-150: o teste fixa o idioma em vez de
  // herdar o que o `detectLocale()` resolver no ambiente do vitest (que é `en`).
  beforeEach(() => useI18nStore.getState().setLocale('pt-BR'))
  afterEach(() => useI18nStore.getState().setLocale('pt-BR'))

  it('devolve o relatório quando ele existe', async () => {
    const fake = vi.fn(async () => resposta(200, RELATORIO))

    expect(await fetchReport('s-1', fake as unknown as typeof fetch)).toEqual(RELATORIO)
  })

  it('devolve null em 404 — "ainda não" não é erro', async () => {
    const fake = vi.fn(async () => resposta(404, { pending: true }))

    expect(await fetchReport('s-1', fake as unknown as typeof fetch)).toBeNull()
  })

  it('erra em 500', async () => {
    const fake = vi.fn(async () => resposta(500, {}))

    await expect(fetchReport('s-1', fake as unknown as typeof fetch)).rejects.toThrow(/HTTP 500/)
  })

  it('erra quando a rede cai', async () => {
    const fake = vi.fn(async () => {
      throw new Error('Failed to fetch')
    })

    await expect(fetchReport('s-1', fake as unknown as typeof fetch)).rejects.toThrow(
      /API fora do ar/,
    )
  })

  it('a falha de rede também sai em inglês (T-150)', async () => {
    const fake = vi.fn(async () => {
      throw new Error('Failed to fetch')
    })

    useI18nStore.getState().setLocale('en')
    await expect(fetchReport('s-1', fake as unknown as typeof fetch)).rejects.toThrow(
      /API is down/,
    )
  })
})

describe('waitForReport', () => {
  it('insiste enquanto o relatório não existe', async () => {
    // Duas negativas e então o relatório: o report-builder consolidando.
    const respostas = [resposta(404, {}), resposta(404, {}), resposta(200, RELATORIO)]
    const fake = vi.fn(async () => respostas.shift()!)
    const dormidas: number[] = []

    const relatorio = await waitForReport('s-1', {
      fetchImpl: fake as unknown as typeof fetch,
      sleep: async (ms) => {
        dormidas.push(ms)
      },
    })

    expect(relatorio).toEqual(RELATORIO)
    expect(fake).toHaveBeenCalledTimes(3)
    expect(dormidas).toHaveLength(2)
  })

  it('desiste depois do limite de tentativas em vez de esperar para sempre', async () => {
    const fake = vi.fn(async () => resposta(404, {}))

    const relatorio = await waitForReport('s-1', {
      attempts: 3,
      fetchImpl: fake as unknown as typeof fetch,
      sleep: async () => {},
    })

    expect(relatorio).toBeNull()
    expect(fake).toHaveBeenCalledTimes(3)
  })

  it('não dorme depois da última tentativa', async () => {
    const fake = vi.fn(async () => resposta(404, {}))
    const dormidas: number[] = []

    await waitForReport('s-1', {
      attempts: 2,
      fetchImpl: fake as unknown as typeof fetch,
      sleep: async (ms) => {
        dormidas.push(ms)
      },
    })

    expect(dormidas).toHaveLength(1)
  })
})

describe('formatDuration', () => {
  it.each([
    [0, '0:00'],
    [30_000, '0:30'],
    [65_400, '1:05'],
  ])('%i ms vira %s', (ms, esperado) => {
    expect(formatDuration(ms)).toBe(esperado)
  })
})
