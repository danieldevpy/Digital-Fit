// Barra inferior do SITE (T-067) — três itens, e o terceiro é a porta do app.
//
// Reaproveita a pele da `.tabbar-v2` (mesmo material da SPEC-014) mas não a tab bar do app:
// aquela navega entre telas de treino, que não existem neste bundle. Item destacado em vez
// de "ativo": "Abrir o app" não é uma aba, é uma saída.
import { useT } from '../i18n'
import { LocaleSwitch } from '../i18n/LocaleSwitch'
import { useI18nStore } from '../i18n/store'
import { appHref, siteRouteHref } from '../shell/origins'
import { IconDumbbell, IconHome, IconLogo } from '../ui/icons'

export function SiteBar({ active }: { active: 'index' | 'sobre' }) {
  const t = useT()
  // O locale do SITE vem da URL desta visita (`SiteApp` sincroniza o store com o `<html lang>`
  // estático), não da preferência do aparelho — por isso ler o store aqui é ler a URL.
  const locale = useI18nStore((state) => state.locale)

  return (
    <>
      {/* Acima da barra, e não como uma quarta aba: as três abas são DESTINOS, e o idioma é
          uma propriedade da página inteira. Aqui ele é um par de LINKS (`hrefOf`) porque no
          site o idioma mora na URL — `/` e `/en/`, as mesmas que os `hreflang` de cada
          `index.html` declaram uma à outra (SPEC-025 §Escopo). O hash viaja junto: quem está
          em Sobre e troca de idioma continua em Sobre — agora por CAMINHO (`/sobre/` ↔
          `/en/about/`), não por fragmento: é a T-158 que os transformou em documentos. */}
      <LocaleSwitch
        className="langsw--site"
        value={locale}
        hrefOf={(alvo) => siteRouteHref(active, alvo)}
      />

      <nav className="tabbar-v2" aria-label={t('site:bar.aria_label')}>
        <a
          className={`tabv2 ${active === 'index' ? 'tabv2--active' : ''}`}
          aria-current={active === 'index' ? 'page' : undefined}
          href={siteRouteHref('index', locale)}
        >
          <IconHome className="tabv2__icon" />
          <span>{t('site:bar.home')}</span>
        </a>
        <a
          className={`tabv2 ${active === 'sobre' ? 'tabv2--active' : ''}`}
          aria-current={active === 'sobre' ? 'page' : undefined}
          href={siteRouteHref('sobre', locale)}
        >
          <IconLogo className="tabv2__icon" />
          <span>{t('site:bar.about')}</span>
        </a>
        <a className="tabv2 tabv2--go" href={appHref()}>
          <IconDumbbell className="tabv2__icon" />
          <span>{t('site:bar.open_app')}</span>
        </a>
      </nav>
    </>
  )
}
