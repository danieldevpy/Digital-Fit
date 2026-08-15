// Conquistas do lado do cliente (SPEC-019 §Conquistas / T-089). Puro + um `localStorage`.
//
// **O catálogo NÃO mora aqui.** Nome, descrição e predicado são do servidor (`ACHIEVEMENTS` em
// `api/engagement.py`), e o `GET /api/engagement` manda a lista inteira com `earned` em cada
// uma. Um catálogo espelhado no bundle seria o `[A/T-051]` outra vez: no dia em que uma
// conquista nova nascesse, ela existiria para o servidor e não para a tela — ou pior, a tela
// mostraria uma que o servidor nunca concede.
//
// O que é responsabilidade do cliente, e só ele pode fazer, é saber **o que esta pessoa ainda
// não viu**: o servidor não guarda "notificado em" (a spec recusa a tabela), então o aviso de
// conquista nova é um diff entre a lista de agora e a última vista — mesma técnica do
// `guide_seen` da SPEC-015.
import type { Achievement } from './api'

const KEY = 'digitalfit.achievements_seen'

function ler(): string[] {
  try {
    const bruto = window.localStorage.getItem(KEY)
    const lista: unknown = bruto ? JSON.parse(bruto) : []
    return Array.isArray(lista) ? lista.filter((s): s is string => typeof s === 'string') : []
  } catch {
    // Safari privado, JSON corrompido: "não sei o que já foi visto" degrada para "tudo visto",
    // e não para "tudo novo" — um app que dispara sete toasts na primeira abertura por causa
    // de um storage quebrado é pior que um que não avisa.
    return []
  }
}

function gravar(slugs: string[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(slugs))
  } catch {
    // Sem armazenamento a pessoa reveria o aviso na próxima visita. É o pior caso, e é ameno.
  }
}

/** Só os slugs ganhos, na ordem do catálogo. */
export function ganhas(lista: Achievement[]): string[] {
  return lista.filter((c) => c.earned).map((c) => c.slug)
}

/**
 * As conquistas ganhas que ainda não foram mostradas.
 *
 * `vistas` entra por parâmetro para a regra ser testável sem `localStorage` — a leitura fica em
 * `novasConquistas` logo abaixo.
 */
export function diffDeConquistas(lista: Achievement[], vistas: string[]): Achievement[] {
  const jaVistas = new Set(vistas)
  return lista.filter((c) => c.earned && !jaVistas.has(c.slug))
}

/**
 * O primeiro acesso NÃO dispara avisos.
 *
 * Quem já treinava antes desta task abriria o app e receberia sete toasts de uma vez — inclusive
 * de conquistas ganhas meses atrás. A primeira leitura **marca tudo como visto em silêncio**; a
 * partir daí, cada conquista nova aparece uma vez. É a mesma escolha do `guide_seen`: a marca
 * existe para não repetir, não para celebrar retroativamente.
 */
export function novasConquistas(lista: Achievement[]): Achievement[] {
  if (lista.length === 0) return []

  let bruto: string | null
  try {
    bruto = window.localStorage.getItem(KEY)
  } catch {
    bruto = null
  }

  const todas = ganhas(lista)
  if (bruto === null) {
    gravar(todas)
    return []
  }

  const novas = diffDeConquistas(lista, ler())
  if (novas.length > 0) gravar(todas)
  return novas
}

/** Usado pelos testes e por um logout: a próxima leitura volta a ser a primeira. */
export function esquecerConquistas(): void {
  try {
    window.localStorage.removeItem(KEY)
  } catch {
    // Nada a fazer — e nada quebra por causa disso.
  }
}
