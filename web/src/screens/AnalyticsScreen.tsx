// Tela Analytics (T-068) — aba própria na bottom nav.
//
// Declarada, não simulada. Analytics é a leitura FINA do treino (qualidade de execução,
// cadência por janela, o que mais aparece como correção) e ela já existe num lugar: a folha
// de relatório do fim da sessão (SPEC-010). O que falta é o acúmulo entre sessões, que
// depende do histórico da SPEC-011/017. Até lá esta tela diz isso e leva ao que existe, em
// vez de mostrar gráfico com número de exemplo.
import { useFreshHistory } from '../history/useFreshHistory'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { useSessionStore } from '../store/session'
import { BrandMark } from '../ui/BrandMark'
import { IconAngle, IconChevronRight, IconPulse, IconTarget } from '../ui/icons'

const PROXIMOS = [
  {
    Icon: IconPulse,
    title: 'Cadência entre sessões',
    text: 'Como seu ritmo muda de um treino para o outro, por janela de 5 segundos.',
  },
  {
    Icon: IconAngle,
    title: 'Qualidade de execução',
    text: 'Quais correções mais aparecem e se elas diminuem com o tempo.',
  },
  {
    Icon: IconTarget,
    title: 'Metas e constância',
    text: 'Sequência de dias treinados e meta semanal (SPEC-017).',
  },
]

export function AnalyticsScreen() {
  const report = useSessionStore((state) => state.report)
  const reopenReport = useSessionStore((state) => state.reopenReport)
  // Mesma razão da ProgressScreen: o frescor entra antes do desenho (T-125), para a tela nova
  // não nascer com o defeito que a spec conserta.
  useFreshHistory()

  return (
    <>
      <div className="panel">
        <header className="panel__head">
          <BrandMark center />
          <p className="guide__kicker">Analytics</p>
          <h1 className="panel__title">Análise do treino</h1>
        </header>

        {report && (
          <button type="button" className="panel__link" onClick={reopenReport}>
            <span>
              <span className="panel__link-title">Abrir a análise do último treino</span>
              <span className="panel__link-sub">
                Cadência, repetições e o que melhorar — o relatório completo da sessão.
              </span>
            </span>
            <IconChevronRight className="panel__link-icon" />
          </button>
        )}

        <p className="panel__note">
          A análise por sessão já existe (é o relatório do fim do treino). O que vem a seguir é
          a comparação entre sessões:
        </p>

        <div className="panel__list">
          {PROXIMOS.map(({ Icon, title, text }) => (
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

        {!report && (
          <button
            type="button"
            className="panel__ghost"
            onClick={() => navigate({ screen: 'preparar' })}
          >
            Fazer um treino para ter o que analisar
          </button>
        )}
      </div>
      <TabBar />
    </>
  )
}
