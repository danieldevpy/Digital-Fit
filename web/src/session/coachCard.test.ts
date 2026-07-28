import { describe, expect, it } from 'vitest'
import { Code, Severity } from '../lib/events'
import {
  COACH_ENTRY_TTL_MS,
  entryFromEvent,
  resolveCoachCard,
  type CoachEntry,
} from './coachCard'

const NOW = 1_700_000_000_000
const DEFAULT_TIP = 'Mantenha o core contraído e movimentos controlados.'

function feedback(overrides: Partial<CoachEntry> = {}): CoachEntry {
  return {
    code: Code.ARMS_TOO_LOW,
    severity: Severity.WARNING,
    message: 'Suba mais os braços até se tocarem.',
    receivedAt: NOW,
    ...overrides,
  }
}

function scene(overrides: Partial<CoachEntry> = {}): CoachEntry {
  return { code: Code.TOO_FAR, severity: Severity.WARNING, receivedAt: NOW, ...overrides }
}

const base = { scene: null, feedback: null, defaultTip: DEFAULT_TIP, now: NOW }

describe('estado vazio', () => {
  it('mostra a dica padrão do exercício quando não há nada ativo', () => {
    const card = resolveCoachCard(base)
    expect(card.text).toBe(DEFAULT_TIP)
    expect(card.tone).toBe('default')
    expect(card.hint).toBeNull()
  })

  it('o card nunca fica sem texto', () => {
    expect(resolveCoachCard({ ...base, defaultTip: DEFAULT_TIP }).text.length).toBeGreaterThan(0)
  })
})

describe('prioridade (critério 3 da SPEC-013)', () => {
  it('warning de cena vence feedback de execução', () => {
    const card = resolveCoachCard({ ...base, scene: scene(), feedback: feedback() })
    expect(card.tone).toBe('scene')
    expect(card.text).toContain('longe demais')
  })

  it('feedback vence a dica padrão', () => {
    const card = resolveCoachCard({ ...base, feedback: feedback() })
    expect(card.tone).toBe('feedback')
    expect(card.text).toBe('Suba mais os braços até se tocarem.')
  })

  it('cena expirada devolve a vez ao feedback ainda válido', () => {
    const card = resolveCoachCard({
      ...base,
      scene: scene({ receivedAt: NOW - COACH_ENTRY_TTL_MS - 1 }),
      feedback: feedback(),
    })
    expect(card.tone).toBe('feedback')
  })
})

describe('expiração', () => {
  it('mantém o aviso dentro do TTL', () => {
    const card = resolveCoachCard({
      ...base,
      feedback: feedback({ receivedAt: NOW - COACH_ENTRY_TTL_MS + 100 }),
    })
    expect(card.tone).toBe('feedback')
  })

  it('volta para a dica padrão quando tudo expira', () => {
    const stale = NOW - COACH_ENTRY_TTL_MS - 1
    const card = resolveCoachCard({
      ...base,
      scene: scene({ receivedAt: stale }),
      feedback: feedback({ receivedAt: stale }),
    })
    expect(card.tone).toBe('default')
    expect(card.text).toBe(DEFAULT_TIP)
  })

  it('respeita TTL customizado', () => {
    const card = resolveCoachCard({
      ...base,
      feedback: feedback({ receivedAt: NOW - 500 }),
      ttlMs: 400,
    })
    expect(card.tone).toBe('default')
  })
})

describe('texto dos códigos', () => {
  it('usa message quando o evento traz (feedback.issued)', () => {
    expect(resolveCoachCard({ ...base, feedback: feedback() }).text).toBe(
      'Suba mais os braços até se tocarem.',
    )
  })

  it('traduz o código quando não há message (scene.warning)', () => {
    expect(resolveCoachCard({ ...base, scene: scene({ code: Code.OUT_OF_FRAME }) }).text).toBe(
      'Você saiu do quadro.',
    )
  })

  it('expõe o hint quando existe', () => {
    const card = resolveCoachCard({ ...base, scene: scene({ hint: 'Aproxime-se da câmera.' }) })
    expect(card.hint).toBe('Aproxime-se da câmera.')
  })
})

describe('entryFromEvent', () => {
  it('converte payload do contrato em entrada do card', () => {
    const entry = entryFromEvent(
      { code: Code.LEGS_TOO_CLOSED, severity: Severity.INFO, message: 'Abra mais.' },
      NOW,
    )
    expect(entry).toEqual({
      code: Code.LEGS_TOO_CLOSED,
      severity: Severity.INFO,
      message: 'Abra mais.',
      hint: undefined,
      receivedAt: NOW,
    })
  })

  it('assume severidade warning quando o evento não manda', () => {
    expect(entryFromEvent({ code: Code.TOO_CLOSE }, NOW).severity).toBe(Severity.WARNING)
  })
})
