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

  it('o ticket deixa a sessão pronta para enviar frames', () => {
    useSessionStore.getState().applyTicket(TICKET)

    const estado = useSessionStore.getState()
    expect(estado.sessionId).toBe('abc-123')
    expect(estado.exerciseKey).toBe('jumping_jack')
    expect(estado.durationS).toBe(30)
    expect(estado.sessionStatus).toBe('running')
  })

  it('admitir não é começar: o countdown só ancora no primeiro frame', () => {
    useSessionStore.getState().applyTicket(TICKET)
    expect(useSessionStore.getState().startedAt).toBeNull()

    useSessionStore.getState().markFirstFrame(1_000)

    expect(useSessionStore.getState().startedAt).toBe(1_000)
  })

  it('o primeiro frame ancora uma vez só — senão o anel reiniciaria a cada frame', () => {
    const { applyTicket, markFirstFrame } = useSessionStore.getState()
    applyTicket(TICKET)

    markFirstFrame(1_000)
    markFirstFrame(1_066)
    markFirstFrame(5_000)

    expect(useSessionStore.getState().startedAt).toBe(1_000)
  })

  it('nova sessão volta a não ter âncora', () => {
    useSessionStore.getState().applyTicket(TICKET)
    useSessionStore.getState().markFirstFrame(1_000)

    useSessionStore.getState().resetSession()

    expect(useSessionStore.getState().startedAt).toBeNull()
    expect(useSessionStore.getState().sessionId).toBeNull()
  })
})
