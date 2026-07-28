// Ponta cliente do WebSocket. Fala o contrato v1 em MessagePack.
//
// Mock e gateway real são a MESMA implementação — muda só a URL
// (`VITE_WS_URL`). Envelope inválido recebido é descartado com log, nunca
// derruba a conexão (mesma regra do gateway, SPEC-002 critério 3).
import { decode, encode } from '@msgpack/msgpack'
import { isValidEnvelope, type Envelope } from './events'

export type GatewayStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

/**
 * Backpressure da SPEC-002: buffer de envio > 3 frames descarta o mais antigo.
 * Frame novo vale mais que frame velho — para análise em tempo real, entregar
 * um frame atrasado é pior do que não entregar.
 */
export const MAX_QUEUED_FRAMES = 3

/** Acima disto o socket já está congestionado; não adianta empurrar mais. */
const HIGH_WATER_MARK_BYTES = 64 * 1024

export interface GatewaySendStats {
  sent: number
  dropped: number
  queued: number
}

export interface GatewayClient {
  readonly url: string
  readonly stats: GatewaySendStats
  send(envelope: Envelope): void
  close(): void
}

export interface GatewayHandlers {
  onEvent(envelope: Envelope): void
  onStatus(status: GatewayStatus): void
}

export interface GatewayTarget {
  sessionId: string
  token: string | null
}

/**
 * URL do gateway. Sem `VITE_WS_URL`, aponta para o mock local — trocar mock por
 * real é essa variável e nada mais.
 */
export function gatewayUrl({ sessionId, token }: GatewayTarget): string {
  const base = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8787'
  const url = new URL(`${base.replace(/\/$/, '')}/ws/session/${encodeURIComponent(sessionId)}`)
  if (token) url.searchParams.set('token', token)
  return url.toString()
}

export function connectGateway(url: string, handlers: GatewayHandlers): GatewayClient {
  const socket = new WebSocket(url)
  socket.binaryType = 'arraybuffer'
  handlers.onStatus('connecting')

  const queue: Uint8Array[] = []
  const stats: GatewaySendStats = { sent: 0, dropped: 0, queued: 0 }

  const flush = () => {
    while (
      queue.length > 0 &&
      socket.readyState === WebSocket.OPEN &&
      socket.bufferedAmount < HIGH_WATER_MARK_BYTES
    ) {
      const bytes = queue.shift()!
      // `.slice()` garante um ArrayBuffer próprio (não compartilhado), que é o
      // que a assinatura de `WebSocket.send` aceita.
      socket.send(bytes.slice().buffer as ArrayBuffer)
      stats.sent += 1
    }
    stats.queued = queue.length
  }

  socket.addEventListener('open', () => {
    handlers.onStatus('open')
    flush()
  })
  socket.addEventListener('close', () => handlers.onStatus('closed'))
  socket.addEventListener('error', () => handlers.onStatus('error'))

  socket.addEventListener('message', (event: MessageEvent<ArrayBuffer | string>) => {
    if (typeof event.data === 'string') {
      console.warn('[gateway] quadro de texto ignorado: o contrato é binário')
      return
    }
    let decoded: unknown
    try {
      decoded = decode(new Uint8Array(event.data))
    } catch (error) {
      console.warn('[gateway] MessagePack inválido descartado', error)
      return
    }
    if (!isValidEnvelope(decoded)) {
      console.warn('[gateway] envelope fora do contrato descartado', decoded)
      return
    }
    handlers.onEvent(decoded)
  })

  return {
    url,
    stats,

    send(envelope) {
      queue.push(encode(envelope))
      while (queue.length > MAX_QUEUED_FRAMES) {
        queue.shift()
        stats.dropped += 1
      }
      flush()
    },

    close() {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    },
  }
}
