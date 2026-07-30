// Casca do SITE (T-067): landing e Sobre, roteadas por hash.
//
// Não há AccountSheet aqui de propósito. O token de conta vive no `localStorage`, que é por
// ORIGEM: entrar em `site.dominio.com` não deixaria ninguém logado em `app.dominio.com`.
// Um "Entrar" que às vezes funciona é pior que um "Entrar" que leva ao app — então o botão
// leva ao app, onde a conta realmente mora.
import { AboutScreen } from './AboutScreen'
import { IndexScreen } from './IndexScreen'
import { useSiteRoute } from './nav'

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
