// Ponta cliente do WebSocket. Fala o contrato v1 em MessagePack.
//
// Mock e gateway real são a MESMA implementação — muda só a URL
// (`VITE_WS_URL`). Envelope inválido é descartado com log, nunca derruba a
// conexão (mesma regra do gateway, SPEC-002 critério 3).
import { decode } from '@msgpack/msgpack'
import { isValidEnvelope, type Envelope } from './events'

export type GatewayStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

export interface GatewayClient {
  close(): void
  readonly url: string
}

export interface GatewayHandlers {
  onEvent(envelope: Envelope): void
  onStatus(status: GatewayStatus): void
}

/** URL do gateway. Sem `VITE_WS_URL` definida, aponta para o mock local. */
export function gatewayUrl(): string {
  return import.meta.env.VITE_WS_URL ?? 'ws://localhost:8787/ws/session/dev'
}

export function connectGateway(url: string, handlers: GatewayHandlers): GatewayClient {
  const socket = new WebSocket(url)
  socket.binaryType = 'arraybuffer'
  handlers.onStatus('connecting')

  socket.addEventListener('open', () => handlers.onStatus('open'))
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
    close() {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close()
      }
    },
  }
}
