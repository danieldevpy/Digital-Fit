// Liga a tela de sessão ao gateway. Caminho padrão: `POST /api/sessions` (T-011) devolve o
// ticket e o WS abre no `ws_url` dele. Com `VITE_WS_URL` definida, fala com o mock local.
import { useEffect, useState } from 'react'
import {
  EventType,
  Source,
  makeEnvelope,
  type Envelope,
  type ExercisePhaseData,
  type FeedbackIssuedData,
  type RepDetectedData,
  type SessionCalibratedData,
  type SceneWarningData,
  type SessionCompletedData,
  type SessionStartedData,
} from '../lib/events'
import { connectGateway, gatewayUrl, type GatewayClient } from '../lib/gateway'
import { toCapabilityData } from '../probe/runProbe'
import { waitForReport } from '../report/sessionReport'
import { useAccountStore } from '../store/account'
import { useSessionStore } from '../store/session'
import { AdmissionError, TRIAL_EXHAUSTED, modeToRequest, requestSession } from './admission'
import { exercisePreference } from './preferences'
import { entryFromEvent } from './coachCard'
import { setGatewayClient, startNewSequence } from './gatewayInstance'

function handle(envelope: Envelope) {
  const store = useSessionStore.getState()
  const now = Date.now()

  switch (envelope.type) {
    case EventType.SESSION_CALIBRATED: {
      // Marco de "corpo MEDIDO" — não mais de "contagem começou" (T-049). Entre um e outro
      // pode haver a preparação, e é o worker quem a segura: ele não alimenta a FSM antes do
      // prazo. O cliente só desenha o "3, 2, 1" em cima do mesmo número.
      const preparo = (envelope.data as SessionCalibratedData).countdown_ms ?? 0
      store.applyCalibrated(now, preparo)
      if (preparo > 0) {
        // O `setTimeout` é cosmético: se ele atrasar, o placar não sai errado — quem decide
        // o que conta é o servidor. Ele só troca o estado da tela na hora certa.
        setTimeout(() => useSessionStore.getState().startCounting(), preparo)
      }
      break
    }
    case EventType.SESSION_STARTED:
      store.applySessionStarted(envelope.data as SessionStartedData, envelope.session_id)
      break
    case EventType.REP_DETECTED:
      store.applyRepDetected(envelope.data as RepDetectedData)
      break
    case EventType.EXERCISE_PHASE:
      store.applyPhase((envelope.data as ExercisePhaseData).phase)
      break
    case EventType.SCENE_WARNING:
      store.applySceneWarning(entryFromEvent(envelope.data as SceneWarningData, now))
      break
    case EventType.FEEDBACK_ISSUED:
      store.applyFeedback(entryFromEvent(envelope.data as FeedbackIssuedData, now))
      break
    case EventType.SESSION_COMPLETED:
      store.applySessionCompleted(envelope.data as SessionCompletedData)
      // O relatório ainda não existe neste instante — o report-builder acabou de receber o
      // mesmo evento. A busca já começa aqui mesmo assim: ela tolera "ainda não" e é o que
      // salva a tela quando o aviso de pronto não chega (WS caído, por exemplo).
      void buscarRelatorio(envelope.session_id)
      break
    case EventType.SESSION_REPORT_READY:
      // Caminho feliz: o relatório está gravado, a próxima tentativa já traz o conteúdo.
      void buscarRelatorio(envelope.session_id)
      break
    default:
      // pose.frame e quality.signal não são empurrados ao cliente (CLIENT_PUSH_TYPES).
      console.warn('[sessão] tipo inesperado vindo do gateway:', envelope.type)
  }
}

/**
 * Busca o relatório uma vez por sessão, venha o gatilho de onde vier.
 *
 * `session.completed` e `session.report.ready` chamam esta função, e no caminho normal os
 * dois chegam. O guarda é o `reportStatus`: `startReport()` só sai de `idle` uma vez, então a
 * segunda chamada não dispara uma segunda espera — nem reabre a tela que o usuário fechou.
 */
async function buscarRelatorio(sessionId: string): Promise<void> {
  const store = useSessionStore.getState()
  if (store.reportStatus !== 'idle') return
  store.startReport()

  try {
    const relatorio = await waitForReport(sessionId)
    if (relatorio) useSessionStore.getState().applyReport(relatorio)
    else useSessionStore.getState().failReport()
  } catch {
    // O erro não sobe: a sessão acabou, e a contagem que o usuário viu ao vivo continua certa.
    // O relatório é um detalhamento — perdê-lo não invalida o treino.
    useSessionStore.getState().failReport()
  }
}

/**
 * Alvo do WebSocket quando se está falando com o **mock** (`VITE_WS_URL` definida).
 * O mock não tem admissão: id e token são de mentira, de propósito.
 */
function mockSessionTarget(): SessionTarget {
  const params = new URLSearchParams(window.location.search)
  const random =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10)
  const sessionId = params.get('session') ?? `dev-${random}`
  const token = params.get('token') ?? import.meta.env.VITE_WS_TOKEN ?? null
  return { sessionId, url: gatewayUrl({ sessionId, token }) }
}

export interface SessionTarget {
  sessionId: string
  /** URL completa do WS. No caminho real vem pronta no ticket — não é remontada aqui. */
  url: string
}

/** Mock só quando pedido explicitamente; o padrão é a API real (SPEC-009). */
export function usandoMock(): boolean {
  return Boolean(import.meta.env.VITE_WS_URL)
}

export function useSession(enabled: boolean) {
  const [target, setTarget] = useState<SessionTarget | null>(null)

  useEffect(() => {
    if (!enabled) return

    let cancelado = false
    let client: GatewayClient | null = null
    const store = useSessionStore.getState()
    store.resetSession()
    store.setError(null)
    const sequencer = startNewSequence()

    const conectar = (alvo: SessionTarget) => {
      client = connectGateway(alvo.url, {
        onEvent: handle,
        onStatus: (status) => {
          useSessionStore.getState().setGatewayStatus(status)

          // No caminho real a capability já foi com o `POST /api/sessions` (o servidor
          // publica o evento). No mock não há admissão, então vai por aqui.
          if (status !== 'open' || !usandoMock()) return
          const capability = useSessionStore.getState().capability
          if (!capability || !client) return
          client.send(
            makeEnvelope({
              type: EventType.SESSION_CAPABILITY,
              session_id: alvo.sessionId,
              ts: Date.now(),
              seq: sequencer.next(),
              source: Source.EDGE,
              data: toCapabilityData(capability),
            }),
          )
        },
      })
      setGatewayClient(client)
      setTarget(alvo)
    }

    if (usandoMock()) {
      conectar(mockSessionTarget())
    } else {
      const { modeOverride, capability } = useSessionStore.getState()
      useSessionStore.getState().setGatewayStatus('connecting')
      void requestSession({
        // A escolha de quem treina (T-051), lida no instante do pedido. Antes era
        // `DEFAULT_EXERCISE` fixo, e o produto não tinha como pedir outra coisa.
        exercise: exercisePreference(),
        requestedMode: modeToRequest(modeOverride, capability),
        probe: capability,
      })
        .then((ticket) => {
          if (cancelado) return
          // Quanto do trial sobrou (SPEC-011). Vem `null`/ausente para quem tem conta.
          useAccountStore.getState().setTrial(ticket.trial ?? null)
          // O ticket é a única fonte de `session_id` no caminho real: `session.started` não
          // está nos CLIENT_PUSH_TYPES, então ele nunca chega pelo WS. Sem isto o cliente
          // não sabe em nome de quem enviar `pose.frame` — e não envia nada.
          useSessionStore.getState().applyTicket({
            sessionId: ticket.session_id,
            exercise: ticket.exercise,
            durationS: ticket.duration_s,
          })
          // `ws_url` vem pronto do ticket, com o token — usar como veio.
          conectar({ sessionId: ticket.session_id, url: ticket.ws_url })
        })
        .catch((erro: unknown) => {
          if (cancelado) return
          const store = useSessionStore.getState()
          store.setError(
            erro instanceof AdmissionError ? erro.message : 'Falha ao abrir a sessão.',
          )
          store.setGatewayStatus('error')
          // Trial esgotado não é falha de infraestrutura: a ação certa é criar conta, então
          // a tela de conta abre sozinha com o motivo (SPEC-011, critério 1).
          if (erro instanceof AdmissionError && erro.code === TRIAL_EXHAUSTED) {
            useAccountStore.getState().blockByTrial()
          }
        })
    }

    return () => {
      cancelado = true
      client?.close()
      setGatewayClient(null)
      setTarget(null)
      const current = useSessionStore.getState()
      current.setGatewayStatus('idle')
      current.resetSession()
    }
  }, [enabled])

  return target
}
