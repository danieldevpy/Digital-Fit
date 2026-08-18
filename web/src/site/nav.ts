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
import { caminhoDaRota, parseSitePath, type SiteScreen } from './routes'

export type SiteRoute = { screen: SiteScreen }

/** A tela deste documento. Não muda sem uma navegação, então é leitura pura. */
export function useSiteRoute(): SiteRoute {
  return { screen: parseSitePath(window.location.pathname).screen }
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
