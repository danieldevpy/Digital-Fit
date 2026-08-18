import { afterEach, describe, expect, it } from 'vitest'

import { useI18nStore } from '../i18n/store'
import { categoryLabel, currentCatalog, DEFAULT_EXERCISE, EXERCISE_CATALOG, getExercise } from './catalog'
import { useConfigStore } from '../store/config'

// O store precisa estar vazio para `currentCatalog` cair no embutido — é justamente esse o
// caminho que a T-090 mudou.
useConfigStore.getState().reset()

describe('maturidade no embutido (T-090 / SPEC-020)', () => {
  it('o embutido declara a maturidade de cada exercício', () => {
    // Sem isto o filtro abaixo não teria como agir, e um `beta` novo entraria calado na tela.
    for (const [slug, info] of Object.entries(EXERCISE_CATALOG)) {
      expect(info.maturity, `${slug} sem maturidade`).toBeTruthy()
    }
  })

  it('o embutido espelha o banco: os quatro em `validado`', () => {
    // Os dois de chão nasceram `beta` (migration 0012), a flexão subiu a `calibrado` na 0018
    // (T-111, com corpus medido) e os dois foram a `validado` na 0019 (T-113, decisão de
    // produto). O embutido tem de contar a MESMA história que o servidor, senão o primeiro
    // paint mostra um card que a admissão recusa — que é o `[A/T-051]` de volta.
    expect(EXERCISE_CATALOG.flexao?.maturity).toBe('validado')
    expect(EXERCISE_CATALOG.abdominal?.maturity).toBe('validado')
  })

  it('antes do servidor falar, só `validado` aparece', () => {
    // O embutido é o catálogo do primeiro paint e do offline. Sem o filtro, quem abre o app vê
    // por um instante um card que o `POST /sessions` recusa — o `[A/T-051]` na janela mais
    // curta e mais difícil de reproduzir que existe. Hoje os quatro são `validado` e passam;
    // o filtro segue de pé para o próximo exercício que entrar abaixo disso.
    expect(Object.keys(currentCatalog())).toEqual(['jumping_jack', 'squat', 'flexao', 'abdominal'])
  })

  it('o default do app é um exercício que todo mundo pode abrir', () => {
    expect(EXERCISE_CATALOG[DEFAULT_EXERCISE]?.maturity).toBe('validado')
  })
})

describe('o embutido existe nas duas línguas (T-152, SPEC-025 critério 1)', () => {
  afterEach(() => useI18nStore.getState().setLocale('pt-BR'))

  it('o texto muda de idioma sem reimportar o módulo — não é congelado no import', () => {
    // O ponto central desta task: `EXERCISE_CATALOG` é montado UMA VEZ, no import, e o texto
    // não pode congelar no idioma de quando o bundle carregou (o mesmo bug que o comentário de
    // `TABS`, em `shell/TabBar.tsx`, evitou desde a T-142).
    useI18nStore.getState().setLocale('pt-BR')
    expect(getExercise('squat').display_name).toBe('Agachamento')

    useI18nStore.getState().setLocale('en')
    expect(getExercise('squat').display_name).toBe('Squat')
  })

  it('nenhum campo de texto do embutido fica em branco em nenhuma das duas línguas', () => {
    for (const locale of ['pt-BR', 'en'] as const) {
      useI18nStore.getState().setLocale(locale)
      for (const slug of Object.keys(EXERCISE_CATALOG)) {
        const info = getExercise(slug)
        expect(info.display_name.length, `${locale}/${slug}.display_name`).toBeGreaterThan(0)
        expect(info.muscle_group.length, `${locale}/${slug}.muscle_group`).toBeGreaterThan(0)
        expect(info.default_tip.length, `${locale}/${slug}.default_tip`).toBeGreaterThan(0)
        for (const passo of info.guide_steps) {
          expect(passo.text.length, `${locale}/${slug}.guide_steps`).toBeGreaterThan(0)
        }
      }
    }
  })

  it('categoria conhecida traduz nas duas línguas — desconhecida devolve o slug nas duas', () => {
    useI18nStore.getState().setLocale('pt-BR')
    expect(categoryLabel('forca')).toBe('Força')
    expect(categoryLabel('hiit')).toBe('hiit')

    useI18nStore.getState().setLocale('en')
    expect(categoryLabel('forca')).toBe('Strength')
    expect(categoryLabel('hiit')).toBe('hiit')
  })
})
