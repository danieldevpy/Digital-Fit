import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { deviceId } from '../auth/storage'
import { installStorage, uninstallStorage } from '../auth/testStorage'
import { useI18nStore } from '../i18n/store'
import { Mode } from '../lib/events'
import type { ProbeOutcome } from '../probe/runProbe'
import {
  AdmissionError,
  QUOTA_EXCEEDED,
  TRIAL_EXHAUSTED,
  isQuotaRefusal,
  modeToRequest,
  requestSession,
} from './admission'

const TICKET = {
  session_id: '6f0d2f2e-0c2e-4a3f-9f0a-2b7c2a1d3e4f',
  token: 'tok.123',
  ws_url: 'ws://localhost:8001/ws/session/6f0d2f2e-0c2e-4a3f-9f0a-2b7c2a1d3e4f?token=tok.123',
  mode: 'edge',
  exercise: 'jumping_jack',
  duration_s: 30,
  expires_at: 1_722_100_045,
}

function fetchFake(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status: init.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  ) as unknown as typeof fetch
}

const probe: ProbeOutcome = {
  modelFps: 21.4,
  inferenceMsP50: 46.7,
  cameraFps: 29.9,
  cameraFpsSource: 'apresentados',
  samples: 43,
  durationMs: 2000,
  failed: false,
  mode: Mode.EDGE,
  reason: 'probe_ok',
  webgl: true,
  wasmSimd: true,
  forced: false,
}

describe('requestSession', () => {
  beforeEach(() => useI18nStore.getState().setLocale('pt-BR'))
  afterEach(() => useI18nStore.getState().setLocale('pt-BR'))

  it('devolve o ticket do servidor', async () => {
    const ticket = await requestSession(
      { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe: null },
      fetchFake(TICKET),
    )

    expect(ticket.ws_url).toBe(TICKET.ws_url)
    expect(ticket.session_id).toBe(TICKET.session_id)
  })

  it('manda o probe no formato do contrato (`probe_fps`)', async () => {
    const fetchSpy = fetchFake(TICKET)

    await requestSession(
      { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe },
      fetchSpy,
    )

    const chamada = (fetchSpy as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const corpo = JSON.parse((chamada?.[1] as RequestInit).body as string)
    expect(corpo.exercise).toBe('jumping_jack')
    expect(corpo.requested_mode).toBe('edge')
    expect(corpo.probe_result.probe_fps).toBeCloseTo(21.4, 1)
    expect(corpo.probe_result.webgl).toBe(true)
  })

  it('cloud negado não vira sessão — é indisponibilidade, não erro de programação', async () => {
    const negado = { ...TICKET, mode: 'denied_cloud' }

    await expect(
      requestSession(
        { exercise: 'jumping_jack', requestedMode: Mode.CLOUD, probe: null },
        fetchFake(negado),
      ),
    ).rejects.toThrow(AdmissionError)
  })

  it('erro do servidor vira mensagem legível', async () => {
    await expect(
      requestSession(
        { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe: null },
        fetchFake({ error: 'exercicio desconhecido' }, { status: 400 }),
      ),
    ).rejects.toThrow('exercicio desconhecido')
  })

  it('API fora do ar não explode com stack de rede', async () => {
    const quebrado = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch

    await expect(
      requestSession(
        { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe: null },
        quebrado,
      ),
    ).rejects.toThrow(/API fora do ar/)
  })

  it('a recusa também sai em inglês — é texto de produto, não de log (T-149)', async () => {
    const quebrado = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch

    useI18nStore.getState().setLocale('en')
    await expect(
      requestSession(
        { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe: null },
        quebrado,
      ),
    ).rejects.toThrow(/API is down/)
  })

  it('ticket sem ws_url é recusado', async () => {
    await expect(
      requestSession(
        { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe: null },
        fetchFake({ ...TICKET, ws_url: '' }),
      ),
    ).rejects.toThrow(/ws_url/)
  })
})

describe('trial anônimo (SPEC-011)', () => {
  afterEach(uninstallStorage)

  const pedido = { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe: null }

  it('a identidade vai no pedido', async () => {
    installStorage()
    const fetchSpy = fetchFake({ ...TICKET, device_id: 'dev-abc12345' })

    await requestSession(pedido, fetchSpy)
    // Segunda sessão: agora o aparelho já é conhecido e acompanha o pedido.
    const outroSpy = fetchFake(TICKET)
    await requestSession(pedido, outroSpy)

    const chamada = (outroSpy as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const headers = (chamada?.[1] as RequestInit).headers as Record<string, string>
    expect(headers['X-Device-Id']).toBe('dev-abc12345')
  })

  it('o id que o servidor gerou na primeira visita fica guardado', async () => {
    installStorage()
    await requestSession(pedido, fetchFake({ ...TICKET, device_id: 'dev-abc12345' }))
    expect(deviceId()).toBe('dev-abc12345')
  })

  it('a recusa também traz o id — senão o contador nunca chegaria a 3', async () => {
    installStorage()
    const recusa = {
      detail: 'Suas 3 sessões grátis de hoje acabaram.',
      code: TRIAL_EXHAUSTED,
      device_id: 'dev-abc12345',
    }

    await expect(requestSession(pedido, fetchFake(recusa, { status: 429 }))).rejects.toThrow(
      /3 sessões grátis/,
    )
    expect(deviceId()).toBe('dev-abc12345')
  })

  it('trial esgotado vem com código próprio: a ação é criar conta, não tentar de novo', async () => {
    installStorage()
    const erro = await requestSession(
      pedido,
      fetchFake({ detail: 'acabou', code: TRIAL_EXHAUSTED }, { status: 429 }),
    ).catch((falha: unknown) => falha)

    expect(erro).toBeInstanceOf(AdmissionError)
    expect((erro as AdmissionError).code).toBe(TRIAL_EXHAUSTED)
    expect((erro as AdmissionError).status).toBe(429)
  })

  it('falha de infraestrutura não tem código — não é caso de mandar criar conta', async () => {
    installStorage()
    const erro = await requestSession(pedido, fetchFake({}, { status: 503 })).catch(
      (falha: unknown) => falha,
    )

    expect((erro as AdmissionError).code).toBeUndefined()
    expect((erro as AdmissionError).message).toMatch(/Redis/)
  })

  it('o ticket carrega quanto sobrou da quota de hoje', async () => {
    installStorage()
    const quota = {
      used: 2,
      limit: 3,
      remaining: 1,
      unlimited: false,
      allowed: true,
      resets_at: '2026-08-01T00:00:00Z',
      plan: 'anon',
      plan_name: 'Visitante',
      message: 'acabou',
    }
    const ticket = await requestSession(pedido, fetchFake({ ...TICKET, quota }))

    expect(ticket.quota).toEqual(quota)
  })

  it('a recusa por quota da conta tem código próprio, e traz o contador junto', async () => {
    installStorage()
    const quota = {
      used: 10,
      limit: 10,
      remaining: 0,
      unlimited: false,
      allowed: false,
      resets_at: '2026-08-01T00:00:00Z',
      plan: 'free',
      plan_name: 'Free',
      message: 'Você treinou muito hoje 🎉',
    }
    const erro = await requestSession(
      pedido,
      fetchFake({ detail: 'acabou', code: QUOTA_EXCEEDED, quota }, { status: 429 }),
    ).catch((falha: unknown) => falha)

    // Sem o contador na recusa, o sheet teria de fazer uma segunda chamada só para dizer
    // "10 de 10" — ou, pior, estimar.
    expect((erro as AdmissionError).quota).toEqual(quota)
    expect(isQuotaRefusal((erro as AdmissionError).code)).toBe(true)
  })

  it('as duas recusas por limite são reconhecidas, e uma falha de infra não', () => {
    expect(isQuotaRefusal(TRIAL_EXHAUSTED)).toBe(true)
    expect(isQuotaRefusal(QUOTA_EXCEEDED)).toBe(true)
    expect(isQuotaRefusal(undefined)).toBe(false)
    expect(isQuotaRefusal('denied_cloud')).toBe(false)
  })
})

describe('modeToRequest', () => {
  it('o override de ?mode= vence o probe', () => {
    expect(modeToRequest(Mode.CLOUD, probe)).toBe(Mode.CLOUD)
  })

  it('sem override vale o que o probe decidiu', () => {
    expect(modeToRequest(null, probe)).toBe(Mode.EDGE)
  })

  it('sem probe nenhum, edge', () => {
    expect(modeToRequest(null, null)).toBe(Mode.EDGE)
  })
})
