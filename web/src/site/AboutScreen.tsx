// Tela Sobre / footer mobile (SPEC-014 §5, tela 5 da referência).
//
// Desde a T-067 é tela do SITE: conteúdo institucional não pertence ao app de treino, e os
// dois links que levam a treinar atravessam para o app por `href`.
import { useT } from '../i18n'
import { DEFAULT_EXERCISE } from '../session/catalog'
import { appHref } from '../shell/origins'
import { IconChevronRight, IconLogo, IconShieldCheck, IconSpark, IconTarget } from '../ui/icons'
import { SiteBar } from './SiteBar'

// Só o ícone e o slug são estáticos aqui (T-147, namespace `site`): título e texto vêm de
// `t()` a cada render, mesmo raciocínio do `TABS` de `shell/TabBar.tsx` — um array de módulo
// com o rótulo já resolvido congelaria no idioma de quando o bundle carregou.
const VALUES = [
  { id: 'privacy', Icon: IconShieldCheck },
  { id: 'levels', Icon: IconTarget },
  { id: 'evolution', Icon: IconSpark },
] as const

export function AboutScreen() {
  const t = useT()

  const recursos = [
    { id: 'how_it_works', href: appHref(`#/guia/${DEFAULT_EXERCISE}`) },
    { id: 'exercises', href: appHref('#/exercicios') },
    { id: 'benefits', href: null },
    { id: 'plans', href: null },
  ] as const

  return (
    <>
      <div className="about">
        <IconLogo className="about__logo" />
        <h1 className="about__title">{t('site:about.title')}</h1>
        <p className="about__sub">{t('site:footer.tagline')}</p>

        <div className="about__cards">
          {VALUES.map(({ id, Icon }) => (
            <div className="feature" key={id}>
              <span className="feature__icon">
                <Icon />
              </span>
              <div>
                <p className="feature__title">{t(`site:about.value.${id}.title`)}</p>
                <p className="feature__text">{t(`site:about.value.${id}.text`)}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="about__links">
          <p className="about__links-title">{t('site:footer.heading.resources')}</p>
          {recursos.map(({ id, href }) =>
            href ? (
              <a key={id} className="about__link" href={href}>
                {t(`site:footer.link.${id}`)}
                <IconChevronRight className="about__link-icon" />
              </a>
            ) : (
              <span
                key={id}
                className="about__link about__link--soon"
                title={t('site:about.coming_soon')}
              >
                {t(`site:footer.link.${id}`)}
                <IconChevronRight className="about__link-icon" />
              </span>
            ),
          )}
        </div>

        <p className="about__copyright">{t('site:footer.copyright')}</p>
      </div>
      <SiteBar active="sobre" />
    </>
  )
}
