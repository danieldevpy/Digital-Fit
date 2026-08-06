// Index / landing (SPEC-014 §1). Única tela responsiva do produto: mobile segue a tela 1
// de `app-completo-mobile.png`; ≥ 900px segue `index.png` (nav, hero em 2 colunas com
// mini-HUD decorativo, seção de exercícios e footer). O mini-HUD é markup estático — a
// SPEC-014 proíbe montar câmera/sessão fora do fluxo de treino.
//
// Desde a T-067 esta tela é o SITE: todo botão que leva a treinar é um `<a href>` para o
// app, não um `navigate()`. O app pode estar em outro host, e ali `#/preparar` não existe.
import { DEFAULT_EXERCISE } from '../session/catalog'
import { appHref } from '../shell/origins'
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
  return (
    <div className={`landing__brand ${mobile ? 'landing__brand--mobile' : ''}`}>
      <IconLogo className="landing__logo" />
      <div>
        <p className="landing__brand-name">
          DIGITAL <em>FIT</em>
        </p>
        <p className="landing__brand-sub">Seu treino. Sua evolução.</p>
      </div>
    </div>
  )
}

const FEATURES = [
  {
    Icon: IconTarget,
    title: 'Análise em Tempo Real',
    text: 'Feedback instantâneo enquanto você se movimenta.',
  },
  {
    Icon: IconCounter,
    title: 'Conte Repetições',
    text: 'Contagem precisa de cada repetição ao longo da série.',
  },
  {
    Icon: IconShieldCheck,
    title: 'Corrija sua Execução',
    text: 'Dicas visuais para melhorar sua postura e performance.',
  },
]

export function IndexScreen() {
  return (
    <div className="landing">
      <div className="landing__scroll">
        <nav className="landing__nav">
          <Brand />
          {/* "Entrar" leva ao app porque é lá que a conta mora: o token fica no localStorage,
              que é por origem — entrar aqui não deixaria ninguém logado no app. */}
          <a className="landing__enter" href={appHref('#/entrar')}>
            Entrar
          </a>
        </nav>

        <Brand mobile />

        <div className="landing__hero-grid">
          <div>
            <span className="landing__badge">
              <IconSpark className="landing__badge-icon" /> Inteligência que te move
            </span>
            <h1 className="landing__title">
              Treine melhor.
              <br />
              <em>Evolua</em> sempre.
            </h1>
            <p className="landing__copy">
              O Digital Fit usa visão computacional para analisar seus movimentos em tempo
              real, contar repetições, corrigir sua execução e classificar o exercício.
            </p>

            <div className="landing__hero landing__hero--mobile">
              <img src="/img/hero-female.jpg" alt="Pessoa treinando com esqueleto de análise neon" />
            </div>

            <div className="landing__features">
              {FEATURES.map(({ Icon, title, text }) => (
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

            <div className="landing__cta">
              <a className="v2-cta" href={appHref('#/exercicios')}>
                Começar Treino
                <span className="v2-cta__play">
                  <IconPlay className="v2-cta__play-icon" />
                </span>
              </a>
            </div>
            {/* Exercício padrão, e não a preferência: preferência é do aparelho na origem do
                APP, e o site não a conhece. Prometer "o seu último exercício" aqui seria
                chutar. */}
            <a className="landing__how" href={appHref(`#/guia/${DEFAULT_EXERCISE}`)}>
              <IconPlay className="landing__how-icon" /> Ver como funciona
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
              <p className="mock-pill__name">POLICHINELO</p>
              <p className="mock-pill__sub">Cardio • Corpo inteiro</p>
            </div>
          </div>
        </div>

        <div className="landing__choose">
          <div className="landing__section-title">
            <p className="guide__kicker">Escolha seu exercício</p>
            <p className="choose__subtitle">
              Treinos rápidos, <em>resultados reais</em>
            </p>
          </div>
          {/* Cada card é um link para o app, que decide Guia ou Pré-config (SPEC-015) — a
              decisão depende do localStorage de lá. */}
          <ExerciseCards />
        </div>

        <footer className="landing__footer">
          <div className="landing__footer-col">
            <Brand />
            <p>Tecnologia de visão computacional para transformar sua forma de treinar.</p>
          </div>
          <div className="landing__footer-col">
            <h3>Recursos</h3>
            <a href={appHref(`#/guia/${DEFAULT_EXERCISE}`)}>Como funciona</a>
            <a href={appHref('#/exercicios')}>Exercícios</a>
            <a href="#/sobre">Benefícios</a>
            <a href="#/sobre">Planos</a>
          </div>
          <div className="landing__footer-col">
            <h3>Sobre</h3>
            <a href="#/sobre">Quem somos</a>
            <a href="#/sobre">Privacidade</a>
            <a href="#/sobre">Termos de uso</a>
            <a href="#/sobre">Contato</a>
          </div>
          <div className="landing__footer-col">
            <h3>Suporte</h3>
            <a href="#/sobre">Central de ajuda</a>
            <a href="#/sobre">FAQ</a>
            <a href="#/sobre">Fale conosco</a>
            <a href="#/sobre">Status</a>
          </div>
          <p className="landing__copyright">© 2025 Digital Fit. Todos os direitos reservados.</p>
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
