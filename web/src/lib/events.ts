// ESPELHO do contrato de eventos — NÃO é fonte da verdade.
//
// Fonte: `workers/shared/events.py` (Agente A, SPEC-002). Este arquivo apenas
// reproduz em TypeScript o que está lá. Regra: o cliente nunca inventa evento,
// campo ou código. Divergiu? Vai para "Descobertas" no BACKLOG, não para cá.
//
// Chaves ficam em snake_case de propósito: é o formato que trafega no fio.
// Traduzir para camelCase na fronteira só criaria uma chance a mais de drift.
//
// Espelhado de events.py v1 (Fase 0).

export const PROTOCOL_VERSION = 1

export const EventType = {
  SESSION_CAPABILITY: 'session.capability',
  SESSION_STARTED: 'session.started',
  FRAME_RAW: 'frame.raw',
  POSE_FRAME: 'pose.frame',
  SESSION_CALIBRATED: 'session.calibrated',
  EXERCISE_PHASE: 'exercise.phase',
  REP_DETECTED: 'rep.detected',
  QUALITY_SIGNAL: 'quality.signal',
  SCENE_WARNING: 'scene.warning',
  FEEDBACK_ISSUED: 'feedback.issued',
  SESSION_COMPLETED: 'session.completed',
  SESSION_REPORT_READY: 'session.report.ready',
} as const
export type EventType = (typeof EventType)[keyof typeof EventType]

export const Source = {
  EDGE: 'edge',
  CLOUD: 'cloud',
  SYSTEM: 'system',
} as const
export type Source = (typeof Source)[keyof typeof Source]

export const Mode = {
  EDGE: 'edge',
  CLOUD: 'cloud',
} as const
export type Mode = (typeof Mode)[keyof typeof Mode]

/**
 * Fase do movimento — par NEUTRO, espelho de `workers/shared/events.py` (T-050).
 *
 * Era `closed`/`open`, que descreve polichinelo e mais nada. `REST` é a posição de partida,
 * `PEAK` o extremo do movimento; o que cada uma parece é do exercício (polichinelo: fechado
 * e aberto; agachamento: em pé e embaixo). Quando alguma tela for desenhar a fase, o texto
 * sai do catálogo de exercícios, não daqui — este arquivo é contrato, não conteúdo.
 */
export const Phase = {
  REST: 'rest',
  PEAK: 'peak',
} as const
export type Phase = (typeof Phase)[keyof typeof Phase]

export const Severity = {
  INFO: 'info',
  WARNING: 'warning',
} as const
export type Severity = (typeof Severity)[keyof typeof Severity]

/**
 * Códigos de sinal e feedback (SPEC-003/SPEC-008). A mensagem em pt-BR vive no catálogo do
 * servidor — aqui fica só o código, que é o contrato.
 *
 * Ficou parado na Fase 0 por três exercícios: enquanto só o polichinelo contava, os dois
 * códigos dele eram o mundo inteiro. Agachamento, flexão e abdominal trouxeram seis códigos de
 * execução que este espelho não conhecia, e o cliente é justamente quem os desenha no
 * relatório — sem estarem aqui, chegavam à tela como o próprio identificador.
 */
export const Code = {
  // Execução — viram `quality.signal` e depois `feedback.issued`.
  ARMS_TOO_LOW: 'ARMS_TOO_LOW',
  LEGS_TOO_CLOSED: 'LEGS_TOO_CLOSED',
  SQUAT_TOO_SHALLOW: 'SQUAT_TOO_SHALLOW',
  PUSHUP_TOO_SHALLOW: 'PUSHUP_TOO_SHALLOW',
  HIPS_SAGGING: 'HIPS_SAGGING',
  HIPS_PIKED: 'HIPS_PIKED',
  CRUNCH_TOO_SHALLOW: 'CRUNCH_TOO_SHALLOW',
  CRUNCH_TOO_FAST: 'CRUNCH_TOO_FAST',
  // Cena — viram `scene.warning`.
  OUT_OF_FRAME: 'OUT_OF_FRAME',
  TOO_FAR: 'TOO_FAR',
  TOO_CLOSE: 'TOO_CLOSE',
} as const
export type Code = (typeof Code)[keyof typeof Code]

export const SessionEndReason = {
  COMPLETED: 'completed',
  TIMEOUT: 'timeout',
  ABORTED: 'aborted',
  NO_DATA: 'no_data',
} as const
export type SessionEndReason = (typeof SessionEndReason)[keyof typeof SessionEndReason]

export const LANDMARK_COUNT = 33

/** Ordem dos 33 landmarks do MediaPipe Pose, igual ao enum `Landmark` do contrato. */
export const LANDMARK_NAMES = [
  'nose',
  'left_eye_inner',
  'left_eye',
  'left_eye_outer',
  'right_eye_inner',
  'right_eye',
  'right_eye_outer',
  'left_ear',
  'right_ear',
  'mouth_left',
  'mouth_right',
  'left_shoulder',
  'right_shoulder',
  'left_elbow',
  'right_elbow',
  'left_wrist',
  'right_wrist',
  'left_pinky',
  'right_pinky',
  'left_index',
  'right_index',
  'left_thumb',
  'right_thumb',
  'left_hip',
  'right_hip',
  'left_knee',
  'right_knee',
  'left_ankle',
  'right_ankle',
  'left_heel',
  'right_heel',
  'left_foot_index',
  'right_foot_index',
] as const

/** O que o gateway empurra de volta ao cliente (`CLIENT_PUSH_TYPES` no contrato). */
export const CLIENT_PUSH_TYPES: readonly EventType[] = [
  // Marca o fim da preparação: é aqui que o servidor começa a contar os 30s, e o anel do
  // HUD tem de ancorar no MESMO instante para não mentir sobre quanto falta.
  EventType.SESSION_CALIBRATED,
  EventType.EXERCISE_PHASE,
  EventType.REP_DETECTED,
  EventType.SCENE_WARNING,
  EventType.FEEDBACK_ISSUED,
  EventType.SESSION_COMPLETED,
  // O relatório já está gravado — pode buscar. Chega DEPOIS do `session.completed`, porque o
  // report-builder só consolida quando a sessão fecha.
  EventType.SESSION_REPORT_READY,
]

// ---------------------------------------------------------------------------
// Payloads (o `data` de cada tipo)
// ---------------------------------------------------------------------------

export interface SessionCapabilityData {
  mode: Mode
  probe_fps: number
  webgl: boolean
  ua: string
}

export interface SessionStartedData {
  exercise: string
  mode: Mode
  duration_s: number
  /** Preparação antes de a contagem valer (T-049). `0` desliga. */
  countdown_s?: number
}

/**
 * Frame JPEG do modo cloud (SPEC-005). Único evento que carrega imagem, e ela morre no
 * `pose-worker` — o dado do sistema são keypoints.
 *
 * O servidor **recusa** frame com o maior lado acima de `FRAME_RAW_MAX_SIDE`: reduzir é
 * responsabilidade do cliente, porque o pose-worker roda em 1 vCPU e é o gargalo do modo.
 */
export interface FrameRawData {
  /** Bytes do JPEG. Vira `bin` no MessagePack, não string. */
  jpeg: Uint8Array
  width: number
  height: number
}

/** Maior lado do JPEG enviado no modo cloud (`FRAME_RAW_MAX_SIDE` no contrato). */
export const FRAME_RAW_MAX_SIDE = 320

/** Qualidade do JPEG (SPEC-005: "qualidade ~60"). */
export const FRAME_RAW_QUALITY = 0.6

/**
 * Baseline medida no countdown (SPEC-004). O cliente usa este evento como marco de "agora
 * vale", não os números em si — quem raciocina sobre proporção corporal é o worker.
 */
export interface SessionCalibratedData {
  torso: number
  shoulder_width: number
  shoulder_span: number
  wrist_rest_y: number
  samples: number
  /**
   * Quanto falta até a contagem valer (T-049). `0` = vale a partir deste evento.
   *
   * O evento significa "corpo MEDIDO", não "contagem começou": quem lê tem de somar isto
   * para saber quando o anel dos 30 s anda.
   */
  countdown_ms?: number
}

/** `[x, y, z, visibility]`, normalizado 0–1 no frame. */
export type LandmarkTuple = [number, number, number, number]

export interface PoseFrameData {
  landmarks: LandmarkTuple[]
  norm?: Record<string, unknown>
  degraded?: boolean
}

export interface ExercisePhaseData {
  phase: Phase
}

export interface RepDetectedData {
  rep_count: number
  phase: Phase
  duration_ms: number
}

export interface QualitySignalData {
  code: Code
  value?: number
  rep_index?: number
}

export interface SceneWarningData {
  code: Code
  severity: Severity
  hint?: string
}

export interface FeedbackIssuedData {
  code: Code
  severity: Severity
  message: string
  hint?: string
}

export interface SessionCompletedData {
  reason: SessionEndReason
  rep_count: number
}

/**
 * `session.report.ready` — payload **vazio de propósito** (ver `SessionReportReady` no
 * contrato). O evento é um sino: diz que o relatório existe, e o conteúdo tem uma fonte só,
 * o `GET /api/sessions/{id}/report`.
 */
export type SessionReportReadyData = Record<string, never>

/** Mapa tipo → payload, para estreitar o `data` de um envelope recebido. */
export interface EventDataMap {
  'session.capability': SessionCapabilityData
  'session.started': SessionStartedData
  'pose.frame': PoseFrameData
  'session.calibrated': SessionCalibratedData
  'exercise.phase': ExercisePhaseData
  'rep.detected': RepDetectedData
  'quality.signal': QualitySignalData
  'scene.warning': SceneWarningData
  'feedback.issued': FeedbackIssuedData
  'session.completed': SessionCompletedData
  'session.report.ready': SessionReportReadyData
}

// ---------------------------------------------------------------------------
// Envelope
// ---------------------------------------------------------------------------

export interface Envelope<T extends EventType = EventType> {
  v: number
  type: T
  session_id: string
  ts: number
  seq: number
  source: Source
  data: T extends keyof EventDataMap ? EventDataMap[T] : Record<string, unknown>
}

export interface MakeEnvelopeInput<T extends EventType> {
  type: T
  session_id: string
  ts: number
  seq: number
  source: Source
  data: Envelope<T>['data']
}

export function makeEnvelope<T extends EventType>(input: MakeEnvelopeInput<T>): Envelope<T> {
  return {
    v: PROTOCOL_VERSION,
    type: input.type,
    session_id: input.session_id,
    ts: input.ts,
    seq: input.seq,
    source: input.source,
    data: input.data,
  }
}

/**
 * Mesmas travas do `Envelope.__post_init__` do contrato. Serve para o cliente não
 * emitir lixo — o gateway valida de novo do lado dele.
 */
export function isValidEnvelope(value: unknown): value is Envelope {
  if (typeof value !== 'object' || value === null) return false
  const envelope = value as Partial<Envelope>
  if (envelope.v !== PROTOCOL_VERSION) return false
  if (typeof envelope.type !== 'string') return false
  if (!Object.values(EventType).includes(envelope.type as EventType)) return false
  if (typeof envelope.session_id !== 'string' || envelope.session_id.length === 0) return false
  if (!Number.isInteger(envelope.ts) || (envelope.ts ?? 0) <= 0) return false
  if (!Number.isInteger(envelope.seq) || (envelope.seq ?? -1) < 0) return false
  if (!Object.values(Source).includes(envelope.source as Source)) return false
  if (typeof envelope.data !== 'object' || envelope.data === null) return false
  return true
}

/** Converte a saída do MediaPipe para o `[x, y, z, visibility]` do contrato. */
export function toLandmarkTuples(
  landmarks: readonly { x: number; y: number; z: number; visibility?: number }[],
): LandmarkTuple[] {
  return landmarks.map((l) => [l.x, l.y, l.z, l.visibility ?? 0])
}
