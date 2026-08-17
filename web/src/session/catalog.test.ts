import { describe, expect, it } from 'vitest'

import { currentCatalog, DEFAULT_EXERCISE, EXERCISE_CATALOG } from './catalog'
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
