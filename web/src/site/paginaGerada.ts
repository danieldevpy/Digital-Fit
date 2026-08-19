// A montagem do HTML final de uma página do site — a injeção que o build faz, como função
// PURA (T-166, SPEC-026 §Escopo · plano §4).
//
// ## Por que isto saiu do `scripts/prerender.mjs`
//
// Até a T-164 a injeção morava dentro do script de build: ler arquivo, casar quatro expressões
// regulares, escrever arquivo. Misturado assim, o único jeito de conferir o resultado era rodar
// `npm run build` e abrir o `dist/` com os olhos — que é exatamente o regime em que o `hreflang`
// relativo da T-147 sobreviveu meses, e o regime que a Fase 8 inteira existe para encerrar.
//
// A fronteira desta casa é sempre a mesma: **decisão no código testável, leitura do mundo na
// borda.** As funções que decidem o que entra no `<head>` já eram puras e testadas
// (`metatags.ts`, `social.ts`); faltava a que decide como elas entram. Com ela aqui, o teste do
// §4 do plano — *"o HTML gerado tem `canonical`, `hreflang` recíproco e `x-default`"* — passa a
// existir sem build, sobre o mesmo código que o build roda. O script ficou com o que só ele
// pode fazer: `readFile`, `writeFile` e a variável de ambiente.
//
// ## A moldura conferida depois de injetar
//
// Injeção em HTML por expressão regular é frágil por natureza, e o preço de usá-la é conferir
// que a moldura continua de pé. A T-159 mediu o custo de não conferir: um `[\s\S]*?` casou a
// palavra `<title>` DENTRO de um comentário de `sobre/index.html`, correu até o `</title>` do
// cabeçalho e levou junto a abertura de `<html>` e de `<head>`. A página ficou sem idioma, o
// cliente caiu no `DEFAULT_LOCALE` e re-renderizou a landing inteira em inglês por cima do HTML
// português — sem erro em lugar nenhum. Falhar é o comportamento certo: um `<html>` comido não
// aparece como erro, aparece como a página na língua errada, semanas depois.
import type { Locale } from '../i18n/locale'
import { linksDeCabecalho } from './metatags'
import type { SiteScreen } from './routes'
import { jsonLd, tagsSociais } from './social'

/** Uma página pronta para virar arquivo — o que `entries/prerender.tsx` produz por rota × idioma. */
export interface PaginaPrerenderizada {
  /** Caminho relativo à raiz do site — o mesmo que nomeia o arquivo no `dist/`. */
  caminho: string
  locale: Locale
  html: string
  titulo: string
  descricao: string
  screen: SiteScreen
  imagemAlt: string
}

/** `String.replace` com string crua interpreta `$&`, `$1`... — o HTML renderizado tem `$`. */
function trocar(fonte: string, procura: string | RegExp, valor: string): string {
  return fonte.replace(procura, () => valor)
}

function escapar(texto: string): string {
  return texto
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/**
 * O HTML de entrada do Vite, preenchido: conteúdo no `<body>`, metadados de rota no `<head>`.
 *
 * `template` é o arquivo como o build o encontra; a saída é o que vai para o `dist/`. Lança
 * quando a injeção destrói a moldura — ver o cabeçalho.
 */
export function montarPagina(
  template: string,
  pagina: PaginaPrerenderizada,
  origem: string,
): string {
  let html = template

  // 1. O conteúdo. É o item que faz o robô ver a página e o Chrome oferecer traduzir.
  const raiz = '<div id="root"></div>'
  if (!html.includes(raiz)) {
    throw new Error(`/${pagina.caminho}: não achei o \`${raiz}\` para injetar o conteúdo.`)
  }
  html = trocar(html, raiz, `<div id="root">${pagina.html}</div>`)

  // 2. Título e descrição, vindos do DICIONÁRIO (`site:meta.*`) via a tabela de rotas. Os
  //    valores estáticos que a T-158 deixou nos HTML são o que sobra se o pré-render não rodar.
  //
  //    `[^<]*` e `[^>]*`, e NUNCA `[\s\S]*?`: uma classe que não casa `<` não consegue
  //    atravessar uma tag, e atravessar uma tag foi o bug descrito no cabeçalho.
  html = trocar(html, /<title>[^<]*<\/title>/, `<title>${escapar(pagina.titulo)}</title>`)
  html = trocar(
    html,
    /<meta\s+name="description"[^>]*\/>/,
    `<meta name="description" content="${escapar(pagina.descricao)}" />`,
  )

  // 3. `canonical` + `alternate` recíprocos + `x-default` — gerados da tabela de rotas
  //    (`metatags.ts`), nunca escritos à mão em cada HTML. Foi o "à mão" que produziu o
  //    `hreflang` relativo e inerte da T-147.
  html = trocar(html, '  </head>', `${linksDeCabecalho(origem, pagina.screen, pagina.locale)}\n  </head>`)

  // 4. Preview de link (Open Graph / Twitter) e dados estruturados (T-164). Entram AQUI, e não
  //    em runtime pelo React, porque nenhum dos robôs que os consomem executa JavaScript — é o
  //    pré-render que torna esta parte possível.
  const social = { ...pagina, origem }
  html = trocar(html, '  </head>', `${tagsSociais(social)}\n  </head>`)
  html = trocar(html, '  </head>', `${jsonLd(social)}\n  </head>`)

  for (const exigido of moldura(pagina, origem)) {
    if (!html.includes(exigido)) {
      throw new Error(`/${pagina.caminho}: a injeção destruiu a estrutura — faltou \`${exigido}\`.`)
    }
  }

  return html
}

/** O que precisa continuar existindo depois de injetar. Uma lista, para poder ser lida. */
function moldura(pagina: PaginaPrerenderizada, origem: string): readonly string[] {
  return [
    '<html lang="',
    '<head>',
    '</head>',
    `<title>${escapar(pagina.titulo)}</title>`,
    `<link rel="canonical" href="${origem}/${pagina.caminho}" />`,
    'hreflang="x-default"',
    `<meta property="og:image" content="${origem}/img/og.jpg" />`,
    '"@type": "SoftwareApplication"',
  ]
}
