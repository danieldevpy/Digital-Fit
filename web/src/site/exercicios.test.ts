// As páginas por exercício (T-165, SPEC-026 §Escopo).
//
// O que este arquivo cobra é o que o snapshot do banco não pode desmentir: que cada exercício
// publicado vira uma rota nas duas línguas, com endereço traduzido, e que o roteador sabe voltar
// de um endereço para o exercício certo — **sem aceitar o endereço da outra língua**.
import { describe, expect, it } from 'vitest'

import { LOCALES } from '../i18n/locale'
import { EXERCICIOS_PUBLICOS, exercicioPorEndereco, exercicioPorSlug } from './exercicios'
import {
  caminhoDaRota,
  idDaRotaDeExercicio,
  parseSitePath,
  ROTAS_INDEXAVEIS,
  slugDoExercicioNaRota,
} from './routes'

describe('o catálogo exportado do banco', () => {
  it('não está vazio — página de exercício é a razão da task existir', () => {
    expect(EXERCICIOS_PUBLICOS.length).toBeGreaterThan(0)
  })

  it('todo exercício tem endereço e nome em todo idioma', () => {
    // `exercicios.ts` já recusa o contrário no carregamento; este caso existe para que a falha
    // apareça como teste vermelho e não como build quebrado depois de um `export_site_catalog`
    // rodado contra banco pela metade.
    for (const exercicio of EXERCICIOS_PUBLICOS) {
      for (const locale of LOCALES) {
        expect(exercicio.por_idioma[locale].url_slug).toBeTruthy()
        expect(exercicio.por_idioma[locale].nome).toBeTruthy()
      }
    }
  })

  it('nenhum endereço se repete dentro do mesmo idioma', () => {
    // O exportador já recusa (`SlugDuplicado`), e aqui a mesma regra é conferida do lado que
    // sofreria a consequência: dois exercícios no mesmo endereço fazem o pré-render escrever os
    // dois no mesmo arquivo, e o segundo apaga o primeiro em silêncio.
    for (const locale of LOCALES) {
      const enderecos = EXERCICIOS_PUBLICOS.map((ex) => ex.por_idioma[locale].url_slug)

      expect(new Set(enderecos).size).toBe(enderecos.length)
    }
  })

  it('cada exercício vira uma rota indexável em cada idioma', () => {
    const rotas = ROTAS_INDEXAVEIS.map((rota) => rota.screen)

    for (const exercicio of EXERCICIOS_PUBLICOS) {
      expect(rotas).toContain(idDaRotaDeExercicio(exercicio.slug))
    }
  })
})

describe('do endereço de volta para o exercício', () => {
  const primeiro = EXERCICIOS_PUBLICOS[0]!

  it('acha pelo endereço daquele idioma', () => {
    for (const locale of LOCALES) {
      const achado = exercicioPorEndereco(primeiro.por_idioma[locale].url_slug, locale)

      expect(achado?.slug).toBe(primeiro.slug)
    }
  })

  it('o caminho completo volta pelo roteador para o exercício e o idioma certos', () => {
    for (const exercicio of EXERCICIOS_PUBLICOS) {
      for (const locale of LOCALES) {
        const caminho = `/${caminhoDaRota(idDaRotaDeExercicio(exercicio.slug), locale)}`

        expect(parseSitePath(caminho)).toEqual({
          screen: idDaRotaDeExercicio(exercicio.slug),
          locale,
        })
      }
    }
  })

  it('o endereço de UM idioma na pasta do OUTRO dá 404, e isso é de propósito', () => {
    // `/exercicios/squat/` (pasta portuguesa, endereço inglês) responderia 200 com a mesma
    // página que `/exercicios/agachamento/` — duas URLs para o mesmo conteúdo, que é exatamente
    // o que o `canonical` da T-160 existe para evitar. Aceitar as duas o desmentiria.
    const comEnderecoTrocado = EXERCICIOS_PUBLICOS.filter(
      (ex) => ex.por_idioma['pt-BR'].url_slug !== ex.por_idioma.en.url_slug,
    )
    expect(comEnderecoTrocado.length).toBeGreaterThan(0)

    for (const exercicio of comEnderecoTrocado) {
      expect(parseSitePath(`/exercicios/${exercicio.por_idioma.en.url_slug}/`).screen).toBe(
        'nao_encontrada',
      )
      expect(parseSitePath(`/en/exercises/${exercicio.por_idioma['pt-BR'].url_slug}/`).screen).toBe(
        'nao_encontrada',
      )
    }
  })

  it('endereço que não existe em idioma nenhum é 404, não a landing', () => {
    expect(parseSitePath('/exercicios/levitacao/').screen).toBe('nao_encontrada')
    expect(parseSitePath('/en/exercises/levitation/').screen).toBe('nao_encontrada')
    // Pasta certa, nível a mais: não é uma página, e não pode virar uma por acidente.
    expect(parseSitePath('/exercicios/agachamento/extra/').screen).toBe('nao_encontrada')
  })
})

describe('o id da rota é o slug TÉCNICO, e é ele que abre a sessão', () => {
  it('o id sobrevive à ida e volta, e não carrega o endereço traduzido', () => {
    for (const exercicio of EXERCICIOS_PUBLICOS) {
      const id = idDaRotaDeExercicio(exercicio.slug)

      expect(slugDoExercicioNaRota(id)).toBe(exercicio.slug)
      expect(exercicioPorSlug(exercicio.slug)?.slug).toBe(exercicio.slug)
    }
  })

  it('rota estática não é confundida com rota de exercício', () => {
    expect(slugDoExercicioNaRota('index')).toBeUndefined()
    expect(slugDoExercicioNaRota('sobre')).toBeUndefined()
    expect(slugDoExercicioNaRota('nao_encontrada')).toBeUndefined()
  })
})
