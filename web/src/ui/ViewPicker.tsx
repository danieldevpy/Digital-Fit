// Escolha da variação de câmera (T-111) — o mesmo controle na pré-configuração e no Guia.
//
// **Segmentado e não ciclo**, ao contrário da Preparação (`CountdownSetting`), e a diferença é
// deliberada: lá as quatro paradas são o mesmo tipo de coisa (segundos) e um toque avança;
// aqui as duas opções pedem que a pessoa faça algo DIFERENTE com o celular antes de deitar no
// chão. Um controle que mostrasse só a opção atual esconderia metade da decisão — e a pessoa
// só descobriria a outra metade errando a montagem da cena e vendo a sessão contar zero.
//
// Por isso as duas ficam visíveis ao mesmo tempo, e a linha de baixo diz onde o celular vai.
import { viewsOf, type ViewId } from '../session/exerciseViews'
import { IconAngle } from './icons'

interface Props {
  exercise: string
  value: ViewId | null
  onChange: (id: ViewId) => void
  /** `true` na coluna da pré-configuração, onde o controle é um card estreito. */
  compact?: boolean
}

export function ViewPicker({ exercise, value, onChange, compact = false }: Props) {
  const views = viewsOf(exercise)
  // Exercício sem variação não desenha nada — mesma regra do `offersChoice` do catálogo: a
  // superfície aparece quando existe o que escolher.
  if (!views) return null

  const atual = views.find((v) => v.id === value) ?? views[0]!

  return (
    <div className={`viewpick ${compact ? 'viewpick--compact' : ''}`}>
      <p className="v2-label">
        {compact ? 'Câmera' : 'De que lado fica a câmera?'}
      </p>
      <div className="viewpick__opts" role="radiogroup" aria-label="Posição da câmera">
        {views.map((view) => (
          <button
            key={view.id}
            type="button"
            role="radio"
            aria-checked={view.id === atual.id}
            className={`viewpick__opt ${view.id === atual.id ? 'viewpick__opt--on' : ''}`}
            onClick={() => onChange(view.id)}
          >
            {compact ? view.short : view.label}
          </button>
        ))}
      </div>
      {/* A frase que muda o que a pessoa FAZ. É ela, e não o rótulo, que evita a sessão
          zerada por celular no lugar errado. */}
      <p className="viewpick__hint">
        <IconAngle className="viewpick__icon" aria-hidden="true" /> {atual.phone}
      </p>
      {!compact && (
        <p className="viewpick__why">
          As duas contam suas repetições. <strong>De lado</strong> o app também avisa se o
          quadril cair ou empinar; <strong>de frente</strong> ele conta, mas não corrige a linha
          do corpo — a câmera não enxerga seus pés desse ângulo.
        </p>
      )}
    </div>
  )
}
