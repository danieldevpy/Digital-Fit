// Histórico de sessões no aparelho (SPEC-024 §3 / T-121).
//
// Existe porque a maioria de quem usa o produto **não tem conta** — e sem isto Progresso e
// Analytics ficariam vazios para quase todo mundo. O servidor continua sendo a autoridade
// quando há conta (SPEC-011); isto é o carbono local, no mesmo espírito do `lastReport` e das
// preferências: conforto, não conta.
//
// Passa tudo por aqui em vez de chamar `localStorage` direto pelo motivo do `auth/storage.ts`:
// ele **falha de verdade** (Safari privado lança ao escrever), e um `setItem` solto derrubaria
// o fim do treino por causa de um registro de progresso.
import type { SessionReport } from '../report/sessionReport'
import { loadLastReport } from '../report/lastReport'

const KEY = 'digitalfit.history'

/**
 * Teto de sessões guardadas. Espelho do `HISTORY_LIMIT` de `server/api/views.py`.
 *
 * Igual ao do servidor **de propósito**: dois tetos diferentes fariam a mesma pessoa ver
 * históricos de tamanhos diferentes antes e depois de criar conta, e o degrau apareceria como
 * "o app apagou meus treinos" no dia do cadastro.
 *
 * (`Plan.history_limit` existe no banco e ninguém lê — Descoberta `[T-073]`. Quando a T-064
 * ligá-la, este número passa a sair do plano, e o piso continua sendo este.)
 */
export const HISTORY_CAP = 50

/** Descarta lixo de storage corrompido sem derrubar o app no boot. */
function pareceRelatorio(item: unknown): item is SessionReport {
  const alvo = item as Partial<SessionReport> | null
  return (
    typeof alvo?.session_id === 'string' &&
    typeof alvo.created_at === 'string' &&
    typeof alvo.rep_count === 'number'
  )
}

/**
 * O que este aparelho lembra de ter treinado.
 *
 * **Migração do `last_report`** (SPEC-024 §Notas): quem já tinha a chave antiga e nenhuma lista
 * entra aqui com uma sessão. Nada a apagar e nada a converter — o `last_report` continua
 * existindo para o seu outro trabalho, que é lembrar se a FOLHA estava aberta no F5. Fundir os
 * dois faria um dado de navegação viajar dentro do dado de treino.
 */
export function loadLocalHistory(): SessionReport[] {
  let bruto: string | null
  try {
    bruto = window.localStorage.getItem(KEY)
  } catch {
    return []
  }

  if (bruto !== null) {
    try {
      const lista: unknown = JSON.parse(bruto)
      if (Array.isArray(lista)) return lista.filter(pareceRelatorio).slice(0, HISTORY_CAP)
    } catch {
      // Storage corrompido: cai na migração abaixo, que é melhor que devolver nada.
    }
  }

  const antigo = loadLastReport()
  return antigo ? [antigo.report] : []
}

function gravar(lista: SessionReport[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(lista))
  } catch {
    // Sem armazenamento (Safari privado): o histórico vale pela sessão da página. O treino
    // acabou de funcionar; não é aqui que ele vai falhar.
  }
}

/**
 * Registra a sessão que acabou e devolve a lista nova.
 *
 * Idempotente por `session_id`: o relatório chega pelo `session.report.ready` **e** pelo
 * repique do `waitForReport` (SPEC-010), e as duas entradas contariam o mesmo treino duas
 * vezes. Substituir em vez de ignorar porque a segunda versão é a mais consolidada.
 */
export function recordLocalSession(report: SessionReport): SessionReport[] {
  const anterior = loadLocalHistory().filter((item) => item.session_id !== report.session_id)
  const lista = [report, ...anterior].slice(0, HISTORY_CAP)
  gravar(lista)
  return lista
}

/** Só o cadastro (T-087) vai querer isto; existe aqui para o teste de logout não mentir. */
export function clearLocalHistory(): void {
  try {
    window.localStorage.removeItem(KEY)
  } catch {
    // idem
  }
}
