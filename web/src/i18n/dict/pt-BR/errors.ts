// Namespace `errors` — as falhas que a pessoa lê na tela, quando a causa é a REDE ou uma recusa
// do servidor sem texto próprio (T-151, SPEC-025 Onda 2). Fonte da verdade do tipo (SPEC-025
// §3.1): `Errors` sai DESTE arquivo, e `dict/en/errors.ts` é tipado por ele.
//
// **Por que um namespace só para isto.** "API fora do ar" nascia em três lugares — a admissão
// (T-149), a busca do relatório (T-150) e o `auth/api` (esta task) — e cada raia da Onda 2
// traduziu a sua no próprio namespace, porque namespace é a unidade de paralelismo e escrever
// no arquivo alheio teria colidido. Esta é a task que toca as três, e por isso é a que pode
// juntá-las (Descoberta `[T-150]` do BACKLOG). Uma frase, uma casa.
//
// O que NÃO entra aqui: recusa com texto PRÓPRIO do servidor (`detail` já traduzido pela T-145,
// `Plan.quota_message` do painel) e falha específica de uma tela (o "não consegui carregar seu
// histórico" mora no `account`, que é onde ele aparece). Aqui fica só o que é da rede.
export const errors = {
  'api_down': 'API fora do ar',
  'api_down_detail': 'API fora do ar: {reason}',
  'login_failed': 'Não foi possível entrar.',
  'save_failed': 'Não foi possível salvar.',
  'history_failed': 'Não foi possível carregar o histórico.',
  'goal_save_failed': 'Não foi possível salvar a meta.',
} as const

export type Errors = Record<keyof typeof errors, string>
