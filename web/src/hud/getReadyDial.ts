// Contas do mostrador da preparação (T-049). Puro: entram instantes, saem números.
//
// Separado do componente pelo mesmo motivo do `reportSummary` e do `accountSummary`: isto é
// regra, não desenho — e regra se testa com um objeto, sem montar React.
export const DIAL_SIZE = 208
export const DIAL_STROKE = 8
export const DIAL_RADIUS = (DIAL_SIZE - DIAL_STROKE) / 2
export const DIAL_CIRCUMFERENCE = 2 * Math.PI * DIAL_RADIUS

/** Quanto falta, em segundos inteiros — 3, 2, 1 e então 0 (que a tela mostra como "VAI!"). */
export function segundosRestantes(ate: number, agora: number): number {
  return Math.max(0, Math.ceil((ate - agora) / 1000))
}

/**
 * Fração do anel ainda cheia, de 1 a 0.
 *
 * Contínua, e não em degraus de um segundo: o anel é o que dá a sensação de tempo correndo, e
 * um anel que pula de terço em terço parece travado, não urgente.
 */
export function fracaoRestante(ate: number, agora: number, totalMs: number): number {
  if (totalMs <= 0) return 0
  return Math.min(1, Math.max(0, (ate - agora) / totalMs))
}
