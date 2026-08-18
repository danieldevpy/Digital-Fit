// Os portões que varrem o CÓDIGO-FONTE (T-154, SPEC-025 critério de aceite 5).
//
// O critério 5 é o único da spec que vale para sempre: *"um commit que acrescenta uma frase em
// português e esquece o inglês não passa nos gates que já existem"*. Três portões já cuidavam
// dele — o `tsc` cobra paridade de chave entre os dicionários, o `no-literal-string` cobra
// string solta em JSX, e o `pytest` cobra os YAML do servidor. Faltavam dois flancos, os dois
// registrados como Descoberta no BACKLOG, e os dois são o que este arquivo fecha:
//
//   - **`[T-149]`** — `mode: 'jsx-only'` olha JSXText e JSXAttribute e mais nada, então uma
//     frase nascida num módulo `.ts` (a recusa da admissão, o conselho de cena, o rótulo do
//     CTA) passa batido;
//   - **`[T-153]`** — nenhum gate olhava header, então uma chamada nova à API nascia sem
//     `Accept-Language` e ninguém acusava.
//
// **Os dois se pagaram na primeira execução.** O primeiro encontrou
// `` `Falha ao iniciar o pipeline de pose: ${error.message}` `` vivo em `useEdgePipeline.ts`,
// que a T-149 deixara passar exatamente pelo buraco que ele descreve. O segundo encontrou
// `session/quota.ts`, a quinta chamada sem idioma, que a T-153 não tinha visto — e o
// `Plan.quota_message` que ela traz é traduzido por locale desde a T-146.
//
// ## Por que "literal acentuada" e não "qualquer literal"
//
// A alternativa era ligar `mode: 'all'` no ESLint para os módulos `.ts`, e ela foi recusada: a
// regra passaria a cobrar tradução de slug (`'jumping_jack'`), chave de armazenamento
// (`'digitalfit.locale'`), nome de header (`'Accept-Language'`) e tipo de evento
// (`'pose.frame'`) — centenas de exceções a escrever, e um portão cheio de exceção deixa de ser
// lido. A heurística daqui é estreita de propósito e cobre **a direção do erro que importa**:
// quem escreve este projeto escreve em português, então é a frase em português que aparece por
// engano. Uma frase nova em inglês esquecida no código é possível e não seria pega — mas ela
// não é o modo de falha real desta equipe, e um portão que mira o modo de falha real vale mais
// que um portão exaustivo que ninguém mantém.
import { describe, expect, it } from 'vitest'

import { localeHeaders } from './http'
import { useI18nStore } from './store'

/**
 * O código-fonte como texto, pelo `import.meta.glob` do Vite (`?raw`) — e não por `node:fs`.
 *
 * Duas razões, e a segunda é a que decide: o `tsconfig.app.json` deste projeto não carrega
 * `@types/node` (é um app de navegador, e acrescentar a tipagem inteira do Node para ler
 * arquivo num teste seria pagar caro por pouco); e o `glob` já respeita a raiz do projeto, sem
 * a armadilha do caminho com espaço ("Digital Fit" vira `Digital%20Fit` num `URL.pathname`).
 *
 * Os padrões de exclusão espelham os `ignores` do bloco global do `eslint.config.js` de
 * propósito: dois portões com a mesma fronteira são um portão só, visto de dois ângulos.
 * `dict/**` porque o dicionário É o texto; `*.test.ts` porque teste fala de texto o tempo todo;
 * `dev/**` porque é ferramenta de operação, a mesma exclusão que a SPEC-025 §Escopo dá ao painel.
 */
const FONTES = import.meta.glob('../**/*.{ts,tsx}', {
  query: '?raw',
  eager: true,
  import: 'default',
}) as Record<string, string>

const FORA = /\/dict\/|\/dev\/|\.test\.tsx?$/

const ACENTO = /[áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]/

/**
 * Contextos em que uma frase em português é legítima — e a lista tem exatamente três entradas
 * porque as três significam a mesma coisa: **ninguém que use o produto vai ler isto**.
 *
 * - `console.*` → log de diagnóstico (a casa usa o prefixo `[gateway]`, `[pose]`, `[sessão]`);
 * - `throw new` → violação de invariante, lida por quem programa (`'#root não encontrado'`);
 * - `super(` → mensagem de uma subclasse de `Error`, mesma categoria do anterior.
 *
 * Note que "aparece na tela" e "é `Error`" não são a mesma coisa: a mensagem crua de uma exceção
 * PODE chegar à tela como detalhe interpolado (`{reason}`), e é por isso que a moldura ao redor
 * dela — essa sim — tem de estar no dicionário. Foi essa distinção que o achado do
 * `useEdgePipeline` deixou clara.
 */
const CONTEXTO_DE_DIAGNOSTICO = /console\.|throw new|super\(/

/** Tira comentário de linha e de bloco — este projeto comenta em português, e muito. */
function semComentarios(texto: string): string {
  return texto
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/\s\/\/[^\n'"`]*$/gm, '')
}

interface Achado {
  arquivo: string
  texto: string
}

function literaisEmPortugues(): Achado[] {
  const achados: Achado[] = []

  for (const [caminho, cru] of Object.entries(FONTES)) {
    if (FORA.test(caminho)) continue
    const fonte = semComentarios(cru)
    const literais = /'([^'\\\n]*)'|"([^"\\\n]*)"|`([^`\\]*)`/g

    for (const casamento of fonte.matchAll(literais)) {
      const valor = casamento[1] ?? casamento[2] ?? casamento[3] ?? ''
      if (!ACENTO.test(valor)) continue

      // O contexto imediato antes do literal decide se ele é diagnóstico. 120 caracteres
      // cobrem `console.warn(` e `throw new DeadlineError(` com folga, e não atravessam a
      // instrução anterior a ponto de dar falso negativo.
      const inicio = Math.max(0, (casamento.index ?? 0) - 120)
      const antes = fonte.slice(inicio, casamento.index)
      if (CONTEXTO_DE_DIAGNOSTICO.test(antes)) continue

      achados.push({ arquivo: caminho.replace('../', 'src/'), texto: valor })
    }
  }

  return achados
}

describe('o portão do texto novo fora de JSX (T-154, SPEC-025 critério 5)', () => {
  it('nenhuma frase em português mora no código — o lugar dela é o dicionário', () => {
    // A mensagem de falha é a lista inteira, e não uma contagem, de propósito: quem quebrar
    // este teste precisa ver QUAL frase escreveu, não descobrir que "sobrou uma".
    expect(literaisEmPortugues()).toEqual([])
  })

  it('a varredura encontra o que tem de encontrar — o portão não é decorativo', () => {
    // Um portão que só sabe dizer "está tudo bem" nunca provou que sabe dizer o contrário.
    // Este caso prova as duas metades da heurística sobre um texto de mentira: a frase de
    // produto é pega, e a mesma frase dentro de um `console` é ignorada.
    const fonte = semComentarios(`
      const aviso = 'Não foi possível salvar'
      console.warn('Não foi possível salvar')
    `)
    const literais = [...fonte.matchAll(/'([^'\\\n]*)'/g)]
    const pegos = literais.filter((m) => {
      const antes = fonte.slice(Math.max(0, (m.index ?? 0) - 120), m.index)
      return ACENTO.test(m[1] ?? '') && !CONTEXTO_DE_DIAGNOSTICO.test(antes)
    })

    expect(pegos).toHaveLength(1)
  })
})

describe('localeHeaders', () => {
  it('manda o locale ATIVO, não o do navegador', () => {
    useI18nStore.getState().setLocale('pt-BR')
    expect(localeHeaders()).toEqual({ 'Accept-Language': 'pt-BR' })

    useI18nStore.getState().setLocale('en')
    expect(localeHeaders()).toEqual({ 'Accept-Language': 'en' })

    useI18nStore.getState().setLocale('pt-BR')
  })
})

describe('o portão do cabeçalho de idioma (T-154, Descoberta `[T-153]`)', () => {
  it('todo arquivo que fala com a nossa API também importa o cabeçalho de idioma', () => {
    const semIdioma = Object.entries(FONTES)
      .filter(([caminho, cru]) => {
        if (/\.test\.tsx?$/.test(caminho)) return false
        // **Sem os comentários**, e isto não é detalhe: a primeira versão deste portão lia o
        // arquivo cru e passou a considerar coberto um arquivo cujo `localeHeaders` só existia
        // dentro de um comentário explicando o header. O teste de mutação é que mostrou —
        // portão que lê comentário acredita em promessa, não em código.
        const fonte = semComentarios(cru)
        // Quem apenas REEXPORTA (`export { apiBaseUrl }`) ou declara a função não está chamando
        // a API — o que interessa é a chamada, `apiBaseUrl()`.
        return /apiBaseUrl\(\)/.test(fonte) && !/localeHeaders/.test(fonte)
      })
      .map(([caminho]) => caminho.replace('../', 'src/'))

    // A lista inteira na falha, e não uma contagem: quem quebrar isto precisa ver QUAL chamada
    // esqueceu o idioma.
    expect(semIdioma).toEqual([])
  })
})
