// Último relatório no aparelho (ajuste pós-teste de 2026-07-30): o relatório vivia só no
// store, e um F5 depois do treino apagava o resultado da tela — para quem treinou sem conta,
// apagava de vez. O servidor continua sendo a autoridade (SPEC-010); isto é o carbono local
// da última sessão, no mesmo espírito das preferências: conforto, não conta.
import type { SessionReport } from './sessionReport'

const KEY = 'digitalfit.last_report'

interface StoredReport {
  report: SessionReport
  /** A folha estava aberta quando a página morreu? Reabre no load — fechada fica fechada. */
  open: boolean
}

export function loadLastReport(): StoredReport | null {
  try {
    const raw = window.localStorage.getItem(KEY)
    if (raw === null) return null
    const parsed = JSON.parse(raw) as StoredReport
    // Validação mínima: um storage corrompido não pode derrubar o app no boot.
    if (typeof parsed?.report?.session_id !== 'string') return null
    return { report: parsed.report, open: parsed.open === true }
  } catch {
    return null
  }
}

export function saveLastReport(report: SessionReport, open: boolean): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify({ report, open }))
  } catch {
    // Sem armazenamento (Safari privado): o relatório vale pela sessão da página.
  }
}

export function markLastReportClosed(): void {
  try {
    const stored = loadLastReport()
    if (stored) saveLastReport(stored.report, false)
  } catch {
    // Idem.
  }
}
