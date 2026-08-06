import { describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import {
  MIN_PONTOS_TENDENCIA,
  cadenciaPorExercicio,
  consistenciaDoRitmo,
  contagens,
  diaLocal,
  diasComTreino,
  inicioDaSemana,
  porExercicio,
  porSemana,
} from './aggregates'

/**
 * Fixture de sessão. `quando` entra como data LOCAL (não ISO com Z) de propósito: as regras
 * daqui falam do dia de quem lê, e um `Z` faria o teste passar ou falhar conforme o fuso da
 * máquina que roda a suíte.
 */
function sessao(campos: {
  id?: string
  quando: Date
  exercise?: string
  reps?: number
  cadence?: number
  duracoes?: number[]
  feedback?: Record<string, number>
  cena?: Record<string, number>
}): SessionReport {
  return {
    session_id: campos.id ?? `s-${campos.quando.getTime()}`,
    exercise: campos.exercise ?? 'jumping_jack',
    created_at: campos.quando.toISOString(),
    rep_count: campos.reps ?? 10,
    cadence_rpm: campos.cadence ?? 30,
    rep_durations_ms: campos.duracoes ?? [],
    feedback_counts: campos.feedback ?? {},
    scene_warning_counts: campos.cena ?? {},
  } as SessionReport
}

// Uma quarta-feira, para os testes de semana não dependerem do dia em que rodam.
const QUARTA = new Date(2026, 7, 5, 10, 0)

describe('dia de quem lê', () => {
  it('devolve o dia local, não o UTC', () => {
    // 22h no fuso local: é hoje para quem está olhando, mesmo que em UTC já seja amanhã.
    const tarde = new Date(2026, 7, 5, 22, 0)
    expect(diaLocal(tarde.toISOString())).toBe('2026-08-05')
  })

  it('data inválida não vira dia nenhum', () => {
    expect(diaLocal('nada disso')).toBeNull()
  })

  it('duas sessões no mesmo dia marcam um dia só', () => {
    const dias = diasComTreino([
      sessao({ quando: new Date(2026, 7, 5, 8, 0) }),
      sessao({ quando: new Date(2026, 7, 5, 20, 0) }),
      sessao({ quando: new Date(2026, 7, 6, 8, 0) }),
    ])
    expect([...dias].sort()).toEqual(['2026-08-05', '2026-08-06'])
  })

  it('sessão com data quebrada não inventa dia', () => {
    const quebrada = { ...sessao({ quando: QUARTA }), created_at: 'lixo' } as SessionReport
    expect(diasComTreino([quebrada]).size).toBe(0)
  })
})

describe('semanas', () => {
  it('a semana abre na segunda', () => {
    expect(inicioDaSemana(QUARTA)).toEqual(new Date(2026, 7, 3))
  })

  it('domingo pertence à semana que começou na segunda anterior', () => {
    const domingo = new Date(2026, 7, 9, 23, 0)
    expect(inicioDaSemana(domingo)).toEqual(new Date(2026, 7, 3))
  })

  it('devolve as N semanas em ordem, da mais antiga para a mais recente', () => {
    const semanas = porSemana([], 4, QUARTA)
    expect(semanas).toHaveLength(4)
    expect(semanas[0]?.inicio).toEqual(new Date(2026, 6, 13))
    expect(semanas[3]?.inicio).toEqual(new Date(2026, 7, 3))
  })

  it('soma sessões e repetições na semana certa', () => {
    const semanas = porSemana(
      [
        sessao({ quando: new Date(2026, 7, 4), reps: 12 }),
        sessao({ quando: new Date(2026, 7, 6), reps: 8 }),
        sessao({ quando: new Date(2026, 6, 28), reps: 20 }),
      ],
      4,
      QUARTA,
    )
    expect(semanas[3]).toMatchObject({ sessoes: 2, reps: 20 })
    expect(semanas[2]).toMatchObject({ sessoes: 1, reps: 20 })
  })

  it('semana sem treino entra com zero — o buraco é a informação', () => {
    const semanas = porSemana([sessao({ quando: QUARTA })], 4, QUARTA)
    expect(semanas[0]).toMatchObject({ sessoes: 0, reps: 0 })
  })

  it('sessão fora da janela não entra em semana nenhuma', () => {
    const semanas = porSemana([sessao({ quando: new Date(2025, 0, 1) })], 4, QUARTA)
    expect(semanas.reduce((total, s) => total + s.sessoes, 0)).toBe(0)
  })
})

describe('por exercício', () => {
  it('soma sessões e reps, do mais treinado para o menos', () => {
    const totais = porExercicio([
      sessao({ quando: QUARTA, exercise: 'squat', reps: 5 }),
      sessao({ quando: QUARTA, exercise: 'jumping_jack', reps: 20 }),
      sessao({ quando: QUARTA, exercise: 'jumping_jack', reps: 15 }),
    ])
    expect(totais).toEqual([
      { exercise: 'jumping_jack', sessoes: 2, reps: 35 },
      { exercise: 'squat', sessoes: 1, reps: 5 },
    ])
  })

  it('lista vazia dá lista vazia', () => {
    expect(porExercicio([])).toEqual([])
  })
})

describe('cadência por exercício', () => {
  it('não mistura exercícios — rep/min de movimentos diferentes não se compara', () => {
    const series = cadenciaPorExercicio([
      sessao({ quando: new Date(2026, 7, 1), exercise: 'squat', cadence: 20 }),
      sessao({ quando: new Date(2026, 7, 2), exercise: 'jumping_jack', cadence: 40 }),
      sessao({ quando: new Date(2026, 7, 3), exercise: 'jumping_jack', cadence: 44 }),
    ])
    expect(series.map((s) => s.exercise)).toEqual(['jumping_jack', 'squat'])
  })

  it('ordena os pontos do mais antigo para o mais recente', () => {
    const series = cadenciaPorExercicio([
      sessao({ quando: new Date(2026, 7, 3), cadence: 44 }),
      sessao({ quando: new Date(2026, 7, 1), cadence: 30 }),
    ])
    expect(series[0]?.pontos.map((p) => p.cadence_rpm)).toEqual([30, 44])
  })

  // Critério 7 da SPEC-024: com uma sessão só não se desenha linha nenhuma.
  it('uma sessão do exercício não vira tendência', () => {
    const series = cadenciaPorExercicio([sessao({ quando: QUARTA })])
    expect(series[0]?.tendencia).toBe(false)
  })

  it(`a partir de ${MIN_PONTOS_TENDENCIA} sessões, vira`, () => {
    const series = cadenciaPorExercicio([
      sessao({ quando: new Date(2026, 7, 1) }),
      sessao({ quando: new Date(2026, 7, 2) }),
    ])
    expect(series[0]?.tendencia).toBe(true)
  })
})

describe('consistência do ritmo', () => {
  it('ritmo perfeitamente regular dá zero', () => {
    expect(consistenciaDoRitmo(sessao({ quando: QUARTA, duracoes: [1000, 1000, 1000] }))).toBe(0)
  })

  it('ritmo irregular dá mais que ritmo regular', () => {
    const regular = consistenciaDoRitmo(sessao({ quando: QUARTA, duracoes: [1000, 1050, 950] }))
    const irregular = consistenciaDoRitmo(sessao({ quando: QUARTA, duracoes: [500, 2000, 900] }))
    expect(irregular).toBeGreaterThan(regular ?? 0)
  })

  it('é relativo à própria média — exercício lento e rápido igualmente regulares empatam', () => {
    const rapido = consistenciaDoRitmo(sessao({ quando: QUARTA, duracoes: [1000, 1200] }))
    const lento = consistenciaDoRitmo(sessao({ quando: QUARTA, duracoes: [2000, 2400] }))
    expect(rapido).toBeCloseTo(lento ?? 0, 10)
  })

  it('uma repetição só não tem dispersão — e `0` afirmaria regularidade que ninguém mediu', () => {
    expect(consistenciaDoRitmo(sessao({ quando: QUARTA, duracoes: [1000] }))).toBeNull()
  })

  it('sessão sem durações não explode', () => {
    expect(consistenciaDoRitmo(sessao({ quando: QUARTA }))).toBeNull()
  })
})

describe('correções e avisos', () => {
  it('soma os contadores, do mais frequente para o menos', () => {
    const lista = contagens(
      [
        sessao({ quando: new Date(2026, 7, 1), feedback: { desce_mais: 3, braco_torto: 1 } }),
        sessao({ quando: new Date(2026, 7, 2), feedback: { desce_mais: 2 } }),
      ],
      'feedback_counts',
    )
    expect(lista.map((c) => [c.key, c.total])).toEqual([
      ['desce_mais', 5],
      ['braco_torto', 1],
    ])
  })

  it('correção que diminui é reportada como caindo', () => {
    const lista = contagens(
      [
        sessao({ quando: new Date(2026, 7, 1), feedback: { desce_mais: 10 } }),
        sessao({ quando: new Date(2026, 7, 2), feedback: { desce_mais: 2 } }),
      ],
      'feedback_counts',
    )
    expect(lista[0]?.rumo).toBe('caindo')
  })

  it('compara por sessão, não por total — treinar mais não é piorar', () => {
    const lista = contagens(
      [
        // Uma sessão antiga com 4; duas recentes com 3 cada. Total recente é maior (6 > 4),
        // mas a média por sessão caiu de 4 para 3.
        sessao({ quando: new Date(2026, 7, 1), feedback: { desce_mais: 4 } }),
        sessao({ quando: new Date(2026, 7, 2), feedback: { desce_mais: 3 } }),
        sessao({ quando: new Date(2026, 7, 3), feedback: { desce_mais: 3 } }),
      ],
      'feedback_counts',
    )
    expect(lista[0]?.total).toBe(10)
    expect(lista[0]?.rumo).toBe('caindo')
  })

  it('variação pequena é estável — ruído de amostra não é notícia sobre o corpo de alguém', () => {
    const lista = contagens(
      [
        sessao({ quando: new Date(2026, 7, 1), feedback: { desce_mais: 10 } }),
        sessao({ quando: new Date(2026, 7, 2), feedback: { desce_mais: 10 } }),
      ],
      'feedback_counts',
    )
    expect(lista[0]?.rumo).toBe('estavel')
  })

  // Critério 7 de novo, do outro lado: sem duas sessões não há duas metades para comparar.
  it('uma sessão só não afirma rumo nenhum', () => {
    const lista = contagens(
      [sessao({ quando: QUARTA, feedback: { desce_mais: 3 } })],
      'feedback_counts',
    )
    expect(lista[0]?.rumo).toBeNull()
  })

  it('vale igual para os avisos de cena', () => {
    const lista = contagens(
      [
        sessao({ quando: new Date(2026, 7, 1), cena: { fora_de_quadro: 2 } }),
        sessao({ quando: new Date(2026, 7, 2), cena: { fora_de_quadro: 1 } }),
      ],
      'scene_warning_counts',
    )
    expect(lista[0]).toMatchObject({ key: 'fora_de_quadro', total: 3, rumo: 'caindo' })
  })

  it('relatório antigo sem os campos não derruba a agregação', () => {
    const sem = { session_id: 's1', created_at: QUARTA.toISOString() } as SessionReport
    expect(contagens([sem], 'feedback_counts')).toEqual([])
  })
})
