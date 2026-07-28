interface TimerRingProps {
  secondsLeft: number
  secondsTotal: number
}

const SIZE = 84
const STROKE = 5
const RADIUS = (SIZE - STROKE) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function formatClock(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

export function TimerRing({ secondsLeft, secondsTotal }: TimerRingProps) {
  const progress = secondsTotal > 0 ? Math.min(Math.max(secondsLeft / secondsTotal, 0), 1) : 0

  return (
    <div className="ring">
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} aria-hidden="true">
        <defs>
          <linearGradient id="ringGradient" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#a855f7" />
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
        <p className="ring__time">{formatClock(secondsLeft)}</p>
        <p className="ring__label">Tempo restante</p>
      </div>
    </div>
  )
}
