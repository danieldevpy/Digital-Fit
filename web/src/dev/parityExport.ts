// Resultado do navegador no formato que a bancada lê (T-040 / SPEC-012).
//
// O `evalctl parity` já compara duas pernas — edge e cloud —, mas as duas são MediaPipe do
// Python. A terceira perna, o navegador, não tinha como entrar na comparação porque roda em
// outro processo, em outra linguagem, em outra máquina possivelmente. O caminho mais simples
// que existe entre os dois mundos é um arquivo: o navegador exporta o que contou, e o
// `evalctl parity --browser <arquivo>` põe o número ao lado dos outros dois.
//
// O formato é o `VideoResult.to_dict()` de `eval/pipeline.py`, e o motivo de ser esse é o
// mesmo do contrato de eventos: já existe, já é lido, e inventar um segundo só criaria
// tradução na fronteira.
import type { SessionReport } from '../report/sessionReport'

/** Espelho de `VideoResult.to_dict()`. Chaves em snake_case porque é o formato que trafega. */
export interface BrowserParityResult {
  name: string
  exercise: string
  reps: number
  expected_reps: number | null
  frames: number
  duration_s: number
  cadence_rpm: number
  rep_durations_ms: number[]
  quality_signals: Record<string, number>
  /** Marca a perna. Sem isto, um arquivo do navegador seria indistinguível de um do harness. */
  source: 'browser-edge'
  /** O que rodou de fato: `gpu` ou `cpu` muda o resultado e precisa aparecer no relatório. */
  delegate: string | null
  user_agent: string
}

export interface ExportInput {
  report: SessionReport
  /** Nome do arquivo de vídeo, sem extensão. */
  videoName: string
  expectedReps?: number | null
  /** Frames que o cliente chegou a mandar (último `seq` + 1). */
  frames?: number
  delegate?: string | null
  userAgent?: string
}

export function buildParityResult({
  report,
  videoName,
  expectedReps = null,
  frames = 0,
  delegate = null,
  userAgent = '',
}: ExportInput): BrowserParityResult {
  return {
    name: videoName,
    exercise: report.exercise,
    reps: report.rep_count,
    expected_reps: expectedReps,
    frames,
    // A duração do relatório é a EFETIVA (da calibração ao fim), não a do arquivo — é a
    // mesma janela que a bancada mede, então os dois números são comparáveis.
    duration_s: Number((report.duration_ms / 1000).toFixed(2)),
    cadence_rpm: report.cadence_rpm,
    rep_durations_ms: report.rep_durations_ms,
    quality_signals: report.scene_warning_counts,
    source: 'browser-edge',
    delegate,
    user_agent: userAgent,
  }
}

/** Nome do arquivo baixado: o do vídeo, para casar com o relatório do harness. */
export function parityFileName(videoName: string): string {
  const limpo = videoName.replace(/[^\w.-]+/g, '_') || 'sessao'
  return `${limpo}.browser.json`
}

export function downloadParityResult(resultado: BrowserParityResult): void {
  const blob = new Blob([JSON.stringify(resultado, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = parityFileName(resultado.name)
  link.click()
  URL.revokeObjectURL(url)
}
