// A tela de 404 do SITE (T-158, SPEC-026 §Escopo — "URL inexistente devolve 404").
//
// **Por que uma tela React e não um HTML escrito à mão.** O texto que o cliente lê nasce nas
// duas línguas por construção (AGENTS §Fluxo 4) — no dicionário, cobrado pelo `tsc`. Um
// `404.html` com as frases dentro seria a única superfície do produto fora desse portão, e
// justamente a que ninguém abre para conferir.
//
// **O idioma aqui segue a PREFERÊNCIA, não a URL** — divergindo do resto do site de propósito.
// A regra "site por URL" (SPEC-025 §Escopo) existe porque o buscador escolhe a versão pela URL;
// esta página é `noindex` por natureza e a URL que a produziu não existe, então não há idioma
// a deduzir dela. Sem URL para perguntar, a pergunta certa é a do `/app/`: o que o aparelho
// prefere. É o `detectLocale()` que o `store.ts` já usa no boot.
import { useT } from '../i18n'
import { useI18nStore } from '../i18n/store'
import { siteRouteHref } from '../shell/origins'

export function NotFoundScreen() {
  const t = useT()
  const locale = useI18nStore((state) => state.locale)

  return (
    <div className="app__phone">
      <section className="notfound">
        <p className="notfound__code" translate="no">
          404
        </p>
        <h1 className="notfound__title">{t('site:not_found.title')}</h1>
        <p className="notfound__text">{t('site:not_found.text')}</p>
        <a className="v2-cta" href={siteRouteHref('index', locale)}>
          {t('site:not_found.home')}
        </a>
      </section>
    </div>
  )
}
