// A seção de engajamento do Perfil (SPEC-019 §Superfícies / T-088).
//
// Fogo, melhor sequência, XP e nível — os quatro números que a spec nomeia. A galeria de
// conquistas, que a mesma linha da spec pede, é a **T-089**: o catálogo de predicados não
// existe, e desenhar uma vitrine vazia diria "você não conquistou nada" sobre uma mecânica que
// ainda não foi ligada.
//
// Componente à parte, e não JSX solto dentro da AccountSheet, porque a fonte do número é outra:
// o Perfil lê histórico, isto lê `GET /api/engagement`.
import { useEngagementStore } from './store'
import { useEngagement } from './useEngagement'

export function EngagementSection() {
  const abrirPainel = useEngagementStore((state) => state.openSheet)
  const view = useEngagement()

  return (
    <button
      type="button"
      className="account__eng"
      onClick={() => abrirPainel(true)}
      aria-label="Abrir o painel de constância"
    >
      <span className="account__eng-item">
        <span className="account__eng-value num tabular">
          <span aria-hidden="true">🔥</span> {view.pending ? '--' : view.streak}
        </span>
        <span className="account__eng-label">sequência</span>
      </span>
      <span className="account__eng-item">
        <span className="account__eng-value num tabular">
          {view.pending ? '--' : view.bestStreak}
        </span>
        <span className="account__eng-label">melhor</span>
      </span>
      {/* XP e nível só existem com conta (§Planos). Esta seção já só é montada no ramo logado
          da AccountSheet, mas o `null` continua sendo tratado: `pending` passa por aqui, e
          `0` no lugar de `--` seria afirmar que a pessoa não pontuou. */}
      <span className="account__eng-item">
        <span className="account__eng-value num tabular">{view.xp ?? '--'}</span>
        <span className="account__eng-label">XP</span>
      </span>
      <span className="account__eng-item">
        <span className="account__eng-value num tabular">{view.level ?? '--'}</span>
        <span className="account__eng-label">nível</span>
      </span>
    </button>
  )
}
