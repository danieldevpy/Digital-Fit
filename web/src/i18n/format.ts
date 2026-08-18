// Data, hora, número e percentual via `Intl`, sempre no locale ATIVO (SPEC-025 §3.1, plano §2.6).
//
// Ninguém mais deve escrever um locale literal (`'pt-BR'`) num `toLocale*` — cada um solto era
// uma tela que ficaria presa em português mesmo depois de trocar o idioma (a descoberta §2.6 do
// plano: `accountSummary.ts` e `ProgressScreen.tsx` fazem isso hoje; migrar esses call sites é
// da T-150/T-151, não desta task — aqui só nasce o formatador certo para eles usarem).
//
// Cada função lê o locale ativo do store por padrão, mas aceita um terceiro parâmetro para
// sobrescrever — é o que torna a função testável sem precisar mexer no store global: os testes
// passam o locale que querem verificar, o app real nunca passa nada e segue a preferência de
// quem está usando.
import { useI18nStore } from './store'
import type { Locale } from './locale'

function activeLocale(): Locale {
  return useI18nStore.getState().locale
}

export function formatDate(
  data: Date | number,
  opcoes?: Intl.DateTimeFormatOptions,
  locale: Locale = activeLocale(),
): string {
  return new Intl.DateTimeFormat(locale, opcoes).format(data)
}

export function formatTime(
  data: Date | number,
  opcoes?: Intl.DateTimeFormatOptions,
  locale: Locale = activeLocale(),
): string {
  return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit', ...opcoes }).format(data)
}

export function formatDateTime(
  data: Date | number,
  opcoes?: Intl.DateTimeFormatOptions,
  locale: Locale = activeLocale(),
): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: 'short', timeStyle: 'short', ...opcoes }).format(
    data,
  )
}

export function formatNumber(
  valor: number,
  opcoes?: Intl.NumberFormatOptions,
  locale: Locale = activeLocale(),
): string {
  return new Intl.NumberFormat(locale, opcoes).format(valor)
}

export function formatPercent(
  valor: number,
  opcoes?: Intl.NumberFormatOptions,
  locale: Locale = activeLocale(),
): string {
  return new Intl.NumberFormat(locale, { style: 'percent', ...opcoes }).format(valor)
}

/**
 * As sete letras do cabeçalho da grade do mês, na ordem em que a tela desenha (T-150).
 *
 * Substitui o `DIAS_DA_SEMANA = ['S','T','Q','Q','S','S','D']` escrito à mão em
 * `ProgressScreen`: aquilo era o calendário brasileiro embutido no código, e em inglês
 * mostraria "S T Q Q S S D" sobre uma tela que diz "Progress".
 *
 * **A semana continua abrindo na SEGUNDA**, e isso é decisão de produto, não de locale: a
 * agregação (`inicioDaSemana`, `history/aggregates.ts`) e a matemática da grade
 * (`(getDay() + 6) % 7`) contam a semana assim, e um cabeçalho que mudasse de primeiro dia por
 * idioma desalinharia as bolinhas do mês em inglês. O que o `Intl` decide aqui é a LETRA de
 * cada dia, não por onde a semana começa.
 *
 * A âncora é 2024-01-01, uma segunda-feira — a data não aparece em lugar nenhum, só serve para
 * o `Intl` ter de que dia falar.
 */
export function weekdayNarrowLabels(locale: Locale = activeLocale()): string[] {
  const formatador = new Intl.DateTimeFormat(locale, { weekday: 'narrow' })
  return Array.from({ length: 7 }, (_, i) => formatador.format(new Date(2024, 0, 1 + i)))
}
