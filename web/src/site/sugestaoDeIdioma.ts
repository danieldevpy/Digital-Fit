// A decisão de sugerir a outra versão do site (T-161, SPEC-026 §Escopo — camada "Chegar certo").
//
// ## O problema que isto resolve, e o que ele NÃO pode ser
//
// A camada "Achar" (T-160) cuida de quem vem da busca: o `hreflang` e o `x-default` mandam o
// buscador para a URL certa. Sobra quem NÃO veio da busca — quem digitou o domínio, quem clicou
// num link compartilhado. Essa pessoa cai em `/`, que é português, seja ela quem for.
//
// **A saída óbvia é proibida.** Redirecionar `/` por `Accept-Language` ou por IP faria o
// Googlebot — que rastreia dos Estados Unidos — ver só a versão inglesa, e a portuguesa sairia
// do índice. É a invariante escrita da SPEC-026: nenhuma das três camadas redireciona ninguém.
// O que sobra é sugerir, e deixar a pessoa decidir.
//
// ## As três regras
//
//   1. **Sugere-se o que o APP daria a essa pessoa.** `detectLocale()` já responde isso
//      (`localStorage` → `navigator.languages` → `DEFAULT_LOCALE`), e reusá-lo tem uma
//      consequência que vale ouro: quem já escolheu um idioma explicitamente no app não recebe
//      sugestão nenhuma no site. A escolha explícita continua vencendo, como em toda a SPEC-025.
//   2. **Um francês recebe sugestão de inglês.** `matchLocale('fr')` é `null` e a cadeia cai em
//      `DEFAULT_LOCALE` — que é `en`, o mesmo destino do `x-default`. É o caso que motivou a
//      frente, e ele funciona por construção, não por regra especial.
//   3. **Dispensou, acabou.** Sem isso o aviso vira faixa de cookie: aparece toda visita, ninguém
//      lê, e passa a ser custo puro.
import { detectLocale, type Locale } from '../i18n/locale'

const CHAVE_DISPENSA = 'digitalfit.lang_hint'

/**
 * O idioma a sugerir, ou `null` para não sugerir nada. Pura: recebe as duas pontas como
 * parâmetro — mesmo padrão de `resolveLocale()`, testável sem navegador.
 */
export function idiomaASugerir(
  preferido: Locale,
  daPagina: Locale,
  dispensado: boolean,
): Locale | null {
  if (dispensado) return null
  return preferido === daPagina ? null : preferido
}

/** Mesmo try/catch de `i18n/locale.ts`: o Safari em navegação privada LANÇA em vez de faltar. */
export function dispensaGravada(): boolean {
  try {
    return window.localStorage.getItem(CHAVE_DISPENSA) === 'dispensado'
  } catch {
    return false
  }
}

export function gravarDispensa(): void {
  try {
    window.localStorage.setItem(CHAVE_DISPENSA, 'dispensado')
  } catch {
    // Sem armazenamento: vale pela visita e pronto — mesma resposta de `persistLocale`.
  }
}

// ---------------------------------------------------------------------------------------
// A ponte para o React: um store externo minúsculo, no lugar de `useState` + `useEffect`.
//
// O aviso é um valor que **só existe no cliente** — no pré-render ele tem de ser `null`, senão
// o HTML do robô difere do da pessoa (cloaking) e a hidratação não bate. O idioma óbvio para
// isso seria `useEffect` chamando `setState`, e foi a primeira versão: o `react-hooks` reprovou
// com "Calling setState synchronously within an effect can trigger cascading renders", e estava
// certo — é um render a mais em toda visita, para um valor que já se sabe ler de saída.
//
// `useSyncExternalStore` é a ferramenta certa e já é a da casa (`i18n/index.ts`, `useLocale`):
// o terceiro argumento é o snapshot de SERVIDOR, e devolver `null` ali é exatamente a regra
// "não existe no HTML pré-renderizado", escrita uma vez e no lugar onde se lê.
// ---------------------------------------------------------------------------------------

const ouvintes = new Set<() => void>()
let dispensado: boolean | null = null
let preferido: Locale | null = null

/** `getSnapshot` roda a cada render: as duas leituras do aparelho ficam em cache de módulo. */
function estadoDoAparelho(): { preferido: Locale; dispensado: boolean } {
  preferido ??= detectLocale()
  dispensado ??= dispensaGravada()
  return { preferido, dispensado }
}

export function assinarSugestao(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte)
  return () => ouvintes.delete(ouvinte)
}

/** A sugestão para esta página, ou `null`. Snapshot: devolve primitivo, nunca objeto novo. */
export function sugestaoAtual(daPagina: Locale): Locale | null {
  const { preferido: pref, dispensado: disp } = estadoDoAparelho()
  return idiomaASugerir(pref, daPagina, disp)
}

/** O snapshot de servidor: no build não há aparelho a consultar, e o aviso não vai ao robô. */
export function semSugestao(): null {
  return null
}

export function dispensar(): void {
  gravarDispensa()
  dispensado = true
  for (const ouvinte of ouvintes) ouvinte()
}
