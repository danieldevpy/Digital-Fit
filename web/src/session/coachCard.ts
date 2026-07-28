// Regra de exibição do card "Dica do Treinador" (SPEC-013 §4 e critério 3).
//
// Prioridade: warning de cena > feedback de execução > dica padrão do exercício.
// O card NUNCA fica vazio — sem nada ativo, mostra o `default_tip`.
//
// Função pura: a decisão de o que mostrar não depende de React nem do WebSocket.
import { Code, Severity, type Severity as SeverityType } from '../lib/events'

export type CoachTone = 'default' | 'feedback' | 'scene'

export interface CoachEntry {
  code: Code
  severity: SeverityType
  /** `feedback.issued` traz `message`; `scene.warning` não tem esse campo. */
  message?: string
  hint?: string
  /** epoch ms de quando chegou — usado para expirar. */
  receivedAt: number
}

export interface CoachCard {
  title: string
  text: string
  hint: string | null
  tone: CoachTone
}

/**
 * Texto em pt-BR dos códigos de cena. O contrato manda só o código, e
 * `scene.warning` não tem campo `message` — sem este mapa não há o que exibir.
 */
const SCENE_MESSAGES: Record<string, string> = {
  [Code.OUT_OF_FRAME]: 'Você saiu do quadro.',
  [Code.TOO_FAR]: 'Afaste-se menos: você está longe demais da câmera.',
  [Code.TOO_CLOSE]: 'Você está perto demais da câmera.',
  [Code.ARMS_TOO_LOW]: 'Suba mais os braços.',
  [Code.LEGS_TOO_CLOSED]: 'Abra mais as pernas.',
}

/**
 * Nada no contrato diz que um aviso deixou de valer — não existe evento de
 * "resolvido". Sem TTL o card ficaria preso no último aviso até o fim da sessão,
 * então o cliente expira sozinho. É cosmético: a autoridade segue no worker.
 */
export const COACH_ENTRY_TTL_MS = 6000

export const COACH_TITLE = 'Dica do treinador'

/**
 * Texto em pt-BR de um código solto. O relatório (SPEC-010) recebe só `{code: contagem}` e
 * precisa do mesmo texto que o HUD mostrou ao vivo — daí reusar este mapa em vez de escrever
 * uma segunda tradução, que envelheceria em separado.
 */
export function textForCode(code: string): string {
  return SCENE_MESSAGES[code] ?? code
}

function isFresh(entry: CoachEntry | null, now: number, ttlMs: number): entry is CoachEntry {
  return entry !== null && now - entry.receivedAt < ttlMs
}

function textOf(entry: CoachEntry): string {
  return entry.message ?? SCENE_MESSAGES[entry.code] ?? entry.code
}

export interface ResolveCoachCardInput {
  scene: CoachEntry | null
  feedback: CoachEntry | null
  defaultTip: string
  now: number
  ttlMs?: number
}

export function resolveCoachCard(input: ResolveCoachCardInput): CoachCard {
  const ttl = input.ttlMs ?? COACH_ENTRY_TTL_MS

  if (isFresh(input.scene, input.now, ttl)) {
    return {
      title: COACH_TITLE,
      text: textOf(input.scene),
      hint: input.scene.hint ?? null,
      tone: 'scene',
    }
  }

  if (isFresh(input.feedback, input.now, ttl)) {
    return {
      title: COACH_TITLE,
      text: textOf(input.feedback),
      hint: input.feedback.hint ?? null,
      tone: 'feedback',
    }
  }

  return { title: COACH_TITLE, text: input.defaultTip, hint: null, tone: 'default' }
}

export function entryFromEvent(
  data: { code: Code; severity?: SeverityType; message?: string; hint?: string },
  receivedAt: number,
): CoachEntry {
  return {
    code: data.code,
    severity: data.severity ?? Severity.WARNING,
    message: data.message,
    hint: data.hint,
    receivedAt,
  }
}
