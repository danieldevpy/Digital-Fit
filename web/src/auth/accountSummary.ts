// Como a conta e o histórico são lidos em português (SPEC-011). Puro: entra dado, sai texto.
//
// Separado do componente pelo mesmo motivo do `reportSummary`: isto é regra, não desenho. O
// convite a criar conta muda conforme quantas sessões restam, e a data do histórico tem de
// dizer "hoje" quando é hoje — as duas coisas se testam com um objeto.
import type { SessionReport } from '../report/sessionReport'
import type { TrialStatus } from '../session/admission'

/** O que dizer sobre o trial de quem ainda não tem conta. `null` = não há o que dizer. */
export function trialMessage(trial: TrialStatus | null, blocked: boolean): string | null {
  if (blocked) {
    return 'Suas 3 sessões grátis de hoje acabaram. Crie uma conta para continuar treinando.'
  }
  if (!trial) return null
  if (trial.remaining <= 0) {
    return 'Você usou suas 3 sessões grátis de hoje.'
  }
  // Só avisa quando o fim está perto: repetir "restam 3" logo na primeira sessão é ansiedade
  // de graça num visitante que ainda nem sabe se gostou do produto.
  if (trial.remaining === 1) return 'Resta 1 sessão grátis hoje. Com conta, não acaba.'
  return null
}

/** Data curta de uma sessão do histórico: "hoje 19:42", "ontem 08:10", "24 jul 07:55". */
export function historyDate(iso: string, agora: Date = new Date()): string {
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return '—'

  const hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const dias = diasDeDiferenca(data, agora)
  if (dias === 0) return `hoje ${hora}`
  if (dias === 1) return `ontem ${hora}`
  return `${data.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })} ${hora}`
}

function diasDeDiferenca(data: Date, agora: Date): number {
  // Diferença de **dia de calendário**, não de 24 h: às 00:30 a sessão das 23:50 é "ontem",
  // e chamá-la de "hoje" por caber em 24 h seria mentira para quem está olhando.
  const inicio = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  return Math.round((inicio(agora) - inicio(data)) / 86_400_000)
}

export interface HistoryTotals {
  sessions: number
  reps: number
  /** Melhor cadência já registrada, em rep/min. */
  bestCadence: number
}

/** Resumo do histórico. Três números, os que a pessoa reconhece sem legenda. */
export function historyTotals(reports: SessionReport[]): HistoryTotals {
  return {
    sessions: reports.length,
    reps: reports.reduce((total, item) => total + item.rep_count, 0),
    bestCadence: reports.reduce((melhor, item) => Math.max(melhor, item.cadence_rpm), 0),
  }
}

/** Primeiro nome, para o cumprimento. Cai no e-mail quando a pessoa não deu nome. */
export function displayName(user: { name: string; email: string } | null): string {
  if (!user) return ''
  const nome = user.name.trim()
  if (nome) return nome.split(/\s+/)[0]
  return user.email.split('@')[0]
}
