import { beforeEach, describe, expect, it } from 'vitest'

import { CLIENT_PUSH_TYPES, EventType } from '../lib/events'
import { useSessionStore } from './session'

const TICKET = { sessionId: 'abc-123', exercise: 'jumping_jack', durationS: 30 }

beforeEach(() => {
  useSessionStore.getState().resetSession()
})

describe('sessão admitida pelo ticket', () => {
  it('o contrato NÃO empurra `session.started` ao cliente', () => {
    // Esta é a raiz do bug que quebrou a primeira sessão real: o mock mandava
    // `session.started`, o gateway não manda, e o cliente tirava o `session_id` de lá.
    // Se algum dia o contrato passar a empurrar, este teste avisa.
    expect(CLIENT_PUSH_TYPES).not.toContain(EventType.SESSION_STARTED)
  })

  it('o ticket deixa a sessão pronta para enviar frames, mas em preparação', () => {
    useSessionStore.getState().applyTicket(TICKET)

    const estado = useSessionStore.getState()
    expect(estado.sessionId).toBe('abc-123')
    expect(estado.exerciseKey).toBe('jumping_jack')
    expect(estado.durationS).toBe(30)
    // Admitida ≠ começada: o exercício só vale quando o servidor calibra (SPEC-004).
    expect(estado.sessionStatus).toBe('calibrating')
  })

  it('nem admitir nem o primeiro frame começam a sessão — só a calibração', () => {
    // O anel do HUD tem de ancorar no MESMO instante que o timer autoritativo do servidor.
    // Ancorar no primeiro frame descontaria a preparação dos 30 s do usuário.
    useSessionStore.getState().applyTicket(TICKET)
    expect(useSessionStore.getState().startedAt).toBeNull()

    useSessionStore.getState().markFirstFrame(1_000)
    expect(useSessionStore.getState().startedAt).toBeNull()
    expect(useSessionStore.getState().firstFrameAt).toBe(1_000)

    useSessionStore.getState().applyCalibrated(3_000)

    expect(useSessionStore.getState().startedAt).toBe(3_000)
    expect(useSessionStore.getState().sessionStatus).toBe('running')
  })

  it('a calibração ancora uma vez só — senão o anel reiniciaria', () => {
    const { applyTicket, markFirstFrame, applyCalibrated } = useSessionStore.getState()
    applyTicket(TICKET)

    markFirstFrame(1_000)
    markFirstFrame(1_066)
    applyCalibrated(3_000)
    applyCalibrated(9_000)

    expect(useSessionStore.getState().firstFrameAt).toBe(1_000)
    expect(useSessionStore.getState().startedAt).toBe(3_000)
  })

  it('nova sessão volta a não ter âncora', () => {
    useSessionStore.getState().applyTicket(TICKET)
    useSessionStore.getState().markFirstFrame(1_000)
    useSessionStore.getState().applyCalibrated(3_000)

    useSessionStore.getState().resetSession()

    expect(useSessionStore.getState().startedAt).toBeNull()
    expect(useSessionStore.getState().firstFrameAt).toBeNull()
    expect(useSessionStore.getState().sessionId).toBeNull()
  })
})
