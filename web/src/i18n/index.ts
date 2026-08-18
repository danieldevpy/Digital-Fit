// Runtime de tradução do cliente (SPEC-025 §3.1/§3.2, PLANO-I18N.md §3.1): `t()` com namespace
// explícito, interpolação `{n}` e plural por `Intl.PluralRules` — sem biblioteca. `i18next` +
// `react-i18next` custam ~50 KB minificados; o projeto tem quatro dependências de runtime e mede
// gzip de `.wasm` no nginx, e a conta não fecha por um `t()` e uma interpolação (SPEC-025 §3.1).
//
// Migra-se UM namespace por task (Onda 2 do BACKLOG) para rodarem em paralelo sem colidir num
// dicionário único — esta task (T-142) migra só `shell`; os outros oito nascem vazios e crescem
// sozinhos: `TKey` abaixo é gerado A PARTIR dos dicionários, então o autocomplete e o erro de
// `tsc` para uma chave errada aparecem sem nenhuma manutenção extra conforme cada um for escrito.
import { useCallback } from 'react'
import { dict as dictEn } from './dict/en'
import { dict as dictPtBR } from './dict/pt-BR'
import type { Locale } from './locale'
import { useI18nStore } from './store'

// `DictShape` larga os valores literais de `dictPtBR` (que carregam `as const`, ex.:
// 'Início') e guarda só a FORMA — cada namespace com suas chaves, cada chave como `string`
// genérico. É o mesmo raciocínio do tipo `Shell`/`Account`/... em cada `dict/pt-BR/<ns>.ts`
// (paridade de chave, não igualdade de valor), aplicado aqui ao dicionário inteiro: sem isso,
// `DICTS` abaixo forçaria o `en` (valores `string` largos) a bater literal por literal com o
// `pt-BR` — e nenhum dicionário `en` compilaria.
type DictShape = { [N in keyof typeof dictPtBR]: Record<keyof (typeof dictPtBR)[N], string> }

const DICTS: Record<Locale, DictShape> = { 'pt-BR': dictPtBR, en: dictEn }

type NamespaceOf = keyof DictShape

/**
 * Todas as chaves válidas de `t()`, derivadas dos NOVE dicionários (o item mais importante da
 * T-142 — SPEC-025 §3.1): namespace sem conteúdo contribui `never` para a união (nada para
 * escolher ainda), então o autocomplete de `t()` cresce sozinho conforme a Onda 2 preenche cada
 * `dict/pt-BR/<namespace>.ts` — ninguém precisa mexer aqui para isso acontecer.
 */
export type TKey = {
  [N in NamespaceOf]: `${N & string}:${Extract<keyof DictShape[N], string>}`
}[NamespaceOf]

type Params = Record<string, string | number>

const INTERPOLATE_RE = /\{(\w+)\}/g

function interpolate(texto: string, params?: Params): string {
  if (!params) return texto
  return texto.replace(INTERPOLATE_RE, (coincidencia, nome: string) =>
    nome in params ? String(params[nome]) : coincidencia,
  )
}

const regrasPluralPorLocale = new Map<Locale, Intl.PluralRules>()

function categoriaPlural(locale: Locale, n: number) {
  let regras = regrasPluralPorLocale.get(locale)
  if (!regras) {
    regras = new Intl.PluralRules(locale)
    regrasPluralPorLocale.set(locale, regras)
  }
  return regras.select(n)
}

/**
 * Plural (critério 2 da T-142) + interpolação sobre UMA tabela já resolvida — separado de
 * `translate()` para ser testável com fixtures próprias, sem depender do conteúdo real dos nove
 * dicionários (a maioria ainda vazio nesta task; só `shell` tem chaves, e nenhuma delas precisa
 * de plural).
 *
 * Quando `params.n` é número, tenta `<chave>.<categoria>` primeiro — a categoria vem de
 * `Intl.PluralRules(locale).select(n)`, nunca de um `if (n === 1)`, porque a regra muda por
 * idioma (a terceira língua da SPEC-025 pode ter mais de duas categorias, e um `if` não
 * escala). Sem a categoria específica, cai em `.other`; sem essa também, cai na chave exata.
 * `undefined` quando nada bate — quem chama decide o fallback final.
 *
 * Balde extra `.zero`: o CLDR do português classifica `n === 0` como categoria `one` (é assim
 * que `Intl.PluralRules('pt-BR').select(0)` responde), mas o texto natural em pt-BR para zero é
 * plural — "0 repetições", não "0 repetição". `Intl.PluralRules` continua sendo o motor (nunca
 * um `if (n === 1)` disfarçado): quando `n === 0` e a tabela tem `<chave>.zero`, esse balde
 * OPCIONAL vence antes de consultar a categoria do CLDR; sem `.zero` na tabela, `n === 0` segue
 * a categoria do CLDR normalmente (cai em `.one` para pt-BR, em `.other` para en).
 */
export function resolveFromTable(
  tabela: Record<string, string | undefined>,
  locale: Locale,
  chave: string,
  params?: Params,
): string | undefined {
  if (typeof params?.n === 'number') {
    if (params.n === 0) {
      const porZero = tabela[`${chave}.zero`]
      if (porZero !== undefined) return interpolate(porZero, params)
    }
    const categoria = categoriaPlural(locale, params.n)
    const porCategoria = tabela[`${chave}.${categoria}`]
    if (porCategoria !== undefined) return interpolate(porCategoria, params)
    const porOutra = tabela[`${chave}.other`]
    if (porOutra !== undefined) return interpolate(porOutra, params)
  }

  const exata = tabela[chave]
  if (exata !== undefined) return interpolate(exata, params)
  return undefined
}

/**
 * Resolve `'namespace:chave'` no dicionário do locale dado. Pura — recebe o locale como
 * parâmetro em vez de ler o store sozinha, o mesmo motivo de a análise de exercício não ler
 * relógio — e é o que `t()`/`useT()` chamam por baixo.
 */
export function translate(locale: Locale, chave: string, params?: Params): string {
  const indice = chave.indexOf(':')
  if (indice === -1) return chave
  const namespace = chave.slice(0, indice) as NamespaceOf
  const resto = chave.slice(indice + 1)

  const tabelaDoNamespace = DICTS[locale][namespace] as Record<string, string | undefined>

  // Chave ausente nunca vira branco nem crash — mesma doutrina do fallback de tradução do banco
  // (SPEC-025 §3.6): devolve a própria chave, visível o bastante para ser notada em revisão. Só
  // alcançável com uma chave fora do tipo `TKey` (cast manual, dicionário desalinhado em tempo
  // de execução) — o caminho normal já é barrado por `tsc` antes de chegar aqui.
  return resolveFromTable(tabelaDoNamespace, locale, resto, params) ?? chave
}

/** `t()` fora de componente (fora do ciclo de render do React): lê o locale ativo agora. */
export function t(chave: TKey, params?: Params): string {
  return translate(useI18nStore.getState().locale, chave, params)
}

/** `t()` dentro de componente — assina o locale no store, então o componente re-renderiza ao trocar de idioma. */
export function useT(): (chave: TKey, params?: Params) => string {
  const locale = useI18nStore((state) => state.locale)
  return useCallback((chave: TKey, params?: Params) => translate(locale, chave, params), [locale])
}

/**
 * Como `t()`, mas para chave MONTADA em tempo de execução — slug de categoria, código de
 * feedback, id de exercício (T-152): `TKey` não cobre essas porque o valor não é conhecido em
 * tempo de compilação (`Extract<keyof DictShape[N], string>` exige literal estático), então
 * `${namespace}:${variável}` nunca seria atribuível a `TKey` sem um `as` mentiroso.
 *
 * `translate()` já devolve a própria chave quando não encontra nada (§ doc de `translate`) — o
 * que basta para chave FIXA, mas aqui a chave é montada (`catalog:category.${slug}`), então
 * devolver ela mesma exporia o namespace na tela. `fallback` é o que aparece nesse caso — o
 * `slug`/`code` cru, a mesma doutrina de "feio de propósito, para ser visto" que já existia em
 * `categoryLabel` e `textForCode` antes desta task.
 */
export function tDynamic(chave: string, fallback: string): string {
  const locale = useI18nStore.getState().locale
  const resolvido = translate(locale, chave)
  return resolvido === chave ? fallback : resolvido
}
