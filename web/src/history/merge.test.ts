import { describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import { HISTORY_CAP } from './localHistory'
import { mergeSessions } from './merge'

function sessao(id: string, created_at: string, campos: Partial<SessionReport> = {}) {
  return { session_id: id, created_at, rep_count: 10, ...campos } as SessionReport
}

describe('mergeSessions', () => {
  // Critério 6 da SPEC-024: a sessão que existe nas duas origens é UMA sessão.
  it('conta uma vez a sessão que está no aparelho e no servidor', () => {
    const local = [sessao('s1', '2026-08-05T10:00:00Z')]
    const servidor = [sessao('s1', '2026-08-05T10:00:00Z')]
    expect(mergeSessions(local, servidor)).toHaveLength(1)
  })

  it('no conflito quem vence é o servidor — ele é a autoridade da SPEC-010', () => {
    const local = [sessao('s1', '2026-08-05T10:00:00Z', { rep_count: 8 })]
    const servidor = [sessao('s1', '2026-08-05T10:00:00Z', { rep_count: 12 })]
    expect(mergeSessions(local, servidor)[0]?.rep_count).toBe(12)
  })

  it('a sessão que só o aparelho tem não some no merge', () => {
    const local = [sessao('local-1', '2026-08-05T10:00:00Z')]
    const servidor = [sessao('serv-1', '2026-08-04T10:00:00Z')]
    const ids = mergeSessions(local, servidor).map((s) => s.session_id)
    expect(ids).toEqual(['local-1', 'serv-1'])
  })

  it('ordena da mais recente para a mais antiga, venha de onde vier', () => {
    const local = [sessao('velha', '2026-08-01T10:00:00Z')]
    const servidor = [
      sessao('nova', '2026-08-06T10:00:00Z'),
      sessao('meio', '2026-08-03T10:00:00Z'),
    ]
    expect(mergeSessions(local, servidor).map((s) => s.session_id)).toEqual([
      'nova',
      'meio',
      'velha',
    ])
  })

  it('`created_at` inválido vai para o fim em vez de embaralhar a ordem com NaN', () => {
    const servidor = [
      sessao('quebrada', 'não é data'),
      sessao('boa', '2026-08-06T10:00:00Z'),
    ]
    expect(mergeSessions([], servidor).map((s) => s.session_id)).toEqual(['boa', 'quebrada'])
  })

  it('corta no teto guardando as mais recentes', () => {
    const muitas = Array.from({ length: HISTORY_CAP + 10 }, (_, i) =>
      sessao(`s${i}`, new Date(2026, 0, 1 + i).toISOString()),
    )
    const resultado = mergeSessions([], muitas)
    expect(resultado).toHaveLength(HISTORY_CAP)
    // A mais nova é a última gerada — ela não pode ser a que o corte come.
    expect(resultado[0]?.session_id).toBe(`s${HISTORY_CAP + 9}`)
  })

  it('duas listas vazias dão lista vazia, não erro', () => {
    expect(mergeSessions([], [])).toEqual([])
  })
})
