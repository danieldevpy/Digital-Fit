// Tela Sobre / footer mobile (SPEC-014 §5, tela 5 da referência).
//
// Desde a T-067 é tela do SITE: conteúdo institucional não pertence ao app de treino, e os
// dois links que levam a treinar atravessam para o app por `href`.
import { DEFAULT_EXERCISE } from '../session/catalog'
import { appHref } from '../shell/origins'
import { IconChevronRight, IconLogo, IconShieldCheck, IconSpark, IconTarget } from '../ui/icons'
import { SiteBar } from './SiteBar'

const VALUES = [
  {
    Icon: IconShieldCheck,
    title: 'Privacidade em primeiro lugar',
    text: 'Analisamos keypoints do seu corpo, não guardamos seu vídeo.',
  },
  {
    Icon: IconTarget,
    title: 'Para todos os níveis',
    text: 'Treinos rápidos e eficientes para iniciantes e avançados.',
  },
  {
    Icon: IconSpark,
    title: 'Evolução constante',
    text: 'Novos exercícios e recursos sendo adicionados sempre.',
  },
]

export function AboutScreen() {
  const recursos = [
    { label: 'Como funciona', href: appHref(`#/guia/${DEFAULT_EXERCISE}`) },
    { label: 'Exercícios', href: appHref('#/exercicios') },
    { label: 'Benefícios', href: null },
    { label: 'Planos', href: null },
  ]

  return (
    <>
      <div className="about">
        <IconLogo className="about__logo" />
        <h1 className="about__title">Sobre o Digital Fit</h1>
        <p className="about__sub">
          Tecnologia de visão computacional para transformar sua forma de treinar.
        </p>

        <div className="about__cards">
          {VALUES.map(({ Icon, title, text }) => (
            <div className="feature" key={title}>
              <span className="feature__icon">
                <Icon />
              </span>
              <div>
                <p className="feature__title">{title}</p>
                <p className="feature__text">{text}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="about__links">
          <p className="about__links-title">Recursos</p>
          {recursos.map(({ label, href }) =>
            href ? (
              <a key={label} className="about__link" href={href}>
                {label}
                <IconChevronRight className="about__link-icon" />
              </a>
            ) : (
              <span key={label} className="about__link about__link--soon" title="Em breve">
                {label}
                <IconChevronRight className="about__link-icon" />
              </span>
            ),
          )}
        </div>

        <p className="about__copyright">© 2025 Digital Fit. Todos os direitos reservados.</p>
      </div>
      <SiteBar active="sobre" />
    </>
  )
}
