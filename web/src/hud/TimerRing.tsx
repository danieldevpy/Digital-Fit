// Anel do cronômetro da sessão.
//
// `translate="no"` no relógio (T-162, SPEC-026 §Escopo): é texto que o React reescreve uma vez
// por segundo, o pior caso para a classe de falha que a tradução de página introduz (o `<font>`
// que o Google Translate embrulha em cada nó de texto). O rótulo "restantes" fica de fora — é
// palavra, e traduzir palavra é o que a pessoa pediu ao ligar a tradução.
import { useT } from '../i18n'
import { formatClock } from '../session/countdown'

interface TimerRingProps {
  secondsLeft: number
  secondsTotal: number
}

const SIZE = 84
const STROKE = 5
const RADIUS = (SIZE - STROKE) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export function TimerRing({ secondsLeft, secondsTotal }: TimerRingProps) {
  const t = useT()
  const progress = secondsTotal > 0 ? Math.min(Math.max(secondsLeft / secondsTotal, 0), 1) : 0

  return (
    <div className="ring">
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} aria-hidden="true">
        <defs>
          {/* SPEC-014 §Design tokens: gradiente accent → accent-2. */}
          <linearGradient id="ringGradient" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
        </defs>
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="rgba(255,255,255,0.09)"
          strokeWidth={STROKE}
        />
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="url(#ringGradient)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE * (1 - progress)}
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
        />
      </svg>
      <div className="ring__content">
        <p className="ring__time tabular" translate="no">
          {formatClock(secondsLeft)}
        </p>
        <p className="ring__label">{t('session:timer.remaining')}</p>
      </div>
    </div>
  )
}
