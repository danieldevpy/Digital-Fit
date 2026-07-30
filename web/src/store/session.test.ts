import { beforeEach, describe, expect, it } from 'vitest'

import { CLIENT_PUSH_TYPES, EventType } from '../lib/events'
import { streamsFrames, useSessionStore } from './session'

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

describe('preparação antes de a contagem valer (T-049)', () => {
  it('sem preparação, calibrar já põe a sessão em `running`', () => {
    const store = useSessionStore.getState()
    store.resetSession()
    store.applyCalibrated(1_000, 0)

    const depois = useSessionStore.getState()
    expect(depois.sessionStatus).toBe('running')
    expect(depois.startedAt).toBe(1_000)
    expect(depois.countingFrom).toBe(1_000)
  })

  it('com preparação, a sessão fica em `preparing` e a âncora vai para o futuro', () => {
    const store = useSessionStore.getState()
    store.resetSession()
    store.applyCalibrated(1_000, 3_000)

    const depois = useSessionStore.getState()
    expect(depois.sessionStatus).toBe('preparing')
    // O anel dos 30 s ancora no "JÁ", não na medição: a preparação não é cobrada do treino.
    expect(depois.startedAt).toBe(4_000)
    expect(depois.countingFrom).toBe(4_000)
  })

  it('`startCounting` fecha a preparação', () => {
    const store = useSessionStore.getState()
    store.resetSession()
    store.applyCalibrated(1_000, 3_000)
    useSessionStore.getState().startCounting()

    expect(useSessionStore.getState().sessionStatus).toBe('running')
  })

  it('`startCounting` fora da preparação não mexe em nada', () => {
    const store = useSessionStore.getState()
    store.resetSession()
    store.applySessionCompleted({ reason: 'completed', rep_count: 12 } as never)
    useSessionStore.getState().startCounting()

    // Sem o guarda, um timer atrasado reabriria uma sessão já encerrada.
    expect(useSessionStore.getState().sessionStatus).toBe('completed')
  })

  it('calibração repetida não reinicia a preparação', () => {
    const store = useSessionStore.getState()
    store.resetSession()
    store.applyCalibrated(1_000, 3_000)
    useSessionStore.getState().applyCalibrated(9_000, 3_000)

    expect(useSessionStore.getState().countingFrom).toBe(4_000)
  })
})

describe('quando a captura deve parar de transmitir (T-077)', () => {
  it('a sessão encerrada não transmite mais — e o `sessionId` continua lá', () => {
    const store = useSessionStore.getState()
    store.applyTicket(TICKET as never)
    store.applySessionCompleted({ reason: 'completed', rep_count: 26 } as never)

    const { sessionId, sessionStatus } = useSessionStore.getState()

    // O id sobrevive de propósito: a tela do relatório precisa dele. Por isso a condição de
    // enviar frame NÃO pode ser "tem sessionId" — era assim, e frames posteriores ao fim
    // faziam o servidor abrir uma sessão nova com o mesmo id, cujo relatório sobrescrevia o
    // bom (26 reps viraram 4 em produção).
    expect(sessionId).toBe(TICKET.sessionId)
    expect(streamsFrames(sessionStatus)).toBe(false)
  })

  it('transmite durante a medição, a preparação e o exercício', () => {
    expect(streamsFrames('calibrating')).toBe(true)
    expect(streamsFrames('preparing')).toBe(true)
    expect(streamsFrames('running')).toBe(true)
  })

  it('não transmite antes de haver sessão', () => {
    expect(streamsFrames('idle')).toBe(false)
  })
})
