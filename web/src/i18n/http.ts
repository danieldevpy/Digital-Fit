// O cabeçalho de idioma das chamadas à API (SPEC-025 §3.4).
//
// **Por que existe um arquivo só para uma linha.** Até a T-153 o `Accept-Language` com o locale
// RESOLVIDO do cliente saía de um lugar só — o `authedFetch` de `auth/api.ts` —, e as três
// chamadas que NÃO passam por ele (`GET /api/config`, `POST /api/sessions`, o relatório) ficavam
// entregues ao `Accept-Language` que o próprio navegador acrescenta sozinho. Isso funcionava
// enquanto o idioma do app era o do navegador; no instante em que existe um seletor, deixa de
// funcionar: a pessoa troca para inglês, o catálogo continua chegando em português, e o bug se
// parece com "o servidor não traduziu" quando na verdade ninguém contou a ele.
//
// A ordem de prioridade do servidor (`?locale=` > `Accept-Language` > `en`, SPEC-025 §3.4) não
// muda; o que muda é o cliente passar a mandar a SUA resposta em vez de deixar o navegador
// responder por ele.
import { useI18nStore } from './store'

/**
 * `Accept-Language` com o locale ativo. Safelisted de CORS — não gera preflight.
 *
 * **O que viaja aqui é o locale RESOLVIDO, nunca o do navegador** (T-162, SPEC-026 §Escopo).
 * A distinção parece detalhe e não é: quem abre o app em francês recebe `en` do
 * `resolveLocale()` (não há catálogo em francês, e `DEFAULT_LOCALE` é a resposta da casa para
 * "não sei quem é você"), então o cabeçalho diz `en` e o servidor responde a mesma língua que a
 * tela está mostrando. Repassar o `navigator.language` cru mandaria `fr`, o servidor cairia no
 * próprio fallback e responderia `en` de qualquer jeito — mas por acidente, e o dia em que
 * existir um catálogo `fr` parcial no servidor a tela ficaria meio em francês e meio em inglês.
 * O cliente é quem sabe em que língua ele está; o cabeçalho é onde ele conta.
 */
export function localeHeaders(): Record<string, string> {
  return { 'Accept-Language': useI18nStore.getState().locale }
}
