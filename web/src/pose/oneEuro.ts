// One Euro Filter — ESPELHO de `workers/shared/filters.py`.
//
// Existe aqui por um motivo só: sem ele o ângulo ao vivo não bate com o do
// worker. O worker suaviza as coordenadas antes de calcular a feature, e a
// diferença de lag chega a 22° no meio de um polichinelo — quatro vezes os 5°
// que a SPEC-013 tolera. Ver a descoberta [B/T-044] no BACKLOG.
//
// Filtra por canal, com estado independente por posição do array — igual à
// versão vetorizada em numpy.

export function alphaFor(cutoff: number, dt: number): number {
  const tau = 1 / (2 * Math.PI * cutoff)
  return 1 / (1 + tau / dt)
}

export interface OneEuroOptions {
  mincutoff?: number
  beta?: number
  dcutoff?: number
}

export class OneEuroFilter {
  readonly mincutoff: number
  readonly beta: number
  readonly dcutoff: number

  private t: number | null = null
  private xHat: number[] | null = null
  private dxHat: number[] | null = null

  constructor({ mincutoff = 1, beta = 0, dcutoff = 1 }: OneEuroOptions = {}) {
    if (mincutoff <= 0 || dcutoff <= 0) throw new Error('mincutoff e dcutoff devem ser > 0')
    if (beta < 0) throw new Error('beta não pode ser negativo')
    this.mincutoff = mincutoff
    this.beta = beta
    this.dcutoff = dcutoff
  }

  get initialized(): boolean {
    return this.t !== null
  }

  /** Esquece o estado — usar entre sessões, nunca no meio de uma. */
  reset(): void {
    this.t = null
    this.xHat = null
    this.dxHat = null
  }

  /** `t` em segundos. Primeiro valor passa direto; `t` que não avança devolve o último. */
  filter(value: readonly number[], t: number): number[] {
    if (this.t === null || this.xHat === null || this.dxHat === null) {
      this.t = t
      this.xHat = [...value]
      this.dxHat = value.map(() => 0)
      return [...this.xHat]
    }

    const dt = t - this.t
    if (dt <= 0) return [...this.xHat]

    const xHat = this.xHat
    const dxHat = this.dxHat
    const alphaD = alphaFor(this.dcutoff, dt)
    const next: number[] = new Array(value.length)

    for (let i = 0; i < value.length; i++) {
      const x = value[i]!
      // 1) velocidade filtrada (unidades do sinal por segundo)
      const dx = (x - xHat[i]!) / dt
      dxHat[i] = alphaD * dx + (1 - alphaD) * dxHat[i]!

      // 2) cutoff adaptativo: cresce onde o sinal está rápido
      const cutoff = this.mincutoff + this.beta * Math.abs(dxHat[i]!)
      const tau = 1 / (2 * Math.PI * cutoff)
      const alphaX = 1 / (1 + tau / dt)

      // 3) passa-baixa do sinal
      next[i] = alphaX * x + (1 - alphaX) * xHat[i]!
    }

    this.xHat = next
    this.t = t
    return [...next]
  }

  filterScalar(value: number, t: number): number {
    return this.filter([value], t)[0]!
  }
}
