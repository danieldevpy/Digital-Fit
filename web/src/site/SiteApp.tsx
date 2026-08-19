// Casca do SITE (T-067). Landing, Sobre e a 404, roteadas por CAMINHO desde a T-158.
//
// Não há AccountSheet aqui de propósito. O token de conta vive no `localStorage`, que é por
// ORIGEM: entrar em `site.dominio.com` não deixaria ninguém logado em `app.dominio.com`.
// Um "Entrar" que às vezes funciona é pior que um "Entrar" que leva ao app — então o botão
// leva ao app, onde a conta realmente mora.
//
// **Este componente não toca `window` nem `document`** (T-159). Até aqui ele lia o
// `<html lang>` num efeito de módulo e a rota de `window.location` — e as duas coisas o
// tornavam impossível de renderizar fora do navegador. Como o pré-render em build é o que faz
// o Google e o tradutor do Chrome enxergarem esta página (SPEC-026 §Notas técnicas), quem lê o
// mundo passou a ser o ENTRY: `entries/site.tsx` no navegador, `entries/prerender.tsx` no
// build. O componente recebe a tela pronta e o idioma pelo store.
import { useLocale } from '../i18n'
import { AboutScreen } from './AboutScreen'
import { AvisoDeIdioma } from './AvisoDeIdioma'
import { IndexScreen } from './IndexScreen'
import { NotFoundScreen } from './NotFoundScreen'
import type { SiteScreen } from './routes'

export function SiteApp({ screen }: { screen: SiteScreen }) {
  const locale = useLocale()

  if (screen === 'nao_encontrada') {
    return (
      <div className="app">
        <NotFoundScreen />
      </div>
    )
  }

  return (
    <div className="app">
      {/* Sugere a outra versão do site a quem não veio da busca (T-161). Nunca redireciona: o
          Googlebot rastreia dos EUA, e um redirecionamento por idioma apagaria a versão
          portuguesa do índice — invariante da SPEC-026. */}
      <AvisoDeIdioma screen={screen} locale={locale} />
      {screen === 'index' ? (
        <IndexScreen />
      ) : (
        <div className="app__phone">
          <AboutScreen />
        </div>
      )}
    </div>
  )
}
