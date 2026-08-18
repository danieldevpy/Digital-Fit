// Regra de exibição do card "Dica do Treinador" (SPEC-013 §4 e critério 3).
//
// Prioridade: warning de cena > feedback de execução > dica padrão do exercício.
// O card NUNCA fica vazio — sem nada ativo, mostra o `default_tip`.
//
// Função pura: a decisão de o que mostrar não depende de React nem do WebSocket.
import { Code, Severity, type Severity as SeverityType } from '../lib/events'
import { useConfigStore } from '../store/config'

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
 * Texto em pt-BR **embutido**, para o primeiro paint e para o caso offline.
 *
 * A fonte da verdade é o catálogo do servidor (`catalog.pt-BR.yaml`, servido no
 * `GET /api/config` desde a T-126), pela regra da SPEC-018 §C: a frase que a pessoa lê suando
 * se reescreve sem deploy. Este mapa é o default do cliente, na mesma doutrina do catálogo de
 * exercícios — nunca é apagado quando o servidor chega, nunca some quando a rede cai.
 *
 * Ele precisa existir porque `scene.warning` **não tem campo `message`** (o contrato manda só o
 * código) e porque o relatório guarda `{código: contagem}`. Está completo de propósito: um
 * código de fora deste mapa e fora do servidor aparece como identificador na tela, que foi
 * exatamente o que aconteceu com os seis códigos de chão e de agachamento.
 */
const CODE_MESSAGES: Record<string, string> = {
  [Code.OUT_OF_FRAME]: 'Apareça inteiro no quadro',
  [Code.TOO_FAR]: 'Aproxime-se da câmera',
  [Code.TOO_CLOSE]: 'Afaste-se da câmera',
  [Code.ARMS_TOO_LOW]: 'Estenda mais os braços acima da cabeça',
  [Code.LEGS_TOO_CLOSED]: 'Abra mais as pernas',
  [Code.SQUAT_TOO_SHALLOW]: 'Desça mais no agachamento',
  [Code.PUSHUP_TOO_SHALLOW]: 'Desça mais na flexão',
  [Code.HIPS_SAGGING]: 'Contraia o abdômen',
  [Code.HIPS_PIKED]: 'Abaixe o quadril',
  [Code.CRUNCH_TOO_SHALLOW]: 'Suba um pouco mais',
  [Code.CRUNCH_TOO_FAST]: 'Mais devagar',
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
 * precisa do mesmo texto que o HUD mostrou ao vivo — daí reusar esta função em vez de escrever
 * uma segunda tradução, que envelheceria em separado.
 *
 * Ordem: servidor, embutido, o próprio código. O último degrau continua sendo feio de
 * propósito — código na tela é um sintoma que se vê, e é assim que a T-126 foi descoberta.
 */
export function textForCode(code: string): string {
  return useConfigStore.getState().feedback?.[code]?.message ?? CODE_MESSAGES[code] ?? code
}

function isFresh(entry: CoachEntry | null, now: number, ttlMs: number): entry is CoachEntry {
  return entry !== null && now - entry.receivedAt < ttlMs
}

/**
 * Prioridade invertida (SPEC-025 §Eventos, T-144): o catálogo local vence, e o `message` do
 * evento vira último recurso — não mais "o servidor escolheu para AQUELA emissão vence tudo".
 *
 * O worker só fala pt-BR (nunca recebeu o locale da sessão, de propósito — ver o docstring de
 * `FeedbackIssued`), então deixar `message` vencer travava o card em português mesmo com o
 * cliente já resolvendo o idioma certo em `textForCode` (servidor, via `GET /api/config`,
 * → embutido). `textForCode` sempre devolve uma string — quando não conhece o código, ecoa o
 * próprio código de volta — e é esse eco que usamos para detectar "catálogo local não sabe":
 * só aí o `message` do fio (pt-BR, mas pelo menos legível) e por fim o código cru entram como
 * último e penúltimo recursos. O HUD e o relatório continuam dizendo a mesma frase sobre o
 * mesmo código, porque os dois passam pelo mesmo `textForCode`.
 */
function textOf(entry: CoachEntry): string {
  const local = textForCode(entry.code)
  return local !== entry.code ? local : (entry.message ?? local)
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
