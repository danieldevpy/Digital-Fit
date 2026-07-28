// Gravador de fixtures (T-007): salva a sequência de keypoints de uma sessão em
// JSON para o Agente A usar nos testes de normalização (SPEC-006) e FSM (SPEC-007).
//
// FORMATO — nada aqui é evento novo:
//   `events` é uma lista de envelopes `pose.frame` do contrato, exatamente como
//   sairiam no WebSocket. O `RawFrame(ts, seq, landmarks)` do lado Python lê
//   direto de `ts`, `seq` e `data.landmarks`.
//
// O resto do arquivo é embalagem de fixture (rótulo, device, resolução), não
// protocolo: por isso vive FORA de `events`, e não como campo inventado dentro
// de um envelope.
import {
  EventType,
  Source,
  makeEnvelope,
  toLandmarkTuples,
  type Envelope,
  type SessionCapabilityData,
} from '../lib/events'
import type { FrameTick } from '../capture/frameClock'
import type { Landmark } from '../pose/skeleton'

export const FIXTURE_FORMAT = 'digital-fit/pose-fixture'
export const FIXTURE_VERSION = 1

export interface FixtureMeta {
  /** Rótulo curto do que foi gravado, ex.: "polichinelo-20-limpos". */
  label: string
  notes: string
}

export interface PoseFixture extends FixtureMeta {
  format: typeof FIXTURE_FORMAT
  version: typeof FIXTURE_VERSION
  recorded_at: string
  session_id: string
  /** Payload `session.capability` do contrato — device e modo em que gravou. */
  capability: SessionCapabilityData | null
  video: { width: number; height: number } | null
  target_fps: number | null
  events: Envelope<typeof EventType.POSE_FRAME>[]
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
  setContext(context: Partial<Pick<PoseFixture, 'capability' | 'video' | 'target_fps'>>): void
  build(meta: FixtureMeta): PoseFixture
}

export function createFixtureRecorder(sessionId: string): FixtureRecorder {
  let recording = false
  let frames: Envelope<typeof EventType.POSE_FRAME>[] = []
  let capability: SessionCapabilityData | null = null
  let video: { width: number; height: number } | null = null
  let targetFps: number | null = null

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
      // Frame sem pose não vira fixture: seria um `landmarks` vazio, que o
      // contrato rejeita (exige exatamente 33).
      if (landmarks.length === 0) return

      frames.push(
        makeEnvelope({
          type: EventType.POSE_FRAME,
          session_id: sessionId,
          ts: tick.ts,
          seq: tick.seq,
          source: Source.EDGE,
          data: { landmarks: toLandmarkTuples(landmarks) },
        }),
      )
    },

    setContext(context) {
      if (context.capability !== undefined) capability = context.capability
      if (context.video !== undefined) video = context.video
      if (context.target_fps !== undefined) targetFps = context.target_fps
    },

    build(meta) {
      return {
        format: FIXTURE_FORMAT,
        version: FIXTURE_VERSION,
        recorded_at: new Date().toISOString(),
        session_id: sessionId,
        label: meta.label,
        notes: meta.notes,
        capability,
        video,
        target_fps: targetFps,
        events: frames,
      }
    },
  }
}

/** Nome de arquivo estável e ordenável: `<label>-<ISO compacto>.json`. */
export function fixtureFileName(fixture: PoseFixture): string {
  const stamp = fixture.recorded_at.replace(/[:.]/g, '-').replace(/Z$/, '')
  const label = fixture.label.trim().replace(/\s+/g, '-').toLowerCase() || 'fixture'
  return `${label}-${stamp}.json`
}
