// O seletor de idioma (T-153, SPEC-025 §Escopo).
//
// **Só desenho.** Não conhece store, não sabe revalidar cache e não sabe navegar — recebe o
// locale ativo e o que fazer com a escolha. É essa ignorância que permite o MESMO controle
// servir às duas superfícies, que decidem de formas incompatíveis (SPEC-025 §Escopo, "site por
// URL, app por preferência"):
//
//   - **app**: `onSelect` troca a preferência do aparelho e revalida o que veio do servidor
//     (`i18n/switchLocale.ts`), sem recarregar nada;
//   - **site**: `hrefOf` devolve `/` ou `/en/`, e a escolha é uma NAVEGAÇÃO — a URL é que
//     carrega o idioma, porque o Google rastreia dos EUA e só veria a versão inglesa se a
//     landing redirecionasse por `navigator.language`.
//
// Passar as duas como props (e não um `if (isSite)`) é o que mantém o bundle da landing sem
// `session/` e `engagement/` dentro (ADR-010): o site importa este arquivo e nada do app.
//
// Dois botões visíveis ao mesmo tempo, e não um ciclo ou um `<select>`: são duas opções, e a
// pessoa que procura idioma normalmente não lê a língua em que a tela está — esconder a outra
// atrás de um toque seria esconder justamente do único público deste controle.
import { LOCALES, type Locale } from './locale'
import { useT } from './index'

interface Props {
  /** Qual está ativo agora. */
  value: Locale
  /** App: aplica a escolha. Ausente no site, onde a escolha é um link. */
  onSelect?: (locale: Locale) => void
  /** Site: para onde cada opção leva. Ausente no app, onde nada navega. */
  hrefOf?: (locale: Locale) => string
  /** Classe extra do contêiner, para cada superfície dar a própria moldura. */
  className?: string
}

export function LocaleSwitch({ value, onSelect, hrefOf, className = '' }: Props) {
  const t = useT()

  return (
    // `radiogroup` no app (opções mutuamente exclusivas, uma marcada) e `group` no site (são
    // links, e um leitor de tela não deve anunciar link como opção de formulário).
    <div
      className={`langsw ${className}`}
      role={hrefOf ? 'group' : 'radiogroup'}
      aria-label={t('shell:lang.aria_label')}
    >
      {LOCALES.map((locale) => {
        const ativo = locale === value
        // O nome de cada idioma na PRÓPRIA língua ("Português", "English") — convenção de
        // seletor de idioma, e a única que funciona para quem abriu o app na língua errada.
        const nome = t(locale === 'pt-BR' ? 'shell:lang.pt' : 'shell:lang.en')

        if (hrefOf) {
          return (
            <a
              key={locale}
              className={`langsw__opt ${ativo ? 'langsw__opt--on' : ''}`}
              href={hrefOf(locale)}
              hrefLang={locale}
              aria-current={ativo ? 'true' : undefined}
            >
              {nome}
            </a>
          )
        }

        return (
          <button
            key={locale}
            type="button"
            role="radio"
            aria-checked={ativo}
            className={`langsw__opt ${ativo ? 'langsw__opt--on' : ''}`}
            onClick={() => onSelect?.(locale)}
          >
            {nome}
          </button>
        )
      })}
    </div>
  )
}
