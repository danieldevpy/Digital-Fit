// Como a conta e o histórico são lidos em português (SPEC-011). Puro: entra dado, sai texto.
//
// Separado do componente pelo mesmo motivo do `reportSummary`: isto é regra, não desenho. O
// convite a criar conta muda conforme quantas sessões restam, e a data do histórico tem de
// dizer "hoje" quando é hoje — as duas coisas se testam com um objeto.
import type { SessionReport } from '../report/sessionReport'
import type { QuotaSnapshot } from '../session/quota'

/** O sheet de limite da SPEC-016, montado. `null` = não há nada a dizer sobre a quota agora. */
export interface QuotaNotice {
  title: string
  /** Texto do servidor (`Plan.quota_message`, editável no painel) — nunca uma cópia local. */
  text: string
  /** "10 de 10 sessões de hoje". `null` quando o plano não tem limite. */
  count: string | null
  /** "Renova às 21:00". `null` quando não há o que renovar. */
  renew: string | null
}

/**
 * O que dizer sobre a quota de hoje.
 *
 * Puro e separado do componente pela mesma razão do `reportSummary`: isto é regra, não desenho.
 * Quando avisar, e com que palavras, muda conforme quem está falando e quanto sobrou — e as
 * três coisas se testam com um objeto.
 *
 * **Todo número aqui vem do servidor.** O texto é o `Plan.quota_message`, a contagem é
 * `used`/`limit` e o horário sai do `resets_at`. O cliente não guarda cópia de nenhum dos três:
 * o painel muda o limite para 15 e esta função passa a dizer 15, sem deploy.
 */
export function quotaNotice(
  quota: QuotaSnapshot | null,
  blocked: boolean,
  agora: Date = new Date(),
): QuotaNotice | null {
  if (!quota || quota.unlimited) return null

  const esgotou = blocked || !quota.allowed
  if (esgotou) {
    return {
      // O título é do cliente e o corpo é do servidor de propósito: o "🎉" da spec é parte do
      // desenho da tela (é ele que faz o limite ler como parabéns e não como punição), e o
      // corpo é o que o suporte reescreve no painel numa terça-feira sem chamar ninguém.
      title: 'Você treinou muito hoje 🎉',
      text: quota.message,
      count: `${quota.used} de ${quota.limit} sessões de hoje`,
      renew: renewLabel(quota.resets_at, agora),
    }
  }

  // Só avisa quando o fim está perto: repetir "restam 10" logo na primeira sessão é ansiedade
  // de graça em quem ainda nem sabe se gostou do produto.
  if (quota.remaining > 1) return null
  return {
    title: 'Última sessão de hoje',
    text:
      quota.plan === 'anon'
        ? 'Resta 1 sessão grátis hoje. Com conta, são mais.'
        : 'Resta 1 sessão hoje. Com assinatura, não acaba.',
    count: `${quota.used} de ${quota.limit} sessões de hoje`,
    renew: renewLabel(quota.resets_at, agora),
  }
}

/**
 * "Renova às 21:00" — no fuso de quem está lendo, não no do contador.
 *
 * O servidor conta o dia em UTC (`api/quota.py`), e dizer "à meia-noite" seria mentir para
 * quem está no Brasil: lá o contador vira às 21 h. Mandar o instante e formatá-lo aqui é o que
 * mantém as duas coisas verdadeiras ao mesmo tempo — o servidor conta como conta, e a pessoa
 * lê a hora do relógio dela.
 *
 * Acima de 12 h de espera vira "amanhã": um horário exato para daqui a 20 h não ajuda ninguém
 * a decidir nada, e "amanhã" é a informação que a pessoa de fato usa.
 */
export function renewLabel(isoUtc: string, agora: Date = new Date()): string | null {
  const virada = new Date(isoUtc)
  if (Number.isNaN(virada.getTime())) return null

  const horas = (virada.getTime() - agora.getTime()) / 3_600_000
  if (horas <= 0) return null
  const hora = virada.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  return horas > 12 ? `Renova amanhã às ${hora}` : `Renova às ${hora}`
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
  // `?? ''` não é decoração: com `noUncheckedIndexedAccess`, `split()[0]` é `string |
  // undefined` para o compilador. Na prática `split` nunca devolve vazio, mas o tipo é o que
  // o build verifica — e o build estava passando sem verificar nada (ver T-048).
  const nome = user.name.trim()
  if (nome) return nome.split(/\s+/)[0] ?? ''
  return user.email.split('@')[0] ?? ''
}
