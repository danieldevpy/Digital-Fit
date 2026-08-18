// Onde mora o site e onde mora o app (T-067).
//
// SITE e APP são dois bundles separados justamente para poderem morar em hosts diferentes
// (`site.dominio.com` | `app.dominio.com`). Um `#/exercicios` cru só funciona dentro do
// próprio bundle: atravessar a fronteira exige a base do outro lado, e ela é decidida no
// BUILD (`VITE_*`), não em runtime — quem serve o app pode não ser quem serve o site, e o
// bundle do site não tem como descobrir isso sozinho.
//
// Default por caminho (`/` e `/app/`): é o deploy de hoje, um domínio só. Migrar para
// subdomínio é mexer no `.env.prod`, não no código.
import type { Locale } from '../i18n/locale'
import { caminhoDaRota, type SiteScreen } from '../site/routes'

/** Base sempre com barra no fim: é o que faz `base + '#/x'` render URL válida. */
export function normalizeBase(bruto: string | undefined, fallback: string): string {
  const valor = (bruto ?? '').trim()
  if (valor === '') return fallback
  return valor.endsWith('/') ? valor : `${valor}/`
}

/**
 * Junta base e hash. Puro de propósito: a decisão "site.dominio.com/#/preparar" tem de ser
 * testável sem subir um bundle com `VITE_APP_URL` definida.
 */
export function hrefFrom(base: string, hash: string): string {
  if (hash === '' || hash === '#') return base
  return base + (hash.startsWith('#') ? hash : `#${hash}`)
}

const SITE_BASE = normalizeBase(import.meta.env.VITE_SITE_URL, '/')
const APP_BASE = normalizeBase(import.meta.env.VITE_APP_URL, '/app/')

/** `href` para uma rota do app, visto de fora dele (site → app). */
export function appHref(hash = ''): string {
  return hrefFrom(APP_BASE, hash)
}

/** `href` para uma rota do site, visto de fora dele (app → site). */
export function siteHref(hash = ''): string {
  return hrefFrom(SITE_BASE, hash)
}

/**
 * `href` de uma tela do SITE, num idioma (T-158, SPEC-026 §Escopo).
 *
 * Sucede o `siteLocaleHref(locale, hash)` da T-153, e a troca é a task inteira em miniatura: o
 * idioma continua morando na URL, mas a TELA também passa a morar — `/sobre/` e `/en/about/`
 * são documentos, não fragmentos. Quem está em Sobre e troca de idioma continua em Sobre, como
 * antes; a diferença é que agora existe uma URL para dizer isso ao buscador.
 *
 * O caminho vem da tabela de rotas (`site/routes.ts`), única fonte — este arquivo só sabe ONDE
 * o site mora (`/` ou `site.dominio.com`, decidido no build pela `VITE_SITE_URL`), nunca quais
 * páginas ele tem. É a mesma separação que já existia entre `siteHref` e o antigo
 * `siteLocaleHref`, agora com a metade de cima num lugar só.
 */
export function siteRouteHref(screen: SiteScreen, locale: Locale): string {
  return SITE_BASE + caminhoDaRota(screen, locale)
}
