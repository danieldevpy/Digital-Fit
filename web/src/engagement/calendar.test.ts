import { describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import { gradeDoMes, INICIAIS_DA_SEMANA } from './calendar'

function sessao(dia: string, reps = 10): SessionReport {
  return {
    session_id: `s-${dia}-${reps}`,
    exercise: 'squat',
    mode: 'edge',
    reason: 'completed',
    rep_count: reps,
    duration_ms: 30000,
    cadence_rpm: 20,
    cadence_windows: [],
    rep_durations_ms: [],
    feedback_counts: {},
    scene_warning_counts: {},
    calibration_samples: 30,
    config_version: 1,
    created_at: `${dia}T15:00:00Z`,
  }
}

describe('gradeDoMes', () => {
  it('agosto de 2026 tem 31 dias e começa num sábado', () => {
    const grade = gradeDoMes([], '2026-08-15')

    expect(grade.dias).toHaveLength(31)
    // Semana abrindo na segunda: sábado é a 6ª coluna, então 5 células vazias antes.
    expect(grade.offset).toBe(5)
    expect(INICIAIS_DA_SEMANA).toHaveLength(7)
  })

  it('marca os dias em que houve sessão válida', () => {
    const grade = gradeDoMes([sessao('2026-08-03'), sessao('2026-08-10')], '2026-08-15')

    expect(grade.ativos).toBe(2)
    expect(grade.dias.find((d) => d.numero === 3)?.ativo).toBe(true)
    expect(grade.dias.find((d) => d.numero === 4)?.ativo).toBe(false)
  })

  it('sessão zerada não acende o dia — a grade tem de casar com o fogo', () => {
    // É a razão de este módulo usar `diasAtivos` e não `diasComTreino`: um dia aceso aqui que
    // não conta para a sequência seria uma contradição na mesma tela, sem nada explicando.
    const grade = gradeDoMes([sessao('2026-08-03', 0)], '2026-08-15')

    expect(grade.ativos).toBe(0)
  })

  it('sessão de outro mês não entra na grade deste', () => {
    const grade = gradeDoMes([sessao('2026-07-20')], '2026-08-15')

    expect(grade.ativos).toBe(0)
  })

  it('dia futuro é marcado como futuro, não como falha', () => {
    const grade = gradeDoMes([], '2026-08-15')

    expect(grade.dias.find((d) => d.numero === 20)?.futuro).toBe(true)
    expect(grade.dias.find((d) => d.numero === 10)?.futuro).toBe(false)
    expect(grade.dias.find((d) => d.numero === 15)?.hoje).toBe(true)
  })

  it('fevereiro bissexto tem 29', () => {
    expect(gradeDoMes([], '2028-02-10').dias).toHaveLength(29)
  })

  it('data sem sentido devolve grade vazia em vez de quebrar a tela', () => {
    expect(gradeDoMes([], '').dias).toHaveLength(0)
  })
})
