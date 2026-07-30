// Capability probe da SPEC-001: decide EDGE vs CLOUD.
//
// A decisão é função pura (`decideMode`) para ser testável sem GPU e sem câmera.
// A medição em si (`runCapabilityProbe`) vive em `runProbe.ts`.
//
// O que este módulo mede mudou na T-084, e a razão importa: até então o probe contava FRAMES
// POR SEGUNDO DE PAREDE numa janela de 2s. Esse número é `min(fps da câmera, throughput do
// modelo)` — ele só sobe quando chega frame novo. Em iPhone com pouca luz o iOS alonga a
// exposição e entrega 12–15fps de câmera; o probe lia 12 e concluía "este aparelho não aguenta
// pose", quando o que não aguentava era a iluminação da sala. Resultado: telefone bom indo para
// CLOUD, que além de gastar slot (são 3 no semáforo da SPEC-009) analisa uma imagem PIOR —
// JPEG de 320px a 10fps. Cena ruim nunca é argumento para trocar de modo; é argumento para
// consertar a cena, e é isso que o aviso da pré-configuração faz.
//
// Agora a capacidade é medida por LATÊNCIA de inferência (mediana de ms por `detectForVideo`),
// que não depende da cadência da câmera. O fps da câmera continua sendo medido, mas com o nome
// certo e para outra finalidade: é sinal de CENA (SPEC-003), não de capacidade.
import { Mode } from '../lib/events'

/** Abaixo disto o device não sustenta pose no navegador (SPEC-001). */
export const EDGE_FPS_THRESHOLD = 12

/** Duração nominal da medição. O critério 1 da spec exige o probe inteiro em ≤ 3s. */
export const PROBE_DURATION_MS = 2000

/**
 * Teto quando a janela nominal não rendeu amostra suficiente (câmera lenta entrega poucos
 * frames, e sem frame não há inferência para cronometrar). Continua dentro do critério de 3s
 * da spec, que é o que o portão da T-069 paga antes de pedir a sessão.
 */
export const PROBE_MAX_MS = 3000

/**
 * Inferências descartadas no começo. As primeiras chamadas depois do `createFromOptions` pagam
 * compilação de shader e primeira alocação — em aparelho real elas chegam a centenas de ms
 * cada, e três delas sozinhas comiam metade da janela de 2s. Aquecimento não é regime.
 */
export const PROBE_WARMUP_SAMPLES = 3

/** Amostras válidas (já sem o aquecimento) para a janela nominal poder fechar. */
export const PROBE_MIN_SAMPLES = 8

/** Por que o modo foi esse. Sem isto, "meu iPhone vai para cloud" não tem diagnóstico. */
export type ModeReason =
  /** Medida acima do limiar. */
  | 'probe_ok'
  /** Medida abaixo do limiar — o aparelho realmente não sustenta o alvo de 15fps. */
  | 'probe_lento'
  | 'sem_webgl'
  | 'sem_simd'
  /** O probe lançou exceção (modelo não carregou, contexto perdido). */
  | 'probe_falhou'
  /** Nenhuma inferência aconteceu — não há medida, nem a favor nem contra. */
  | 'sem_medida'

export interface CapabilityInput {
  /** fps sustentável do MODELO (1000 / mediana da latência); `null` quando não houve medida. */
  modelFps: number | null
  webgl: boolean
  wasmSimd: boolean
  /** O probe lançou exceção (modelo não carregou, contexto perdido, etc.). */
  failed?: boolean
}

export interface ModeDecision {
  mode: Mode
  reason: ModeReason
}

/**
 * CLOUD nunca é escolha otimista: só sai daqui quando o device realmente não dá conta. Mesmo
 * assim ainda depende de slot de admission control (SPEC-009) — esta função decide o que
 * *pedir*, não o que a sessão vai usar.
 *
 * `sem_medida` cai para EDGE (T-084; a regra anterior mandava para cloud). O motivo é que
 * cloud não resolve esse caso: sem frame de câmera não há o que mandar ao servidor tampouco —
 * os dois modos dependem da mesma imagem. Ir para cloud por ausência de evidência só queimava
 * slot de quem tem evidência. Falha COM exceção continua indo para cloud: ali o que quebrou
 * foi o pipeline local, e o servidor é a alternativa real.
 */
export function decideMode(input: CapabilityInput): ModeDecision {
  if (input.failed) return { mode: Mode.CLOUD, reason: 'probe_falhou' }
  if (!input.webgl) return { mode: Mode.CLOUD, reason: 'sem_webgl' }
  if (!input.wasmSimd) return { mode: Mode.CLOUD, reason: 'sem_simd' }
  if (input.modelFps === null || !Number.isFinite(input.modelFps)) {
    return { mode: Mode.EDGE, reason: 'sem_medida' }
  }
  return input.modelFps >= EDGE_FPS_THRESHOLD
    ? { mode: Mode.EDGE, reason: 'probe_ok' }
    : { mode: Mode.CLOUD, reason: 'probe_lento' }
}

/** Mediana — e não média — porque um GC no meio da janela não pode decidir a sessão. */
export function mediana(valores: readonly number[]): number | null {
  const validos = valores.filter((valor) => Number.isFinite(valor)).sort((a, b) => a - b)
  if (validos.length === 0) return null
  const meio = Math.floor(validos.length / 2)
  if (validos.length % 2 === 1) return validos[meio] ?? null
  const antes = validos[meio - 1]
  const depois = validos[meio]
  if (antes === undefined || depois === undefined) return null
  return (antes + depois) / 2
}

/**
 * fps que o modelo sustenta, a partir das latências medidas. Descarta o aquecimento e usa a
 * mediana do que sobra — este é O número da decisão edge × cloud.
 */
export function fpsSustentavel(
  latenciasMs: readonly number[],
  aquecimento: number = PROBE_WARMUP_SAMPLES,
): number | null {
  const regime = mediana(latenciasMs.slice(aquecimento))
  if (regime === null || regime <= 0) return null
  return 1000 / regime
}

/** `?mode=edge|cloud` força o modo para debug (SPEC-001). Valor inválido é ignorado. */
export function parseModeOverride(search: string): Mode | null {
  const raw = new URLSearchParams(search).get('mode')?.trim().toLowerCase()
  if (raw === Mode.EDGE || raw === Mode.CLOUD) return raw
  return null
}

/**
 * WebGL2, com fallback para WebGL1 — é o delegate GPU do MediaPipe.
 *
 * O contexto é DEVOLVIDO no fim (T-084). O Safari de iPhone tem orçamento apertado de
 * contextos WebGL vivos, e este detector roda a cada montagem do pipeline (parar/iniciar
 * câmera, entrar e sair do treino). Contexto vazado aqui faz o delegate GPU do MediaPipe
 * falhar mais adiante → queda para CPU → medida baixa → cloud, tudo por causa de um canvas de
 * descarte que ninguém fechou.
 */
export function detectWebgl(): boolean {
  try {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('webgl2') ?? canvas.getContext('webgl')
    if (!context) return false
    context.getExtension('WEBGL_lose_context')?.loseContext()
    return true
  } catch {
    return false
  }
}

/**
 * Módulo WASM mínimo que usa `v128` (SIMD). Se o motor não validar, o runtime
 * do MediaPipe cai para o build `nosimd`, bem mais lento.
 */
const WASM_SIMD_PROBE = Uint8Array.from([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x05, 0x01, 0x60, 0x00, 0x01, 0x7b, 0x03,
  0x02, 0x01, 0x00, 0x0a, 0x0a, 0x01, 0x08, 0x00, 0x41, 0x00, 0xfd, 0x0f, 0xfd, 0x62, 0x0b,
])

export function detectWasmSimd(): boolean {
  try {
    return WebAssembly.validate(WASM_SIMD_PROBE)
  } catch {
    return false
  }
}
