// As leituras do histórico (SPEC-024 §4 / T-123). Puro: entram sessões e uma data, sai objeto.
//
// Mesma filosofia da FSM e do `accountSummary`: isto é **regra**, não desenho. Nenhuma função
// aqui lê relógio, rede ou store — "hoje" é parâmetro. Por isso tudo se testa com uma lista de
// objetos, sem mock de tempo, e por isso as telas da T-124/T-125 não têm lógica dentro.
//
// Tudo aqui é derivável de `SessionReport[]`, que é o que `GET /api/sessions?mine` já devolve.
// Nada de kcal (depende do peso, SPEC-017) e nada de fogo/XP (SPEC-019) — ver §Fora de escopo.
import type { SessionReport } from '../report/sessionReport'

// ------------------------------------------------------------------ dias

/**
 * Dia-calendário **de quem lê**, como `AAAA-MM-DD`. `null` quando a data não presta.
 *
 * Local, e não UTC: a sessão das 22h de um brasileiro é de hoje, e chamá-la de amanhã porque
 * o servidor guarda em UTC seria mentir para quem está olhando. Diverge **de propósito** do
 * America/Sao_Paulo fixo que a SPEC-019 escolhe para o fogo: lá a pergunta é "o mesmo dia para
 * todo mundo", aqui é "que dia foi para mim".
 */
export function diaLocal(iso: string): string | null {
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return null
  const mes = String(data.getMonth() + 1).padStart(2, '0')
  const dia = String(data.getDate()).padStart(2, '0')
  return `${data.getFullYear()}-${mes}-${dia}`
}

/**
 * Dias em que houve pelo menos uma sessão.
 *
 * Chama-se `diasComTreino`, e **não** "dias ativos", de propósito: "dia ativo" é vocabulário
 * vinculante da SPEC-019, onde exige sessão *válida* (`rep_count ≥ 1`, senão abrir a câmera
 * por 30 s vira fazenda de fogo). Aqui a SPEC-024 §4 pede a grade do mês, que marca o dia em
 * que a pessoa treinou. Dois nomes para dois conceitos evita o pior desfecho possível: o M1
 * acender o fogo num dia que esta grade não marcou, ou o contrário.
 */
export function diasComTreino(sessions: SessionReport[]): Set<string> {
  const dias = new Set<string>()
  for (const sessao of sessions) {
    const dia = diaLocal(sessao.created_at)
    if (dia !== null) dias.add(dia)
  }
  return dias
}

// ---------------------------------------------------------------- semanas

export interface ResumoSemana {
  /** Segunda-feira que abre a semana, 00:00 local. */
  inicio: Date
  sessoes: number
  reps: number
}

/** Segunda-feira que abre a semana da data, 00:00 no fuso de quem lê. */
export function inicioDaSemana(data: Date): Date {
  const dia = new Date(data.getFullYear(), data.getMonth(), data.getDate())
  // `getDay()` devolve 0 para domingo; a semana brasileira abre na segunda.
  const desdeSegunda = (dia.getDay() + 6) % 7
  dia.setDate(dia.getDate() - desdeSegunda)
  return dia
}

/**
 * As últimas N semanas, da mais antiga para a mais recente.
 *
 * Semana de calendário (segunda a domingo) e não janela de 7 dias corridos: a pessoa compara
 * com o que ela chama de semana, e uma janela deslizante faria o mesmo treino mudar de semana
 * a cada dia que passa. Semanas vazias entram com zero — o buraco é a informação.
 */
export function porSemana(
  sessions: SessionReport[],
  semanas = 4,
  hoje: Date = new Date(),
): ResumoSemana[] {
  const atual = inicioDaSemana(hoje)
  const resumo: ResumoSemana[] = []

  for (let recuo = semanas - 1; recuo >= 0; recuo -= 1) {
    const inicio = new Date(atual)
    inicio.setDate(inicio.getDate() - recuo * 7)
    const fim = new Date(inicio)
    fim.setDate(fim.getDate() + 7)

    let contadas = 0
    let reps = 0
    for (const sessao of sessions) {
      const quando = new Date(sessao.created_at).getTime()
      if (Number.isNaN(quando)) continue
      if (quando >= inicio.getTime() && quando < fim.getTime()) {
        contadas += 1
        reps += sessao.rep_count
      }
    }
    resumo.push({ inicio, sessoes: contadas, reps })
  }

  return resumo
}

// ------------------------------------------------------------- exercícios

export interface TotalPorExercicio {
  exercise: string
  sessoes: number
  reps: number
}

/** Quanto de cada exercício, da maior soma de repetições para a menor. */
export function porExercicio(sessions: SessionReport[]): TotalPorExercicio[] {
  const mapa = new Map<string, TotalPorExercicio>()
  for (const sessao of sessions) {
    const atual = mapa.get(sessao.exercise) ?? { exercise: sessao.exercise, sessoes: 0, reps: 0 }
    atual.sessoes += 1
    atual.reps += sessao.rep_count
    mapa.set(sessao.exercise, atual)
  }
  return [...mapa.values()].sort((a, b) => b.reps - a.reps || b.sessoes - a.sessoes)
}

// --------------------------------------------------------------- cadência

/**
 * Mínimo de pontos para uma linha significar alguma coisa (SPEC-024 §5).
 *
 * Um gráfico com um ponto não é um gráfico — é a sugestão de uma tendência que ninguém mediu.
 * É a régua do `--` da SPEC-014 §Desvios aplicada a série temporal.
 */
export const MIN_PONTOS_TENDENCIA = 2

export interface PontoCadencia {
  at: string
  cadence_rpm: number
}

export interface SerieCadencia {
  exercise: string
  /** Do mais antigo para o mais recente — é assim que uma linha se lê. */
  pontos: PontoCadencia[]
  /** `false` obriga a tela a dizer o que falta em vez de desenhar. */
  tendencia: boolean
}

/**
 * Cadência ao longo do tempo, **por exercício**.
 *
 * Separado por exercício porque comparar o rep/min de polichinelo com o de agachamento não
 * significa nada: são movimentos de duração diferente, e a linha misturada oscilaria conforme
 * o que a pessoa escolheu treinar, não conforme ela melhorou.
 */
export function cadenciaPorExercicio(sessions: SessionReport[]): SerieCadencia[] {
  const mapa = new Map<string, PontoCadencia[]>()
  for (const sessao of sessions) {
    const quando = new Date(sessao.created_at).getTime()
    if (Number.isNaN(quando)) continue
    const pontos = mapa.get(sessao.exercise) ?? []
    pontos.push({ at: sessao.created_at, cadence_rpm: sessao.cadence_rpm })
    mapa.set(sessao.exercise, pontos)
  }

  return [...mapa.entries()]
    .map(([exercise, pontos]) => ({
      exercise,
      pontos: pontos.sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime()),
      tendencia: pontos.length >= MIN_PONTOS_TENDENCIA,
    }))
    .sort((a, b) => b.pontos.length - a.pontos.length)
}

// ---------------------------------------------------------------- ritmo

/**
 * Quão constante foi o ritmo **dentro** de uma sessão: desvio-padrão dividido pela média das
 * durações de repetição (coeficiente de variação). Menor = mais regular.
 *
 * Relativo, e não em milissegundos, porque a comparação que interessa é entre sessões de
 * exercícios diferentes: 300 ms de desvio é muito num polichinelo e pouco num agachamento.
 * Dividir pela própria média é a mesma doutrina das features da FSM — razão contra si mesmo.
 *
 * `null` com menos de duas repetições: dispersão de um número só não existe, e devolver `0`
 * afirmaria uma regularidade perfeita que ninguém mediu.
 */
export function consistenciaDoRitmo(sessao: SessionReport): number | null {
  const duracoes = (sessao.rep_durations_ms ?? []).filter((ms) => Number.isFinite(ms) && ms > 0)
  if (duracoes.length < 2) return null

  const media = duracoes.reduce((total, ms) => total + ms, 0) / duracoes.length
  if (media === 0) return null
  const variancia =
    duracoes.reduce((total, ms) => total + (ms - media) ** 2, 0) / duracoes.length
  return Math.sqrt(variancia) / media
}

// ------------------------------------------------- correções e avisos

export type Rumo = 'caindo' | 'subindo' | 'estavel'

export interface Contagem {
  key: string
  total: number
  /**
   * Para onde vai, comparando a metade mais recente do histórico com a mais antiga.
   * `null` quando não há sessões suficientes para dizer — e aí a tela não diz.
   */
  rumo: Rumo | null
}

type CampoDeContagem = 'feedback_counts' | 'scene_warning_counts'

/**
 * Soma os contadores de todas as sessões, da mais frequente para a menos.
 *
 * O rumo compara a metade recente com a antiga **por sessão**, não por total absoluto: quem
 * treinou o dobro de vezes acumularia o dobro de correções sem ter piorado em nada.
 */
export function contagens(sessions: SessionReport[], campo: CampoDeContagem): Contagem[] {
  const ordenadas = [...sessions].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  )
  const meio = Math.floor(ordenadas.length / 2)
  const antigas = ordenadas.slice(0, meio)
  const recentes = ordenadas.slice(meio)

  const totais = new Map<string, number>()
  for (const sessao of ordenadas) {
    for (const [chave, valor] of Object.entries(sessao[campo] ?? {})) {
      totais.set(chave, (totais.get(chave) ?? 0) + valor)
    }
  }

  // Com menos de duas sessões não há duas metades para comparar (SPEC-024 §5).
  const podeComparar = ordenadas.length >= MIN_PONTOS_TENDENCIA

  return [...totais.entries()]
    .map(([key, total]) => ({
      key,
      total,
      rumo: podeComparar
        ? rumo(mediaPorSessao(antigas, campo, key), mediaPorSessao(recentes, campo, key))
        : null,
    }))
    .sort((a, b) => b.total - a.total || a.key.localeCompare(b.key))
}

function mediaPorSessao(sessions: SessionReport[], campo: CampoDeContagem, key: string): number {
  if (sessions.length === 0) return 0
  const soma = sessions.reduce((total, sessao) => total + ((sessao[campo] ?? {})[key] ?? 0), 0)
  return soma / sessions.length
}

/**
 * Margem de 10% antes de chamar de mudança.
 *
 * Sem ela, duas correções contra 2,1 viraria "está piorando" — e a tela passaria a informar
 * ruído de amostra como se fosse notícia sobre o corpo de alguém.
 */
const MARGEM = 0.1

function rumo(antes: number, depois: number): Rumo {
  const base = Math.max(antes, depois)
  if (base === 0) return 'estavel'
  const variacao = (depois - antes) / base
  if (variacao < -MARGEM) return 'caindo'
  if (variacao > MARGEM) return 'subindo'
  return 'estavel'
}
