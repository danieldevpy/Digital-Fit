// O catálogo público do site, como o build o recebe (T-165, SPEC-026 §Escopo).
//
// ## De onde vem este dado
//
// De `manage.py export_site_catalog`, que o `scripts/prod.sh` roda ANTES do `compose build` e
// que escreve `exercicios.json` ao lado deste arquivo. O porquê de ser um snapshot exportado, e
// não o build lendo o Postgres, está no cabeçalho de `server/api/site_catalog.py`: o
// `web.Dockerfile` builda num `node:22-alpine` sem Django e sem banco, e no `prod.sh up` a
// ordem é build → migrate → start, então nem a API está de pé nessa hora.
//
// O que isso compra aqui dentro: o build é **hermético** (roda no CI e em clone novo), o
// conteúdo publicado fica **no diff** — dá para saber o que estava no ar em cada deploy — e
// banco fora do ar congela o conteúdo em vez de derrubar o build.
//
// O preço, dito de frente: exercício despublicado só some do site no **próximo build**. É a
// natureza do pré-render, não desta escolha — a página é um arquivo, e arquivo não consulta
// banco.
//
// ## Por que a versão é conferida
//
// O JSON é um artefato de outro processo, versionado à mão junto com o código. Um snapshot
// velho num build novo entregaria páginas pela metade — e página pela metade vai para o índice
// do Google exatamente como uma inteira. O build para; é o mesmo princípio do `exigirOrigem()`
// da T-160.
import bruto from './exercicios.json'
import { LOCALES, type Locale } from '../i18n/locale'

/** Espelha `VERSAO_DO_CATALOGO` em `server/api/site_catalog.py`. Mudou lá, muda aqui. */
const VERSAO_ESPERADA = 1

/** O que muda com o idioma. Espelha `_texto()` do exportador. */
export interface TextoDoExercicio {
  /** O endereço público NESTE idioma: `agachamento` em pt-BR, `squat` em en. */
  readonly url_slug: string
  readonly nome: string
  readonly grupo_muscular: string
  readonly dica: string
  readonly dica_de_cena: string
  readonly passos: readonly string[]
}

export interface ExercicioPublico {
  /**
   * O slug TÉCNICO — a chave do registro do servidor (`EXERCISES`), igual em todo idioma.
   *
   * É ele que identifica a rota (`exercicio/squat`) e é ele que o botão da página manda para o
   * app. O endereço público é traduzido; o contrato com a admissão não é, e misturar os dois
   * faria renomear uma URL quebrar a abertura da sessão.
   */
  readonly slug: string
  readonly category: string
  readonly demo_img: string
  readonly dot_color: string
  readonly met: number
  readonly por_idioma: Readonly<Record<Locale, TextoDoExercicio>>
}

function validar(): readonly ExercicioPublico[] {
  const documento = bruto as { versao?: number; exercicios?: unknown }

  if (documento.versao !== VERSAO_ESPERADA) {
    throw new Error(
      `exercicios.json: versao ${String(documento.versao)}, esperada ${VERSAO_ESPERADA}. Rode \`manage.py export_site_catalog\` e versione o resultado.`,
    )
  }

  const lista = (documento.exercicios ?? []) as ExercicioPublico[]

  for (const exercicio of lista) {
    for (const locale of LOCALES) {
      const texto = exercicio.por_idioma?.[locale]
      // Um idioma sem bloco viraria uma rota sem endereço — e o `hreflang` recíproco da T-160
      // prometeria ao Google uma página que ninguém escreve.
      if (!texto?.url_slug || !texto.nome) {
        throw new Error(
          `exercicios.json: o exercicio ${exercicio.slug} nao tem endereco e nome em ${locale}. Rode \`manage.py export_site_catalog\` contra um banco migrado.`,
        )
      }
    }
  }

  return lista
}

/** Os exercícios com página pública, na ordem do catálogo (`ordem, slug`). */
export const EXERCICIOS_PUBLICOS: readonly ExercicioPublico[] = validar()

export function exercicioPorSlug(slug: string): ExercicioPublico | undefined {
  return EXERCICIOS_PUBLICOS.find((exercicio) => exercicio.slug === slug)
}

/** O exercício cujo ENDEREÇO num idioma é este — o caminho de volta que o roteador usa. */
export function exercicioPorEndereco(
  endereco: string,
  locale: Locale,
): ExercicioPublico | undefined {
  return EXERCICIOS_PUBLICOS.find(
    (exercicio) => exercicio.por_idioma[locale].url_slug === endereco,
  )
}
