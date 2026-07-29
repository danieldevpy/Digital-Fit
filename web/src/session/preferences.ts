// Preferências de quem treina (T-049). Ficam no aparelho: são conforto, não conta.
//
// Guardar no servidor exigiria conta — e a SPEC-011 é explícita em que treinar não exige
// conta. Uma preferência que só funciona depois de cadastrar seria uma pequena punição por
// não se cadastrar, no produto que se define por não precisar disso.

import { DEFAULT_EXERCISE, isExerciseKey } from './catalog'

const COUNTDOWN_KEY = 'digitalfit.countdown_s'
const EXERCISE_KEY = 'digitalfit.exercise'

/** Espelho de `DEFAULT_COUNTDOWN_S` em `workers/shared/events.py`. */
export const DEFAULT_COUNTDOWN_S = 3

/** Espelho de `MAX_COUNTDOWN_S`. O servidor também limita — este é só o da UI. */
export const MAX_COUNTDOWN_S = 10

/** As opções que a tela oferece. `0` é "desligado", e existe porque a spec pede. */
export const COUNTDOWN_OPTIONS = [0, 3, 5, 10] as const

export function clampCountdown(valor: unknown): number {
  const numero = Number(valor)
  if (!Number.isFinite(numero)) return DEFAULT_COUNTDOWN_S
  return Math.max(0, Math.min(MAX_COUNTDOWN_S, Math.round(numero)))
}

export function countdownPreference(): number {
  try {
    const bruto = window.localStorage.getItem(COUNTDOWN_KEY)
    // Nunca escolheu: vale o default do produto, não zero.
    if (bruto === null) return DEFAULT_COUNTDOWN_S
    return clampCountdown(bruto)
  } catch {
    return DEFAULT_COUNTDOWN_S
  }
}

export function setCountdownPreference(segundos: number): number {
  const valor = clampCountdown(segundos)
  try {
    window.localStorage.setItem(COUNTDOWN_KEY, String(valor))
  } catch {
    // Sem armazenamento (Safari privado): vale pela sessão atual e pronto.
  }
  return valor
}

/** Próxima opção do ciclo — é assim que o controle da tela avança com um toque. */
export function nextCountdown(atual: number): number {
  const indice = COUNTDOWN_OPTIONS.indexOf(clampCountdown(atual) as (typeof COUNTDOWN_OPTIONS)[number])
  if (indice === -1) return DEFAULT_COUNTDOWN_S
  return COUNTDOWN_OPTIONS[(indice + 1) % COUNTDOWN_OPTIONS.length] ?? DEFAULT_COUNTDOWN_S
}

/** Texto do controle. "Sem preparação" é mais claro que "0 s" para quem só quer treinar. */
export function countdownLabel(segundos: number): string {
  return segundos === 0 ? 'sem preparação' : `${segundos}s de preparação`
}

/**
 * Último exercício escolhido (T-051). Mesma casa e mesmo motivo da preparação: é conforto de
 * quem treina, e a SPEC-011 garante treinar sem conta.
 *
 * Validado contra o catálogo na LEITURA, não só na escrita. Um slug guardado hoje pode deixar
 * de existir amanhã (exercício removido, aparelho que ficou meses parado) — e um slug morto
 * no armazenamento derrubaria a admissão do servidor a cada tentativa de treinar, sem nenhum
 * caminho de volta pela interface.
 */
export function exercisePreference(): string {
  try {
    const bruto = window.localStorage.getItem(EXERCISE_KEY)
    return isExerciseKey(bruto) ? bruto : DEFAULT_EXERCISE
  } catch {
    return DEFAULT_EXERCISE
  }
}

export function setExercisePreference(chave: string): string {
  const valor = isExerciseKey(chave) ? chave : DEFAULT_EXERCISE
  try {
    window.localStorage.setItem(EXERCISE_KEY, valor)
  } catch {
    // Sem armazenamento (Safari privado): vale pela sessão atual e pronto.
  }
  return valor
}
