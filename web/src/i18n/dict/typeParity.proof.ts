// PROVA do critério mais importante da T-142 (SPEC-025 §3.1, PLANO-I18N.md §3.1): o tipo do
// dicionário `en` sai do `pt-BR`, e chave faltando, sobrando ou renomeada de um lado é erro de
// `tsc` — não bug descoberto em produção com o navegador em inglês, não disciplina de quem
// lembra de conferir.
//
// Este arquivo não é importado por ninguém e não roda nada em runtime — ele É o teste. As duas
// declarações abaixo são deliberadamente inválidas contra `Shell` (a mesma técnica de
// `@ts-expect-error` usada para testar tipos sem precisar de um framework de type-testing à
// parte): se algum dia a tipagem do dicionário afrouxar a ponto de aceitar uma delas, o PRÓPRIO
// `@ts-expect-error` vira erro ("Unused '@ts-expect-error' directive" — TS2578), e
// `npm run typecheck` cai de qualquer jeito. É impossível "consertar" isto silenciosamente.
import type { Shell } from './pt-BR/shell'

/** Função-armadilha: só existe para forçar a checagem de propriedade em falta/sobra no literal. */
function aceitaShell(valor: Shell): Shell {
  return valor
}

// Falta 'tab.perfil'. Chave faltando no `en` é exatamente o que o portão do §4 do plano tem de
// pegar — sem isso, uma tela nova nasceria com metade do rótulo em português por engano.
// @ts-expect-error — falta a chave 'tab.perfil': isto TEM de ser erro de tsc.
aceitaShell({
  'nav.aria_label': 'x',
  'tab.inicio': 'x',
  'tab.progresso': 'x',
  'tab.analytics': 'x',
})

// 'tab.extra' não existe em `Shell`. Chave sobrando (ou renomeada — o mesmo efeito de "falta a
// antiga E sobra a nova" ao mesmo tempo) também tem de ser pega na mesma checagem. O erro de
// "excess property" do `tsc` aponta para a PROPRIEDADE em si, não para o literal inteiro — por
// isso o `@ts-expect-error` fica colado em cima de 'tab.extra', não em cima de `aceitaShell(`.
aceitaShell({
  'nav.aria_label': 'x',
  'tab.inicio': 'x',
  'tab.progresso': 'x',
  'tab.analytics': 'x',
  'tab.perfil': 'x',
  // @ts-expect-error — 'tab.extra' não existe em Shell: chave sobrando também TEM de ser erro.
  'tab.extra': 'x',
})
