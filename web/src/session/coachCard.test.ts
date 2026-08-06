import { afterEach, describe, expect, it } from 'vitest'
import { Code, Severity } from '../lib/events'
import { useConfigStore } from '../store/config'
import {
  COACH_ENTRY_TTL_MS,
  entryFromEvent,
  resolveCoachCard,
  textForCode,
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
    // `TOO_FAR` é "a pessoa está longe": o texto manda aproximar. Era "afaste-se menos" no mapa
    // do cliente, contra "aproxime-se da câmera" no catálogo que o HUD já usava ao vivo.
    expect(card.text).toContain('Aproxime-se')
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
      'Apareça inteiro no quadro',
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

describe('textForCode', () => {
  afterEach(() => useConfigStore.getState().reset())

  // O gate da T-126: espelho do contrato e mapa de texto crescem juntos. Código novo em
  // `events.ts` sem frase aqui quebra este teste — e não a tela de quem acabou de treinar.
  it('todo código do contrato tem texto embutido', () => {
    for (const code of Object.values(Code)) {
      expect(textForCode(code), `código sem texto embutido: ${code}`).not.toBe(code)
    }
  })

  it('o catálogo do servidor vence o embutido (SPEC-018 §C: texto sem deploy)', () => {
    useConfigStore.setState({
      feedback: { [Code.SQUAT_TOO_SHALLOW]: { message: 'Desça até a coxa ficar paralela' } },
    })

    expect(textForCode(Code.SQUAT_TOO_SHALLOW)).toBe('Desça até a coxa ficar paralela')
    // O que o servidor não mandou continua vindo do embutido, e não some.
    expect(textForCode(Code.HIPS_PIKED)).toBe('Abaixe o quadril')
  })

  it('código desconhecido devolve ele mesmo — feio de propósito, para ser visto', () => {
    expect(textForCode('CODIGO_QUE_NAO_EXISTE')).toBe('CODIGO_QUE_NAO_EXISTE')
  })
})
