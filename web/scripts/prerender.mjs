// Pré-render do SITE (T-159, SPEC-026 §Escopo · ADR-012).
//
// Roda DEPOIS das duas passadas do `vite build`: a normal, que produz os HTML e os bundles do
// navegador em `dist/`, e a de `--ssr`, que compila `src/entries/prerender.tsx` para
// `dist-ssr/`. Aqui as duas se encontram — o HTML de cada rota é gerado em Node e injetado no
// `<body>` do arquivo correspondente.
//
// ## O que este arquivo compra
//
// O `<body>` do site era `<div id="root"></div>`. Quem não executa JavaScript — o preview do
// WhatsApp, o do LinkedIn, os rastreadores de LLM — via uma página em branco; o Google via
// conteúdo só na segunda onda de renderização. E o Chrome, que decide oferecer "Traduzir esta
// página" analisando o texto do HTML da RESPOSTA, não tinha idioma para detectar: a camada
// "Traduzir" da SPEC-026 estava desligada sem ninguém ter decidido isso.
//
// ## O que este arquivo deliberadamente NÃO faz
//
// **Decidir qualquer coisa.** Desde a T-166 ele lê arquivo, chama funções puras e escreve
// arquivo — nada mais. Quem monta o HTML de uma página é `src/site/paginaGerada.ts`, quem monta
// o `<head>` é `metatags.ts`/`social.ts`, e quem monta o mapa é `descoberta.ts`; todas saem da
// mesma tabela de rotas (`src/site/routes.ts`) e todas são cobradas por teste sem build. A
// fronteira existe porque o modo de falha desta frente é o silêncio: o `hreflang` escrito à mão
// pela T-147 ficou inerte por meses sem nada acusar, e o que só o build sabe fazer é o que
// ninguém consegue testar.
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..')
const DIST = join(RAIZ, 'dist')

/**
 * A origem pública do site (T-160). **`VITE_SITE_ORIGIN`, e não `VITE_SITE_URL`.**
 *
 * As duas parecem a mesma coisa e não são. `VITE_SITE_URL` responde "qual a base para um link
 * de um bundle para o outro" e é VAZIA no deploy de domínio único, porque ali o site mora em
 * `/` e o caminho relativo basta. `canonical` e `hreflang` fazem outra pergunta — "em que
 * origem pública esta página vai ser servida" —, e essa tem resposta nos dois deploys.
 * Reaproveitar a primeira deixaria metade dos deploys sem anotação nenhuma.
 *
 * Sem ela o build **para**, com uma frase que diz o que fazer. A T-159 omitia em silêncio
 * quando não sabia; silêncio é exatamente como o `hreflang` relativo da T-147 sobreviveu meses.
 */
const ORIGEM_BRUTA = process.env.VITE_SITE_ORIGIN

async function main() {
  const { renderizarPaginas, montarPagina, exigirOrigem, robotsTxt, sitemapXml } = await import(
    join(RAIZ, 'dist-ssr', 'prerender.js')
  )

  const origem = exigirOrigem(ORIGEM_BRUTA)
  const paginas = renderizarPaginas()

  for (const pagina of paginas) {
    const arquivo = join(DIST, pagina.caminho, 'index.html')
    const template = await readFile(arquivo, 'utf8')

    // Toda a decisão está aqui dentro, e é testada sem build (`src/site/paginaGerada.test.ts`):
    // conteúdo no `<body>`, título e descrição do dicionário, `canonical`/`hreflang`/`x-default`
    // da tabela de rotas, Open Graph e JSON-LD — mais a conferência da moldura depois de
    // injetar. Se ela lançar, o build para, que é o comportamento certo.
    let html
    try {
      html = montarPagina(template, pagina, origem)
    } catch (erro) {
      throw new Error(`${arquivo}: ${erro.message}`, { cause: erro })
    }

    await writeFile(arquivo, html)
    console.log(`[prerender] /${pagina.caminho} (${pagina.locale}) — ${pagina.html.length} B`)
  }

  // `sitemap.xml` e `robots.txt` (T-163) — a quarta e última saída da tabela de rotas. Saem
  // daqui, e não de arquivos em `public/`, exatamente para não serem uma quinta lista que
  // precisa concordar com as outras quatro à mão.
  await writeFile(join(DIST, 'sitemap.xml'), sitemapXml(origem))
  await writeFile(join(DIST, 'robots.txt'), robotsTxt(origem))
  console.log('[prerender] sitemap.xml + robots.txt')

  console.log(`[prerender] ${paginas.length} páginas em ${origem}`)
}

await main()
