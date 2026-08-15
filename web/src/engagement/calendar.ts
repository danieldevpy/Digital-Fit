// A grade do mês do painel de engajamento (SPEC-019 §Superfícies / T-088). Puro.
//
// **Usa `diasAtivos` de `fire.ts`, e não `diasComTreino` de `history/aggregates.ts`.** Os dois
// existem, e a diferença é deliberada — o docstring do segundo já avisava disto:
//
// | | fuso | o que conta |
// |---|---|---|
// | `diasComTreino` (Progresso, SPEC-024) | de quem lê | qualquer sessão |
// | `diasAtivos` (fogo, SPEC-019) | America/Sao_Paulo fixo | só sessão **válida** (≥ 1 rep) |
//
// Este calendário é a explicação visual do fogo: ele tem de marcar exatamente os dias que o
// fogo contou. Usar a outra função produziria o pior desfecho possível — um dia aceso na grade
// que não conta para a sequência, ou o contrário, sem nada na tela explicando por quê.
import type { SessionReport } from '../report/sessionReport'
import { diasAtivos } from './fire'

export interface DiaDoMes {
  /** `AAAA-MM-DD` em São Paulo. */
  dia: string
  /** Dia do mês, 1–31. */
  numero: number
  ativo: boolean
  /** Depois de hoje: desenhado apagado, sem sugerir falha em dia que não chegou. */
  futuro: boolean
  hoje: boolean
}

export interface GradeDoMes {
  /** Quantas células vazias antes do dia 1, para a coluna bater com o dia da semana. */
  offset: number
  dias: DiaDoMes[]
  ativos: number
}

/** Iniciais da semana, começando na segunda — como o calendário brasileiro. */
export const INICIAIS_DA_SEMANA = ['S', 'T', 'Q', 'Q', 'S', 'S', 'D']

function totalDeDias(ano: number, mes: number): number {
  return new Date(Date.UTC(ano, mes, 0)).getUTCDate()
}

/**
 * A grade do mês de `hoje` (`AAAA-MM-DD` em SP), marcando os dias ativos.
 *
 * Datas montadas em UTC ao meio-dia de propósito: o mês é um rótulo de calendário, e construir
 * `new Date(ano, mes, dia)` no fuso do navegador faria a grade de quem está no Japão começar
 * num dia da semana diferente da de quem está aqui — para o mesmo mês do mesmo produto.
 */
export function gradeDoMes(sessoes: SessionReport[], hoje: string): GradeDoMes {
  const [ano, mes] = hoje.split('-').map(Number)
  if (!ano || !mes) return { offset: 0, dias: [], ativos: 0 }

  const ativos = diasAtivos(sessoes)
  const total = totalDeDias(ano, mes)
  const primeiro = new Date(Date.UTC(ano, mes - 1, 1, 12))
  // `getUTCDay()` devolve 0 para domingo; a grade abre na segunda.
  const offset = (primeiro.getUTCDay() + 6) % 7

  const dias: DiaDoMes[] = []
  for (let numero = 1; numero <= total; numero += 1) {
    const dia = `${ano}-${String(mes).padStart(2, '0')}-${String(numero).padStart(2, '0')}`
    dias.push({
      dia,
      numero,
      ativo: ativos.has(dia),
      futuro: dia > hoje,
      hoje: dia === hoje,
    })
  }

  return { offset, dias, ativos: dias.filter((d) => d.ativo).length }
}
