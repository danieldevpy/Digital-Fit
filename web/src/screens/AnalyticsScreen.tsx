// Tela Analytics (T-068, reescrita na T-125) — a leitura FINA do treino, entre sessões.
//
// Até esta task era uma lista de três bullets declarando o que viria. O que faltava não era
// dado: `GET /api/sessions?mine` sempre devolveu `cadence_rpm`, `rep_durations_ms`,
// `feedback_counts` e `scene_warning_counts` de até 50 sessões (SPEC-024).
//
// A régua desta tela é o §5 da spec: **abaixo de 2 sessões do mesmo exercício, nada de
// tendência**. Aqui isso não é um `if` que alguém precisa lembrar — vem no `tendencia` de
// cada série, calculado em `aggregates.ts`.
import { historyDate } from '../auth/accountSummary'
import {
  cadenciaPorExercicio,
  consistenciaDoRitmo,
  contagens,
  type Contagem,
  type SerieCadencia,
} from '../history/aggregates'
import { useHistoryStore } from '../history/store'
import { useFreshHistory } from '../history/useFreshHistory'
import type { SessionReport } from '../report/sessionReport'
import { getExercise } from '../session/catalog'
import { textForCode } from '../session/coachCard'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { useSessionStore } from '../store/session'
import { BrandMark } from '../ui/BrandMark'
import { IconAngle, IconChevronRight, IconTarget } from '../ui/icons'

/** Quantas sessões recentes entram no bloco de constância. Além disso vira parede de números. */
const SESSOES_NO_RITMO = 6

export function AnalyticsScreen() {
  const report = useSessionStore((state) => state.report)
  const reopenReport = useSessionStore((state) => state.reopenReport)
  const sessions = useHistoryStore((state) => state.sessions)
  useFreshHistory()

  const series = cadenciaPorExercicio(sessions)
  const correcoes = contagens(sessions, 'feedback_counts')
  const cena = contagens(sessions, 'scene_warning_counts')

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

        {sessions.length === 0 ? (
          <>
            <p className="panel__note">
              A análise entre sessões nasce do seu histórico. Faça um treino e ela começa a
              existir — a análise de uma sessão só já é o relatório do fim do treino.
            </p>
            <button
              type="button"
              className="panel__ghost"
              onClick={() => navigate({ screen: 'preparar' })}
            >
              Fazer um treino para ter o que analisar
            </button>
          </>
        ) : (
          <>
            <Ritmo series={series} />
            <Constancia sessions={sessions} />
            <Lista
              titulo="O que mais aparece"
              Icon={IconAngle}
              itens={correcoes}
              vazio="Nenhuma correção registrada — execução limpa nas sessões guardadas."
            />
            <Lista
              titulo="Enquadramento"
              Icon={IconTarget}
              itens={cena}
              vazio="Nenhum aviso de cena. A câmera te viu bem em todas as sessões."
            />
          </>
        )}
      </div>
      <TabBar />
    </>
  )
}

/**
 * Cadência ao longo do tempo, uma linha por exercício.
 *
 * Série com um ponto **não vira linha** (SPEC-024 §5): a tela diz o que falta para ela
 * existir. Um gráfico de um ponto sugeriria uma tendência que ninguém mediu.
 */
function Ritmo({ series }: { series: SerieCadencia[] }) {
  return (
    <>
      <p className="prog__section">
        Ritmo por exercício
        <span className="prog__section-note">rep/min</span>
      </p>
      <div className="prog__exercicios">
        {series.map((serie) => {
          const nome = getExercise(serie.exercise).display_name
          const valores = serie.pontos.map((ponto) => ponto.cadence_rpm)
          const ultimo = valores[valores.length - 1] ?? 0

          if (!serie.tendencia) {
            return (
              <div className="ana__serie" key={serie.exercise}>
                <div className="prog__exercicio-linha">
                  <span className="prog__exercicio-nome">{nome}</span>
                  <span className="prog__exercicio-valor tabular">{ultimo.toFixed(0)}</span>
                </div>
                {/* O que falta, dito com todas as letras — em vez de uma linha de um ponto. */}
                <span className="ana__falta">
                  Mais um treino de {nome.toLowerCase()} e o ritmo vira linha.
                </span>
              </div>
            )
          }

          const menor = Math.min(...valores)
          const maior = Math.max(...valores)
          return (
            <div className="ana__serie" key={serie.exercise}>
              <div className="prog__exercicio-linha">
                <span className="prog__exercicio-nome">{nome}</span>
                <span className="prog__exercicio-valor tabular">{ultimo.toFixed(0)}</span>
              </div>
              <Linha valores={valores} />
              <span className="prog__exercicio-sub">
                de {menor.toFixed(0)} a {maior.toFixed(0)} rep/min em {valores.length} treinos
              </span>
            </div>
          )
        })}
      </div>
    </>
  )
}

/**
 * Linha simples em SVG. Sem biblioteca: são pontos numa `polyline`, e trazer um motor de
 * gráfico para isso engordaria o bundle de um app que roda inferência de pose no celular.
 *
 * A escala é o próprio intervalo da série, como o `cadenceBars` do relatório: escala fixa
 * achataria a variação que o gráfico existe para mostrar.
 */
function Linha({ valores }: { valores: number[] }) {
  const largura = 100
  const altura = 28
  const menor = Math.min(...valores)
  const maior = Math.max(...valores)
  const vao = maior - menor

  const pontos = valores
    .map((valor, indice) => {
      const x = valores.length === 1 ? largura / 2 : (indice / (valores.length - 1)) * largura
      // Série constante desenha no meio: dividir por zero mandaria a linha para fora do quadro.
      const y = vao === 0 ? altura / 2 : altura - ((valor - menor) / vao) * altura
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <svg
      className="ana__linha"
      viewBox={`-2 -2 ${largura + 4} ${altura + 4}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <polyline points={pontos} />
      {valores.map((valor, indice) => {
        const x = valores.length === 1 ? largura / 2 : (indice / (valores.length - 1)) * largura
        const y = vao === 0 ? altura / 2 : altura - ((valor - menor) / vao) * altura
        return <circle key={`${indice}-${valor}`} cx={x} cy={y} r={1.8} />
      })}
    </svg>
  )
}

/**
 * Constância do ritmo, sessão a sessão.
 *
 * Mostrado como `±X%` e não como coeficiente de variação: "±12%" é uma frase que alguém
 * entende sobre o próprio treino; "0,12" é um número de estatística. Sessão com menos de duas
 * repetições não entra — lá a dispersão não existe, e `0%` afirmaria uma regularidade perfeita
 * que ninguém mediu.
 */
function Constancia({ sessions }: { sessions: SessionReport[] }) {
  const linhas = sessions
    .map((sessao) => ({ sessao, cv: consistenciaDoRitmo(sessao) }))
    .filter((linha): linha is { sessao: SessionReport; cv: number } => linha.cv !== null)
    .slice(0, SESSOES_NO_RITMO)

  if (linhas.length === 0) {
    return (
      <>
        <p className="prog__section">Constância do ritmo</p>
        <p className="panel__note">
          Precisa de sessões com pelo menos duas repetições para medir variação de ritmo.
        </p>
      </>
    )
  }

  // A barra é relativa à pior sessão da lista: o que interessa é comparar consigo mesmo.
  const pior = linhas.reduce((topo, linha) => Math.max(topo, linha.cv), 0)

  return (
    <>
      <p className="prog__section">
        Constância do ritmo
        <span className="prog__section-note">menor é mais regular</span>
      </p>
      <div className="prog__exercicios">
        {linhas.map(({ sessao, cv }) => (
          <div key={sessao.session_id}>
            <div className="prog__exercicio-linha">
              <span className="prog__exercicio-nome">
                {getExercise(sessao.exercise).display_name}
              </span>
              <span className="prog__exercicio-valor tabular">±{(cv * 100).toFixed(0)}%</span>
            </div>
            <div className="prog__exercicio-trilho">
              <div
                className="ana__ritmo-barra"
                style={{ width: pior > 0 ? `${(cv / pior) * 100}%` : '0%' }}
              />
            </div>
            <span className="prog__exercicio-sub">{historyDate(sessao.created_at)}</span>
          </div>
        ))}
      </div>
    </>
  )
}

const RUMO_TEXTO: Record<string, { texto: string; classe: string }> = {
  caindo: { texto: 'diminuindo', classe: 'ana__rumo--bom' },
  subindo: { texto: 'aumentando', classe: 'ana__rumo--ruim' },
  estavel: { texto: 'estável', classe: '' },
}

/** Correções e avisos de cena: mesma forma, porque para quem treina é a mesma pergunta. */
function Lista({
  titulo,
  Icon,
  itens,
  vazio,
}: {
  titulo: string
  Icon: (props: { className?: string }) => React.ReactNode
  itens: Contagem[]
  vazio: string
}) {
  return (
    <>
      <p className="prog__section">{titulo}</p>
      {itens.length === 0 ? (
        <p className="panel__note">{vazio}</p>
      ) : (
        <div className="prog__exercicios">
          {itens.map((item) => {
            const rumo = item.rumo === null ? null : RUMO_TEXTO[item.rumo]
            return (
              <div className="ana__item" key={item.key}>
                <span className="feature__icon ana__item-icon">
                  <Icon />
                </span>
                <div className="ana__item-corpo">
                  <p className="ana__item-texto">{textForCode(item.key)}</p>
                  {/* Sem rumo, nada é dito: uma sessão só não tem duas metades para comparar. */}
                  {rumo && (
                    <p className={`ana__rumo ${rumo.classe}`}>{rumo.texto} entre as sessões</p>
                  )}
                </div>
                <span className="ana__item-valor tabular">{item.total}</span>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}
