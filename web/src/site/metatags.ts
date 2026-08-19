// As anotações de cabeçalho que dizem ao buscador QUAL versão desta página mostrar a quem
// (T-160, SPEC-026 §Escopo — camada "Achar").
//
// ## O bug que esta função existe para não repetir
//
// A T-147 escreveu `hreflang` à mão em cada `index.html`, com `href="/"` e `href="/en/"`. A
// especificação exige URL **absoluta, com esquema e host**; relativa é ignorada — sem aviso, sem
// erro, sem nada em log. O par pt/en que a Onda 2 da i18n entregou nunca existiu para o Google,
// e ninguém tinha como saber. É o achado que abriu a Fase 8 inteira.
//
// Por isso três coisas mudam de natureza aqui: os links passam a ser **gerados** da tabela de
// rotas (fonte única, SPEC-026 §Escopo), a origem é **exigida** em vez de deduzida, e a saída é
// uma função **pura** — que é o que permite testá-la sem build, e é o teste que faltava quando o
// erro entrou.
//
// ## O que cada anotação faz
//
//   - `canonical`   — "esta é a URL oficial desta página". Só existe absoluta.
//   - `alternate`   — o par recíproco: cada idioma aponta para todos, inclusive para si mesmo,
//                     que é exigência do formato e o erro mais comum de quem escreve à mão.
//   - `x-default`   — **a resposta para "e quem não é nem pt nem en?"**, que é a pergunta que
//                     motivou esta frente. Aponta para `/en/` pelo mesmo motivo que
//                     `DEFAULT_LOCALE` é `'en'` em `i18n/locale.ts`: é a resposta certa para
//                     "não sei quem é você". As duas pontas dizem a mesma coisa de propósito.
import { LOCALES, type Locale } from '../i18n/locale'
import { caminhoDaRota, type SiteScreen } from './routes'

/** O idioma para onde o `x-default` aponta — o mesmo `DEFAULT_LOCALE` de `i18n/locale.ts`. */
export const LOCALE_PADRAO_DO_BUSCADOR: Locale = 'en'

/**
 * A URL absoluta de uma tela num idioma.
 *
 * `origem` sem barra no fim, sempre com esquema — quem valida isso é `exigirOrigem()`, para o
 * erro aparecer uma vez, no build, e não quatro vezes por página.
 */
export function urlAbsoluta(origem: string, screen: SiteScreen, locale: Locale): string {
  return `${origem}/${caminhoDaRota(screen, locale)}`
}

/**
 * `canonical` + `alternate` de todos os idiomas + `x-default`, prontos para o `<head>`.
 *
 * Indentação de quatro espaços porque é onde eles entram; a saída é comparada em teste, então a
 * forma faz parte do contrato.
 */
export function linksDeCabecalho(origem: string, screen: SiteScreen, locale: Locale): string {
  const linhas = [
    `<link rel="canonical" href="${urlAbsoluta(origem, screen, locale)}" />`,
    ...LOCALES.map(
      (outro) =>
        `<link rel="alternate" hreflang="${outro}" href="${urlAbsoluta(origem, screen, outro)}" />`,
    ),
    `<link rel="alternate" hreflang="x-default" href="${urlAbsoluta(origem, screen, LOCALE_PADRAO_DO_BUSCADOR)}" />`,
  ]

  return linhas.map((linha) => `    ${linha}`).join('\n')
}

/**
 * A origem, validada — ou um erro que diz o que fazer.
 *
 * **Exigir em vez de deduzir** é a decisão desta task. A T-159 emitia `canonical` só quando
 * conhecia a origem e o omitia calado quando não; omitir é melhor que escrever relativo, mas
 * continua sendo uma página sem anotação nenhuma indo para produção sem ninguém ver. Agora quem
 * quiser as anotações precisa dizer onde o site mora, e quem não disser recebe uma frase.
 */
export function exigirOrigem(bruta: string | undefined): string {
  const valor = (bruta ?? '').trim().replace(/\/+$/, '')

  if (!/^https?:\/\/[^/]+$/.test(valor)) {
    // Uma interpolação só, e não três literais concatenados: o portão de `i18n/portoes.test.ts`
    // isenta frase em português quando ela nasce depois de um `throw new`, mas olha só os 120
    // caracteres anteriores — o terceiro pedaço da versão anterior caía fora da janela e
    // reprovava. O portão estava certo e a forma da mensagem é que estava errada.
    throw new Error(
      `VITE_SITE_ORIGIN inválida: ${JSON.stringify(bruta ?? '')}. Esperado a origem pública do site, absoluta e sem caminho (ex.: "https://exemplo.com.br"); em produção o scripts/prod.sh a deriva de SITE_DOMAIN/DOMAIN.`,
    )
  }

  return valor
}
