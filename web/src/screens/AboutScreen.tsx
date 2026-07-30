// Tela Sobre / footer mobile (SPEC-014 §5, tela 5 da referência).
import { exercisePreference } from '../session/preferences'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { IconChevronRight, IconLogo, IconShieldCheck, IconSpark, IconTarget } from '../ui/icons'

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
    { label: 'Como funciona', go: () => navigate({ screen: 'guia', exercise: exercisePreference() }) },
    { label: 'Exercícios', go: () => navigate({ screen: 'exercicios' }) },
    { label: 'Benefícios', go: null },
    { label: 'Planos', go: null },
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
          {recursos.map(({ label, go }) => (
            <button
              key={label}
              type="button"
              className="about__link"
              onClick={go ?? undefined}
              aria-disabled={go ? undefined : true}
              title={go ? undefined : 'Em breve'}
              style={go ? undefined : { opacity: 0.5, cursor: 'default' }}
            >
              {label}
              <IconChevronRight className="about__link-icon" />
            </button>
          ))}
        </div>

        <p className="about__copyright">© 2025 Digital Fit. Todos os direitos reservados.</p>
      </div>
      <TabBar />
    </>
  )
}
