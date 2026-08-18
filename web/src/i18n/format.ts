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
