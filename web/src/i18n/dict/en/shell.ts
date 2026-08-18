// Namespace `shell` — tipado pelo `pt-BR` (SPEC-025 §3.1): o tipo `Shell` vem de
// `dict/pt-BR/shell.ts`, então uma chave faltando, sobrando ou renomeada aqui é erro de `tsc`,
// não bug descoberto em produção com o navegador em inglês.
import type { Shell } from '../pt-BR/shell'

export const shell: Shell = {
  'nav.aria_label': 'Main navigation',
  'tab.inicio': 'Home',
  'tab.progresso': 'Progress',
  'tab.analytics': 'Analytics',
  'tab.perfil': 'Profile',

  // "Português"/"English" NÃO mudam entre os dois dicionários — ver o comentário no `pt-BR`.
  'lang.aria_label': 'Language',
  'lang.pt': 'Português',
  'lang.en': 'English',
}
