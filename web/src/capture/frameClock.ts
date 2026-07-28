// Frame clock da SPEC-001: cada frame emitido ganha `ts` (epoch ms) e `seq`
// (monotônico por sessão), com decimação **por tempo** — não por contagem.
//
// Contar frames quebraria com câmera de 24, 30 ou 60fps: a nota da spec pede
// fps alvo estável independentemente da taxa da fonte.

/** fps alvo de processamento por modo (SPEC-001/SPEC-005). */
export const EDGE_TARGET_FPS = 15
export const CLOUD_TARGET_FPS = 10

export interface FrameTick {
  /** epoch ms, medido no produtor (contrato: `Envelope.ts`). */
  ts: number
  /** contador monotônico por sessão (contrato: `Envelope.seq`). */
  seq: number
}

export interface FrameClock {
  /** Devolve o tick quando este instante deve virar frame, ou `null` para descartar. */
  tick(nowMs: number): FrameTick | null
  /** Zera `seq` e o agendamento — nova sessão começa do zero. */
  reset(): void
  readonly targetFps: number
  readonly emitted: number
}

export function createFrameClock(targetFps: number, tolerance?: number): FrameClock {
  if (!Number.isFinite(targetFps) || targetFps <= 0) {
    throw new Error(`targetFps deve ser positivo, recebido ${targetFps}`)
  }

  const interval = 1000 / targetFps
  // Uma fonte de 30fps entrega frames a cada 33,3ms; sem folga, o frame dos
  // 66,6ms perderia o alvo de 66,7ms por 0,1ms e o fps efetivo cairia à metade.
  const slack = tolerance ?? interval / 3

  let seq = 0
  let emitted = 0
  let nextDue: number | null = null

  return {
    get targetFps() {
      return targetFps
    },
    get emitted() {
      return emitted
    },

    tick(nowMs: number): FrameTick | null {
      if (nextDue !== null && nowMs < nextDue - slack) return null

      nextDue = nextDue === null ? nowMs + interval : nextDue + interval
      // Depois de uma pausa longa (aba escondida, travada), não dispara rajada
      // para "recuperar" o atraso: reancora no agora.
      if (nextDue <= nowMs) nextDue = nowMs + interval

      emitted += 1
      return { ts: Math.round(nowMs), seq: seq++ }
    },

    reset(): void {
      seq = 0
      emitted = 0
      nextDue = null
    },
  }
}
