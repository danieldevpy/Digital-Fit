// Locale ativo do cliente (SPEC-025 §3.1), no mesmo padrão de `store/config.ts` (zustand).
//
// O estado nasce já resolvido: `detectLocale()` é síncrona (lê `localStorage` e
// `navigator.languages`, os dois disponíveis antes de qualquer render), então não existe aqui
// o "ainda não sei" do `store/config.ts` — aquele espera uma resposta de rede; este não depende
// de nada além do próprio aparelho. Computar de saída evita o flash de idioma errado que uma
// hidratação em `useEffect` (o padrão do `AppShell` para o que VEM da rede) introduziria à toa.
//
// O store fica sem tocar o DOM de propósito — `set()` puro, como `config.ts` e `account.ts`.
// Quem reage a `locale` para reescrever `<html lang>` é o `AppShell` (critério 6 da T-142),
// pelo mesmo canal (`useEffect`) que já sincroniza histórico, conta e config com o mundo de
// fora — side effect de boot é responsabilidade dele, não do store.
import { create } from 'zustand'
import { detectLocale, persistLocale, type Locale } from './locale'

export interface I18nState {
  locale: Locale
  /** Escolha explícita (T-153 vai chamar isto pelo seletor). Persiste e atualiza o estado. */
  setLocale: (locale: Locale) => void
}

export const useI18nStore = create<I18nState>((set) => ({
  locale: detectLocale(),
  setLocale: (locale) => {
    persistLocale(locale)
    set({ locale })
  },
}))
