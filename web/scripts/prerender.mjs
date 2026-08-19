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
// `hreflang` absoluto e `x-default` são da T-160; `sitemap.xml` e `robots.txt` são da T-163.
// Todos vão sair da MESMA tabela de rotas que este script consome (`src/site/routes.ts`) — é a
// fonte única da SPEC-026, e o motivo de ela existir é que o `hreflang` escrito à mão pela
// T-147 ficou inerte por meses sem nada acusar.
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

/** `String.replace` com string crua interpreta `$&`, `$1`... — o HTML renderizado tem `$`. */
function trocar(fonte, procura, valor) {
  return fonte.replace(procura, () => valor)
}

function escapar(texto) {
  return texto
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

async function main() {
  const { renderizarPaginas, linksDeCabecalho, exigirOrigem, robotsTxt, sitemapXml } =
    await import(join(RAIZ, 'dist-ssr', 'prerender.js'))

  const origem = exigirOrigem(ORIGEM_BRUTA)
  const paginas = renderizarPaginas()

  for (const pagina of paginas) {
    const arquivo = join(DIST, pagina.caminho, 'index.html')
    let html = await readFile(arquivo, 'utf8')

    // 1. O conteúdo. É o item que faz o robô ver a página e o Chrome oferecer traduzir.
    const raiz = '<div id="root"></div>'
    if (!html.includes(raiz)) throw new Error(`${arquivo}: não achei o \`${raiz}\``)
    html = trocar(html, raiz, `<div id="root">${pagina.html}</div>`)

    // 2. Título e descrição, vindos do DICIONÁRIO (`site:meta.*`) via a tabela de rotas. Os
    //    valores estáticos que a T-158 deixou nos HTML eram cópia temporária declarada; a
    //    partir daqui eles são gerados, e a duplicação acabou.
    //
    //    `[^<]*` e `[^>]*`, e NUNCA `[\s\S]*?`. O não-guloso parece equivalente e não é: o
    //    comentário de `sobre/index.html` citava a palavra `<title>`, o casamento começou LÁ,
    //    correu até o `</title>` do `<head>` e levou junto o `<html lang="pt-BR">` e a abertura
    //    do `<head>`. A página ficou sem idioma, o cliente caiu no `DEFAULT_LOCALE` e
    //    re-renderizou a landing INTEIRA em inglês por cima do HTML português — sem erro em
    //    lugar nenhum. Uma classe que não casa `<` não consegue atravessar uma tag.
    html = trocar(html, /<title>[^<]*<\/title>/, `<title>${escapar(pagina.titulo)}</title>`)
    html = trocar(
      html,
      /<meta\s+name="description"[^>]*\/>/,
      `<meta name="description" content="${escapar(pagina.descricao)}" />`,
    )

    // 3. `canonical` + `alternate` recíprocos + `x-default` — gerados da tabela de rotas
    //    (`src/site/metatags.ts`, puro e testado), nunca escritos à mão em cada HTML. Foi o
    //    "à mão" que produziu o `hreflang` relativo e inerte da T-147.
    const links = linksDeCabecalho(origem, pagina.screen, pagina.locale)
    html = trocar(html, '  </head>', `${links}\n  </head>`)

    // O invariante que teria pego o bug acima na hora. Injeção em HTML por expressão regular
    // é frágil por natureza; o preço de usá-la é conferir, a cada arquivo, que a moldura
    // continua de pé. Falhar o build é o comportamento certo: um `<html>` comido não aparece
    // como erro em lugar nenhum — aparece como a página na língua errada, semanas depois.
    const exigidos = [
      '<html lang="',
      '<head>',
      '</head>',
      `<title>${escapar(pagina.titulo)}</title>`,
      `<link rel="canonical" href="${origem}/${pagina.caminho}" />`,
      'hreflang="x-default"',
    ]
    for (const exigido of exigidos) {
      if (!html.includes(exigido)) {
        throw new Error(`${arquivo}: a injeção destruiu a estrutura — faltou \`${exigido}\``)
      }
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
