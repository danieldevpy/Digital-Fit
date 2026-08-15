// Chip do fogo + anel da meta, na Início (SPEC-019 §Superfícies / T-088).
//
// Mora sobre o cabeçalho da pré-configuração porque é lá que a pessoa chega ao abrir o app —
// é a tela "Início" da tab bar desde a T-067. Toque abre o painel.
import { fireAriaLabel, fireLabel } from './format'
import { useEngagement } from './useEngagement'

/**
 * O anel fino da meta do dia: 0/N sessões válidas.
 *
 * SVG e não `conic-gradient` porque o anel tem de animar o traço e ser legível a 20 px; é a
 * mesma técnica dos anéis do HUD (SPEC-014).
 */
function GoalRing({ done, target }: { done: number; target: number }) {
  const raio = 9
  const perimetro = 2 * Math.PI * raio
  const fracao = target <= 0 ? 0 : Math.min(1, done / target)

  return (
    <svg className="fire-chip__ring" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="fire-chip__ring-bg" cx="12" cy="12" r={raio} />
      <circle
        className="fire-chip__ring-fg"
        cx="12"
        cy="12"
        r={raio}
        strokeDasharray={`${perimetro * fracao} ${perimetro}`}
      />
    </svg>
  )
}

export function FireChip({ onOpen }: { onOpen: () => void }) {
  const view = useEngagement()

  return (
    <button
      type="button"
      className={`fire-chip ${view.streak > 0 ? 'fire-chip--lit' : ''}`}
      onClick={onOpen}
      aria-label={fireAriaLabel(view)}
    >
      <span className="fire-chip__flame" aria-hidden="true">
        🔥
      </span>
      <span className="fire-chip__num num tabular">{fireLabel(view)}</span>
      <GoalRing done={view.sessionsToday} target={view.goalTarget} />
      {/* O ponto do fantasma: pequeno, mas presente em toda tela onde o número aparece. A
          explicação inteira fica no painel — aqui o que cabe é o sinal de que há uma. */}
      {view.source === 'local' && !view.pending && (
        <span className="fire-chip__ghost" aria-hidden="true" title="Só neste aparelho" />
      )}
    </button>
  )
}
