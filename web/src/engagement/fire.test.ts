import { describe, expect, it } from 'vitest'

import type { SessionReport } from '../report/sessionReport'
import { diaDoFogo, diasAtivos, fogoLocal, sessaoValida } from './fire'

function sessao(iso: string, reps = 10): SessionReport {
  return {
    session_id: `s-${iso}-${reps}`,
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
    set_mode: 'livre',
    target_reps: 0,
    set_index: 0,
    set_total: 0,
    created_at: iso,
  }
}

/** Meio-dia em SP num dia, escrito em UTC (SP é UTC-3). */
function meioDia(dia: string): string {
  return `${dia}T15:00:00Z`
}

describe('diaDoFogo', () => {
  it('a virada é a meia-noite de quem treina, não a de um país (T-156)', () => {
    // 15/08 01h30 UTC é 14/08 22h30 em São Paulo e já 15/08 02h30 em Lisboa. O §Fuso da
    // SPEC-019 nomeia o caso: "treinei às 22h e o app disse que foi amanhã" mata a mecânica no
    // primeiro contato — e era o que acontecia com QUEM NÃO ESTÁ NO BRASIL até a T-156, porque
    // o fuso era São Paulo fixo para todo mundo.
    expect(diaDoFogo('2026-08-15T01:30:00Z', 'America/Sao_Paulo')).toBe('2026-08-14')
    expect(diaDoFogo('2026-08-15T01:30:00Z', 'Europe/Lisbon')).toBe('2026-08-15')
    expect(diaDoFogo('2026-08-15T01:30:00Z', 'Asia/Tokyo')).toBe('2026-08-15')
  })

  it('a virada de São Paulo continua às 03h UTC — o que mudou é ela não valer para todos', () => {
    expect(diaDoFogo('2026-08-15T02:59:00Z', 'America/Sao_Paulo')).toBe('2026-08-14')
    expect(diaDoFogo('2026-08-15T03:01:00Z', 'America/Sao_Paulo')).toBe('2026-08-15')
  })

  it('sem fuso explícito usa o do APARELHO — é o mesmo que o servidor vai receber', () => {
    // O `X-Timezone` que o cliente manda (`lib/tz.ts`) sai desta mesma fonte, e é isso que faz
    // o fogo fantasma do visitante bater com o da conta no instante seguinte ao cadastro.
    const doAparelho = Intl.DateTimeFormat().resolvedOptions().timeZone
    expect(diaDoFogo('2026-08-15T01:30:00Z')).toBe(
      diaDoFogo('2026-08-15T01:30:00Z', doAparelho),
    )
  })

  it('data inválida devolve null em vez de inventar um dia', () => {
    expect(diaDoFogo('não é data')).toBeNull()
  })
})

describe('sessão válida', () => {
  it('zero repetição não conta — senão abrir a câmera vira fazenda de fogo', () => {
    expect(sessaoValida(sessao(meioDia('2026-08-15'), 0))).toBe(false)
    expect(sessaoValida(sessao(meioDia('2026-08-15'), 1))).toBe(true)
  })

  it('dia com só sessões zeradas não é dia ativo', () => {
    expect(diasAtivos([sessao(meioDia('2026-08-15'), 0)]).size).toBe(0)
  })
})

describe('fogoLocal', () => {
  it('conta dias seguidos terminando hoje', () => {
    const sessoes = ['2026-08-15', '2026-08-14', '2026-08-13'].map((d) => sessao(meioDia(d)))

    expect(fogoLocal(sessoes, '2026-08-15').streak).toBe(3)
  })

  it('duas sessões no mesmo dia contam um dia só', () => {
    const sessoes = [sessao('2026-08-15T13:00:00Z', 10), sessao('2026-08-15T22:00:00Z', 12)]

    const fogo = fogoLocal(sessoes, '2026-08-15')

    expect(fogo.streak).toBe(1)
    expect(fogo.sessoesHoje).toBe(2)
  })

  it('hoje sem treino não quebra a sequência — o dia não acabou', () => {
    const sessoes = ['2026-08-14', '2026-08-13'].map((d) => sessao(meioDia(d)))

    const fogo = fogoLocal(sessoes, '2026-08-15')

    expect(fogo.streak).toBe(2)
    expect(fogo.treinouHoje).toBe(false)
  })

  it('sem proteção nenhuma, um dia falho apaga o fogo', () => {
    // O visitante tem zero proteções (§Planos) — e é essa fragilidade que dá força ao CTA.
    const sessoes = ['2026-08-13', '2026-08-12'].map((d) => sessao(meioDia(d)))

    expect(fogoLocal(sessoes, '2026-08-15').streak).toBe(0)
  })

  it('lembra o melhor mesmo com o fogo apagado', () => {
    const sessoes = ['2026-07-01', '2026-07-02', '2026-07-03'].map((d) => sessao(meioDia(d)))

    const fogo = fogoLocal(sessoes, '2026-08-15')

    expect(fogo.streak).toBe(0)
    expect(fogo.melhor).toBe(3)
  })

  it('sem sessão nenhuma tudo é zero, e não NaN', () => {
    expect(fogoLocal([], '2026-08-15')).toEqual({
      streak: 0,
      melhor: 0,
      treinouHoje: false,
      sessoesHoje: 0,
    })
  })

  it('atravessa a virada do mês', () => {
    const sessoes = ['2026-08-01', '2026-07-31', '2026-07-30'].map((d) => sessao(meioDia(d)))

    expect(fogoLocal(sessoes, '2026-08-01').streak).toBe(3)
  })
})
