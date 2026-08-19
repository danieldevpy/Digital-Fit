// A tabela de rotas é a fonte única — e este arquivo é o que a obriga a ser (T-158, SPEC-026).
import { describe, expect, it } from 'vitest'

import { ENTRADAS_DO_BUILD } from '../../vite.config'
import { LOCALES } from '../i18n/locale'
import { EXERCICIOS_PUBLICOS } from './exercicios'
import {
  caminhoDaRota,
  idDaRotaDeExercicio,
  parseSitePath,
  ROTAS,
  ROTAS_COM_ENTRY,
  ROTAS_INDEXAVEIS,
  rotaDe,
  slugDoExercicioNaRota,
} from './routes'

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
  const entries = Object.values(ENTRADAS_DO_BUILD)

  it('toda rota com entry próprio, em todo idioma, tem um HTML no build', () => {
    const esperados = ROTAS_COM_ENTRY.filter((rota) => rota.indexavel).flatMap((rota) =>
      LOCALES.map((locale) => `${caminhoDaRota(rota.screen, locale)}index.html`),
    )

    for (const esperado of esperados) expect(entries).toContain(esperado)
  })

  it('toda rota CLONADA aponta para um molde que tem entry — senão o build não teria o que copiar', () => {
    // A outra metade da mesma regra, depois que a T-165 trouxe rotas do banco. Entry do Rollup
    // precisa ser arquivo real em disco, então página de exercício não tem o seu: ela clona o
    // de `sobre`. Um molde que por sua vez fosse clonado, ou que não existisse, quebraria o
    // pré-render — aqui isso é erro de teste, não erro de deploy.
    const clonadas = ROTAS.filter((rota) => rota.molde !== null)

    expect(clonadas.length).toBe(EXERCICIOS_PUBLICOS.length)
    for (const rota of clonadas) {
      const molde = rotaDe(rota.molde!)

      expect(molde.molde).toBeNull()
      for (const locale of LOCALES) {
        expect(entries).toContain(`${caminhoDaRota(molde.screen, locale)}index.html`)
      }
    }
  })

  it('a 404 também tem entry, e é declarada como não indexável', () => {
    expect(entries).toContain('404.html')
    expect(ROTAS.find((rota) => rota.screen === 'nao_encontrada')?.indexavel).toBe(false)
    expect(ROTAS_INDEXAVEIS.map((rota) => rota.screen)).not.toContain('nao_encontrada')
  })

  it('nenhuma rota ESTÁTICA reaproveita a chave de outra — o `tsc` cobra que elas existam', () => {
    // O tipo já garante que as chaves são `TKey` válidas; o que este caso impede é a rota
    // nascer apontando para a chave de OUTRA rota por copiar-e-colar.
    //
    // Só as estáticas: as de exercício compartilham a MESMA chave de propósito, porque a frase
    // é um template (`{nome}: como fazer corretamente`) e o que as diferencia é o `params`. É a
    // linha abaixo que cobra essa outra metade.
    const estaticas = ROTAS.filter((rota) => slugDoExercicioNaRota(rota.screen) === undefined)

    expect(new Set(estaticas.map((rota) => rota.titulo)).size).toBe(estaticas.length)
    expect(new Set(estaticas.map((rota) => rota.descricao)).size).toBe(estaticas.length)
  })

  it('cada rota de exercício traz o nome no idioma certo — não o português nos dois', () => {
    // O erro que este caso pega já aconteceu nesta task: `params` era um valor só, montado do
    // `pt-BR`, e a página inglesa saía com o título "Agachamento: how to..." — meia página em
    // cada língua, que é o modo de falha que a SPEC-025 existe para não repetir.
    for (const exercicio of EXERCICIOS_PUBLICOS) {
      const rota = rotaDe(idDaRotaDeExercicio(exercicio.slug))

      for (const locale of LOCALES) {
        expect(rota.params?.[locale]?.nome).toBe(exercicio.por_idioma[locale].nome)
      }
    }
  })

  it('o endereço de exercício é traduzido, e o id da rota NÃO é', () => {
    // O id é o slug técnico porque ele é o que não muda com o idioma: usar o endereço público
    // como identidade daria duas identidades à mesma página, e o `hreflang` não teria como
    // parear as duas.
    for (const exercicio of EXERCICIOS_PUBLICOS) {
      const id = idDaRotaDeExercicio(exercicio.slug)

      expect(slugDoExercicioNaRota(id)).toBe(exercicio.slug)
      expect(caminhoDaRota(id, 'pt-BR')).toBe(
        `exercicios/${exercicio.por_idioma['pt-BR'].url_slug}/`,
      )
      expect(caminhoDaRota(id, 'en')).toBe(`en/exercises/${exercicio.por_idioma.en.url_slug}/`)
    }
  })
})
