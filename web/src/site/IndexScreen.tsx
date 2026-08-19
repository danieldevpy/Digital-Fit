// Index / landing (SPEC-014 §1). Única tela responsiva do produto: mobile segue a tela 1
// de `app-completo-mobile.png`; ≥ 900px segue `index.png` (nav, hero em 2 colunas com
// mini-HUD decorativo, seção de exercícios e footer). O mini-HUD é markup estático — a
// SPEC-014 proíbe montar câmera/sessão fora do fluxo de treino.
//
// Desde a T-067 esta tela é o SITE: todo botão que leva a treinar é um `<a href>` para o
// app, não um `navigate()`. O app pode estar em outro host, e ali `#/preparar` não existe.
import { useT, useLocale } from '../i18n'
import { DEFAULT_EXERCISE } from '../session/catalog'
import { appHref, siteRouteHref } from '../shell/origins'
import {
  IconAngle,
  IconCounter,
  IconFlame,
  IconHeart,
  IconLogo,
  IconPlay,
  IconPulse,
  IconSeries,
  IconShieldCheck,
  IconSpark,
  IconTarget,
} from '../ui/icons'
import { ExerciseCards } from '../screens/ExerciseCards'
import { SiteBar } from './SiteBar'

function Brand({ mobile = false }: { mobile?: boolean }) {
  const t = useT()

  return (
    <div className={`landing__brand ${mobile ? 'landing__brand--mobile' : ''}`}>
      <IconLogo className="landing__logo" />
      <div>
        {/* "DIGITAL FIT" é o nome da marca, não texto de produto — fica igual nas duas
            línguas (mesma razão de `Category` guardar `forca`, não `"Força"`: aqui o
            valor literal É o dado, não uma frase a traduzir). */}
        <p className="landing__brand-name">
          DIGITAL <em>FIT</em>
        </p>
        <p className="landing__brand-sub">{t('site:brand.tagline')}</p>
      </div>
    </div>
  )
}

// Só o ícone é estático aqui (T-147, namespace `site`): título e texto vêm de `t()` a cada
// render, mesmo raciocínio do `TABS` de `shell/TabBar.tsx`.
const FEATURES = [
  { id: 'realtime', Icon: IconTarget },
  { id: 'count', Icon: IconCounter },
  { id: 'correct', Icon: IconShieldCheck },
] as const

export function IndexScreen() {
  const t = useT()
  // O rodapé aponta dez links institucionais para o Sobre — a tela que ainda não existe
  // separada para cada assunto (Planos, Privacidade, Termos...). Desde a T-158 é um CAMINHO
  // (`/sobre/`, `/en/about/`), não `#/sobre`: fragmento não viaja no pedido e o buscador nunca
  // via essas páginas. O idioma vem do store, que o `SiteApp` sincroniza com o `<html lang>`
  // deste documento — ou seja, com a URL.
  const locale = useLocale()
  const sobreHref = siteRouteHref('sobre', locale)

  return (
    <div className="landing">
      <div className="landing__scroll">
        <nav className="landing__nav">
          <Brand />
          {/* "Entrar" leva ao app porque é lá que a conta mora: o token fica no localStorage,
              que é por origem — entrar aqui não deixaria ninguém logado no app. */}
          <a className="landing__enter" href={appHref('#/entrar')}>
            {t('site:nav.enter')}
          </a>
        </nav>

        <Brand mobile />

        <div className="landing__hero-grid">
          <div>
            <span className="landing__badge">
              <IconSpark className="landing__badge-icon" /> {t('site:hero.badge')}
            </span>
            <h1 className="landing__title">
              {t('site:hero.title_top')}
              <br />
              <em>{t('site:hero.title_bottom')}</em>
            </h1>
            <p className="landing__copy">{t('site:hero.copy')}</p>

            <div className="landing__hero landing__hero--mobile">
              <img src="/img/hero-female.jpg" alt={t('site:hero.image_alt')} />
            </div>

            <div className="landing__features">
              {FEATURES.map(({ id, Icon }) => (
                <div className="feature" key={id}>
                  <span className="feature__icon">
                    <Icon />
                  </span>
                  <div>
                    <p className="feature__title">{t(`site:feature.${id}.title`)}</p>
                    <p className="feature__text">{t(`site:feature.${id}.text`)}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="landing__cta">
              <a className="v2-cta" href={appHref('#/exercicios')}>
                {t('site:cta.start')}
                <span className="v2-cta__play">
                  <IconPlay className="v2-cta__play-icon" />
                </span>
              </a>
            </div>
            {/* Exercício padrão, e não a preferência: preferência é do aparelho na origem do
                APP, e o site não a conhece. Prometer "o seu último exercício" aqui seria
                chutar. */}
            <a className="landing__how" href={appHref(`#/guia/${DEFAULT_EXERCISE}`)}>
              <IconPlay className="landing__how-icon" /> {t('site:cta.how_it_works')}
            </a>
          </div>

          {/* Mini-HUD decorativo do index.png — números de amostra, marcados como tal. */}
          <div className="landing__mock" aria-hidden="true">
            <img src="/img/hero-female.jpg" alt="" />
            <div className="mock-stats">
              <div className="mock-stats__cell">
                <IconSeries className="stats__icon" />
                <p className="mock-stats__value">1/1</p>
              </div>
              <div className="mock-stats__cell">
                <IconPulse className="stats__icon" />
                <p className="mock-stats__value">12</p>
              </div>
              <div className="mock-stats__cell">
                <IconAngle className="stats__icon" />
                {/* Número de amostra do mock decorativo (aria-hidden acima) — grau é
                    unidade, não texto de produto; mesma unidade nas duas línguas. */}
                {/* eslint-disable-next-line i18next/no-literal-string */}
                <p className="mock-stats__value">176°</p>
              </div>
              <div className="mock-stats__cell">
                <IconFlame className="stats__icon stats__icon--flame" />
                <p className="mock-stats__value">87</p>
              </div>
              <div className="mock-stats__cell">
                <IconHeart className="stats__icon" />
                <p className="mock-stats__value">124</p>
              </div>
            </div>
            <div className="mock-pill">
              <p className="mock-pill__name">{t('site:mock.exercise_name')}</p>
              <p className="mock-pill__sub">{t('site:mock.exercise_sub')}</p>
            </div>
          </div>
        </div>

        <div className="landing__choose">
          <div className="landing__section-title">
            <p className="guide__kicker">{t('site:choose.kicker')}</p>
            <p className="choose__subtitle">
              {t('site:choose.subtitle_top')} <em>{t('site:choose.subtitle_em')}</em>
            </p>
          </div>
          {/* Cada card é um link para o app, que decide Guia ou Pré-config (SPEC-015) — a
              decisão depende do localStorage de lá. */}
          <ExerciseCards />
        </div>

        <footer className="landing__footer">
          <div className="landing__footer-col">
            <Brand />
            <p>{t('site:footer.tagline')}</p>
          </div>
          <div className="landing__footer-col">
            <h3>{t('site:footer.heading.resources')}</h3>
            <a href={appHref(`#/guia/${DEFAULT_EXERCISE}`)}>{t('site:footer.link.how_it_works')}</a>
            <a href={appHref('#/exercicios')}>{t('site:footer.link.exercises')}</a>
            <a href={sobreHref}>{t('site:footer.link.benefits')}</a>
            <a href={sobreHref}>{t('site:footer.link.plans')}</a>
          </div>
          <div className="landing__footer-col">
            <h3>{t('site:footer.heading.about')}</h3>
            <a href={sobreHref}>{t('site:footer.link.who_we_are')}</a>
            <a href={sobreHref}>{t('site:footer.link.privacy')}</a>
            <a href={sobreHref}>{t('site:footer.link.terms')}</a>
            <a href={sobreHref}>{t('site:footer.link.contact')}</a>
          </div>
          <div className="landing__footer-col">
            <h3>{t('site:footer.heading.support')}</h3>
            <a href={sobreHref}>{t('site:footer.link.help_center')}</a>
            <a href={sobreHref}>{t('site:footer.link.faq')}</a>
            <a href={sobreHref}>{t('site:footer.link.talk_to_us')}</a>
            <a href={sobreHref}>{t('site:footer.link.status')}</a>
          </div>
          <p className="landing__copyright">{t('site:footer.copyright')}</p>
        </footer>
      </div>

      {/* A tab bar do app (Início/Progresso/Analytics/Perfil) não cabe aqui: são as telas de
          treino, que vivem no outro bundle. O site tem barra própria, e o item que importa
          nela é a porta do app. */}
      <div className="landing__tabbar">
        <SiteBar active="index" />
      </div>
    </div>
  )
}
