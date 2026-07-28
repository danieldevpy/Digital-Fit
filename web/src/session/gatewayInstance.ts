// Instância única do cliente de gateway + o sequenciador da sessão.
//
// Fica fora do React pelo mesmo motivo do gravador de fixtures: o loop de
// frames publica a 15Hz e não pode provocar render.
import { createClientSequencer, type ClientSequencer } from '../lib/clientSequencer'
import type { GatewayClient } from '../lib/gateway'

let client: GatewayClient | null = null
let sequencer: ClientSequencer = createClientSequencer()

export function setGatewayClient(next: GatewayClient | null): void {
  client = next
}

export function getGatewayClient(): GatewayClient | null {
  return client
}

export function getSequencer(): ClientSequencer {
  return sequencer
}

/** Nova sessão: `seq` recomeça do zero, como manda o contrato. */
export function startNewSequence(): ClientSequencer {
  sequencer = createClientSequencer()
  return sequencer
}
