// Detecção, normalização e persistência do idioma (SPEC-025 §3.3, plano PLANO-I18N.md §3.3).
//
// Mesma casa e mesmo motivo de `session/preferences.ts`: fica no aparelho, não exige conta — a
// SPEC-011 garante treinar sem conta, e uma preferência que só valesse depois de cadastrar seria
// punição por não se cadastrar. Por isso o padrão é o mesmo: função pura testável (`resolveLocale`)
// separada da leitura de armazenamento (`storedLocale`), com o mesmo try/catch para o Safari em
// navegação privada, onde `localStorage` LANÇA em vez de simplesmente faltar.

export type Locale = 'pt-BR' | 'en'

const LOCALE_KEY = 'digitalfit.locale'

/**
 * `'en'`, não `'pt-BR'`, de propósito (SPEC-025 §3.3): um navegador brasileiro já cai na regra
 * de `navigator.languages` antes de chegar aqui. `en` é a resposta certa para "não sei quem é
 * você" — o mesmo raciocínio que fez o produto não usar GeoIP.
 */
export const DEFAULT_LOCALE: Locale = 'en'

export function isLocale(valor: unknown): valor is Locale {
  return valor === 'pt-BR' || valor === 'en'
}

/**
 * Casa uma tag de idioma de navegador (`pt`, `pt-PT`, `en-US`, `fr-FR`, ...) por PREFIXO com um
 * locale suportado: `pt*` → `pt-BR` (uma única variante de português por ora — a SPEC-025 deixa
 * um terceiro idioma para quando houver motivo de produto, não é este o lugar); `en*` → `en`.
 * Sem casar, `null` — quem chama decide o próximo passo da cadeia.
 */
export function matchLocale(tag: string): Locale | null {
  const prefixo = tag.slice(0, 2).toLowerCase()
  if (prefixo === 'pt') return 'pt-BR'
  if (prefixo === 'en') return 'en'
  return null
}

/**
 * `resolveLocale()` pura (SPEC-025 §3.3, critério 4 da T-142): recebe as duas fontes como
 * parâmetro em vez de ler `window` sozinha — o mesmo motivo de a análise de exercício não ler
 * relógio: testável com fixtures, sem navegador, sem mock de global.
 *
 * Ordem de prioridade:
 *   1. `stored`             → escolha explícita (localStorage), vence sempre
 *   2. `navegador`          → primeiro idioma de `navigator.languages` que casar por prefixo
 *   3. `DEFAULT_LOCALE`     → `'en'`, fallback global
 */
export function resolveLocale(stored: string | null, navegador: readonly string[] = []): Locale {
  if (isLocale(stored)) return stored
  for (const tag of navegador) {
    const casado = matchLocale(tag)
    if (casado) return casado
  }
  return DEFAULT_LOCALE
}

/** A leitura de armazenamento, separada da resolução pura — mesmo padrão de `preferences.ts`. */
function lerStorage(): string | null {
  try {
    return window.localStorage.getItem(LOCALE_KEY)
  } catch {
    return null
  }
}

function gravarStorage(locale: Locale): void {
  try {
    window.localStorage.setItem(LOCALE_KEY, locale)
  } catch {
    // Sem armazenamento (Safari privado): vale pela sessão atual e pronto — mesma resposta de
    // `setCountdownPreference`.
  }
}

/**
 * Os idiomas do navegador, defensivo contra ambientes sem página de verdade (SSR, testes,
 * Node). A checagem é em `window`, não em `navigator`: a partir do Node 21 o runtime expõe um
 * `navigator` global próprio (`navigator.language` vem do locale do SISTEMA OPERACIONAL, não do
 * usuário) mesmo sem `window` nenhum — em Node puro isso faria o boot "adivinhar" o idioma pelo
 * locale da máquina que roda o processo, o mesmo raciocínio que já tirou GeoIP de cogitação
 * (SPEC-025 §3.3). `navigator` só é um sinal de idioma do VISITANTE quando existe um `window`
 * por trás dele — sem `window`, não há navegador de verdade para perguntar.
 */
function idiomasDoNavegador(): readonly string[] {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return []
  return navigator.languages ?? (navigator.language ? [navigator.language] : [])
}

/** Locale ativo no boot: lê o armazenamento real e `navigator.languages` de verdade. */
export function detectLocale(): Locale {
  return resolveLocale(lerStorage(), idiomasDoNavegador())
}

/** Escolha explícita (troca de idioma nas configurações, T-153) — persiste para o próximo boot. */
export function persistLocale(locale: Locale): void {
  gravarStorage(locale)
}
