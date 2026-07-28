import { describe, expect, it, vi } from 'vitest'

import { Mode } from '../lib/events'
import type { ProbeOutcome } from '../probe/runProbe'
import { AdmissionError, modeToRequest, requestSession } from './admission'

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
  probeFps: 21.4,
  frames: 43,
  durationMs: 2000,
  failed: false,
  mode: Mode.EDGE,
  webgl: true,
  wasmSimd: true,
  forced: false,
}

describe('requestSession', () => {
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

  it('ticket sem ws_url é recusado', async () => {
    await expect(
      requestSession(
        { exercise: 'jumping_jack', requestedMode: Mode.EDGE, probe: null },
        fetchFake({ ...TICKET, ws_url: '' }),
      ),
    ).rejects.toThrow(/ws_url/)
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
