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
  type SceneWarningData,
  type SessionCompletedData,
  type SessionStartedData,
} from '../lib/events'
import { connectGateway, gatewayUrl, type GatewayClient } from '../lib/gateway'
import { toCapabilityData } from '../probe/runProbe'
import { useSessionStore } from '../store/session'
import { AdmissionError, modeToRequest, requestSession } from './admission'
import { DEFAULT_EXERCISE } from './catalog'
import { entryFromEvent } from './coachCard'
import { setGatewayClient, startNewSequence } from './gatewayInstance'

function handle(envelope: Envelope) {
  const store = useSessionStore.getState()
  const now = Date.now()

  switch (envelope.type) {
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
      break
    default:
      // pose.frame e quality.signal não são empurrados ao cliente (CLIENT_PUSH_TYPES).
      console.warn('[sessão] tipo inesperado vindo do gateway:', envelope.type)
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
        exercise: DEFAULT_EXERCISE,
        requestedMode: modeToRequest(modeOverride, capability),
        probe: capability,
      })
        .then((ticket) => {
          if (cancelado) return
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
