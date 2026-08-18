// Namespace `shell` — casca do app: bottom nav (SPEC-014 §Mapa de navegação). Fonte da verdade
// do dicionário (SPEC-025 §3.1): o tipo `Shell` sai DESTE arquivo, e `dict/en/shell.ts` é
// tipado por ele — chave faltando, sobrando ou renomeada de um lado só é erro de `tsc`.
//
// As chaves reaproveitam o vocabulário que já existe em `shell/TabBar.tsx` (`TabId`:
// `inicio`/`progresso`/`analytics`/`perfil`) — é a mesma separação código×frase que a SPEC-025
// já usa em outros lugares (`Category` guarda `forca`, não `"Força"`): o slug é o contrato, o
// texto é só o valor deste dicionário.
export const shell = {
  'nav.aria_label': 'Navegação principal',
  'tab.inicio': 'Início',
  'tab.progresso': 'Progresso',
  'tab.analytics': 'Analytics',
  'tab.perfil': 'Perfil',

  // Seletor de idioma (T-153). O NOME de cada idioma fica na própria língua nos dois
  // dicionários — "Português" e "English" não se traduzem, é convenção de seletor: quem procura
  // este controle normalmente não lê a língua em que a tela está, e "Portuguese" não ajudaria
  // quem abriu o app em inglês por engano. Chave igual, valor igual, de propósito.
  'lang.aria_label': 'Idioma',
  'lang.pt': 'Português',
  'lang.en': 'English',
} as const

// `Record<keyof typeof shell, string>`, não `typeof shell`: o contrato entre `pt-BR` e `en` é
// PARIDADE DE CHAVES, não igualdade de valor — `typeof shell` carregaria os literais
// ('Início', 'Perfil', ...) e `dict/en/shell.ts` nunca compilaria, porque 'Home' não é
// atribuível a 'Início'. `Record<keyof typeof shell, string>` larga o valor literal e mantém
// exatamente as chaves — chave faltando é erro de propriedade ausente, chave sobrando é erro de
// "excess property" (a checagem de objeto literal do `tsc`), os dois com objeto literal como em
// `dict/en/shell.ts` (ver `typeParity.proof.ts`).
export type Shell = Record<keyof typeof shell, string>
