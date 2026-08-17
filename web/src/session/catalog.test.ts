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

  it('o embutido espelha o banco: flexão `calibrado`, abdominal ainda `beta`', () => {
    // Os dois nasceram `beta` na migration 0012. A flexão subiu na 0018 (T-111) porque ganhou
    // corpus real — oito itens, cinco com rótulo contado a mão, MAE de 0,20 rep; o abdominal
    // continua sem um único vídeo de gente treinando. O embutido tem de contar a mesma
    // história que o servidor, senão o primeiro paint mostra um card que a admissão recusa.
    expect(EXERCISE_CATALOG.flexao?.maturity).toBe('calibrado')
    expect(EXERCISE_CATALOG.abdominal?.maturity).toBe('beta')
  })

  it('antes do servidor falar, só `validado` aparece', () => {
    // O embutido é o catálogo do primeiro paint e do offline. Sem o filtro, quem abre o app vê
    // por um instante dois cards que o `POST /sessions` recusa — o `[A/T-051]` na janela mais
    // curta e mais difícil de reproduzir que existe.
    expect(Object.keys(currentCatalog())).toEqual(['jumping_jack', 'squat'])
  })

  it('o default do app é um exercício que todo mundo pode abrir', () => {
    expect(EXERCISE_CATALOG[DEFAULT_EXERCISE]?.maturity).toBe('validado')
  })
})
