// Casca do SITE (T-067): landing e Sobre, roteadas por hash.
//
// Não há AccountSheet aqui de propósito. O token de conta vive no `localStorage`, que é por
// ORIGEM: entrar em `site.dominio.com` não deixaria ninguém logado em `app.dominio.com`.
// Um "Entrar" que às vezes funciona é pior que um "Entrar" que leva ao app — então o botão
// leva ao app, onde a conta realmente mora.
//
// Site por URL, não por preferência (SPEC-025 §Escopo — Site por URL; T-147): cada entry HTML
// (`index.html` = pt-BR, `en/index.html` = en) já grava o `lang` estático correspondente antes
// deste bundle carregar. O store de i18n é sincronizado com esse `lang` aqui, no import do
// módulo — mesmo raciocínio do `detectLocale()` de `i18n/store.ts` (computar de saída evita o
// flash de idioma errado que uma hidratação em `useEffect` introduziria à toa) — em vez de com
// o `detectLocale()` do APP, que serve preferência de aparelho: a regra certa para o `/app/`
// (não indexado) é a errada aqui (indexado, rastreado por URL). `setState` direto, não
// `setLocale()`: a escolha é da URL desta visita, não uma preferência para persistir em
// `digitalfit.locale` — visitar `/en/` não deve trocar o idioma que o app abre depois.
import { useI18nStore } from '../i18n/store'
import { AboutScreen } from './AboutScreen'
import { IndexScreen } from './IndexScreen'
import { useSiteRoute } from './nav'

const localeDoSite = document.documentElement.lang === 'en' ? 'en' : 'pt-BR'
if (useI18nStore.getState().locale !== localeDoSite) {
  useI18nStore.setState({ locale: localeDoSite })
}

export function SiteApp() {
  const route = useSiteRoute()

  return (
    <div className="app">
      {route.screen === 'index' ? (
        <IndexScreen />
      ) : (
        <div className="app__phone">
          <AboutScreen />
        </div>
      )}
    </div>
  )
}
