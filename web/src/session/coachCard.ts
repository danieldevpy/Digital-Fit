// Regra de exibição do card "Dica do Treinador" (SPEC-013 §4 e critério 3).
//
// Prioridade: warning de cena > feedback de execução > dica padrão do exercício.
// O card NUNCA fica vazio — sem nada ativo, mostra o `default_tip`.
//
// Função pura: a decisão de o que mostrar não depende de React nem do WebSocket.
import { t, tDynamic } from '../i18n'
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
 * Nada no contrato diz que um aviso deixou de valer — não existe evento de
 * "resolvido". Sem TTL o card ficaria preso no último aviso até o fim da sessão,
 * então o cliente expira sozinho. É cosmético: a autoridade segue no worker.
 */
export const COACH_ENTRY_TTL_MS = 6000

/**
 * Título do card, nas duas línguas (namespace `catalog`, T-152: `coach.title`). Função, não
 * `const` — mesmo motivo do resto desta migração: `resolveCoachCard` é chamada a cada render do
 * HUD, e uma constante de módulo congelaria no idioma de quando o bundle carregou.
 */
function coachTitle(): string {
  return t('catalog:coach.title')
}

/**
 * Texto **embutido**, nas duas línguas (T-152; antes, herança pendente da T-144), para o
 * primeiro paint e para o caso offline.
 *
 * A fonte da verdade é o catálogo do servidor (`catalog.<locale>.yaml`, servido no
 * `GET /api/config` desde a T-126, com idioma desde a T-144), pela regra da SPEC-018 §C: a
 * frase que a pessoa lê suando se reescreve sem deploy. Este dicionário (`catalog:code.*`) é o
 * default do cliente, na mesma doutrina do catálogo de exercícios — nunca é apagado quando o
 * servidor chega, nunca some quando a rede cai, e agora nasce nas duas línguas por construção
 * (o mesmo `tsc` que cobra `dict/en/*` de `dict/pt-BR/*` cobra este namespace).
 *
 * Ele precisa existir porque `scene.warning` **não tem campo `message`** (o contrato manda só o
 * código) e porque o relatório guarda `{código: contagem}`. Cobre TODO o enum `Code` de
 * propósito — código de fora deste mapa e fora do servidor aparece como identificador cru na
 * tela, que foi exatamente o que aconteceu com os seis códigos de chão e de agachamento antes
 * da T-126 (o teste `textForCode` abaixo cobra isso).
 *
 * `tDynamic`, não `t()`: `code` é `string` (código desconhecido é um caso coberto de propósito
 * — ver o teste "código desconhecido devolve ele mesmo"), não um literal fechado em `TKey`.
 */
function textoEmbutido(code: string): string {
  return tDynamic(`catalog:code.${code}`, code)
}

/**
 * Texto de um código solto, no idioma ativo. O relatório (SPEC-010) recebe só `{code: contagem}`
 * e precisa do mesmo texto que o HUD mostrou ao vivo — daí reusar esta função em vez de escrever
 * uma segunda tradução, que envelheceria em separado.
 *
 * Ordem: servidor, embutido, o próprio código. O último degrau continua sendo feio de
 * propósito — código na tela é um sintoma que se vê, e é assim que a T-126 foi descoberta.
 */
export function textForCode(code: string): string {
  return useConfigStore.getState().feedback?.[code]?.message ?? textoEmbutido(code)
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
      title: coachTitle(),
      text: textOf(input.scene),
      hint: input.scene.hint ?? null,
      tone: 'scene',
    }
  }

  if (isFresh(input.feedback, input.now, ttl)) {
    return {
      title: coachTitle(),
      text: textOf(input.feedback),
      hint: input.feedback.hint ?? null,
      tone: 'feedback',
    }
  }

  return { title: coachTitle(), text: input.defaultTip, hint: null, tone: 'default' }
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
