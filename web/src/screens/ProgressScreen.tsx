// Tela Progresso (T-068, reescrita na T-124) — a evolução ao longo do tempo.
//
// Até esta task ela mostrava **uma** sessão: o `digitalfit.last_report` do aparelho, com um
// parágrafo dizendo que histórico e sequência de dias eram "em breve". O em breve chegou sem
// backend novo — o `GET /api/sessions?mine` sempre devolveu o relatório inteiro de até 50
// sessões, e o que faltava era alguém lê-lo (SPEC-024).
//
// Nenhum cálculo mora aqui: tudo vem de `history/aggregates.ts`, que é puro e testado. Esta
// tela é desenho, e a régua da SPEC-014 §Desvios continua valendo — sem kcal (depende do peso,
// SPEC-017) e sem fogo/XP (SPEC-019), porque nenhum dos dois é derivável do que já se mede.
import {
  diasComTreino,
  porExercicio,
  porSemana,
  type ResumoSemana,
} from '../history/aggregates'
import { useFreshHistory } from '../history/useFreshHistory'
import { useHistoryStore } from '../history/store'
import { reasonText } from '../report/reportSummary'
import { getExercise } from '../session/catalog'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { useSessionStore } from '../store/session'
import { BrandMark } from '../ui/BrandMark'
import { IconChart, IconCounter, IconPlay, IconPulse } from '../ui/icons'

function segundos(ms: number): string {
  return `${(ms / 1000).toFixed(0)}s`
}

const DIAS_DA_SEMANA = ['S', 'T', 'Q', 'Q', 'S', 'S', 'D']

export function ProgressScreen() {
  const report = useSessionStore((state) => state.report)
  const sessions = useHistoryStore((state) => state.sessions)
  const source = useHistoryStore((state) => state.source)
  const loadError = useHistoryStore((state) => state.loadError)
  useFreshHistory()

  const hoje = new Date()
  const dias = diasComTreino(sessions)
  const semanas = porSemana(sessions, 4, hoje)
  const exercicios = porExercicio(sessions)
  const repsTotais = exercicios.reduce((total, item) => total + item.reps, 0)

  if (sessions.length === 0) {
    return (
      <>
        <div className="panel">
          <Cabecalho />
          <div className="panel__empty">
            <IconChart className="panel__empty-icon" />
            <p className="panel__empty-title">Nenhum treino registrado ainda</p>
            <p className="panel__empty-text">
              Termine uma sessão e o resultado aparece aqui — mesmo sem conta.
            </p>
            <button
              type="button"
              className="v2-cta"
              onClick={() => navigate({ screen: 'preparar' })}
            >
              Treinar agora
              <span className="v2-cta__play">
                <IconPlay className="v2-cta__play-icon" />
              </span>
            </button>
          </div>
        </div>
        <TabBar />
      </>
    )
  }

  return (
    <>
      <div className="panel">
        <Cabecalho />

        <div className="panel__metrics">
          <div className="panel__metric">
            <IconChart className="panel__metric-icon" />
            <p className="panel__metric-value tabular">{sessions.length}</p>
            <p className="v2-label">{sessions.length === 1 ? 'treino' : 'treinos'}</p>
          </div>
          <div className="panel__metric">
            <IconCounter className="panel__metric-icon" />
            <p className="panel__metric-value tabular">{repsTotais}</p>
            <p className="v2-label">repetições</p>
          </div>
          <div className="panel__metric">
            <IconPulse className="panel__metric-icon" />
            <p className="panel__metric-value tabular">{dias.size}</p>
            <p className="v2-label">{dias.size === 1 ? 'dia' : 'dias'}</p>
          </div>
        </div>

        <Mes dias={dias} hoje={hoje} />
        <Semanas semanas={semanas} />
        <PorExercicio exercicios={exercicios} totalDeReps={repsTotais} />

        {report && (
          <>
            <p className="prog__section">Último treino</p>
            <div className="panel__card">
              <p className="panel__card-title">{getExercise(report.exercise).display_name}</p>
              <p className="panel__card-sub">{reasonText(report.reason)}</p>
              <div className="panel__metrics">
                <div className="panel__metric">
                  <IconCounter className="panel__metric-icon" />
                  <p className="panel__metric-value tabular">{report.rep_count}</p>
                  <p className="v2-label">repetições</p>
                </div>
                <div className="panel__metric">
                  <IconPulse className="panel__metric-icon" />
                  <p className="panel__metric-value tabular">{report.cadence_rpm.toFixed(0)}</p>
                  <p className="v2-label">rep/min</p>
                </div>
                <div className="panel__metric">
                  <IconChart className="panel__metric-icon" />
                  <p className="panel__metric-value tabular">{segundos(report.duration_ms)}</p>
                  <p className="v2-label">duração</p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Rótulo honesto (SPEC-024 §3): sem conta, isto é o que ESTE aparelho lembra, e
            limpar o navegador leva embora. O convite vem junto porque é o único remédio. */}
        {source === 'local' && (
          <p className="panel__note">
            Este é o histórico guardado <strong>neste aparelho</strong> — limpar o navegador leva
            embora. Com uma conta, ele fica.
          </p>
        )}
        {loadError && source === 'server' && (
          <p className="panel__note">Não consegui atualizar agora — pode faltar algo recente.</p>
        )}
      </div>
      <TabBar />
    </>
  )
}

function Cabecalho() {
  return (
    <header className="panel__head">
      <BrandMark center />
      <p className="guide__kicker">Progresso</p>
      <h1 className="panel__title">Seu treino ao longo do tempo</h1>
    </header>
  )
}

/**
 * Grade do mês corrente. Dia com treino acende; hoje ganha contorno.
 *
 * Mês de calendário e não "últimos 30 dias" pela mesma razão da semana de calendário nas
 * agregações: a pessoa lê o mês em que está, e uma janela deslizante faria o mesmo treino
 * mudar de lugar todo dia.
 */
function Mes({ dias, hoje }: { dias: Set<string>; hoje: Date }) {
  const primeiro = new Date(hoje.getFullYear(), hoje.getMonth(), 1)
  const totalDeDias = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0).getDate()
  // A grade abre na segunda, como `inicioDaSemana`; `getDay()` devolve 0 para domingo.
  const vazios = (primeiro.getDay() + 6) % 7
  const chaveDeHoje = chaveDoDia(hoje)

  const mes = hoje.toLocaleDateString('pt-BR', { month: 'long' })

  return (
    <>
      <p className="prog__section">
        {mes}
        <span className="prog__section-note tabular">
          {contarNoMes(dias, hoje)} {contarNoMes(dias, hoje) === 1 ? 'dia' : 'dias'}
        </span>
      </p>
      <div className="prog__mes">
        {DIAS_DA_SEMANA.map((letra, indice) => (
          <span className="prog__dia-label" key={`${letra}-${indice}`} aria-hidden="true">
            {letra}
          </span>
        ))}
        {Array.from({ length: vazios }, (_, i) => (
          <span className="prog__dia prog__dia--vazio" key={`vazio-${i}`} />
        ))}
        {Array.from({ length: totalDeDias }, (_, i) => {
          const data = new Date(hoje.getFullYear(), hoje.getMonth(), i + 1)
          const chave = chaveDoDia(data)
          const treinou = dias.has(chave)
          return (
            <span
              key={chave}
              className={`prog__dia ${treinou ? 'prog__dia--treino' : ''} ${
                chave === chaveDeHoje ? 'prog__dia--hoje' : ''
              }`}
              title={treinou ? `Treinou em ${data.toLocaleDateString('pt-BR')}` : undefined}
            >
              {i + 1}
            </span>
          )
        })}
      </div>
    </>
  )
}

/** Mesmo formato do `diaLocal` das agregações — as duas pontas têm de casar. */
function chaveDoDia(data: Date): string {
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${data.getFullYear()}-${mes}-${dia}`
}

function contarNoMes(dias: Set<string>, hoje: Date): number {
  const prefixo = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}-`
  return [...dias].filter((dia) => dia.startsWith(prefixo)).length
}

/** Quatro semanas em barras. A escala é a maior semana — comparação é com a própria pessoa. */
function Semanas({ semanas }: { semanas: ResumoSemana[] }) {
  const maior = semanas.reduce((topo, semana) => Math.max(topo, semana.reps), 0)

  return (
    <>
      <p className="prog__section">Últimas 4 semanas</p>
      <div className="prog__semanas">
        {semanas.map((semana) => (
          <div className="prog__semana" key={semana.inicio.toISOString()}>
            <div className="prog__barra-trilho">
              <div
                className="prog__barra"
                // Semana sem treino fica com o trilho vazio, não com uma barra de 1px: o zero
                // tem de parecer zero.
                style={{ height: maior > 0 ? `${(semana.reps / maior) * 100}%` : '0%' }}
              />
            </div>
            <span className="prog__semana-valor tabular">{semana.reps}</span>
            <span className="prog__semana-label">
              {semana.inicio.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
            </span>
          </div>
        ))}
      </div>
    </>
  )
}

function PorExercicio({
  exercicios,
  totalDeReps,
}: {
  exercicios: ReturnType<typeof porExercicio>
  totalDeReps: number
}) {
  return (
    <>
      <p className="prog__section">Por exercício</p>
      <div className="prog__exercicios">
        {exercicios.map((item) => (
          <div className="prog__exercicio" key={item.exercise}>
            <div className="prog__exercicio-linha">
              <span className="prog__exercicio-nome">
                {getExercise(item.exercise).display_name}
              </span>
              <span className="prog__exercicio-valor tabular">
                {item.reps} <span className="prog__exercicio-unidade">reps</span>
              </span>
            </div>
            <div className="prog__exercicio-trilho">
              <div
                className="prog__exercicio-barra"
                style={{
                  width: totalDeReps > 0 ? `${(item.reps / totalDeReps) * 100}%` : '0%',
                }}
              />
            </div>
            <span className="prog__exercicio-sub">
              {item.sessoes} {item.sessoes === 1 ? 'treino' : 'treinos'}
            </span>
          </div>
        ))}
      </div>
    </>
  )
}
