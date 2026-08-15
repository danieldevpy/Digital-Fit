// Gravador de fixtures (T-007): salva a sequência de keypoints de uma sessão em
// JSON para os testes do núcleo (normalização SPEC-006, FSM SPEC-007).
//
// FORMATO — não é escolha minha: é o `schema: 1` de `workers/shared/keypoints.py`,
// que o Agente A declara como "o mesmo formato que o gravador do cliente (T-007)
// escreve e que o `evalctl run --save-keypoints` exporta. Um formato, três
// produtores". `load_fixture()` do lado Python lê o que sai daqui sem conversão.
//
// `landmarks` são os CRUS (0–1 no frame), nunca normalizados — normalização é
// código que muda, e a fixture existe justamente para medir mudança de código.
import type { FrameTick } from '../capture/frameClock'
import type { LandmarkTuple, SessionCapabilityData } from '../lib/events'
import { toLandmarkTuples } from '../lib/events'
import type { Landmark } from '../pose/skeleton'

export const FIXTURE_SCHEMA = 1

/** Casas decimais por coordenada — mesmo `_PRECISION` do lado Python. */
const PRECISION = 5

export interface FixtureFrame {
  ts: number
  seq: number
  landmarks: LandmarkTuple[]
}

export interface KeypointFixture {
  schema: typeof FIXTURE_SCHEMA
  label: string
  exercise: string
  expected_reps: number | null
  source: string
  fps: number | null
  notes: string | null
  /**
   * Dimensões do frame de origem (T-110) — a normalização precisa delas para pôr `x` e `y`
   * na mesma moeda. Já viviam dentro de `conditions.video`, mas ali são contexto de
   * gravação: `conditions` é campo livre por contrato (SPEC-012) e ninguém deve derivar
   * geometria dele. No topo, elas são schema, e o gate do corpus as cobra.
   */
  width: number | null
  height: number | null
  /** Campo livre do schema: onde cabe o contexto do device sem inventar chave. */
  conditions: Record<string, unknown>
  frames: FixtureFrame[]
}

export interface FixtureMeta {
  label: string
  notes?: string | null
  /** Quantas repetições o gravador fez de fato — o rótulo do teste. */
  expected_reps?: number | null
}

export interface FixtureContext {
  capability?: SessionCapabilityData | null
  video?: { width: number; height: number } | null
  fps?: number | null
}

export interface FixtureRecorder {
  readonly sessionId: string
  readonly isRecording: boolean
  readonly frameCount: number
  start(): void
  stop(): void
  clear(): void
  /** Ignorado silenciosamente quando não está gravando — o loop não precisa saber. */
  addFrame(tick: FrameTick, landmarks: readonly Landmark[]): void
  setContext(context: FixtureContext): void
  build(meta: FixtureMeta): KeypointFixture
}

function round(value: number): number {
  const factor = 10 ** PRECISION
  return Math.round(value * factor) / factor
}

export function createFixtureRecorder(sessionId: string, exercise = 'jumping_jack'): FixtureRecorder {
  let recording = false
  let frames: FixtureFrame[] = []
  let capability: SessionCapabilityData | null = null
  let video: { width: number; height: number } | null = null
  let fps: number | null = null

  return {
    get sessionId() {
      return sessionId
    },
    get isRecording() {
      return recording
    },
    get frameCount() {
      return frames.length
    },

    start() {
      recording = true
    },

    stop() {
      recording = false
    },

    clear() {
      recording = false
      frames = []
    },

    addFrame(tick, landmarks) {
      if (!recording) return
      // Frame sem pose não vira fixture: `landmarks` vazio quebra qualquer
      // consumidor que espere exatamente 33 pontos.
      if (landmarks.length === 0) return

      frames.push({
        ts: tick.ts,
        seq: tick.seq,
        landmarks: toLandmarkTuples(landmarks).map(
          (tuple) => tuple.map(round) as unknown as LandmarkTuple,
        ),
      })
    },

    setContext(context) {
      if (context.capability !== undefined) capability = context.capability
      if (context.video !== undefined) video = context.video
      if (context.fps !== undefined) fps = context.fps
    },

    build(meta) {
      return {
        schema: FIXTURE_SCHEMA,
        label: meta.label.trim() || 'sem-rotulo',
        exercise,
        expected_reps: meta.expected_reps ?? null,
        source: 'camera',
        fps,
        notes: meta.notes ?? null,
        width: video?.width ?? null,
        height: video?.height ?? null,
        conditions: {
          session_id: sessionId,
          recorded_at: new Date().toISOString(),
          ...(capability ? { capability } : {}),
          ...(video ? { video } : {}),
        },
        frames,
      }
    },
  }
}

/** Nome de arquivo estável e ordenável: `<label>-<ISO compacto>.json`. */
export function fixtureFileName(fixture: KeypointFixture): string {
  const stamp = String(fixture.conditions.recorded_at ?? new Date().toISOString())
    .replace(/[:.]/g, '-')
    .replace(/Z$/, '')
  const label = fixture.label.trim().replace(/\s+/g, '-').toLowerCase() || 'fixture'
  return `${label}-${stamp}.json`
}
