// Liga a tela de sessão ao gateway (mock ou real — muda só a URL).
import { useEffect } from 'react'
import {
  EventType,
  type Envelope,
  type RepDetectedData,
  type SceneWarningData,
  type FeedbackIssuedData,
  type SessionCompletedData,
  type SessionStartedData,
  type ExercisePhaseData,
} from '../lib/events'
import { connectGateway, gatewayUrl } from '../lib/gateway'
import { useSessionStore } from '../store/session'
import { entryFromEvent } from './coachCard'

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

export function useSession(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return

    const store = useSessionStore.getState()
    store.resetSession()

    const client = connectGateway(gatewayUrl(), {
      onEvent: handle,
      onStatus: (status) => useSessionStore.getState().setGatewayStatus(status),
    })

    return () => {
      client.close()
      const current = useSessionStore.getState()
      current.setGatewayStatus('idle')
      current.resetSession()
    }
  }, [enabled])
}
