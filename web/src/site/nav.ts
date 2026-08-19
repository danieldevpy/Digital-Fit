// Navegação do SITE — por CAMINHO desde a T-158 (SPEC-026 §Escopo).
//
// Roteador próprio, minúsculo, em vez de reaproveitar o do app: são conjuntos de rotas
// diferentes que vão morar em hosts diferentes. Compartilhar o union de rotas obrigaria cada
// bundle a conhecer as telas do outro — e a fronteira que a T-067 desenhou voltaria a vazar
// pelo tipo (ADR-010).
//
// **Não há mais `subscribe`.** Enquanto o site roteava por `#/sobre`, trocar de tela era mudar
// o fragmento e o React tinha de ouvir `hashchange`. Agora cada tela é um DOCUMENTO: o link é
// um `href` de verdade, o navegador carrega a página, e a rota não muda durante a vida do
// documento. Um `useSyncExternalStore` aqui estaria assinando um evento que não acontece.
//
// O custo é uma navegação de rede por clique, e ele é baixo e bem gasto: o bundle do site pesa
// ~8,8 kB (ADR-010) e já está em cache, não há estado de sessão para preservar, e em troca cada
// URL passa a ser um documento próprio — que é a condição para o pré-render da T-159 e para
// existir `sitemap.xml`.
import { DEFAULT_LOCALE, matchLocale } from '../i18n/locale'
import { useI18nStore } from '../i18n/store'
import { caminhoDaRota, parseSitePath, type SiteScreen } from './routes'

/** A tela deste documento. Não muda sem uma navegação, então é leitura pura. */
export function telaDoDocumento(): SiteScreen {
  return parseSitePath(window.location.pathname).screen
}

/**
 * O idioma deste documento, a partir do `<html lang>` que o entry HTML já traz (T-159).
 *
 * Vivia num efeito de módulo dentro do `SiteApp` e mudou de casa por um motivo concreto: um
 * componente que lê `document` no import não renderiza no build, e o pré-render é o que faz
 * esta página existir para o Google. Continua rodando ANTES do primeiro render — agora no
 * entry, que é o único lugar do bundle que tem direito a conhecer o navegador.
 *
 * Site por URL, app por preferência (SPEC-025 §Escopo): o `lang` é escrito estaticamente em
 * cada entry HTML, então ler o `lang` é ler a URL. `setState` direto e não `setLocale()`: a
 * escolha é desta visita, não uma preferência para gravar em `digitalfit.locale` — visitar
 * `/en/` não deve trocar o idioma com que o app abre depois.
 */
export function sincronizarLocaleDoDocumento(): void {
  const locale = matchLocale(document.documentElement.lang) ?? DEFAULT_LOCALE
  if (useI18nStore.getState().locale !== locale) useI18nStore.setState({ locale })
}

/**
 * Os `#/sobre` antigos, redirecionados (T-158).
 *
 * **Não dá para fazer isto no nginx, e a razão é a mesma que motivou a task**: o fragmento não
 * viaja no pedido HTTP. O servidor recebe `GET /` e não tem como saber que o `#/sobre` estava
 * ali — só o navegador sabe. Então o "301" desta migração é necessariamente do lado do cliente,
 * e roda antes do React montar (`entries/site.tsx`), não em `useEffect`: quem chega por um link
 * salvo deve ver a página certa, não a landing piscando antes dela.
 *
 * `location.replace` e não `history.replaceState`: uma navegação de verdade traz o DOCUMENTO
 * certo, com o `<title>`, o `canonical` e o `hreflang` daquela rota. Um `replaceState` mudaria
 * a barra de endereço e deixaria os metadados da página anterior — que é exatamente o tipo de
 * meia-correção que esta frente existe para não repetir. Também não deixa a URL velha no
 * histórico, então o botão "voltar" não devolve a pessoa ao redirecionamento.
 */
export function redirecionarHashLegado(): void {
  const alvo = TELA_POR_HASH_LEGADO[window.location.hash.replace(/\/$/, '')]
  if (alvo === undefined) return

  const { locale } = parseSitePath(window.location.pathname)
  window.location.replace(`/${caminhoDaRota(alvo, locale)}`)
}

/**
 * Só o que um dia foi endereço público. `#/` e `#` ficam de fora: já apontavam para a landing,
 * que é a página em que a pessoa já está — redirecionar seria uma volta à rede por nada.
 */
const TELA_POR_HASH_LEGADO: Readonly<Record<string, SiteScreen>> = {
  '#/sobre': 'sobre',
}
