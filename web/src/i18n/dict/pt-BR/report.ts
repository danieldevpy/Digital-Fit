// Namespace `report` — o relatório do fim do treino (T-150, SPEC-025 Onda 2 / SPEC-010):
// `report/ReportSheet`, `report/reportSummary` (o porquê do fim e o "o que melhorar") e as
// falhas de rede de `report/sessionReport`. Fonte da verdade do tipo (SPEC-025 §3.1): `Report`
// sai DESTE arquivo, e `dict/en/report.ts` é tipado por ele.
//
// O texto de cada item de "o que melhorar" NÃO está aqui: ele vem do `code` pelo catálogo do
// treinador (`session/coachCard`, T-144/T-152). Aqui mora só a moldura do relatório.
export const report = {
  'sheet.aria_label': 'Relatório da sessão',

  // Enquanto o worker consolida (o relatório não existe no instante em que a sessão acaba).
  'loading.title': 'Consolidando o treino…',
  'loading.hint': 'Repetições contadas. Buscando o detalhamento…',

  // O relatório não veio, mas a contagem veio — e é ela que a pessoa quer saber.
  'error.title': 'Treino concluído',
  'error.hint':
    'Não consegui carregar o detalhamento desta sessão. A contagem acima é a do servidor e está correta.',

  'reps_label': 'repetições',
  'stat.rpm': 'rep/min',
  'stat.valid_time': 'tempo válido',
  // Modo contado (SPEC-023 §6, T-139): o MESMO `duration_ms` muda de significado. Com janela
  // fixa ele é "quanto tempo valeu"; com meta fixa ele é quanto se levou para chegar lá — e é
  // esse o número que mede evolução, não a contagem.
  'stat.time_to_target': 'tempo até a meta',
  'stat.mode': 'modo',

  'section.pace': 'Ritmo ao longo da série',
  'section.improve': 'O que melhorar',
  'clean': 'Nenhum aviso nesta série. Execução limpa.',
  // Quantas vezes o mesmo aviso apareceu. O `×` é multiplicação lida como "vezes" — junto do
  // número, e não uma palavra, porque a linha inteira tem a largura de um celular.
  'count_suffix': '{n}×',
  // Eixo do gráfico de ritmo: início de cada janela, em segundos.
  'window_label': '{s}s',
  'close': 'Fechar',

  // Por que a sessão terminou (`SessionEndReason` é o contrato; estas são as frases).
  'reason.completed': 'Série completa',
  'reason.timeout': 'Sessão encerrada pelo tempo limite',
  'reason.aborted': 'Você encerrou antes do fim',
  'reason.no_data': 'Encerrada: paramos de te ver na câmera',
  'reason.target_reached': 'Meta atingida',
  'reason.unknown': 'Sessão encerrada',

  'set_of': 'série {n} de {total}',

  // Falha ao buscar o relatório. A de REDE saiu daqui na T-151, para o namespace `errors` —
  // era a mesma frase em três arquivos. Esta fica: é específica do relatório.
  'fetch.failed': 'Falha ao buscar o relatório (HTTP {status}).',
} as const

export type Report = Record<keyof typeof report, string>
