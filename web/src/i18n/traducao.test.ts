// O portão da tradução de página (T-162, SPEC-026 §Escopo — "a tradução do navegador não pode
// derrubar o app").
//
// ## O que este portão protege
//
// O app é oferecido em duas línguas CURADAS (`pt-BR`, `en`). Quem fala uma terceira usa `en` e
// pode pedir a tradução da página ao navegador — é a camada "Traduzir" da SPEC-026, e ela é de
// graça em ~130 línguas justamente porque o produto não a implementa. O preço de aceitá-la são
// duas consequências que ninguém vê até acontecer:
//
//   1. **Produto.** Número não se traduz. `12` repetições, `28 rpm`, `00:07`, `edge` — passar
//      isso por tradução de máquina é ruído com risco, e `edge`/`cloud` ainda por cima é
//      vocabulário de contrato (SPEC-025 §Entidade), que o projeto mantém em inglês no fio.
//   2. **Técnica.** O Google Translate **embrulha cada nó de texto num `<font>`**. O React
//      continua tratando aquele nó como filho direto do elemento que o criou, e a partir daí
//      qualquer redesenho pisa numa árvore que não é mais a que ele conhece — a classe de falha
//      que aparece nos relatos como `NotFoundError: Failed to execute 'removeChild' on 'Node'`.
//      Quais nós exatamente quebram depende da forma do DOM; por isso a defesa aqui **não** é
//      auditar nó por nó, é tirar do alcance da tradução as regiões que redesenham durante a
//      sessão.
//
// ## Por que um portão de código-fonte, e não um teste de comportamento
//
// Quem honra `translate="no"` é o **tradutor do navegador**, não o React e não o DOM. Nenhum
// ambiente de teste deste repositório (`environment: 'node'`, sem jsdom) pode provar que o
// atributo funciona — nem um com jsdom poderia, porque jsdom não traduz nada. Um teste que
// renderizasse a árvore e embrulhasse os nós à mão provaria que o **bug** existe, não que a
// **correção** existe: seria uma demonstração cara, com uma dependência de desenvolvimento
// pesada a reboque.
//
// O que dá para garantir daqui, e para sempre, é o que de fato regride: **a marcação sair sem
// ninguém notar.** É o mesmo raciocínio do portão vizinho em `portoes.test.ts` — mirar o modo
// de falha real desta equipe (esquecer) em vez de perseguir uma prova exaustiva que ninguém
// mantém. A prova de que o atributo surte efeito é o critério 4 da SPEC-026, e ele é de
// aparelho real, declarado como tal.
import { describe, expect, it } from 'vitest'

const FONTES = import.meta.glob('../**/*.{ts,tsx}', {
  query: '?raw',
  eager: true,
  import: 'default',
}) as Record<string, string>

/**
 * As regiões voláteis, por classe de CSS — a unidade certa porque é ela que o componente usa
 * para dizer "isto é o valor" e "isto é o rótulo".
 *
 * A lista é curta de propósito e a regra para crescer está escrita: entra aqui **o que o React
 * reescreve enquanto a pessoa treina ou logo depois** (contador, ângulo, relógio, dica do
 * treinador, números do relatório). NÃO entra rótulo — "Repetições"/"Reps", "restantes",
 * "Detalhes" são exatamente o que alguém que ligou a tradução quer ler na própria língua, e só
 * mudam quando o locale muda.
 */
const VOLATEIS: ReadonlyArray<{ arquivo: string; classe: string }> = [
  { arquivo: 'src/hud/StatsBar.tsx', classe: 'stats__value' },
  { arquivo: 'src/hud/TimerRing.tsx', classe: 'ring__time' },
  { arquivo: 'src/hud/CoachTip.tsx', classe: 'tip__body' },
  { arquivo: 'src/report/ReportSheet.tsx', classe: 'report__reps' },
  { arquivo: 'src/report/ReportSheet.tsx', classe: 'report__stat-value' },
  { arquivo: 'src/report/ReportSheet.tsx', classe: 'report__count' },
]

/**
 * As tags de abertura de um fonte JSX.
 *
 * Heurística assumida e suas fronteiras: o `[^>]*` para no primeiro `>`, então uma tag com `>`
 * dentro de um atributo (`style={{ a: b > c }}`) sairia cortada. Nenhuma das tags visadas tem
 * isso, e o custo de errar é um falso POSITIVO no portão — ele acusaria falta de marcação onde
 * ela existe, que é a direção segura de errar para um gate.
 */
function tagsDeAbertura(fonte: string): string[] {
  return [...fonte.matchAll(/<[a-zA-Z][^>]*>/g)].map((m) => m[0])
}

/** As tags que declaram `classe` e NÃO carregam `translate="no"`. */
export function tagsDesprotegidas(fonte: string, classe: string): string[] {
  return tagsDeAbertura(fonte).filter(
    (tag) => tag.includes(`${classe}"`) || tag.includes(`${classe} `)
      ? !tag.includes('translate="no"')
      : false,
  )
}

function fonteDe(arquivo: string): string {
  const chave = arquivo.replace('src/', '../')
  const cru = FONTES[chave]
  if (cru === undefined) throw new Error(`fonte não encontrada no glob: ${arquivo}`)
  return cru
}

describe('o portão da tradução de página (T-162, SPEC-026)', () => {
  it.each(VOLATEIS)('$arquivo · .$classe carrega translate="no"', ({ arquivo, classe }) => {
    // A mensagem de falha mostra a TAG inteira, e não uma contagem: quem quebrar este teste
    // precisa ver qual elemento nasceu sem a marcação, não descobrir que "faltou uma".
    expect(tagsDesprotegidas(fonteDe(arquivo), classe)).toEqual([])
  })

  it('a varredura sabe dizer "não" — o portão não é decorativo', () => {
    // Um portão que só sabe dizer "está tudo bem" nunca provou que sabe dizer o contrário.
    const desprotegida = '<p className="stats__value tabular">{repCount}</p>'
    const protegida = '<p className="stats__value tabular" translate="no">{repCount}</p>'
    const alheia = '<p className="stats__label">{t(\'session:label.reps\')}</p>'

    expect(tagsDesprotegidas(desprotegida, 'stats__value')).toHaveLength(1)
    expect(tagsDesprotegidas(protegida, 'stats__value')).toEqual([])
    expect(tagsDesprotegidas(alheia, 'stats__value')).toEqual([])
  })

  it('o rótulo continua traduzível — a marcação é cirúrgica, não uma cortina', () => {
    // O contrário do teste acima, e é ele que impede a "correção" preguiçosa de amanhã: pôr
    // `translate="no"` na barra inteira faria este teste passar e a camada "Traduzir" da
    // SPEC-026 morrer em silêncio, porque "Repetições" pararia de virar "Reps"/"Répétitions".
    const fonte = fonteDe('src/hud/StatsBar.tsx')
    const rotulos = tagsDeAbertura(fonte).filter((tag) => tag.includes('stats__label'))

    expect(rotulos.length).toBeGreaterThan(0)
    expect(rotulos.filter((tag) => tag.includes('translate="no"'))).toEqual([])
    // E a barra que envolve os dois também não pode carregar o atributo.
    const container = tagsDeAbertura(fonte).filter((tag) => tag.includes('"stats"'))
    expect(container.filter((tag) => tag.includes('translate="no"'))).toEqual([])
  })
})
