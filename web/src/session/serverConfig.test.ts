// Catálogo servido pelo `GET /api/config` (SPEC-018 / T-074).
//
// O que estes testes protegem é a assimetria que a spec pede: o servidor **vence** quando
// chega, e o cliente **nunca fica vazio** quando ele não chega. As duas metades erram para
// lados opostos, e é fácil consertar uma quebrando a outra.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import { useConfigStore, type ServerConfig, type ServerExercise } from '../store/config'
import {
  EXERCISE_CATALOG,
  categoryLabel,
  currentCatalog,
  getExercise,
  isExerciseKey,
  offersChoice,
} from './catalog'
import { liveKcal } from './kcal'
import { fetchServerConfig, hydrateStoredConfig } from './serverConfig'

function exercicioDoServidor(over: Partial<ServerExercise> = {}): ServerExercise {
  return {
    slug: 'marcha',
    display_name: 'Marcha estacionária',
    category: 'mobilidade',
    muscle_group: 'Pernas',
    default_tip: 'Joelhos na altura do quadril.',
    main_angle: 'none',
    demo_img: '/img/guia/marcha.jpg',
    dot_color: '#f59e0b',
    met: 3.8,
    ref_cadence_rpm: 60,
    maturity: 'validado',
    guide_steps: [],
    ...over,
  }
}

function config(exercises: ServerExercise[]): ServerConfig {
  return {
    config_version: 7,
    plan: {
      slug: 'anon',
      name: 'Visitante',
      daily_sessions: 3,
      quota_message: 'acabou',
      allow_cloud: true,
      history_limit: 50,
      kcal_accumulation: false,
      effects_enabled: false,
      flags: {},
    },
    session: {
      duration_s: 30,
      min_s: 30,
      max_s: 30,
      countdown_default_s: 3,
      countdown_max_s: 10,
    },
    steppers: {
      series_min: 1,
      series_max: 9,
      series_default: 1,
      reps_min: 5,
      reps_max: 30,
      reps_default: 15,
    },
    exercises,
  }
}

beforeEach(() => {
  installStorage()
  useConfigStore.getState().reset()
})

afterEach(() => {
  useConfigStore.getState().reset()
  uninstallStorage()
  vi.restoreAllMocks()
})

describe('o catálogo embutido é o default, não o dono', () => {
  it('sem servidor, vale o embutido — o app desenha sem rede', () => {
    expect(currentCatalog()).toBe(EXERCISE_CATALOG)
    expect(getExercise('squat').display_name).toBe('Agachamento')
  })

  it('quando o servidor fala, ele vence', () => {
    useConfigStore
      .getState()
      .apply(config([exercicioDoServidor({ slug: 'squat', display_name: 'Agachamento livre' })]))

    expect(getExercise('squat').display_name).toBe('Agachamento livre')
  })

  it('o servidor SUBSTITUI o catálogo, não completa o embutido', () => {
    // O ponto do `[A/T-051]`: exercício que o servidor não listou está desligado ou fora do
    // plano. Mantê-lo por herança recriaria o card que a admissão recusa.
    useConfigStore.getState().apply(config([exercicioDoServidor({ slug: 'jumping_jack' })]))

    expect(isExerciseKey('squat')).toBe(false)
    expect(Object.keys(currentCatalog())).toEqual(['jumping_jack'])
  })

  it('lista vazia quer dizer "não sei", e o embutido continua no ar', () => {
    // É o que o servidor manda com o banco fora (`_catalogo_serializado`). Guardar `[]` aqui
    // apagaria a tela Escolha por causa de um soluço de banco.
    useConfigStore.getState().apply(config([]))

    expect(currentCatalog()).toBe(EXERCISE_CATALOG)
    expect(offersChoice()).toBe(true)
  })

  it('com um exercício só, não há escolha a oferecer', () => {
    useConfigStore.getState().apply(config([exercicioDoServidor()]))

    expect(offersChoice()).toBe(false)
  })

  it('o padrão desligado no painel não devolve `undefined` no meio da tela', () => {
    useConfigStore.getState().apply(config([exercicioDoServidor({ slug: 'squat' })]))

    expect(getExercise(null).display_name.length).toBeGreaterThan(0)
    expect(getExercise('jumping_jack').display_name.length).toBeGreaterThan(0)
  })

  it('`main_angle` que este cliente não conhece cai em `none`', () => {
    // Mostrar um ângulo que o cliente não sabe ler daria número errado na barra de métricas —
    // e a regra da casa é `--`, não um número inventado.
    useConfigStore
      .getState()
      .apply(config([exercicioDoServidor({ slug: 'squat', main_angle: 'joelho_futuro' })]))

    expect(getExercise('squat').main_angle).toBe('none')
  })
})

describe('categoria virou slug de contrato', () => {
  it('o embutido guarda slug, não rótulo', () => {
    expect(EXERCISE_CATALOG.jumping_jack?.category).toBe('cardio')
    expect(EXERCISE_CATALOG.squat?.category).toBe('forca')
  })

  it('o rótulo é derivado na hora de exibir', () => {
    expect(categoryLabel('forca')).toBe('Força')
    expect(categoryLabel('mobilidade')).toBe('Mobilidade')
  })

  it('categoria nova do servidor aparece feia, mas não some', () => {
    expect(categoryLabel('hiit')).toBe('hiit')
  })
})

describe('a busca da configuração', () => {
  it('aplica o que o servidor mandou', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(config([exercicioDoServidor()])), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ETag: '"abc"' },
      }),
    )

    expect(await fetchServerConfig(fetchFalso as unknown as typeof fetch)).toBe(true)
    expect(useConfigStore.getState().configVersion).toBe(7)
    expect(useConfigStore.getState().plan?.slug).toBe('anon')
  })

  it('falhar é silencioso e deixa o embutido de pé', async () => {
    const fetchFalso = vi.fn().mockRejectedValue(new Error('sem rede'))

    expect(await fetchServerConfig(fetchFalso as unknown as typeof fetch)).toBe(false)
    expect(currentCatalog()).toBe(EXERCISE_CATALOG)
  })

  it('500 também é silencioso', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(new Response('', { status: 500 }))

    expect(await fetchServerConfig(fetchFalso as unknown as typeof fetch)).toBe(false)
    expect(currentCatalog()).toBe(EXERCISE_CATALOG)
  })

  it('aba nova hidrata do disco e AÍ revalida', async () => {
    // Sem hidratar, o ETag seria decoração: o store nasce vazio a cada reload, `If-None-Match`
    // nunca sairia, e o payload inteiro desceria em toda abertura do app.
    window.localStorage.setItem('digitalfit.config_etag', '"abc"')
    window.localStorage.setItem(
      'digitalfit.config',
      JSON.stringify(config([exercicioDoServidor()])),
    )
    const fetchFalso = vi.fn().mockResolvedValue({ status: 304, ok: false })

    expect(await fetchServerConfig(fetchFalso as unknown as typeof fetch)).toBe(false)

    const enviados = (fetchFalso.mock.calls[0]?.[1] as RequestInit).headers as Record<string, string>
    expect(enviados['If-None-Match']).toBe('"abc"')
    // O 304 confirmou o que o disco trouxe — e o catálogo está de pé, não vazio.
    expect(Object.keys(currentCatalog())).toEqual(['marcha'])
  })

  it('sem nada no disco, não revalida — 304 sobre store vazio seria o pior dos mundos', async () => {
    window.localStorage.setItem('digitalfit.config_etag', '"abc"')
    const fetchFalso = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(config([exercicioDoServidor()])), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await fetchServerConfig(fetchFalso as unknown as typeof fetch)

    const enviados = (fetchFalso.mock.calls[0]?.[1] as RequestInit).headers as Record<string, string>
    expect(enviados['If-None-Match']).toBeUndefined()
  })

  it('payload corrompido no disco é descartado, não derruba o boot', () => {
    window.localStorage.setItem('digitalfit.config', '{isto nao e json')

    expect(hydrateStoredConfig()).toBe(false)
    expect(currentCatalog()).toBe(EXERCISE_CATALOG)
  })

  it('com catálogo em memória, revalida e o 304 não apaga nada', async () => {
    const primeira = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(config([exercicioDoServidor()])), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ETag: '"abc"' },
      }),
    )
    await fetchServerConfig(primeira as unknown as typeof fetch)

    // `new Response(..., {status: 304})` é proibido pelo construtor (304 não tem corpo), então
    // o dublê expõe só o que `fetchServerConfig` lê.
    const segunda = vi.fn().mockResolvedValue({ status: 304, ok: false })
    expect(await fetchServerConfig(segunda as unknown as typeof fetch)).toBe(false)

    const enviados = (segunda.mock.calls[0]?.[1] as RequestInit).headers as Record<string, string>
    expect(enviados['If-None-Match']).toBe('"abc"')
    expect(Object.keys(currentCatalog())).toEqual(['marcha'])
  })
})

// --------------------------------------------------------------------------------------
// A fiação do kcal (T-128) — do payload do servidor até o número
//
// O `kcal.test.ts` cobre a fórmula com objetos montados à mão; estes cobrem o **caminho**:
// `GET /api/config` → store → catálogo mesclado → `liveKcal`. É a parte que um teste de
// fórmula não pega, e é exatamente onde a T-063 tinha o defeito — a conta estava certa, o
// insumo é que não era o que a tela precisava.
// --------------------------------------------------------------------------------------

describe('kcal a partir do catálogo servido', () => {
  it('a cadência de referência atravessa payload, store e catálogo até virar caloria', async () => {
    const polichinelo = exercicioDoServidor({
      slug: 'jumping_jack',
      display_name: 'Polichinelo',
      met: 8,
      ref_cadence_rpm: 50,
    })
    useConfigStore.getState().apply(config([polichinelo]))

    const info = getExercise('jumping_jack')

    expect(info.met).toBe(8)
    expect(info.ref_cadence_rpm).toBe(50)
    // 25 repetições em 30 s é o ritmo de referência: 4,9 kcal.
    expect(
      liveKcal({
        met: info.met,
        refCadenceRpm: info.ref_cadence_rpm,
        reps: 25,
        elapsedS: 30,
      }),
    ).toBeCloseTo(4.9, 2)
  })

  it('sem servidor o embutido não tem cadência, e o card mostra `--`', () => {
    // O catálogo em código não carrega MET nem cadência ("o servidor é quem sabe"), então o
    // caminho degradado tem de terminar em `--` — e não num número inventado a partir de meio
    // insumo, que é o modo silencioso de errar.
    useConfigStore.getState().reset()
    const info = getExercise('jumping_jack')

    expect(info.ref_cadence_rpm).toBeUndefined()
    expect(
      liveKcal({
        met: info.met,
        refCadenceRpm: info.ref_cadence_rpm,
        reps: 25,
        elapsedS: 30,
      }),
    ).toBeNull()
  })

  it('exercício servido sem cadência não vira número: MET sozinho não basta', () => {
    // O caso de um exercício novo cadastrado no painel com MET preenchido e cadência em 0 —
    // que é o esquecimento que o teste do servidor (`test_todo_exercicio_tem_cadencia`) cobra
    // do outro lado.
    useConfigStore
      .getState()
      .apply(config([exercicioDoServidor({ slug: 'novo', met: 6, ref_cadence_rpm: 0 })]))
    const info = getExercise('novo')

    expect(
      liveKcal({ met: info.met, refCadenceRpm: info.ref_cadence_rpm, reps: 20, elapsedS: 30 }),
    ).toBeNull()
  })
})
