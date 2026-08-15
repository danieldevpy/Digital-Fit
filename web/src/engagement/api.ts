// `GET /api/engagement` (SPEC-019 / T-088). Espelho de `Engajamento.to_dict()` no servidor.
//
// Chaves em snake_case pelo mesmo motivo do `SessionReport`: é o formato que trafega, e
// traduzir na fronteira só criaria uma chance a mais de drift.
import { authedFetch } from '../auth/api'

export interface EngagementLevel {
  number: number
  xp_min: number
  /** `null` no último nível — resposta honesta, não teto inventado. */
  xp_next: number | null
  progress: number
}

/**
 * Corpo do `GET /api/engagement`.
 *
 * **Não tem `achievements`**: o catálogo de conquistas é a T-089, e o servidor omite a chave em
 * vez de mandar lista vazia — vazio seria lido como "não conquistou nada", que é uma afirmação.
 */
export interface Engagement {
  streak: number
  best_streak: number
  protections_used_month: number
  protections_month: number
  today_active: boolean
  sessions_today: number
  goal: string
  goal_target: number
  goal_done_today: boolean
  xp: number
  xp_formula_v: number
  level: EngagementLevel
}

/** `null` quando não há conta (401) ou a rede falhou — quem chama decide o que mostrar. */
export async function fetchEngagement(fetchImpl: typeof fetch = fetch): Promise<Engagement | null> {
  try {
    const resposta = await authedFetch('/api/engagement', {}, fetchImpl)
    if (!resposta.ok) return null
    return (await resposta.json()) as Engagement
  } catch {
    // Rede fora não é motivo para apagar o fogo da tela: quem chama mantém o que já tinha.
    return null
  }
}
