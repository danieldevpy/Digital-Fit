// O portão do HTML GERADO (T-166, SPEC-026 §Critérios de aceite 7 · plano §4).
//
// Os testes que já existiam cobrem as funções que *decidem* o `<head>`: `metatags.test.ts`
// confere que `linksDeCabecalho()` devolve `href` absoluto e recíproco, `descoberta.test.ts`
// confere o `sitemap.xml`, `social.test.ts` confere o Open Graph. Todos verdadeiros, e nenhum
// deles responde à pergunta que a Fase 8 existe para responder: **a página que vai para o ar
// tem essas anotações?** Entre a função e o arquivo há uma injeção por expressão regular que já
// comeu a abertura de `<html>` uma vez (T-159) — e um `hreflang` perfeito numa string que não
// chega ao arquivo é exatamente o mesmo prejuízo que o `hreflang` relativo da T-147.
//
// Este arquivo fecha esse vão. Ele monta cada página com o MESMO código do build
// (`montarPagina`, sobre o template real em disco) e cobra o resultado — sem `npm run build`,
// que leva minutos e não caberia numa suíte que roda a cada salvamento.
//
// ## O que ele NÃO alcança, dito aqui para não ser confundido com cobertura
//
// O template lido aqui é o **fonte** (`web/index.html`); o build injeta nele os `<script>` e
// `<link>` dos assets com hash antes do pré-render rodar. Se uma atualização do Vite mudasse a
// forma como esses `<script>` entram e isso quebrasse uma âncora de injeção, este teste
// continuaria verde. Quem cobre esse flanco é a conferência de moldura dentro do próprio
// `montarPagina()`, que roda no build de verdade e o derruba — os dois juntos são o portão.
import { describe, expect, it } from 'vitest'

import { renderizarPaginas } from '../entries/prerender'
import { LOCALES, type Locale } from '../i18n/locale'
import { LOCALE_PADRAO_DO_BUSCADOR, urlAbsoluta } from './metatags'
import { montarPagina, type PaginaPrerenderizada } from './paginaGerada'
import { ROTAS_INDEXAVEIS } from './routes'

const ORIGEM = 'https://exemplo.com.br'

/**
 * Os HTML de entrada, pelo `import.meta.glob` do Vite (`?raw`) — e não por `node:fs`, pelo mesmo
 * motivo de `i18n/portoes.test.ts`: o `tsconfig.app.json` não carrega `@types/node`, e o glob
 * já resolve a raiz do projeto sem a armadilha do caminho com espaço ("Digital Fit").
 *
 * As exclusões são obrigatórias e não decorativas: `**` alcançaria `node_modules/` e os
 * artefatos de build, que têm HTML aos milhares e nenhum deles é entrada de rota.
 */
const TEMPLATES = import.meta.glob(
  [
    '../../**/*.html',
    '!../../node_modules/**',
    '!../../dist/**',
    '!../../dist-ssr/**',
    '!../../scripts/**',
  ],
  { query: '?raw', eager: true, import: 'default' },
) as Record<string, string>

/**
 * O template de uma rota. Lançar aqui já é metade do portão: uma rota nova na tabela sem entry
 * no `vite.config.ts` derruba este arquivo antes de qualquer asserção sobre metadado.
 */
function templateDe(caminho: string): string {
  const chave = `../../${caminho}index.html`
  const bruto = TEMPLATES[chave]
  if (bruto === undefined) {
    throw new Error(`rota gerada sem HTML de entrada no build: ${chave} (ver vite.config.ts)`)
  }
  return bruto
}

interface Gerada {
  pagina: PaginaPrerenderizada
  html: string
}

/** As páginas como o build as escreveria — mesmo render, mesma injeção, mesma origem exigida. */
const GERADAS: readonly Gerada[] = renderizarPaginas().map((pagina) => ({
  pagina,
  html: montarPagina(templateDe(pagina.caminho), pagina, ORIGEM),
}))

function canonicalDe(html: string): string[] {
  return [...html.matchAll(/<link rel="canonical" href="([^"]*)" \/>/g)].map(([, href]) => href!)
}

function alternativasDe(html: string): { hreflang: string; href: string }[] {
  return [
    ...html.matchAll(/<link rel="alternate" hreflang="([^"]*)" href="([^"]*)" \/>/g),
  ].map(([, hreflang, href]) => ({ hreflang: hreflang!, href: href! }))
}

function conteudoDaMeta(html: string, nome: string): string | undefined {
  return html.match(new RegExp(`<meta name="${nome}" content="([^"]*)" />`))?.[1]
}

function paginaDe(screen: string, locale: Locale): Gerada {
  const achada = GERADAS.find((g) => g.pagina.screen === screen && g.pagina.locale === locale)
  if (!achada) throw new Error(`não foi gerada página para ${screen} · ${locale}`)
  return achada
}

const CASOS = GERADAS.map(({ pagina }) => ({
  nome: `/${pagina.caminho} (${pagina.locale})`,
  screen: pagina.screen,
  locale: pagina.locale,
}))

describe('o HTML gerado de cada rota (T-166 — o portão que vale para sempre)', () => {
  it('existe uma página por rota indexável por idioma, e nenhuma a mais', () => {
    expect(GERADAS).toHaveLength(ROTAS_INDEXAVEIS.length * LOCALES.length)
  })

  describe.each(CASOS)('$nome', ({ screen, locale }) => {
    const { html } = paginaDe(screen, locale)

    it('tem UM `canonical`, absoluto, e ele é a própria URL', () => {
      // Um só: dois `canonical` numa página fazem o Google ignorar os dois. É o modo de falha
      // de injetar em cima de um template que já trazia a anotação escrita à mão.
      expect(canonicalDe(html)).toEqual([urlAbsoluta(ORIGEM, screen, locale)])
    })

    it('declara `alternate` para todos os idiomas, todos absolutos', () => {
      const alternativas = alternativasDe(html)
      const idiomas = alternativas.map((alternativa) => alternativa.hreflang)

      for (const outro of LOCALES) expect(idiomas).toContain(outro)
      for (const { href } of alternativas) expect(href).toMatch(/^https:\/\//)
    })

    it('tem `x-default`, e ele aponta para a versão inglesa DESTA rota', () => {
      // Não para a home: o estrangeiro que caiu em `/sobre/` quer o Sobre em inglês, não a
      // landing. Apontar tudo para `/en/` é o erro clássico de `x-default` escrito à mão.
      const xDefault = alternativasDe(html).filter((a) => a.hreflang === 'x-default')

      expect(xDefault).toEqual([
        { hreflang: 'x-default', href: urlAbsoluta(ORIGEM, screen, LOCALE_PADRAO_DO_BUSCADOR) },
      ])
    })

    it('tem `title` e `description` preenchidos e escapados', () => {
      const titulo = html.match(/<title>([^<]*)<\/title>/)?.[1]

      expect(titulo?.trim()).toBeTruthy()
      expect(conteudoDaMeta(html, 'description')?.trim()).toBeTruthy()
    })

    it('sobrevive à injeção: `lang`, `head` e o conteúdo no lugar', () => {
      // A T-159 perdeu a abertura de `<html>` e de `<head>` para um regex guloso, e o sintoma
      // foi a landing renderizando em inglês por cima do HTML português — sem erro nenhum.
      expect(html).toContain(`<html lang="${locale}">`)
      expect(html.match(/<title>/g)).toHaveLength(1)
      expect(html).toContain('</head>')
      expect(html).toMatch(/<div id="root">\s*<[^>]/)
    })
  })
})

describe('o par de idiomas, conferido contra as páginas que existem de verdade', () => {
  // A diferença entre este bloco e `metatags.test.ts`: lá as duas pontas saem da mesma função,
  // então a reciprocidade é tautológica. Aqui cada `href` é procurado no `canonical` de uma
  // página REALMENTE gerada — um `alternate` que aponte para uma URL que ninguém escreve
  // (rota removida de um lado só, slug renomeado em um idioma) cai aqui e em nenhum outro lugar.
  const porCanonical = new Map(GERADAS.map((g) => [canonicalDe(g.html)[0]!, g]))

  it.each(CASOS)('$nome aponta para páginas existentes, e elas apontam de volta', ({ screen, locale }) => {
    const origem = paginaDe(screen, locale)
    const meuCanonical = canonicalDe(origem.html)[0]

    for (const { hreflang, href } of alternativasDe(origem.html)) {
      const destino = porCanonical.get(href)

      expect(destino, `${hreflang} → ${href} não é o canonical de nenhuma página gerada`).toBeDefined()
      expect(destino!.pagina.screen).toBe(screen)
      if (hreflang !== 'x-default') expect(destino!.pagina.locale).toBe(hreflang)

      const devolve = alternativasDe(destino!.html).map((a) => a.href)
      expect(devolve).toContain(meuCanonical)
    }
  })
})

describe('título e descrição não podem ser os mesmos nos dois idiomas', () => {
  // O erro que este bloco pega é o mais barato de cometer e o mais caro de descobrir: a chave
  // nova nasce no `pt-BR`, o `tsc` cobra a existência dela no `en` — e copiar o português para
  // dentro do inglês satisfaz o tipo. A página inglesa vai para o índice com título português,
  // e nenhum portão existente diz nada.
  it.each(ROTAS_INDEXAVEIS.map((rota) => ({ nome: rota.screen, screen: rota.screen })))(
    '$nome tem título e descrição próprios em cada idioma',
    ({ screen }) => {
      const titulos = new Set<string>()
      const descricoes = new Set<string>()

      for (const locale of LOCALES) {
        const { pagina } = paginaDe(screen, locale)
        titulos.add(pagina.titulo)
        descricoes.add(pagina.descricao)
      }

      expect(titulos.size).toBe(LOCALES.length)
      expect(descricoes.size).toBe(LOCALES.length)
    },
  )
})

describe('montarPagina falha alto quando a moldura não sobrevive', () => {
  const [primeira] = GERADAS
  const pagina = primeira!.pagina

  it('sem o ponto de montagem, para o build em vez de escrever página vazia', () => {
    expect(() => montarPagina('<html lang="pt-BR"><head></head><body></body></html>', pagina, ORIGEM)).toThrow(
      /id="root"/,
    )
  })

  it('sem o fecho do `head` na coluna esperada, acusa a anotação que não entrou', () => {
    // O `</head>` sem os dois espaços de indentação é o caso real: as três injeções do
    // cabeçalho ancoram nele, e nenhuma delas casa. Antes da T-166 isto produziria uma página
    // servida sem `canonical`, sem `hreflang` e sem Open Graph, e o build terminaria com 0.
    const torto = '<html lang="pt-BR">\n<head>\n<title>x</title>\n</head>\n<body><div id="root"></div></body>\n</html>'

    expect(() => montarPagina(torto, pagina, ORIGEM)).toThrow(/canonical|x-default|og:image/)
  })
})
