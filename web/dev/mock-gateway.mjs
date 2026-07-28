// Mock do gateway (T-005 é do Agente A). Fica FORA do bundle: é um servidor
// node de desenvolvimento que fala exatamente o contrato v1 — MessagePack sobre
// WebSocket, envelope {v, type, session_id, ts, seq, source, data}.
//
// Não inventa evento: só emite os tipos de `CLIENT_PUSH_TYPES` mais
// `session.started`. Quando o gateway real existir, trocar a URL é o suficiente.
//
//   node dev/mock-gateway.mjs [porta]
import { encode } from '@msgpack/msgpack'
import { WebSocketServer } from 'ws'

const PORT = Number(process.argv[2] ?? 8787)
const PROTOCOL_VERSION = 1
const SESSION_DURATION_S = 30

// Espelho mínimo do contrato — este arquivo não pode importar do bundle do app.
const EventType = {
  SESSION_STARTED: 'session.started',
  EXERCISE_PHASE: 'exercise.phase',
  REP_DETECTED: 'rep.detected',
  SCENE_WARNING: 'scene.warning',
  FEEDBACK_ISSUED: 'feedback.issued',
  SESSION_COMPLETED: 'session.completed',
}

const FEEDBACKS = [
  {
    code: 'ARMS_TOO_LOW',
    severity: 'warning',
    message: 'Suba mais os braços até se tocarem.',
    hint: 'Na abertura, leve as mãos acima da cabeça.',
  },
  {
    code: 'LEGS_TOO_CLOSED',
    severity: 'warning',
    message: 'Abra mais as pernas na abertura.',
    hint: 'Os pés devem passar da largura dos ombros.',
  },
]

const SCENE_WARNINGS = [
  { code: 'TOO_FAR', severity: 'warning', hint: 'Aproxime-se da câmera.' },
  { code: 'OUT_OF_FRAME', severity: 'warning', hint: 'Você saiu do quadro.' },
]

function createSession(socket) {
  const sessionId = `mock-${Math.random().toString(36).slice(2, 8)}`
  let seq = 0
  let repCount = 0
  let phase = 'closed'
  const timers = []

  const send = (type, data) => {
    if (socket.readyState !== socket.OPEN) return
    socket.send(
      encode({
        v: PROTOCOL_VERSION,
        type,
        session_id: sessionId,
        ts: Date.now(),
        seq: seq++,
        source: 'system',
        data,
      }),
    )
  }

  const every = (ms, fn) => timers.push(setInterval(fn, ms))
  const after = (ms, fn) => timers.push(setTimeout(fn, ms))

  send(EventType.SESSION_STARTED, {
    exercise: 'jumping_jack',
    mode: 'edge',
    duration_s: SESSION_DURATION_S,
  })

  // ~1 rep a cada 1,2s, alternando a fase no meio do caminho.
  every(600, () => {
    phase = phase === 'closed' ? 'open' : 'closed'
    send(EventType.EXERCISE_PHASE, { phase })
    if (phase === 'closed') {
      repCount += 1
      send(EventType.REP_DETECTED, { rep_count: repCount, phase, duration_ms: 1200 })
    }
  })

  after(4500, () => send(EventType.FEEDBACK_ISSUED, FEEDBACKS[0]))
  after(9000, () => send(EventType.SCENE_WARNING, SCENE_WARNINGS[0]))
  after(14000, () => send(EventType.FEEDBACK_ISSUED, FEEDBACKS[1]))

  after(SESSION_DURATION_S * 1000, () => {
    send(EventType.SESSION_COMPLETED, { reason: 'completed', rep_count: repCount })
    stop()
  })

  function stop() {
    for (const timer of timers) {
      clearInterval(timer)
      clearTimeout(timer)
    }
    timers.length = 0
  }

  return { sessionId, stop }
}

const server = new WebSocketServer({ port: PORT })

server.on('connection', (socket, request) => {
  const session = createSession(socket)
  console.log(`[mock-gateway] conectado ${request.url} → ${session.sessionId}`)

  // O cliente manda pose.frame; o mock só conta, a análise real é do worker.
  let received = 0
  socket.on('message', () => {
    received += 1
  })

  socket.on('close', () => {
    session.stop()
    console.log(`[mock-gateway] desconectado ${session.sessionId} (${received} frames recebidos)`)
  })
})

console.log(`[mock-gateway] ouvindo em ws://localhost:${PORT} — contrato v1, MessagePack`)
