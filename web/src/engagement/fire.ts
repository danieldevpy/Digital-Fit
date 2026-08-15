// O fogo fantasma do visitante (SPEC-019 §Anônimo / T-088). Puro: entram sessões e uma data.
//
// **Este arquivo é a única derivação de engajamento que existe no cliente, e existe só para
// quem NÃO tem conta.** O critério de aceite 8 da SPEC-019 é literal: *"anônimo nunca vê número
// do servidor; logado nunca vê número calculado no cliente"*. Quem tem conta lê o
// `GET /api/engagement` e ponto — nada daqui entra na tela dessa pessoa.
//
// O visitante precisa de um número porque a dor de perder uma sequência de 4 dias é um CTA de
// cadastro melhor que o `429` do trial. Ele vem com rótulo honesto ("vive só neste aparelho"),
// e o `localStorage` que o alimenta já existe desde a T-121.
//
// ## Por que isto NÃO é um espelho da regra do servidor
//
// O servidor tem proteções, piso de downgrade e orçamento por mês-calendário. O visitante tem
// **zero proteções** (§Planos), e com zero a regra inteira colapsa em "dias seguidos terminando
// hoje ou ontem" — que é o que está escrito aqui. Copiar a mecânica de proteção para o cliente
// seria manter duas implementações de uma regra que só uma das duas pode executar.
import type { SessionReport } from '../report/sessionReport'

/**
 * Fuso do fogo: **America/Sao_Paulo fixo**, igual ao servidor (SPEC-019 §Fuso).
 *
 * Diverge de `aggregates.diaLocal`, que usa o fuso de quem lê — e a divergência é o ponto. Ali
 * a pergunta é "que dia foi para mim"; aqui é "que dia o servidor vai dizer que foi", porque
 * este número tem de bater com o que a conta mostra no instante seguinte ao cadastro. Um fogo
 * fantasma de 3 que vira 2 assim que a conta existe destruiria a confiança na mecânica no
 * primeiro contato — e seria culpa de um fuso, não de um treino.
 */
export const FUSO_DO_FOGO = 'America/Sao_Paulo'

const FORMATO_DO_DIA = new Intl.DateTimeFormat('en-CA', {
  timeZone: FUSO_DO_FOGO,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

/** Dia-calendário de um instante em São Paulo, como `AAAA-MM-DD`. `null` se a data não presta. */
export function diaDoFogo(iso: string | Date): string | null {
  const data = typeof iso === 'string' ? new Date(iso) : iso
  if (Number.isNaN(data.getTime())) return null
  // `en-CA` já formata como AAAA-MM-DD; `formatToParts` seria o caminho longo para o mesmo.
  return FORMATO_DO_DIA.format(data)
}

/**
 * Sessão que conta (SPEC-019 §Vocabulário): ao menos uma repetição.
 *
 * Sem a modalidade `hold`, que não existe no catálogo (T-098) e que o visitante não alcançaria
 * de todo jeito — exercício `beta`/`calibrado` é do assinante.
 */
export function sessaoValida(sessao: SessionReport): boolean {
  return sessao.rep_count >= 1
}

/** Dias (em SP) com pelo menos uma sessão válida. */
export function diasAtivos(sessoes: SessionReport[]): Set<string> {
  const dias = new Set<string>()
  for (const sessao of sessoes) {
    if (!sessaoValida(sessao)) continue
    const dia = diaDoFogo(sessao.created_at)
    if (dia !== null) dias.add(dia)
  }
  return dias
}

function diaAnterior(dia: string): string {
  // Meio-dia UTC para atravessar a subtração sem esbarrar em horário de verão.
  const data = new Date(`${dia}T12:00:00Z`)
  data.setUTCDate(data.getUTCDate() - 1)
  return data.toISOString().slice(0, 10)
}

export interface FogoLocal {
  /** Dias seguidos terminando hoje ou ontem. */
  streak: number
  /** Maior sequência já feita neste aparelho. */
  melhor: number
  treinouHoje: boolean
  sessoesHoje: number
}

/**
 * O fogo do visitante. `hoje` é parâmetro — nada aqui lê relógio.
 *
 * Sem proteção nenhuma: dia falho apaga. É o §Planos ("Proteções/mês: anônimo 0"), e é também
 * o que dá ao CTA a força que a spec quer — o visitante *sente* a fragilidade que a conta
 * resolve.
 */
export function fogoLocal(sessoes: SessionReport[], hoje: string): FogoLocal {
  const dias = diasAtivos(sessoes)
  const sessoesHoje = sessoes.filter(
    (s) => sessaoValida(s) && diaDoFogo(s.created_at) === hoje,
  ).length

  let streak = 0
  // Hoje sem treino não quebra: o dia não acabou. A sequência pode terminar em ontem.
  let cursor = dias.has(hoje) ? hoje : diaAnterior(hoje)
  while (dias.has(cursor)) {
    streak += 1
    cursor = diaAnterior(cursor)
  }

  let melhor = streak
  for (const dia of dias) {
    let corrente = 0
    let anda = dia
    while (dias.has(anda)) {
      corrente += 1
      anda = diaAnterior(anda)
    }
    if (corrente > melhor) melhor = corrente
  }

  return { streak, melhor, treinouHoje: dias.has(hoje), sessoesHoje }
}
