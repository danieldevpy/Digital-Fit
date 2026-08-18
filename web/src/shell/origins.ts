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
 * `href` da versão do SITE em cada idioma (T-153): `/` é o pt-BR e `/en/` é o inglês — as
 * mesmas duas URLs que os `hreflang` de `index.html`/`en/index.html` declaram uma à outra.
 *
 * O `hash` da tela atual viaja junto: quem está em `#/sobre` e troca de idioma continua em
 * Sobre, na outra língua. Perder a tela na troca seria mandar a pessoa para a home como preço
 * de ter escolhido o idioma.
 *
 * Não passa pelo `siteHref` de propósito: aquele responde "onde mora o site", e esta pergunta é
 * "onde mora a versão EM TAL LÍNGUA do site" — que é um subcaminho dele, não outro host.
 */
export function siteLocaleHref(locale: 'pt-BR' | 'en', hash = ''): string {
  const base = locale === 'en' ? `${SITE_BASE}en/` : SITE_BASE
  return hrefFrom(base, hash)
}
