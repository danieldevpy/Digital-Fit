import { afterEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import type { SessionReport } from '../report/sessionReport'
import { saveLastReport } from '../report/lastReport'
import {
  HISTORY_CAP,
  clearLocalHistory,
  loadLocalHistory,
  recordLocalSession,
} from './localHistory'

afterEach(uninstallStorage)

function sessao(id: string, created_at = '2026-08-05T10:00:00Z', reps = 10) {
  return { session_id: id, created_at, rep_count: reps } as SessionReport
}

describe('histórico no aparelho', () => {
  it('guarda a sessão que acabou e a devolve na próxima leitura', () => {
    installStorage()
    recordLocalSession(sessao('s1'))
    expect(loadLocalHistory().map((s) => s.session_id)).toEqual(['s1'])
  })

  it('a mais recente fica na frente', () => {
    installStorage()
    recordLocalSession(sessao('s1', '2026-08-01T10:00:00Z'))
    recordLocalSession(sessao('s2', '2026-08-05T10:00:00Z'))
    expect(loadLocalHistory().map((s) => s.session_id)).toEqual(['s2', 's1'])
  })

  it('o mesmo `session_id` não vira dois treinos — o relatório chega duas vezes', () => {
    installStorage()
    recordLocalSession(sessao('s1', '2026-08-05T10:00:00Z', 8))
    // Segunda chegada (repique do `waitForReport`), já consolidada: substitui, não soma.
    recordLocalSession(sessao('s1', '2026-08-05T10:00:00Z', 12))
    const lista = loadLocalHistory()
    expect(lista).toHaveLength(1)
    expect(lista[0]?.rep_count).toBe(12)
  })

  it('não passa do teto, e quem cai é a mais antiga', () => {
    installStorage()
    for (let i = 0; i < HISTORY_CAP + 5; i += 1) {
      recordLocalSession(sessao(`s${i}`, new Date(2026, 0, 1 + i).toISOString()))
    }
    const lista = loadLocalHistory()
    expect(lista).toHaveLength(HISTORY_CAP)
    expect(lista.some((s) => s.session_id === 's0')).toBe(false)
  })

  it('sem `window` (o ambiente dos testes) devolve lista vazia em vez de explodir', () => {
    expect(loadLocalHistory()).toEqual([])
  })

  it('storage somente-leitura (Safari privado) não derruba o fim do treino', () => {
    installStorage({ readOnly: true })
    expect(() => recordLocalSession(sessao('s1'))).not.toThrow()
  })

  it('lista corrompida não derruba o app no boot', () => {
    const fake = installStorage()
    fake.store.set('digitalfit.history', '{isso não é json')
    expect(loadLocalHistory()).toEqual([])
  })

  it('descarta item sem os campos que uma sessão precisa ter', () => {
    const fake = installStorage()
    fake.store.set(
      'digitalfit.history',
      JSON.stringify([{ lixo: true }, sessao('s1')]),
    )
    expect(loadLocalHistory().map((s) => s.session_id)).toEqual(['s1'])
  })

  it('quem só tinha o `last_report` entra no histórico com uma sessão', () => {
    installStorage()
    saveLastReport(sessao('antiga'), false)
    expect(loadLocalHistory().map((s) => s.session_id)).toEqual(['antiga'])
  })

  it('a migração não sobrescreve um histórico que já existe', () => {
    installStorage()
    recordLocalSession(sessao('nova', '2026-08-05T10:00:00Z'))
    saveLastReport(sessao('antiga', '2026-01-01T10:00:00Z'), false)
    expect(loadLocalHistory().map((s) => s.session_id)).toEqual(['nova'])
  })

  it('apagar deixa o aparelho sem histórico', () => {
    installStorage()
    recordLocalSession(sessao('s1'))
    clearLocalHistory()
    expect(loadLocalHistory()).toEqual([])
  })
})
