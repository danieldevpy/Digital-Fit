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
//
// ## Rotas que vêm do banco (T-165)
//
// Até aqui toda rota era escrita à mão aqui dentro, e a identidade de uma rota era uma tela:
// `'index'`, `'sobre'`. As páginas por exercício quebram isso — são N rotas que saem do
// catálogo (`exercicios.json`), e o mesmo componente serve todas. A identidade passou a ser um
// **id**: `'exercicio/squat'`, com o slug TÉCNICO depois da barra.
//
// Técnico, e não o endereço público, por uma razão que decide: o endereço é traduzido
// (`/exercicios/agachamento/` × `/en/exercises/squat/`), então usá-lo como identidade faria a
// mesma página ter duas identidades e o `hreflang` não teria como parear as duas. O id é o que
// não muda com o idioma; o caminho é o que muda.
//
// Manter o id como uma STRING (e não um par `{tela, slug}`) é deliberado: `metatags.ts`,
// `descoberta.ts`, `social.ts` e `shell/origins.ts` recebem uma rota e devolvem URL, e nenhum
// deles precisa saber que existem rotas dinâmicas. A alternativa espalharia o parâmetro por
// quatro módulos para servir a um só.
import type { TKey } from '../i18n'
import { LOCALES, type Locale } from '../i18n/locale'
import { EXERCICIOS_PUBLICOS, exercicioPorEndereco, type ExercicioPublico } from './exercicios'

/** O prefixo do id de uma rota de exercício. `exercicio/squat` — o slug é o TÉCNICO. */
const PREFIXO_DE_EXERCICIO = 'exercicio/'

export type SiteScreen =
  | 'index'
  | 'sobre'
  | 'nao_encontrada'
  | `${typeof PREFIXO_DE_EXERCICIO}${string}`

/**
 * O prefixo de cada idioma no caminho. `pt-BR` é a fonte e mora na raiz; os outros ganham
 * segmento próprio — as mesmas duas URLs que a SPEC-025 §Escopo já declarava (`/` e `/en/`),
 * agora escritas num lugar só.
 */
const PREFIXO_DE_LOCALE: Record<Locale, string> = { 'pt-BR': '', en: 'en/' }

/** Valores que preenchem um título/descrição de template (`{nome}`) — só rota dinâmica usa. */
export type ParamsDaRota = Record<string, string>

export interface Rota {
  readonly screen: SiteScreen
  /** O caminho DEPOIS do prefixo de idioma, com barra no fim. A landing é `''`. */
  readonly slug: Record<Locale, string>
  readonly titulo: TKey
  readonly descricao: TKey
  /**
   * O que preenche `{nome}` no título e na descrição, quando eles são template — **por idioma**.
   *
   * É assim que a página de exercício mantém o texto no DICIONÁRIO — cobrado pelo `tsc` nas
   * duas línguas — e ainda assim fala de um exercício específico. O conteúdo vem do banco, a
   * frase que o embrulha não.
   *
   * Por idioma, e não um valor só: o nome do exercício também é traduzido. Um `params` único
   * poria "Agachamento" dentro da moldura inglesa — meia página em cada língua, que é
   * exatamente o modo de falha que a SPEC-025 §Escopo existe para não repetir.
   */
  readonly params?: Readonly<Record<Locale, ParamsDaRota>>
  /**
   * Entra no `sitemap.xml` e ganha `hreflang` (T-160/T-163)?
   *
   * A 404 não: ela não é uma página que existe, é a resposta para uma que não existe. Declarar
   * isso aqui — e não como exceção espalhada em cada consumidor — é o ponto da tabela.
   */
  readonly indexavel: boolean
  /**
   * De onde sai o HTML de entrada desta rota no build.
   *
   * `null` = tem `index.html` próprio, declarado em `ENTRADAS_DO_BUILD` (`vite.config.ts`).
   * Uma tela = o pré-render **clona** o entry já construído daquela tela, no mesmo idioma, e
   * escreve o arquivo novo.
   *
   * Existe porque entry do Rollup precisa ser um arquivo real em disco: N páginas de exercício
   * exigiriam N `index.html` versionados e idênticos, gerados por script e commitados — lixo
   * que envelhece. Clonar no pré-render usa o entry que o Vite já preencheu com os `<script>`
   * dos assets com hash, então a página nova nasce com o mesmo bundle e o mesmo CSS.
   */
  readonly molde: SiteScreen | null
}

/** As rotas escritas à mão — as que não dependem de nenhum dado. */
const ROTAS_ESTATICAS: readonly Rota[] = [
  {
    screen: 'index',
    slug: { 'pt-BR': '', en: '' },
    titulo: 'site:meta.index.title',
    descricao: 'site:meta.index.description',
    indexavel: true,
    molde: null,
  },
  {
    screen: 'sobre',
    slug: { 'pt-BR': 'sobre/', en: 'about/' },
    titulo: 'site:meta.about.title',
    descricao: 'site:meta.about.description',
    indexavel: true,
    molde: null,
  },
  {
    screen: 'nao_encontrada',
    slug: { 'pt-BR': '404.html', en: '404.html' },
    titulo: 'site:meta.not_found.title',
    descricao: 'site:meta.not_found.description',
    indexavel: false,
    molde: null,
  },
]

/** O segmento de pasta das páginas de exercício, por idioma — traduzido, como todo slug daqui. */
const PASTA_DE_EXERCICIOS: Record<Locale, string> = { 'pt-BR': 'exercicios', en: 'exercises' }

export function idDaRotaDeExercicio(slugTecnico: string): SiteScreen {
  return `${PREFIXO_DE_EXERCICIO}${slugTecnico}`
}

/** O slug técnico dentro de um id de rota, ou `undefined` se a rota não for de exercício. */
export function slugDoExercicioNaRota(screen: SiteScreen): string | undefined {
  return screen.startsWith(PREFIXO_DE_EXERCICIO)
    ? screen.slice(PREFIXO_DE_EXERCICIO.length)
    : undefined
}

function rotaDoExercicio(exercicio: ExercicioPublico): Rota {
  const slug = {} as Record<Locale, string>
  const params = {} as Record<Locale, ParamsDaRota>
  for (const locale of LOCALES) {
    slug[locale] = `${PASTA_DE_EXERCICIOS[locale]}/${exercicio.por_idioma[locale].url_slug}/`
    params[locale] = { nome: exercicio.por_idioma[locale].nome }
  }

  return {
    screen: idDaRotaDeExercicio(exercicio.slug),
    slug,
    // Título e descrição são TEMPLATE no dicionário, preenchidos com o nome vindo do banco.
    // É o que mantém a frase sob o portão do `tsc` (existe nas duas línguas) sem congelar o
    // conteúdo em código — e é a distinção curado × traduzido da SPEC-026 em uma linha: a
    // moldura é curada, o miolo é do painel.
    titulo: 'site:meta.exercise.title',
    descricao: 'site:meta.exercise.description',
    params,
    indexavel: true,
    // Clonam o entry de `sobre` do próprio idioma: mesma casca, mesmo bundle, mesmo CSS.
    molde: 'sobre',
  }
}

/**
 * A tabela inteira: o que é escrito à mão mais o que vem do catálogo.
 *
 * As rotas de exercício entram **depois** das estáticas de propósito: `parseSitePath` percorre
 * esta lista, e uma pasta de exercício nunca colide com `sobre/` — mas a ordem estável mantém o
 * `sitemap.xml` com diff limpo entre builds.
 */
export const ROTAS: readonly Rota[] = [
  ...ROTAS_ESTATICAS,
  ...EXERCICIOS_PUBLICOS.map(rotaDoExercicio),
]

/** As rotas que o buscador deve conhecer — o que a T-160 e a T-163 percorrem. */
export const ROTAS_INDEXAVEIS: readonly Rota[] = ROTAS.filter((rota) => rota.indexavel)

/** As rotas com `index.html` próprio no build — as que `ENTRADAS_DO_BUILD` precisa listar. */
export const ROTAS_COM_ENTRY: readonly Rota[] = ROTAS.filter((rota) => rota.molde === null)

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

  return { screen: rota?.screen ?? paginaDeExercicio(comBarra, locale) ?? 'nao_encontrada', locale }
}

/**
 * `/exercicios/agachamento/` → `exercicio/squat`, se esse endereço existir NESTE idioma.
 *
 * Separado da busca linear acima porque a pergunta é outra: lá se compara caminho com caminho,
 * aqui se traduz um endereço público de volta para o slug técnico. E é por idioma de propósito
 * — `/exercicios/squat/` (pasta portuguesa, endereço inglês) **não** existe e deve dar 404, em
 * vez de responder 200 com a página certa em duas URLs. Duas URLs para a mesma página é
 * conteúdo duplicado, que é exatamente o que o `canonical` da T-160 existe para evitar; deixar
 * o roteador aceitar as duas o desmentiria.
 */
function paginaDeExercicio(comBarra: string, locale: Locale): SiteScreen | undefined {
  const partes = comBarra.split('/').filter((parte) => parte !== '')
  if (partes.length !== 2 || partes[0] !== PASTA_DE_EXERCICIOS[locale]) return undefined

  const exercicio = exercicioPorEndereco(partes[1]!, locale)
  return exercicio ? idDaRotaDeExercicio(exercicio.slug) : undefined
}
