// A linha "+XP" do relatório (SPEC-019 §Superfícies / T-088).
//
// É **onde o bônus de forma ensina que forma vale ponto**: ver "limpa +10" logo abaixo de um
// treino sem correção é o que liga, na cabeça de quem treinou, execução a recompensa. Um total
// sozinho não ensinaria nada — por isso a decomposição, e não só o número.
//
// ## Os números vêm do servidor, e isso não é preguiça
//
// A fórmula de XP é **versionada** (`XP_FORMULA_V` em `api/engagement.py`), o que é outra
// maneira de dizer que ela vai mudar. Um espelho em TypeScript seria uma segunda implementação
// da mesma conta, e no dia da mudança um dos dois lados ficaria para trás — em silêncio, porque
// nenhum teste pode comparar as duas linguagens. É o `[A/T-051]` de novo, com pontos no lugar
// de exercícios. Então o `GET /api/sessions/{id}/report` traz a decomposição pronta.
import type { XpBreakdown } from '../report/sessionReport'
import { parcelasDeXp } from './format'

/**
 * `undefined` quando não há conta: XP não existe para o visitante (§Planos), e o servidor
 * simplesmente não manda a chave. Nada é desenhado — nem um `--`, porque não é um número que
 * está faltando, é uma mecânica que não se aplica a quem está olhando.
 */
export function XpLine({ xp }: { xp?: XpBreakdown }) {
  if (!xp || xp.total <= 0) return null

  return (
    <p className="report__xp">
      <span className="report__xp-total num tabular">+{xp.total} XP</span>
      <span className="report__xp-parts">
        {parcelasDeXp(xp).map((parcela) => (
          <span key={parcela.rotulo} className="report__xp-part">
            {parcela.rotulo} <span className="num tabular">+{parcela.valor}</span>
          </span>
        ))}
      </span>
    </p>
  )
}
