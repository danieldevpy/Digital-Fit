// Namespace `progress` — as duas telas de leitura do histórico (T-150, SPEC-025 Onda 2 /
// SPEC-024): `screens/ProgressScreen` (a evolução ao longo do tempo) e `screens/AnalyticsScreen`
// (a leitura fina entre sessões). Fonte da verdade do tipo (SPEC-025 §3.1): `Progress` sai
// DESTE arquivo, e `dict/en/progress.ts` é tipado por ele.
//
// **Plural por `Intl.PluralRules`, não por `+ 's'`.** Cada contagem tem `.one`/`.other` e o
// número entra como `{n}` mesmo quando não aparece no texto — é ele que escolhe o balde
// (`resolveFromTable`, T-142). Era `sessions.length === 1 ? 'treino' : 'treinos'` espalhado pela
// tela, que funciona em português e em inglês e quebra na terceira língua.
//
// O que NÃO está aqui: nome do exercício (catálogo), o texto de cada correção (resolvido pelo
// `code` no catálogo do treinador) e a DATA — `historyDate` mora em `auth/accountSummary.ts` e é
// a T-151 quem a tira do `toLocaleTimeString('pt-BR')`.
export const progress = {
  // --- Cabeçalho ---
  'kicker': 'Progresso',
  'title': 'Seu treino ao longo do tempo',

  // --- Tela vazia ---
  'empty.title': 'Nenhum treino registrado ainda',
  'empty.text': 'Termine uma sessão e o resultado aparece aqui — mesmo sem conta.',
  'empty.cta': 'Treinar agora',

  // --- Métricas do topo e do card do último treino ---
  'metric.workouts.one': 'treino',
  'metric.workouts.other': 'treinos',
  'metric.reps': 'repetições',
  'metric.days.one': 'dia',
  'metric.days.other': 'dias',
  'metric.rpm': 'rep/min',
  'metric.duration': 'duração',
  'unit.reps': 'reps',

  // --- Seções ---
  'section.last': 'Último treino',
  'section.weeks': 'Últimas 4 semanas',
  'section.by_exercise': 'Por exercício',
  // `title` de cada quadradinho do mês. `{date}` vem do formatador de data no locale ativo.
  'day_title': 'Treinou em {date}',

  // --- Avisos de origem do histórico (SPEC-024 §3) ---
  // Quebrada em três porque "neste aparelho" é `<strong>` no meio da frase — mesma solução do
  // `view.why.*` (T-148) e do `getready.hint_*` (T-149).
  'note.local_lead': 'Este é o histórico guardado',
  'note.local_strong': 'neste aparelho',
  'note.local_tail': '— limpar o navegador leva embora. Com uma conta, ele fica.',
  'note.stale': 'Não consegui atualizar agora — pode faltar algo recente.',

  // --- Analytics ---
  'analytics.kicker': 'Analytics',
  'analytics.title': 'Análise do treino',
  'analytics.open_last': 'Abrir a análise do último treino',
  'analytics.open_last_sub':
    'Cadência, repetições e o que melhorar — o relatório completo da sessão.',
  'analytics.empty_note':
    'A análise entre sessões nasce do seu histórico. Faça um treino e ela começa a existir — a análise de uma sessão só já é o relatório do fim do treino.',
  'analytics.empty_cta': 'Fazer um treino para ter o que analisar',

  'analytics.section.pace': 'Ritmo por exercício',
  // O que falta para a série virar linha (SPEC-024 §5: abaixo de 2 sessões, nada de tendência).
  'analytics.needs_more': 'Mais um treino de {exercise} e o ritmo vira linha.',
  'analytics.range.one': 'de {min} a {max} rep/min em {n} treino',
  'analytics.range.other': 'de {min} a {max} rep/min em {n} treinos',

  'analytics.section.consistency': 'Constância do ritmo',
  'analytics.consistency_note': 'menor é mais regular',
  'analytics.consistency_empty':
    'Precisa de sessões com pelo menos duas repetições para medir variação de ritmo.',

  'analytics.section.most': 'O que mais aparece',
  'analytics.empty.corrections': 'Nenhuma correção registrada — execução limpa nas sessões guardadas.',
  'analytics.section.framing': 'Enquadramento',
  'analytics.empty.scene': 'Nenhum aviso de cena. A câmera te viu bem em todas as sessões.',

  // O rumo do aviso entre sessões. O slug (`caindo`/`subindo`/`estavel`) é contrato de
  // `history/aggregates.ts`; a frase inteira mora aqui para a ordem das palavras poder mudar de
  // língua — `{rumo} entre as sessões` montado no JSX não sobreviveria a isso.
  'analytics.trend.caindo': 'diminuindo entre as sessões',
  'analytics.trend.subindo': 'aumentando entre as sessões',
  'analytics.trend.estavel': 'estável entre as sessões',
} as const

export type Progress = Record<keyof typeof progress, string>
