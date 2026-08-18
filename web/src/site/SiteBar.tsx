// Barra inferior do SITE (T-067) — três itens, e o terceiro é a porta do app.
//
// Reaproveita a pele da `.tabbar-v2` (mesmo material da SPEC-014) mas não a tab bar do app:
// aquela navega entre telas de treino, que não existem neste bundle. Item destacado em vez
// de "ativo": "Abrir o app" não é uma aba, é uma saída.
import { useT } from '../i18n'
import { IconDumbbell, IconHome, IconLogo } from '../ui/icons'
import { appHref } from '../shell/origins'
import { siteRouteHash } from './nav'

export function SiteBar({ active }: { active: 'index' | 'sobre' }) {
  const t = useT()

  return (
    <nav className="tabbar-v2" aria-label={t('site:bar.aria_label')}>
      <a
        className={`tabv2 ${active === 'index' ? 'tabv2--active' : ''}`}
        aria-current={active === 'index' ? 'page' : undefined}
        href={siteRouteHash({ screen: 'index' })}
      >
        <IconHome className="tabv2__icon" />
        <span>{t('site:bar.home')}</span>
      </a>
      <a
        className={`tabv2 ${active === 'sobre' ? 'tabv2--active' : ''}`}
        aria-current={active === 'sobre' ? 'page' : undefined}
        href={siteRouteHash({ screen: 'sobre' })}
      >
        <IconLogo className="tabv2__icon" />
        <span>{t('site:bar.about')}</span>
      </a>
      <a className="tabv2 tabv2--go" href={appHref()}>
        <IconDumbbell className="tabv2__icon" />
        <span>{t('site:bar.open_app')}</span>
      </a>
    </nav>
  )
}
