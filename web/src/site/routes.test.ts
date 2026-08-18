// A tabela de rotas é a fonte única — e este arquivo é o que a obriga a ser (T-158, SPEC-026).
import { describe, expect, it } from 'vitest'

import viteConfig from '../../vite.config'
import { LOCALES } from '../i18n/locale'
import { caminhoDaRota, parseSitePath, ROTAS, ROTAS_INDEXAVEIS } from './routes'

describe('caminhoDaRota — o slug é traduzido, e o prefixo de idioma é do pt-BR para fora', () => {
  it('a landing é a raiz em pt-BR e `/en/` em inglês', () => {
    expect(caminhoDaRota('index', 'pt-BR')).toBe('')
    expect(caminhoDaRota('index', 'en')).toBe('en/')
  })

  it('Sobre vira `about` em inglês — palavra na URL é sinal de busca', () => {
    expect(caminhoDaRota('sobre', 'pt-BR')).toBe('sobre/')
    expect(caminhoDaRota('sobre', 'en')).toBe('en/about/')
  })
})

describe('parseSitePath — ida e volta, e o que NÃO existe', () => {
  it.each(
    ROTAS_INDEXAVEIS.flatMap((rota) =>
      LOCALES.map((locale) => ({ screen: rota.screen, locale })),
    ),
  )('$screen · $locale volta de onde saiu', ({ screen, locale }) => {
    expect(parseSitePath(`/${caminhoDaRota(screen, locale)}`)).toEqual({ screen, locale })
  })

  it('caminho desconhecido é `nao_encontrada`, não a landing', () => {
    // Mandar o desconhecido para a home era o que o `parseSiteHash` fazia — a versão em
    // JavaScript do mesmo soft 404 que o `try_files` produzia no nginx.
    expect(parseSitePath('/planos/').screen).toBe('nao_encontrada')
    expect(parseSitePath('/en/pricing/').screen).toBe('nao_encontrada')
    expect(parseSitePath('/sobre/extra/').screen).toBe('nao_encontrada')
  })

  it('o prefixo de idioma é reconhecido mesmo quando a rota não é', () => {
    // Importa para a 404: ela ainda deve saber que a pessoa estava no lado inglês do site.
    expect(parseSitePath('/en/pricing/').locale).toBe('en')
    expect(parseSitePath('/planos/').locale).toBe('pt-BR')
  })

  it('tolera a barra final ausente — link escrito à mão não deve dar 404', () => {
    expect(parseSitePath('/sobre').screen).toBe('sobre')
    expect(parseSitePath('/en/about').screen).toBe('sobre')
    expect(parseSitePath('/en').screen).toBe('index')
  })
})

describe('a tabela é a fonte ÚNICA (SPEC-026 §Escopo)', () => {
  // O portão desta task. A lista de entries do Vite e a tabela de rotas respondem à mesma
  // pergunta e vivem em arquivos diferentes; foi exatamente esse tipo de par independente que
  // deixou o `hreflang` da T-147 inerte por meses. Aqui elas são confrontadas.
  const entries = Object.values(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (viteConfig as any).build.rollupOptions.input as Record<string, string>,
  )

  it('toda rota indexável, em todo idioma, tem um HTML no build', () => {
    const esperados = ROTAS_INDEXAVEIS.flatMap((rota) =>
      LOCALES.map((locale) => `${caminhoDaRota(rota.screen, locale)}index.html`),
    )

    for (const esperado of esperados) expect(entries).toContain(esperado)
  })

  it('a 404 também tem entry, e é declarada como não indexável', () => {
    expect(entries).toContain('404.html')
    expect(ROTAS.find((rota) => rota.screen === 'nao_encontrada')?.indexavel).toBe(false)
    expect(ROTAS_INDEXAVEIS.map((rota) => rota.screen)).not.toContain('nao_encontrada')
  })

  it('nenhuma rota fica sem título e sem descrição — o `tsc` cobra que as chaves existam', () => {
    // O tipo já garante que as chaves são `TKey` válidas; o que este caso impede é a rota
    // nascer apontando para a chave de OUTRA rota por copiar-e-colar.
    const titulos = ROTAS.map((rota) => rota.titulo)
    const descricoes = ROTAS.map((rota) => rota.descricao)

    expect(new Set(titulos).size).toBe(ROTAS.length)
    expect(new Set(descricoes).size).toBe(ROTAS.length)
  })
})
