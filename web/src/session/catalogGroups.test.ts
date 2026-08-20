// O agrupamento por categoria da tela Escolha (SPEC-020). Cobre a regra pura; o desenho da
// faixa é CSS e não tem o que cobrar aqui — a suíte do web roda em `node`, sem DOM.
import { describe, expect, it } from 'vitest'
import { useI18nStore } from '../i18n/store'
import { EXERCISE_CATALOG, EXERCISE_KEYS, groupByCategory, type ExerciseInfo } from './catalog'

// `categoryLabel` (usada por `groupByCategory`) resolve por `t()` — o teste do rótulo conhecido
// checa texto em pt-BR ('Força').
useI18nStore.getState().setLocale('pt-BR')

function ex(category: string): ExerciseInfo {
  return {
    display_name: 'X',
    category,
    muscle_group: 'G',
    default_tip: 'T',
    main_angle: 'none',
    orientacao_recomendada: 'qualquer',
    demo_img: '',
    dot_color: '#fff',
    guide_steps: [],
  }
}

describe('groupByCategory', () => {
  it('agrupa o catálogo embutido sem perder nenhum exercício', () => {
    const grupos = groupByCategory(EXERCISE_KEYS, EXERCISE_CATALOG)
    expect(grupos.flatMap((g) => g.keys).sort()).toEqual([...EXERCISE_KEYS].sort())
  })

  it('põe as categorias conhecidas na ordem declarada, não na ordem do catálogo', () => {
    const catalogo = { a: ex('core'), b: ex('cardio'), c: ex('forca') }
    expect(groupByCategory(['a', 'b', 'c'], catalogo).map((g) => g.category)).toEqual([
      'cardio',
      'forca',
      'core',
    ])
  })

  it('mantém a ordem do catálogo dentro da categoria (é a `ordem` do servidor)', () => {
    const catalogo = { primeiro: ex('cardio'), segundo: ex('cardio'), terceiro: ex('cardio') }
    const grupos = groupByCategory(['primeiro', 'segundo', 'terceiro'], catalogo)
    expect(grupos[0]!.keys).toEqual(['primeiro', 'segundo', 'terceiro'])
  })

  it('não inventa seção para categoria sem exercício', () => {
    const grupos = groupByCategory(['a'], { a: ex('cardio') })
    expect(grupos).toHaveLength(1)
  })

  it('categoria desconhecida vira seção no fim, com o slug cru — some é que não pode', () => {
    const catalogo = { a: ex('equilibrio'), b: ex('cardio') }
    const grupos = groupByCategory(['a', 'b'], catalogo)
    expect(grupos.map((g) => g.category)).toEqual(['cardio', 'equilibrio'])
    expect(grupos[1]!.label).toBe('equilibrio')
  })

  it('resolve o rótulo de exibição das conhecidas', () => {
    expect(groupByCategory(['a'], { a: ex('forca') })[0]!.label).toBe('Força')
  })

  it('ignora chave sem entrada no catálogo em vez de quebrar', () => {
    expect(groupByCategory(['a', 'fantasma'], { a: ex('cardio') })).toHaveLength(1)
  })
})
