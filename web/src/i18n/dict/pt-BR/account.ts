// Namespace `account` — a conta, a quota e o engajamento (T-151, SPEC-025 Onda 2 /
// SPEC-011/016/019): `auth/AccountSheet`, `auth/accountSummary`, `engagement/EngagementSheet`,
// `EngagementSection`, `FireChip`, `XpLine`, `AchievementGallery`, `AchievementToast` e
// `engagement/format`. Fonte da verdade do tipo (SPEC-025 §3.1): `Account` sai DESTE arquivo, e
// `dict/en/account.ts` é tipado por ele.
//
// **Aqui mora a maior concentração de plural do app** — dias de sequência, treinos guardados,
// sessões da meta, dias treinados no mês. Todos por `.one`/`.other` com `{n}`, resolvidos pelo
// `Intl.PluralRules` (plano §2.7): eram seis ternários `x === 1 ? 'dia' : 'dias'` espalhados por
// cinco arquivos, cada um uma regra de português embutida em componente.
//
// O que NÃO está aqui: nome e descrição de conquista (vêm do `GET /api/engagement`, T-145), o
// nome do plano e o `quota_message` (do painel, T-146) e as falhas de rede (namespace `errors`).
export const account = {
  // --- Ações e títulos que se repetem entre o formulário e os CTAs ---
  'action.create_account': 'Criar conta',
  'action.login': 'Entrar',
  'action.have_account': 'Já tenho conta',
  'action.create_one': 'Criar uma conta',
  'action.close': 'Fechar',
  'action.not_now': 'Agora não',

  // --- Folha da conta ---
  'sheet.aria_label': 'Sua conta',
  'field.name': 'Nome (opcional)',
  'field.email': 'E-mail',
  'field.password': 'Senha',
  'submit.busy': 'Só um instante…',
  'greeting': 'Olá, {name}',

  // Quantos treinos este aparelho já guardou — o argumento honesto para criar conta (T-121).
  // Separado em `suffix` + `tail` porque o número vive num `<span class="tabular">` próprio, e
  // é a fonte tabular que mantém os dígitos alinhados.
  'stored.suffix.one': 'treino guardado',
  'stored.suffix.other': 'treinos guardados',
  'stored.tail': 'neste aparelho — limpar o navegador leva embora. Com conta, ficam.',

  // --- Plano e quota (SPEC-016) ---
  'plan.remaining': 'restam {n}',
  'quota.exhausted_title': 'Você treinou muito hoje 🎉',
  'quota.last_title': 'Última sessão de hoje',
  'quota.last_anon': 'Resta 1 sessão grátis hoje. Com conta, são mais.',
  'quota.last_account': 'Resta 1 sessão hoje. Com assinatura, não acaba.',
  'quota.count': '{used} de {limit} sessões de hoje',
  'quota.renew': 'Renova às {time}',
  'quota.renew_tomorrow': 'Renova amanhã às {time}',
  'quota.upsell_soon': 'Assinatura em breve — e aí o limite deixa de existir.',

  // --- Datas curtas do histórico. `{time}` e `{date}` saem dos formatadores do locale ativo. ---
  'date.today': 'hoje {time}',
  'date.yesterday': 'ontem {time}',
  'date.other': '{date} {time}',

  // --- Totais e lista do histórico ---
  'totals.sessions': 'sessões',
  'totals.reps': 'repetições',
  'totals.best_rpm': 'melhor rep/min',
  'history.title': 'Histórico',
  'history.loading': 'Carregando…',
  'history.load_failed': 'Não consegui carregar seu histórico agora.',
  'history.local': 'Mostrando o que está guardado neste aparelho.',
  'history.stale': 'Não consegui atualizar agora — pode faltar algo recente.',
  'history.empty': 'Nenhuma sessão ainda. Toque no botão do meio para treinar 30 segundos.',
  'history.item_reps': '{n} reps',

  // --- Sair (a única ação destrutiva do app, T-079) ---
  'logout.ask': 'Sair da conta neste aparelho?',
  'logout.cancel': 'Cancelar',
  'logout.confirm': 'Sair da conta',

  // --- Chip do fogo (SPEC-019) ---
  // O rótulo acessível é montado por template para a ordem das partes poder mudar de língua.
  'fire.aria': '{days}, {goal}{where}',
  'fire.aria_pending': 'Sequência ainda carregando',
  'fire.days.one': '{n} dia seguido',
  'fire.days.other': '{n} dias seguidos',
  'fire.aria_goal': 'meta do dia {done} de {target}',
  'fire.aria_local': ', guardado só neste aparelho',
  'fire.ghost_title': 'Só neste aparelho',

  // --- XP (a decomposição vem do servidor; os rótulos são daqui) ---
  'xp.total': '+{n} XP',
  'xp.part': '+{n}',
  'xp.session': 'sessão',
  'xp.reps': 'reps',
  'xp.clean': 'limpa',

  // --- Seção de engajamento no Perfil e painel do fogo ---
  'eng.section_aria': 'Abrir o painel de constância',
  'eng.sheet_aria': 'Seu engajamento',
  'eng.title': 'Sua constância',
  'eng.streak': 'sequência',
  'eng.best': 'melhor',
  'eng.xp': 'XP',
  // Minúsculo porque o `.v2-label` do painel já aplica `text-transform: uppercase` e a seção do
  // Perfil (`.account__eng-label`) NÃO aplica — uma chave só serve às duas, e a que precisa de
  // caixa alta a recebe do CSS.
  'eng.level': 'nível',
  'eng.days.one': 'dia seguido',
  'eng.days.other': 'dias seguidos',
  'eng.best_label': 'Melhor sequência:',
  'eng.ghost_title': 'Seu fogo vive só neste aparelho',
  'eng.ghost_text':
    'Limpar o navegador leva sua sequência embora. Uma conta guarda o que você já treinou — e é de graça.',
  'eng.cal_day': '{n}',
  'eng.cal_day_active': '{n}, treinou',
  'eng.days_trained.one': 'dia treinado neste mês',
  'eng.days_trained.other': 'dias treinados neste mês',
  'eng.goal_today': 'Meta de hoje',
  'eng.protections': 'Proteções de sequência usadas neste mês:',
  'eng.protections_count': '{used} de {total}',
  'eng.goal_label': 'Meta diária',
  'eng.goal.casual': 'Casual',
  'eng.goal.regular': 'Regular',
  'eng.goal.intenso': 'Intenso',
  'eng.sessions.one': 'sessão',
  'eng.sessions.other': 'sessões',

  // --- Conquistas ---
  'ach.title': 'Conquistas',
  'ach.earned': 'conquistada',
  'ach.locked': 'bloqueada',
  'ach.toast_title': 'Nova conquista',
  'ach.toast_close_aria': 'Fechar aviso',
} as const

export type Account = Record<keyof typeof account, string>
