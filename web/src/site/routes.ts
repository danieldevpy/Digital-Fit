// A tabela de rotas do SITE — fonte ÚNICA (T-158, SPEC-026 §Escopo).
//
// ## Por que uma tabela, e não quatro lugares que precisam concordar
//
// Roteador, pré-render, `sitemap.xml` e `hreflang` respondem à mesma pergunta ("quais páginas
// existem, em que idiomas, com que endereço") e até aqui cada um respondia por conta própria.
// Foi essa independência que produziu o bug que abriu a Fase 8: a T-147 escreveu `hreflang` à
// mão, com `href` relativo, e a especificação exige URL absoluta — o par pt/en ficou inerte por
// meses sem nada acusar. Com uma fonte só, "rota nova sem sitemap" deixa de ser *possível* em
// vez de deixar de ser *esquecido*. É a mesma doutrina do dicionário tipado da SPEC-025: o
// portão nasce da forma do dado, não da memória de quem escreve.
//
// Esta task consome a tabela no roteador e nos links. A T-159 (pré-render), a T-160 (`hreflang`
// absoluto) e a T-163 (`sitemap.xml`) consomem a MESMA tabela — nenhuma delas volta a escrever
// caminho à mão.
//
// ## Caminho, e não fragmento
//
// Até a T-158 o site roteava por `#/sobre`. Fragmento não viaja no pedido HTTP: o servidor
// nunca o vê, e o buscador trata `/#/sobre` e `/` como a mesma página — o site inteiro tinha
// UMA URL indexável por idioma. Agora cada tela é um documento de verdade, servido do próprio
// arquivo (ver `vite.config.ts`), que é o que o pré-render vai preencher.
//
// ## Slug traduzido
//
// `/sobre/` ↔ `/en/about/`, e não `/en/sobre/`. A palavra na URL é sinal de busca — é o
// objetivo declarado da frente —, e o custo é uma entrada a mais por rota nesta tabela, que é
// justamente o lugar onde ela deve doer.
import type { TKey } from '../i18n'
import { LOCALES, type Locale } from '../i18n/locale'

export type SiteScreen = 'index' | 'sobre' | 'nao_encontrada'

/**
 * O prefixo de cada idioma no caminho. `pt-BR` é a fonte e mora na raiz; os outros ganham
 * segmento próprio — as mesmas duas URLs que a SPEC-025 §Escopo já declarava (`/` e `/en/`),
 * agora escritas num lugar só.
 */
const PREFIXO_DE_LOCALE: Record<Locale, string> = { 'pt-BR': '', en: 'en/' }

interface Rota {
  readonly screen: SiteScreen
  /** O caminho DEPOIS do prefixo de idioma, com barra no fim. A landing é `''`. */
  readonly slug: Record<Locale, string>
  readonly titulo: TKey
  readonly descricao: TKey
  /**
   * Entra no `sitemap.xml` e ganha `hreflang` (T-160/T-163)?
   *
   * A 404 não: ela não é uma página que existe, é a resposta para uma que não existe. Declarar
   * isso aqui — e não como exceção espalhada em cada consumidor — é o ponto da tabela.
   */
  readonly indexavel: boolean
}

export const ROTAS: readonly Rota[] = [
  {
    screen: 'index',
    slug: { 'pt-BR': '', en: '' },
    titulo: 'site:meta.index.title',
    descricao: 'site:meta.index.description',
    indexavel: true,
  },
  {
    screen: 'sobre',
    slug: { 'pt-BR': 'sobre/', en: 'about/' },
    titulo: 'site:meta.about.title',
    descricao: 'site:meta.about.description',
    indexavel: true,
  },
  {
    screen: 'nao_encontrada',
    slug: { 'pt-BR': '404.html', en: '404.html' },
    titulo: 'site:meta.not_found.title',
    descricao: 'site:meta.not_found.description',
    indexavel: false,
  },
]

/** As rotas que o buscador deve conhecer — o que a T-160 e a T-163 vão percorrer. */
export const ROTAS_INDEXAVEIS: readonly Rota[] = ROTAS.filter((rota) => rota.indexavel)

export function rotaDe(screen: SiteScreen): Rota {
  const rota = ROTAS.find((candidata) => candidata.screen === screen)
  if (!rota) throw new Error(`rota não declarada: ${screen}`)
  return rota
}

/**
 * O caminho de uma tela num idioma, relativo à raiz do site: `''`, `'sobre/'`, `'en/'`,
 * `'en/about/'`. Sem barra inicial de propósito — quem monta a URL final é `shell/origins.ts`,
 * que sabe se o site mora em `/` ou em `site.dominio.com`.
 */
export function caminhoDaRota(screen: SiteScreen, locale: Locale): string {
  return PREFIXO_DE_LOCALE[locale] + rotaDe(screen).slug[locale]
}

/**
 * A tela e o idioma que um `location.pathname` representa.
 *
 * Assume o site servido na RAIZ do seu host — é o que os dois deploys previstos entregam
 * (`docs/DEPLOY.md`: domínio único com o site em `/`, ou `site.dominio.com`), e é o default de
 * `normalizeBase`. Servir o site sob um subcaminho (`/site/`) não é deploy suportado hoje e
 * quebraria aqui de forma visível — que é melhor que quebrar em silêncio no `sitemap.xml`.
 *
 * Caminho desconhecido devolve `nao_encontrada`: o roteador **não** manda para a landing. Era o
 * que o `parseSiteHash` fazia, e é a versão em JavaScript do mesmo *soft 404* que o `try_files`
 * do nginx produzia — 200 com a home no lugar de "não existe" (SPEC-026 §Notas técnicas).
 */
export function parseSitePath(pathname: string): { screen: SiteScreen; locale: Locale } {
  const segmentos = pathname.split('/').filter((parte) => parte !== '')

  const prefixo = segmentos[0]
  const localeDaUrl = LOCALES.find(
    (locale) => PREFIXO_DE_LOCALE[locale] !== '' && PREFIXO_DE_LOCALE[locale] === `${prefixo}/`,
  )
  const locale: Locale = localeDaUrl ?? 'pt-BR'
  const resto = (localeDaUrl ? segmentos.slice(1) : segmentos).join('/')
  const comBarra = resto === '' ? '' : `${resto}/`

  const rota = ROTAS.find(
    (candidata) => candidata.indexavel && candidata.slug[locale] === comBarra,
  )

  return { screen: rota?.screen ?? 'nao_encontrada', locale }
}
