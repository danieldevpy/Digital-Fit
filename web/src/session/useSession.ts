// Liga a tela de sessão ao gateway (mock ou real — muda só `VITE_WS_URL`).
import { useEffect, useMemo } from 'react'
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
import { connectGateway, gatewayUrl } from '../lib/gateway'
import { toCapabilityData } from '../probe/runProbe'
import { useSessionStore } from '../store/session'
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
 * Identidade da sessão. Na Fase 0 o cliente inventa: `POST /sessions` (T-011,
 * Agente A) ainda não existe. Quando existir, id e token vêm de lá — e só daqui.
 */
function devSessionTarget(): { sessionId: string; token: string | null } {
  const params = new URLSearchParams(window.location.search)
  const random =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10)
  return {
    sessionId: params.get('session') ?? `dev-${random}`,
    token: params.get('token') ?? import.meta.env.VITE_WS_TOKEN ?? null,
  }
}

export function useSession(enabled: boolean) {
  const target = useMemo(() => devSessionTarget(), [])

  useEffect(() => {
    if (!enabled) return

    const store = useSessionStore.getState()
    store.resetSession()
    const sequencer = startNewSequence()

    const client = connectGateway(gatewayUrl(target), {
      onEvent: handle,
      onStatus: (status) => {
        useSessionStore.getState().setGatewayStatus(status)

        // O probe já terminou quando a câmera está de pé, então a capability
        // pode ir no primeiro instante em que o socket abre.
        if (status !== 'open') return
        const capability = useSessionStore.getState().capability
        if (!capability) return
        client.send(
          makeEnvelope({
            type: EventType.SESSION_CAPABILITY,
            session_id: target.sessionId,
            ts: Date.now(),
            seq: sequencer.next(),
            source: Source.EDGE,
            data: toCapabilityData(capability),
          }),
        )
      },
    })
    setGatewayClient(client)

    return () => {
      client.close()
      setGatewayClient(null)
      const current = useSessionStore.getState()
      current.setGatewayStatus('idle')
      current.resetSession()
    }
  }, [enabled, target])

  return target
}
