// Quando o app sugere virar o celular (SPEC-027 §E).
//
// O catálogo já sabia disto em texto solto: o `scene_tip` da flexão e do abdominal diz
// "celular deitado no chão, de lado". Texto serve para a pessoa LER; não serve para a tela
// COMPARAR com a orientação medida do aparelho. `orientacao_recomendada` é a mesma informação
// em forma consultável, e esta função é a comparação.
//
// **Orienta, nunca bloqueia** — a regra inteira herdada da decisão 1 da T-085 (SPEC-003). O
// conselho não desabilita o CTA, não vira modal e não impede treinar. Travar por causa de uma
// preferência de enquadramento seria o caminho curto para o app parecer quebrado em cima de
// alguém que estava prestes a treinar.
import type { Orientation } from '../shell/orientation'

/** O que o exercício prefere. `qualquer` é afirmação, não omissão: as duas servem. */
export type OrientacaoRecomendada = 'retrato' | 'paisagem' | 'qualquer'

export function isOrientacaoRecomendada(valor: unknown): valor is OrientacaoRecomendada {
  return valor === 'retrato' || valor === 'paisagem' || valor === 'qualquer'
}

/**
 * O contrato do campo é fechado no cliente e aberto no servidor (`CharField`), como em
 * `main_angle`. Valor desconhecido cai em `qualquer` — o único default honesto: um cliente
 * antigo não deve dar conselho sobre um vocabulário que ele não conhece.
 */
export function recomendacaoDe(valor: unknown): OrientacaoRecomendada {
  return isOrientacaoRecomendada(valor) ? valor : 'qualquer'
}

/**
 * Qual conselho mostrar, se algum.
 *
 * `null` nos dois casos em que falar seria ruído: o exercício não tem preferência, ou o
 * aparelho já está como ele pede. Conselho que aparece quando não há o que mudar é o que
 * ensina a ignorar conselho.
 */
export function orientationAdvice(
  recomendada: OrientacaoRecomendada,
  atual: Orientation,
): 'retrato' | 'paisagem' | null {
  if (recomendada === 'qualquer') return null
  const atualComoRecomendacao: OrientacaoRecomendada =
    atual === 'landscape' ? 'paisagem' : 'retrato'
  return recomendada === atualComoRecomendacao ? null : recomendada
}
