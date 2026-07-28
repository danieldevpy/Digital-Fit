/**
 * E2E contra o stack REAL (T-014, parte que não precisa de câmera).
 *
 * Não roda por padrão: só com `DIGITALFIT_E2E=1` e `docker compose up` de pé. O resto da
 * suíte continua sem dependência externa.
 *
 *     DIGITALFIT_E2E=1 VITE_API_URL=http://localhost:8000 npm run test:e2e
 *
 * O que ele prova, e que nenhum outro teste prova: o **espelho TS do contrato**
 * (`lib/events.ts`) fala com o gateway Python de verdade. O mock foi validado contra o
 * `events.py`, mas mock e servidor podem concordar entre si e estarem os dois errados.
 *
 * A pose vem de um polichinelo sintético — a mesma ideia das fixtures do lado Python, porque
 * a parte "pessoa de verdade na frente da câmera" é a única que exige gente.
 */

import { describe, expect, it } from 'vitest'

import {
  EventType,
  Source,
  makeEnvelope,
  type Envelope,
  type LandmarkTuple,
  type RepDetectedData,
  type SessionCompletedData,
} from '../lib/events'
import { Mode } from '../lib/events'
import { waitForReport } from '../report/sessionReport'
import { requestSession } from './admission'

// `process` via `globalThis`: o tsconfig do app é o do navegador (sem tipos de Node), e este
// arquivo mora dentro de `src/` para reusar os módulos do cliente sem cópia.
const LIGADO =
  (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env
    ?.DIGITALFIT_E2E === '1'
const FPS = 15
const REPS = 8

/** Um corpo em pé, com braços e pernas na posição que `fracao` (0=fechado, 1=aberto) pede. */
function polichinelo(fracao: number): LandmarkTuple[] {
  const marcos: LandmarkTuple[] = Array.from(
    { length: 33 },
    () => [0.5, 0.5, 0, 0.95] as LandmarkTuple,
  )
  const ponto = (x: number, y: number): LandmarkTuple => [x, y, 0, 0.95]

  // Braços: descem ao lado do corpo (fechado) ou sobem acima da cabeça (aberto).
  const punhoY = 0.52 - 0.42 * fracao
  const punhoX = 0.22 + 0.2 * fracao
  // Pernas: pés juntos (fechado) ou afastados (aberto).
  const tornozeloX = 0.06 + 0.12 * fracao

  marcos[0] = ponto(0.5, 0.18) // nariz
  marcos[11] = ponto(0.58, 0.32) // ombro esquerdo
  marcos[12] = ponto(0.42, 0.32) // ombro direito
  marcos[13] = ponto(0.58 + punhoX * 0.4, (0.32 + punhoY) / 2)
  marcos[14] = ponto(0.42 - punhoX * 0.4, (0.32 + punhoY) / 2)
  marcos[15] = ponto(0.5 + punhoX, punhoY) // punho esquerdo
  marcos[16] = ponto(0.5 - punhoX, punhoY) // punho direito
  marcos[23] = ponto(0.55, 0.58) // quadril esquerdo
  marcos[24] = ponto(0.45, 0.58) // quadril direito
  marcos[25] = ponto(0.5 + tornozeloX * 0.6, 0.75)
  marcos[26] = ponto(0.5 - tornozeloX * 0.6, 0.75)
  marcos[27] = ponto(0.5 + tornozeloX, 0.93) // tornozelo esquerdo
  marcos[28] = ponto(0.5 - tornozeloX, 0.93) // tornozelo direito
  return marcos
}

/** Frames parados do countdown (SPEC-004): é neles que o servidor mede o corpo. */
const COUNTDOWN_FRAMES = 20

function sequencia(reps: number, framesPorRep = FPS): LandmarkTuple[][] {
  const quadros: LandmarkTuple[][] = []
  // Uma sessão real SEMPRE começa com a pessoa parada — é o que a calibração consome. Sem
  // isto, a medição comeria a primeira repetição e o E2E toleraria em silêncio um erro que
  // o usuário não veria em produção.
  for (let i = 0; i < COUNTDOWN_FRAMES; i++) quadros.push(polichinelo(0))
  for (let rep = 0; rep < reps; rep++) {
    for (let i = 0; i < framesPorRep; i++) {
      quadros.push(polichinelo((1 - Math.cos((2 * Math.PI * i) / framesPorRep)) / 2))
    }
  }
  // Termina em pé, parado: sem isso a última repetição fica eternamente "em andamento".
  quadros.push(polichinelo(0), polichinelo(0))
  return quadros
}

/** Espera um tipo aparecer na lista de recebidos, com teto. Devolve se apareceu. */
async function esperarEvento(
  recebidos: Envelope[],
  tipo: EventType,
  timeoutMs: number,
): Promise<boolean> {
  const limite = Date.now() + timeoutMs
  while (Date.now() < limite) {
    if (recebidos.some((e) => e.type === tipo)) return true
    await new Promise((r) => setTimeout(r, 100))
  }
  return false
}

describe.skipIf(!LIGADO)('E2E: cliente TS ↔ stack real', () => {
  it(
    'admite a sessão, manda pose.frame e recebe a contagem do servidor',
    { timeout: 60_000 },
    async () => {
      const ticket = await requestSession({
        exercise: 'jumping_jack',
        requestedMode: Mode.EDGE,
        probe: null,
      })
      expect(ticket.mode).toBe('edge')

      const socket = new WebSocket(ticket.ws_url)
      socket.binaryType = 'arraybuffer'
      const recebidos: Envelope[] = []
      const { decode, encode } = await import('@msgpack/msgpack')

      socket.addEventListener('message', (evento) => {
        recebidos.push(decode(new Uint8Array(evento.data as ArrayBuffer)) as Envelope)
      })
      await new Promise<void>((resolve, reject) => {
        socket.addEventListener('open', () => resolve(), { once: true })
        socket.addEventListener('error', () => reject(new Error('WS não abriu')), { once: true })
      })

      const quadros = sequencia(REPS)
      for (const [indice, marcos] of quadros.entries()) {
        socket.send(
          encode(
            makeEnvelope({
              type: EventType.POSE_FRAME,
              session_id: ticket.session_id,
              ts: Date.now(),
              seq: indice,
              source: Source.EDGE,
              data: { landmarks: marcos },
            }),
          ),
        )
        await new Promise((r) => setTimeout(r, 1000 / FPS))
      }
      await new Promise((r) => setTimeout(r, 1500))
      socket.close()

      // A preparação tem de ter acontecido: sem `session.calibrated` o servidor teria
      // contado durante o countdown.
      expect(recebidos.some((e) => e.type === EventType.SESSION_CALIBRATED)).toBe(true)

      const tipos = new Set(recebidos.map((e) => e.type))
      const reps = recebidos.filter((e) => e.type === EventType.REP_DETECTED)
      const ultima = reps.at(-1)?.data as RepDetectedData | undefined

      // O contrato do servidor é o que manda: o cliente não soma reps.
      expect(reps.length).toBeGreaterThan(0)
      expect(ultima?.rep_count).toBe(reps.length)
      // Exato, não "±1": com o countdown no lugar, keypoints sintéticos e limpos não têm
      // motivo para perder repetição. Uma tolerância aqui esconderia regressão de contagem.
      expect(reps.length).toBe(REPS)
      expect(tipos.has(EventType.EXERCISE_PHASE)).toBe(true)

      // Nada fora dos CLIENT_PUSH_TYPES pode chegar ao cliente.
      for (const tipo of tipos) {
        expect(tipo).not.toBe(EventType.POSE_FRAME)
        expect(tipo).not.toBe(EventType.QUALITY_SIGNAL)
      }
    },
  )

  it(
    'o servidor encerra a sessão sozinho quando o cliente para de mandar frames',
    { timeout: 60_000 },
    async () => {
      const ticket = await requestSession({
        exercise: 'jumping_jack',
        requestedMode: Mode.EDGE,
        probe: null,
      })
      const socket = new WebSocket(ticket.ws_url)
      socket.binaryType = 'arraybuffer'
      const { decode, encode } = await import('@msgpack/msgpack')
      let fim: SessionCompletedData | null = null

      socket.addEventListener('message', (evento) => {
        const envelope = decode(new Uint8Array(evento.data as ArrayBuffer)) as Envelope
        if (envelope.type === EventType.SESSION_COMPLETED) {
          fim = envelope.data as SessionCompletedData
        }
      })
      await new Promise<void>((resolve) =>
        socket.addEventListener('open', () => resolve(), { once: true }),
      )

      for (const [indice, marcos] of sequencia(2).entries()) {
        socket.send(
          encode(
            makeEnvelope({
              type: EventType.POSE_FRAME,
              session_id: ticket.session_id,
              ts: Date.now(),
              seq: indice,
              source: Source.EDGE,
              data: { landmarks: marcos },
            }),
          ),
        )
        await new Promise((r) => setTimeout(r, 1000 / FPS))
      }

      // Cala a boca e espera: o timer autoritativo é do servidor (SPEC-009).
      await new Promise((r) => setTimeout(r, 13_000))
      socket.close()

      expect(fim).not.toBeNull()
      expect(fim!.reason).toBe('no_data')
    },
  )

  it(
    'gera o relatório da sessão e o entrega pela API (SPEC-010)',
    { timeout: 60_000 },
    async () => {
      // Prova a cadeia inteira da T-020 num caminho só: analysis-worker publica em
      // `events.analysis`, o report-builder consolida e grava no Postgres, e o cliente busca
      // pelo `GET /api/sessions/{id}/report`. Nenhum teste unitário cobre isso: cada um deles
      // dublê um dos elos.
      const ticket = await requestSession({
        exercise: 'jumping_jack',
        requestedMode: Mode.EDGE,
        probe: null,
      })
      const socket = new WebSocket(ticket.ws_url)
      socket.binaryType = 'arraybuffer'
      const { decode, encode } = await import('@msgpack/msgpack')
      const recebidos: Envelope[] = []

      socket.addEventListener('message', (evento) => {
        recebidos.push(decode(new Uint8Array(evento.data as ArrayBuffer)) as Envelope)
      })
      await new Promise<void>((resolve) =>
        socket.addEventListener('open', () => resolve(), { once: true }),
      )

      const quadros = sequencia(3)
      for (const [indice, marcos] of quadros.entries()) {
        socket.send(
          encode(
            makeEnvelope({
              type: EventType.POSE_FRAME,
              session_id: ticket.session_id,
              ts: Date.now(),
              seq: indice,
              source: Source.EDGE,
              data: { landmarks: marcos },
            }),
          ),
        )
        await new Promise((r) => setTimeout(r, 1000 / FPS))
      }

      // Encerra pelo cliente (abort) em vez de esperar o timer: o relatório é o alvo aqui.
      socket.send(
        encode(
          makeEnvelope({
            type: EventType.SESSION_COMPLETED,
            session_id: ticket.session_id,
            ts: Date.now(),
            seq: quadros.length,
            source: Source.EDGE,
            data: { reason: 'aborted', rep_count: 0 },
          }),
        ),
      )

      const relatorio = await waitForReport(ticket.session_id)

      expect(relatorio).not.toBeNull()
      expect(relatorio!.session_id).toBe(ticket.session_id)
      expect(relatorio!.exercise).toBe('jumping_jack')
      expect(relatorio!.mode).toBe('edge')
      expect(relatorio!.reason).toBe('aborted')

      // O total do relatório é o mesmo que o cliente viu ao vivo — se divergir, uma das duas
      // contagens está mentindo, e o usuário veria dois números para o mesmo treino.
      const reps = recebidos.filter((e) => e.type === EventType.REP_DETECTED)
      expect(relatorio!.rep_count).toBe(reps.length)
      expect(relatorio!.duration_ms).toBeGreaterThan(0)
      expect(relatorio!.cadence_windows.reduce((a, b) => a + b, 0)).toBe(reps.length)
      // A calibração aconteceu, e o relatório registra com quantos frames ela foi medida.
      expect(relatorio!.calibration_samples).toBeGreaterThan(0)

      // O sino chega pelo WS — mas DEPOIS do relatório existir, e essa ordem é do produto,
      // não do teste: o report-builder grava no Postgres e só então publica o aviso. Quem
      // busca por polling pode portanto ver o relatório antes do sino tocar. Sem esta espera
      // o teste falharia em ~metade das execuções, por uma corrida que o usuário não vive.
      await esperarEvento(recebidos, EventType.SESSION_REPORT_READY, 5_000)
      socket.close()

      expect(recebidos.some((e) => e.type === EventType.SESSION_REPORT_READY)).toBe(true)
    },
  )
})
