import { describe, expect, it } from 'vitest'

import { caminhoDaRota, parseSitePath } from './routes'

// O roteador do site virou uma leitura de `location.pathname` (T-158) — a lógica toda mora em
// `routes.ts` e é lá que ela é testada. O que sobra de próprio aqui é a migração: os endereços
// que um dia foram públicos como fragmento continuam levando a algum lugar.
describe('os `#/sobre` antigos (T-158)', () => {
  it('o alvo do redirecionamento é a rota nova, no idioma do lado do site em que se está', () => {
    // `redirecionarHashLegado` não é chamada aqui porque ela navega (`location.replace`) e o
    // ambiente é `environment: 'node'`, sem `window`. O que dá para provar sem navegador é o
    // destino que ela calcula, e é o que importa: `#/sobre` no lado pt vai para `/sobre/`; no
    // lado inglês, para `/en/about/`.
    expect(`/${caminhoDaRota('sobre', parseSitePath('/').locale)}`).toBe('/sobre/')
    expect(`/${caminhoDaRota('sobre', parseSitePath('/en/').locale)}`).toBe('/en/about/')
  })

  it('a landing não redireciona para si mesma', () => {
    // `#/` e `#` já apontavam para a página em que a pessoa está — voltar à rede por isso seria
    // pagar uma navegação por nada.
    expect(parseSitePath('/').screen).toBe('index')
  })
})
