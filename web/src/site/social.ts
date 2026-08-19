// Open Graph, Twitter Card e dados estruturados (T-164, SPEC-026 §Escopo).
//
// ## Por que existe
//
// O `<title>` normal não alimenta preview de link. WhatsApp, Instagram, LinkedIn, Telegram,
// Slack e Discord leem **Open Graph** — e sem ele o link do produto aparece como uma caixa
// cinza, sem título e sem imagem. É o canal que motiva a task: no Brasil, app de treino se
// espalha em grupo de WhatsApp antes de se espalhar na busca.
//
// **Nada disto funcionaria sem a T-159.** Nenhum desses robôs executa JavaScript; uma tag de OG
// escrita em runtime pelo React seria invisível para todos eles. É o pré-render que torna esta
// task possível — e é por isso que ela depende dele no BACKLOG.
//
// ## A regra que governa os dados estruturados
//
// Só entra o que é **verdade verificável**. Nada de `aggregateRating`, `offers`, contagem de
// downloads ou prêmio — são os campos que mais "rendem" no resultado de busca e são exatamente
// os que o produto ainda não tem. É a mesma doutrina do `--` da SPEC-014 ("a célula existe no
// design, o dado ainda não"), aqui com um agravante: dado estruturado inventado é violação de
// política do Google e derruba o rich result inteiro, não só o campo mentiroso.
import type { Locale } from '../i18n/locale'
import { LOCALES } from '../i18n/locale'
import { urlAbsoluta } from './metatags'
import type { SiteScreen } from './routes'

/** O arquivo é ARTEFATO de `scripts/og-image.html` — ver o cabeçalho daquele arquivo. */
const IMAGEM = '/img/og.jpg'
const IMAGEM_LARGURA = '1200'
const IMAGEM_ALTURA = '630'

/**
 * `og:locale` quer `idioma_TERRITÓRIO`, não a tag BCP-47 do `<html lang>`.
 *
 * `pt-BR` → `pt_BR` é direto. `en` não tem território, e `en_US` é o default do formato — o
 * mapa é explícito para a escolha ficar visível quando um terceiro idioma entrar, em vez de
 * uma substituição de `-` por `_` que erra em silêncio.
 */
const OG_LOCALE: Record<Locale, string> = { 'pt-BR': 'pt_BR', en: 'en_US' }

export interface DadosDaPagina {
  origem: string
  screen: SiteScreen
  locale: Locale
  titulo: string
  descricao: string
  imagemAlt: string
}

function meta(propriedade: string, conteudo: string): string {
  return `    <meta property="${propriedade}" content="${escaparAtributo(conteudo)}" />`
}

function metaNome(nome: string, conteudo: string): string {
  return `    <meta name="${nome}" content="${escaparAtributo(conteudo)}" />`
}

function escaparAtributo(texto: string): string {
  return texto.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;')
}

/** As tags de preview de link, prontas para o `<head>`. */
export function tagsSociais(dados: DadosDaPagina): string {
  const { origem, screen, locale, titulo, descricao, imagemAlt } = dados
  const url = urlAbsoluta(origem, screen, locale)
  const imagem = origem + IMAGEM

  return [
    meta('og:type', 'website'),
    meta('og:site_name', 'Digital Fit'),
    meta('og:url', url),
    meta('og:title', titulo),
    meta('og:description', descricao),
    meta('og:locale', OG_LOCALE[locale]),
    // As outras línguas em que ESTA página existe — o irmão social do `hreflang` da T-160.
    ...LOCALES.filter((outro) => outro !== locale).map((outro) =>
      meta('og:locale:alternate', OG_LOCALE[outro]),
    ),
    meta('og:image', imagem),
    meta('og:image:width', IMAGEM_LARGURA),
    meta('og:image:height', IMAGEM_ALTURA),
    meta('og:image:alt', imagemAlt),
    // `summary_large_image`: a arte é 1200×630 e o card pequeno a cortaria no meio.
    metaNome('twitter:card', 'summary_large_image'),
    metaNome('twitter:title', titulo),
    metaNome('twitter:description', descricao),
    metaNome('twitter:image', imagem),
    metaNome('twitter:image:alt', imagemAlt),
  ].join('\n')
}

/**
 * `SoftwareApplication` + `Organization`, num grafo só.
 *
 * `HealthApplication` é a categoria do schema.org que corresponde ao produto. `operatingSystem:
 * Web` porque é o que ele é — não há binário para instalar, e declarar `Android`/`iOS` seria a
 * primeira mentira de uma ladeira. Ver a regra no cabeçalho deste arquivo sobre o que NÃO entra.
 */
export function jsonLd(dados: DadosDaPagina): string {
  const { origem, screen, locale, descricao } = dados

  const grafo = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'SoftwareApplication',
        '@id': `${origem}/#app`,
        name: 'Digital Fit',
        url: urlAbsoluta(origem, screen, locale),
        description: descricao,
        applicationCategory: 'HealthApplication',
        operatingSystem: 'Web',
        inLanguage: locale,
        publisher: { '@id': `${origem}/#org` },
      },
      {
        '@type': 'Organization',
        '@id': `${origem}/#org`,
        name: 'Digital Fit',
        url: origem,
        logo: origem + IMAGEM,
      },
    ],
  }

  // `<` vira `<`: sem isto, um `</script>` dentro de qualquer texto fecharia o bloco cedo
  // e o resto do JSON viraria HTML. É a única forma de injeção que este arquivo pode sofrer.
  const json = JSON.stringify(grafo, null, 2).replace(/</g, '\\u003c')

  return `    <script type="application/ld+json">\n${json}\n    </script>`
}
