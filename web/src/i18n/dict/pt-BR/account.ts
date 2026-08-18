// Namespace `account` — vazio até a T-151 migrar as telas dele para cá (SPEC-025 Onda 2,
// BACKLOG.md). Nasce como arquivo próprio (não uma chave a mais num dicionário único) porque é
// isso que deixa as tasks da Onda 2 rodarem em paralelo sem colidir (PLANO-I18N.md §3.2).
export const account = {} as const

export type Account = Record<keyof typeof account, string>
