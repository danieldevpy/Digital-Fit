// A vista única do engajamento (SPEC-019 / T-088): uma forma, duas fontes.
//
// O critério de aceite 8 é o que desenha este arquivo: *"anônimo nunca vê número do servidor;
// logado nunca vê número calculado no cliente"*. A escolha entre as duas fontes acontece
// **aqui, uma vez**, e não em cada componente — chip, painel e Perfil recebem o mesmo objeto e
// não sabem de onde ele veio. Componente que decidisse sozinho acabaria decidindo diferente.
import { useEffect } from 'react'
import { useHistoryStore } from '../history/store'
import { useFreshHistory } from '../history/useFreshHistory'
import { useAccountStore } from '../store/account'
import type { Achievement } from './api'
import { diaDoFogo, fogoLocal } from './fire'
import { refreshEngagement, useEngagementStore } from './store'

/** Alvo de cada meta (SPEC-019 §Vocabulário). Espelho de `engagement.METAS` no servidor. */
export const METAS: Record<string, number> = { casual: 1, regular: 2, intenso: 4 }
export const META_PADRAO = 'casual'

export interface EngagementView {
  /**
   * `local` obriga o rótulo honesto ("vive só neste aparelho") e o CTA de conta. Mesmo
   * vocabulário do `HistorySource` da SPEC-024, e pela mesma razão.
   */
  source: 'local' | 'server'
  streak: number
  bestStreak: number
  todayActive: boolean
  sessionsToday: number
  goalTarget: number
  goalDone: boolean
  /** `null` para o visitante: XP e nível não existem sem conta (§Planos). */
  xp: number | null
  level: number | null
  /** Proteções gastas / disponíveis no mês. `null` para o visitante, que tem zero. */
  protections: { used: number; total: number } | null
  /** Ainda não chegou nada do servidor para quem tem conta — a tela mostra `--`. */
  pending: boolean
  /**
   * Catálogo inteiro de conquistas, com `earned` em cada uma (T-089).
   *
   * **Vazio para o visitante**, e não um catálogo todo bloqueado: conquistas são do servidor
   * (§Planos diz "básicas" para o Free e nada para o anônimo), e desenhar a vitrine para quem
   * não pode ganhar nenhuma seria uma promessa que a conta é que cumpre.
   */
  achievements: Achievement[]
}

const VISITANTE_SEM_TREINO: EngagementView = {
  source: 'local',
  streak: 0,
  bestStreak: 0,
  todayActive: false,
  sessionsToday: 0,
  goalTarget: METAS[META_PADRAO] ?? 1,
  goalDone: false,
  xp: null,
  level: null,
  protections: null,
  pending: false,
  achievements: [],
}

/**
 * O engajamento de quem está olhando, já resolvido.
 *
 * Revalida junto com o histórico (mesmo contrato de frescor da SPEC-024 §2) porque as duas
 * coisas mudam pelo mesmo fato: uma sessão terminou.
 */
export function useEngagement(hoje: string = diaDoFogo(new Date()) ?? ''): EngagementView {
  const user = useAccountStore((state) => state.user)
  const doServidor = useEngagementStore((state) => state.data)
  const sessoes = useHistoryStore((state) => state.sessions)

  useFreshHistory()

  useEffect(() => {
    void refreshEngagement()

    if (typeof document === 'undefined') return
    const aoVoltar = () => {
      if (!document.hidden) void refreshEngagement()
    }
    document.addEventListener('visibilitychange', aoVoltar)
    return () => document.removeEventListener('visibilitychange', aoVoltar)
    // A identidade entra na dependência: entrar numa conta troca a fonte do número.
  }, [user?.id])

  if (user === null) {
    const local = fogoLocal(sessoes, hoje)
    return {
      ...VISITANTE_SEM_TREINO,
      streak: local.streak,
      bestStreak: local.melhor,
      todayActive: local.treinouHoje,
      sessionsToday: local.sessoesHoje,
      goalDone: local.sessoesHoje >= (METAS[META_PADRAO] ?? 1),
    }
  }

  if (doServidor === null) {
    // Logado e sem resposta ainda. **Não cai no fantasma**: seria o número do cliente na tela
    // de quem tem conta, que é exatamente o que o critério 8 proíbe. A tela mostra `--`.
    return { ...VISITANTE_SEM_TREINO, source: 'server', pending: true }
  }

  return {
    source: 'server',
    streak: doServidor.streak,
    bestStreak: doServidor.best_streak,
    todayActive: doServidor.today_active,
    sessionsToday: doServidor.sessions_today,
    goalTarget: doServidor.goal_target,
    goalDone: doServidor.goal_done_today,
    xp: doServidor.xp,
    level: doServidor.level.number,
    protections: {
      used: doServidor.protections_used_month,
      total: doServidor.protections_month,
    },
    pending: false,
    achievements: doServidor.achievements ?? [],
  }
}
