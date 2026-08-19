// Entry do PRÉ-RENDER (T-159, SPEC-026 §Escopo · ADR-012).
//
// O par de `entries/site.tsx`: o mesmo `SiteApp`, montado no build em vez de no navegador. Este
// arquivo não é servido a ninguém — ele é compilado por `vite build --ssr` para `dist-ssr/` e
// consumido pelo `scripts/prerender.mjs`, que injeta o resultado nos HTML do `dist/`.
//
// ## Por que isto existe
//
// Até aqui o `<body>` do site era `<div id="root"></div>` e mais nada. Duas consequências, e a
// segunda quase ninguém enxerga (SPEC-026 §Notas técnicas):
//
//   1. O robô não lê. O Google renderiza JavaScript, mas na segunda onda e com atraso; o
//      WhatsApp, o LinkedIn e os rastreadores de LLM não renderizam nada.
//   2. **O Chrome não oferece traduzir.** Ele decide analisando o texto do HTML da RESPOSTA —
//      sem texto, não há idioma para detectar. Ou seja: o pré-render é o que liga a camada
//      "Traduzir" da SPEC-026, que é de graça em ~130 línguas e que o site desligava sem querer.
//
// ## Por que aqui e não num framework
//
// ADR-012, resumida: a superfície que precisa de SEO é ~2% do frontend, a fonte de conteúdo é o
// Postgres e não o sistema de arquivos, e o encanamento de build atual foi medido e é caro de
// refazer. O substituto cabe neste arquivo e num script.
import { renderToString } from 'react-dom/server'
import { t } from '../i18n'
import { LOCALES } from '../i18n/locale'
import { useI18nStore } from '../i18n/store'
import { SiteApp } from '../site/SiteApp'
import type { PaginaPrerenderizada } from '../site/paginaGerada'
import { caminhoDaRota, ROTAS_INDEXAVEIS } from '../site/routes'

// Reexportadas para o `scripts/prerender.mjs`: as funções são puras e testadas em
// `site/metatags.test.ts`; quem conhece o ambiente (a variável de build com a origem) é o
// script, não o bundle. A fronteira é a mesma de sempre neste projeto — decisão no código
// testável, leitura do mundo na borda.
export { exigirOrigem } from '../site/metatags'
export { robotsTxt, sitemapXml } from '../site/descoberta'

// A montagem do HTML final é `site/paginaGerada.ts` — pura, e por isso coberta pelo portão da
// T-166 (`paginaGerada.test.ts`) sem precisar de build. Aqui ela é só reexportada, para o
// script de build ter uma porta de entrada só.
//
// O TIPO da página fica de fora desta linha de propósito: quem o consome é o teste, que importa
// de `site/paginaGerada` direto, e o `scripts/prerender.mjs` é JavaScript e não vê tipo nenhum.
// Reexportá-lo aqui custava cinco avisos de `react-refresh` — o plugin lê um nome capitalizado
// num `export { ... }` como componente e passa a cobrar do arquivo inteiro a regra de módulo de
// componente.
export { montarPagina } from '../site/paginaGerada'

/**
 * Todas as páginas indexáveis, em todos os idiomas — a tabela de rotas percorrida.
 *
 * A 404 fica de fora, e é decisão e não esquecimento: ela é a resposta a uma URL que não existe,
 * então não há idioma a deduzir dela (`site/NotFoundScreen.tsx`). Sem idioma não há o que
 * pré-renderizar, e o cliente a monta na preferência do aparelho.
 *
 * O store de idioma é ajustado antes de cada render porque ele é um singleton de módulo e o
 * `t()` lê dele. Render é síncrono, então o par (`setState`, `renderToString`) nunca se
 * intercala — a alternativa seria um `t()` com locale explícito, que espalharia o parâmetro por
 * toda a árvore para servir só a este arquivo.
 */
export function renderizarPaginas(): PaginaPrerenderizada[] {
  const paginas: PaginaPrerenderizada[] = []

  for (const rota of ROTAS_INDEXAVEIS) {
    for (const locale of LOCALES) {
      useI18nStore.setState({ locale })

      paginas.push({
        caminho: caminhoDaRota(rota.screen, locale),
        locale,
        html: renderToString(<SiteApp screen={rota.screen} />),
        titulo: t(rota.titulo),
        descricao: t(rota.descricao),
        screen: rota.screen,
        imagemAlt: t('site:meta.og_image_alt'),
      })
    }
  }

  return paginas
}
