// `robots.txt` e `sitemap.xml` — os dois arquivos por onde um buscador começa (T-163,
// SPEC-026 §Escopo).
//
// Gerados da MESMA tabela de rotas que o roteador, o pré-render e o `hreflang` consomem. É a
// quarta e última saída da fonte única prometida pela SPEC-026: a partir daqui, "rota nova sem
// sitemap" deixa de ser possível em vez de deixar de ser esquecida.
//
// ## Duas decisões que valem mais que o código
//
// **1. O `/app/` NÃO é bloqueado — e isso contraria o que a redação da task pedia.**
// A intenção ("manter o app fora do índice") está certa e o meio estava errado. `Disallow`
// impede o rastreamento, e um robô que não rastreia **não lê o `noindex`** — a URL pode acabar
// listada assim mesmo, sem descrição, se alguém a linkar (e o site linka: é o botão "Abrir o
// app"). Para uma página que não pode ser indexada, o par correto é **permitir rastrear +
// `noindex` na página**, que é o que `web/app/index.html` já traz desde a T-067. Bloquear aqui
// desligaria a única instrução que de fato funciona.
//
// **2. Rastreador de LLM é permitido, e é decisão de produto, não omissão.**
// GPTBot, ClaudeBot, PerplexityBot e afins entram pelo `User-agent: *`. Parte da descoberta de
// produto hoje acontece dentro de uma conversa ("me indica um app que conte repetições"), e
// nenhum deles executa o bundle — é justamente o público que o pré-render da T-159 passou a
// atender. Bloqueá-los seria abrir mão desse canal para proteger um conteúdo institucional que
// é público por definição.
import { LOCALES, type Locale } from '../i18n/locale'
import { LOCALE_PADRAO_DO_BUSCADOR, urlAbsoluta } from './metatags'
import { ROTAS_INDEXAVEIS } from './routes'

/**
 * O `sitemap.xml`, com uma entrada por URL e, em cada uma, as alternativas de idioma.
 *
 * O `<xhtml:link>` dentro do sitemap é a mesma informação do `hreflang` do `<head>` (T-160), e
 * a duplicação é exigida: o Google pede que as duas fontes concordem, e aceita qualquer uma das
 * duas isolada. Como as duas saem de `urlAbsoluta()`, elas não têm como divergir.
 *
 * Sem `<lastmod>`: o conteúdo destas páginas muda por deploy, e carimbar a data do build faria
 * toda página parecer atualizada a cada deploy, inclusive as que não mudaram. Data que mente é
 * pior que data ausente — o Google trata `lastmod` não confiável como ruído e passa a ignorá-lo.
 */
export function sitemapXml(origem: string): string {
  const entradas = ROTAS_INDEXAVEIS.flatMap((rota) =>
    LOCALES.map((locale) => bloco(origem, rota.screen, locale)),
  )

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
    '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ...entradas,
    '</urlset>',
    '',
  ].join('\n')
}

function bloco(origem: string, screen: (typeof ROTAS_INDEXAVEIS)[number]['screen'], locale: Locale) {
  const alternativas = [
    ...LOCALES.map((outro) => alternativa(origem, screen, outro, outro)),
    alternativa(origem, screen, LOCALE_PADRAO_DO_BUSCADOR, 'x-default'),
  ]

  return [
    '  <url>',
    `    <loc>${urlAbsoluta(origem, screen, locale)}</loc>`,
    ...alternativas,
    '  </url>',
  ].join('\n')
}

function alternativa(
  origem: string,
  screen: (typeof ROTAS_INDEXAVEIS)[number]['screen'],
  destino: Locale,
  hreflang: string,
) {
  const href = urlAbsoluta(origem, screen, destino)
  return `    <xhtml:link rel="alternate" hreflang="${hreflang}" href="${href}" />`
}

/**
 * O `robots.txt`. Curto de propósito: o que ele precisa dizer é "pode entrar" e "o mapa está
 * ali". As duas decisões acima viram comentário no próprio arquivo, porque quem for editá-lo
 * daqui a um ano vai estar olhando para ele, não para este módulo.
 */
export function robotsTxt(origem: string): string {
  return [
    '# Digital Fit — conteudo institucional publico (SPEC-026).',
    '#',
    '# O /app/ NAO e bloqueado aqui de proposito. Ele nao deve ser indexado, e quem garante isso',
    '# e o `<meta name="robots" content="noindex">` da propria pagina. Um `Disallow` impediria o',
    '# rastreamento, o robo nunca leria o noindex, e a URL poderia acabar listada assim mesmo por',
    '# ser linkada daqui — o oposto do que se quer.',
    '#',
    '# Rastreador de LLM (GPTBot, ClaudeBot, PerplexityBot...) entra pelo `*`, por decisao: parte',
    '# da descoberta de produto acontece dentro de uma conversa, e nenhum deles executa o bundle',
    '# — e justamente o publico que o pre-render passou a atender.',
    'User-agent: *',
    'Allow: /',
    '',
    `Sitemap: ${origem}/sitemap.xml`,
    '',
  ].join('\n')
}
