// O que os componentes de engajamento *dizem* (SPEC-019 / T-088). Puro.
//
// Separado dos `.tsx` por dois motivos que coincidem: o lint da casa não aceita arquivo de
// componente exportando função solta (quebra o fast refresh), e — mais importante — estas são
// as **regras de honestidade** da tela, não desenho. "Mostrar `--` em vez de `0`" e "dizer em
// palavras que o número vive só neste aparelho" são decisões da SPEC-014 e da SPEC-019; num
// arquivo próprio elas têm teste, e não dependem de renderizar componente para serem checadas.
import type { XpBreakdown } from '../report/sessionReport'
import type { EngagementView } from './useEngagement'

/**
 * O número do chip.
 *
 * `--` e não `0` enquanto o servidor não respondeu (SPEC-014, "honestidade > fidelidade"):
 * zero é uma afirmação sobre o treino de alguém, e "ainda não sei" não é zero.
 */
export function fireLabel(view: EngagementView): string {
  return view.pending ? '--' : String(view.streak)
}

/**
 * Rótulo acessível do chip — onde a diferença entre fogo local e do servidor vira palavra.
 *
 * Um leitor de tela não pode receber "3 dias seguidos" quando o número vive só neste
 * navegador: o ponto cinza que avisa isso na tela não existe para quem não vê a tela.
 */
export function fireAriaLabel(view: EngagementView): string {
  if (view.pending) return 'Sequência ainda carregando'
  const dias = view.streak === 1 ? '1 dia seguido' : `${view.streak} dias seguidos`
  const meta = `meta do dia ${view.sessionsToday} de ${view.goalTarget}`
  const onde = view.source === 'local' ? ', guardado só neste aparelho' : ''
  return `${dias}, ${meta}${onde}`
}

/**
 * As parcelas do XP que valem a pena mostrar.
 *
 * Parcela zerada some: "limpa +0" não é informação, é ruído com cara de repreensão. Quem fez um
 * treino com correções vê "sessão +10 · reps +18" e o total menor — a ausência do bônus é o que
 * comunica, sem apontar o dedo.
 */
export function parcelasDeXp(xp: XpBreakdown): Array<{ rotulo: string; valor: number }> {
  return [
    { rotulo: 'sessão', valor: xp.session },
    { rotulo: 'reps', valor: xp.reps },
    { rotulo: 'limpa', valor: xp.clean },
  ].filter((parcela) => parcela.valor > 0)
}
