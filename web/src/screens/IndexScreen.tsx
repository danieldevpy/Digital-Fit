// Index / landing (SPEC-014 §1). Única tela responsiva do produto: mobile segue a tela 1
// de `app-completo-mobile.png`; ≥ 900px segue `index.png` (nav, hero em 2 colunas com
// mini-HUD decorativo, seção de exercícios e footer). O mini-HUD é markup estático — a
// SPEC-014 proíbe montar câmera/sessão fora do fluxo de treino.
import { exercisePreference } from '../session/preferences'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { useAccountStore } from '../store/account'
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
import { ExerciseCards } from './ExerciseCards'

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
  const openAccount = useAccountStore((state) => state.openSheet)

  return (
    <div className="landing">
      <div className="landing__scroll">
        <nav className="landing__nav">
          <Brand />
          <button type="button" className="landing__enter" onClick={() => openAccount(true)}>
            Entrar
          </button>
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
              <img src="/img/hero.jpg" alt="Pessoa treinando com esqueleto de análise neon" />
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
              <button
                type="button"
                className="v2-cta"
                onClick={() => navigate({ screen: 'exercicios' })}
              >
                Começar Treino
                <span className="v2-cta__play">
                  <IconPlay className="v2-cta__play-icon" />
                </span>
              </button>
            </div>
            <button
              type="button"
              className="landing__how"
              onClick={() => navigate({ screen: 'guia', exercise: exercisePreference() })}
            >
              <IconPlay className="landing__how-icon" /> Ver como funciona
            </button>
          </div>

          {/* Mini-HUD decorativo do index.png — números de amostra, marcados como tal. */}
          <div className="landing__mock" aria-hidden="true">
            <img src="/img/hero.jpg" alt="" />
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
          <ExerciseCards grid />
        </div>

        <footer className="landing__footer">
          <div className="landing__footer-col">
            <Brand />
            <p>Tecnologia de visão computacional para transformar sua forma de treinar.</p>
          </div>
          <div className="landing__footer-col">
            <h3>Recursos</h3>
            <a href="#/guia/jumping_jack">Como funciona</a>
            <a href="#/exercicios">Exercícios</a>
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

      <div className="landing__tabbar">
        <TabBar />
      </div>
    </div>
  )
}
