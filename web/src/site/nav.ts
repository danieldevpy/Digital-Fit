// Navegação do SITE (T-067). Duas telas institucionais e nada mais.
//
// Roteador próprio, minúsculo, em vez de reaproveitar o do app: são conjuntos de rotas
// diferentes que vão morar em hosts diferentes. Compartilhar o union de rotas obrigaria
// cada bundle a conhecer as telas do outro — e a fronteira que a T-067 acabou de desenhar
// voltaria a vazar pelo tipo.
import { useSyncExternalStore } from 'react'

export type SiteRoute = { screen: 'index' } | { screen: 'sobre' }

export function parseSiteHash(hash: string): SiteRoute {
  const path = hash.replace(/^#\/?/, '').replace(/\/$/, '')
  return path === 'sobre' ? { screen: 'sobre' } : { screen: 'index' }
}

export function siteRouteHash(route: SiteRoute): string {
  return route.screen === 'index' ? '#/' : '#/sobre'
}

export function navigateSite(route: SiteRoute): void {
  window.location.hash = siteRouteHash(route)
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

function snapshot(): string {
  return window.location.hash
}

export function useSiteRoute(): SiteRoute {
  const hash = useSyncExternalStore(subscribe, snapshot, () => '')
  return parseSiteHash(hash)
}
