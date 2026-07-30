// Pré-configuração + Treino ao Vivo (SPEC-014 §3–4, protótipo "Evolução UI v2").
//
// É UM componente com dois modos porque a CameraView precisa sobreviver à passagem
// pré-config → treino: ela vive num slot estável (`.sess__cam`) e o resto é cromo
// absoluto que troca por cima. Desvios honestos da referência (FC `--`, kcal `--`,
// stop no lugar de pause) estão na tabela §Desvios da SPEC-014.
import { useEffect, useState } from 'react'
import { CameraView } from '../capture/CameraView'
import { CountdownSetting } from '../hud/CountdownSetting'
import { TimerRing } from '../hud/TimerRing'
import { exerciseSubtitle, getExercise } from '../session/catalog'
import { resolveCoachCard } from '../session/coachCard'
import {
  FIXED_DURATION_S,
  REPS_MAX,
  REPS_MIN,
  repsGoalPreference,
  SERIES_MAX,
  SERIES_MIN,
  seriesPreference,
  setRepsGoalPreference,
  setSeriesPreference,
} from '../session/configPrefs'
import { useCountdown } from '../session/countdown'
import { exercisePreference } from '../session/preferences'
import { useNow } from '../session/useNow'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { useSessionStore } from '../store/session'
import {
  IconAngle,
  IconFlame,
  IconHeart,
  IconLogo,
  IconMirror,
  IconMusic,
  IconNext,
  IconPlay,
  IconPrev,
  IconStop,
} from '../ui/icons'

/** Onda de ECG decorativa dos cards de FC (a referência a mostra; dado real não há). */
function EcgWave({ color }: { color: string }) {
  return (
    <svg width="72" height="16" viewBox="0 0 76 16" aria-hidden="true">
      <path
        d="M0 9 C8 9 9 3 16 3 S26 14 34 14 S45 4 52 6 S62 12 70 8 76 7 76 8"
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeDasharray="6 4"
        className="hud-wave-path"
      />
    </svg>
  )
}

/** Silhueta-guia ciano do protótipo — sobre a câmera na pré-configuração. */
function SilhouetteGuide() {
  return (
    <svg viewBox="0 0 200 300" className="prep__silhouette v2-glow" aria-hidden="true">
      <g
        fill="none"
        stroke="rgba(77,210,255,.75)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="5 8"
        style={{ filter: 'drop-shadow(0 0 5px rgba(77,210,255,.7))' }}
      >
        <circle cx="100" cy="44" r="15" />
        <path d="M100 59 L100 92 M72 80 L128 80 M72 80 L50 50 L32 22 M128 80 L150 50 L168 22 M100 92 L84 158 M100 92 L116 158 M84 158 L116 158 M84 158 L70 213 L60 266 M116 158 L130 213 L140 266" />
      </g>
      <g fill="#bfe9ff">
        {[
          [72, 80],
          [128, 80],
          [32, 22],
          [168, 22],
          [84, 158],
          [116, 158],
          [60, 266],
          [140, 266],
        ].map(([cx, cy]) => (
          <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="3" />
        ))}
      </g>
    </svg>
  )
}

/** Anel de progresso de repetições do HUD (azul, 56px, como no protótipo). */
function RepsRing({ count, goal }: { count: number; goal: number }) {
  const R = 25
  const C = 2 * Math.PI * R
  const progress = goal > 0 ? Math.min(count / goal, 1) : 0
  return (
    <div className="hud-ring">
      <svg width="56" height="56" viewBox="0 0 56 56" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="28" cy="28" r={R} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth="4" />
        <circle
          cx="28"
          cy="28"
          r={R}
          fill="none"
          stroke="#4d8cff"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${(C * progress).toFixed(1)} ${C.toFixed(1)}`}
          style={{
            filter: 'drop-shadow(0 0 4px rgba(77,140,255,.9))',
            transition: 'stroke-dasharray .6s',
          }}
        />
      </svg>
      <div className="hud-ring__content">
        <p className="hud-card__big tabular">
          {count}
          <small>/{goal}</small>
        </p>
      </div>
    </div>
  )
}

interface StepperCellProps {
  label: string
  value: string
  onDec?: () => void
  onInc?: () => void
  disabled?: boolean
  disabledTitle?: string
  small?: boolean
}

function StepperCell({ label, value, onDec, onInc, disabled, disabledTitle, small }: StepperCellProps) {
  return (
    <div className="prep-cell">
      <p className="v2-label">{label}</p>
      <p className={`prep-cell__value tabular ${small ? 'prep-cell__value--sm' : ''}`}>{value}</p>
      <div className="prep-cell__steppers">
        <button type="button" className="stepper" onClick={onDec} disabled={disabled} title={disabled ? disabledTitle : undefined} aria-label={`Diminuir ${label}`}>
          −
        </button>
        <button type="button" className="stepper" onClick={onInc} disabled={disabled} title={disabled ? disabledTitle : undefined} aria-label={`Aumentar ${label}`}>
          +
        </button>
      </div>
    </div>
  )
}

export function SessionScreen({ mode }: { mode: 'preparar' | 'treino' }) {
  const cameraStatus = useSessionStore((state) => state.cameraStatus)
  const cameraControls = useSessionStore((state) => state.cameraControls)
  const repCount = useSessionStore((state) => state.repCount)
  const armAngleDeg = useSessionStore((state) => state.armAngleDeg)
  const exerciseKeyLive = useSessionStore((state) => state.exerciseKey)
  const toggleMirrored = useSessionStore((state) => state.toggleMirrored)
  const sceneEntry = useSessionStore((state) => state.sceneEntry)
  const feedbackEntry = useSessionStore((state) => state.feedbackEntry)
  const { secondsLeft, durationS } = useCountdown()

  const [series, setSeries] = useState(seriesPreference)
  const [repsGoal, setRepsGoal] = useState(repsGoalPreference)

  // Persistência fora do updater: dois toques rápidos no stepper não podem perder um
  // incremento (closure velha), e o updater funcional tem de continuar puro.
  useEffect(() => {
    setSeriesPreference(series)
  }, [series])
  useEffect(() => {
    setRepsGoalPreference(repsGoal)
  }, [repsGoal])

  // Na pré-config vale a preferência; no treino vale o que o servidor admitiu.
  const exerciseKey = mode === 'treino' && exerciseKeyLive ? exerciseKeyLive : exercisePreference()
  const exercise = getExercise(exerciseKey)

  const cameraReady = cameraStatus === 'ready'
  const now = useNow(sceneEntry !== null || feedbackEntry !== null)
  const coach = resolveCoachCard({
    scene: sceneEntry,
    feedback: feedbackEntry,
    defaultTip: exercise.default_tip,
    now,
  })

  const mostraAngulo = exercise.main_angle === 'arm_abduction' && armAngleDeg !== null
  const angulo = mostraAngulo ? `${Math.round(armAngleDeg)}°` : '--'

  const iniciar = () => {
    if (!cameraReady) cameraControls?.start()
    navigate({ screen: 'treino' })
  }

  const encerrar = () => {
    cameraControls?.stop()
    navigate({ screen: 'preparar' })
  }

  const duracaoFmt = `00:${String(FIXED_DURATION_S).padStart(2, '0')}`

  return (
    <div className="sess">
      <div className={`sess__cam ${mode === 'preparar' ? 'sess__cam--prep' : 'sess__cam--live'}`}>
        <CameraView compactCover={mode === 'preparar'} />

        {mode === 'preparar' && (
          <div className="prep__overlay">
            <div className="prep__grid-bg" />
            <div className="prep__scanline v2-scan" />
            <SilhouetteGuide />
            <div className="prep__hint-pill">
              <span>
                {cameraReady
                  ? 'Você já está visível · alinhe-se à guia'
                  : 'A câmera abre aqui — alinhe-se à guia'}
              </span>
            </div>
          </div>
        )}
      </div>

      {mode === 'preparar' ? (
        <>
          <header className="prep__head">
            <h1 className="prep__title">Pré-configuração</h1>
            <p className="prep__sub">Vamos preparar seu treino</p>
          </header>

          <div className="prep__side prep__side--left">
            <button
              type="button"
              className="prep-cell prep-cell--action prep-cell--ex"
              onClick={() => navigate({ screen: 'exercicios' })}
            >
              <p className="v2-label">Exercício</p>
              <IconLogo className="prep-cell__ex-icon" />
              <p className="prep-cell__ex-name">{exercise.display_name}</p>
            </button>

            <StepperCell
              label="Série"
              value={String(series)}
              onDec={() => setSeries((v) => Math.max(SERIES_MIN, v - 1))}
              onInc={() => setSeries((v) => Math.min(SERIES_MAX, v + 1))}
            />
            <StepperCell
              label="Repetições"
              value={String(repsGoal)}
              onDec={() => setRepsGoal((v) => Math.max(REPS_MIN, v - 1))}
              onInc={() => setRepsGoal((v) => Math.min(REPS_MAX, v + 1))}
            />
            {/* Duração travada nos 30s: a autoridade é o servidor (SPEC-009). Fingir que o
                stepper obedeceu seria mentir — destravamos quando a evolução aceitar. */}
            <StepperCell
              label="Duração"
              value={duracaoFmt}
              disabled
              disabledTitle="Duração configurável: em breve"
              small
            />
          </div>

          <div className="prep__side prep__side--right">
            <button type="button" className="prep-cell prep-cell--action" onClick={toggleMirrored}>
              <span className="prep-cell__mirror">
                <IconMirror className="prep-cell__mirror-icon" />
                <span>Espelhar</span>
              </span>
            </button>

            <div className="prep-cell">
              <p className="v2-label">Frequência cardíaca</p>
              <p className="prep-cell__value prep-cell__value--sm">
                <IconHeart className="prep-cell__hud-icon prep-cell__hud-icon--blue" /> --
              </p>
              <p className="prep-cell__unit">BPM</p>
              <EcgWave color="#8b5cf6" />
            </div>

            <div className="prep-cell">
              <p className="v2-label">Ângulo</p>
              <p className="prep-cell__value tabular">
                <IconAngle className="prep-cell__hud-icon prep-cell__hud-icon--purple" /> {angulo}
              </p>
            </div>

            <div className="prep-cell">
              <p className="v2-label">Calorias estimadas</p>
              <IconFlame className="prep-cell__hud-icon prep-cell__hud-icon--hot" />
              <p className="prep-cell__value prep-cell__value--sm">
                -- <span className="prep-cell__unit">kcal</span>
              </p>
            </div>

            <CountdownSetting />
          </div>

          <div className="prep__bottom">
            <div className="prep__cta">
              <button type="button" className="v2-cta" onClick={iniciar}>
                Iniciar Exercício
                <span className="v2-cta__play">
                  <IconPlay className="v2-cta__play-icon" />
                </span>
              </button>
            </div>
            <TabBar />
          </div>
        </>
      ) : (
        <div className="live__chrome">
          <div className="live__fade-top" />
          <div className="live__fade-bottom" />

          <header className="live__head">
            <p className="live__head-title">
              <span className="live__dot" />
              Treino ao Vivo
            </p>
            <p className="live__head-sub">
              {exercise.display_name} • Série 1/{series}
            </p>
          </header>

          <svg width="300" height="300" viewBox="0 0 300 300" className="live__orbit v2-orbit" aria-hidden="true">
            <g>
              <circle cx="150" cy="150" r="132" fill="none" stroke="rgba(107,140,255,.5)" strokeWidth="1.5" strokeDasharray="4 10" />
              <circle cx="150" cy="150" r="120" fill="none" stroke="rgba(139,92,246,.35)" strokeWidth="1" strokeDasharray="60 200" />
            </g>
          </svg>

          <div className="hud-card hud-card--reps">
            <p className="v2-label">Repetições</p>
            <RepsRing count={repCount} goal={repsGoal} />
          </div>

          <div className="hud-card hud-card--fc">
            <p className="v2-label">Frequência cardíaca</p>
            <p className="hud-card__big">
              <IconHeart className="hud-card__icon hud-card__icon--blue" /> --
            </p>
            <p className="prep-cell__unit">BPM</p>
            <EcgWave color="#4d8cff" />
          </div>

          <div className="hud-card hud-card--angle">
            <p className="v2-label">Ângulo</p>
            <p className="hud-card__big tabular">{angulo}</p>
            <IconAngle className="hud-card__icon hud-card__icon--purple" />
          </div>

          <div className="hud-card hud-card--kcal">
            <p className="v2-label">Calorias</p>
            <IconFlame className="hud-card__icon hud-card__icon--hot" />
            <p className="hud-card__big">
              -- <small>kcal</small>
            </p>
          </div>

          {coach.tone !== 'default' && (
            <div className={`live__toast ${coach.tone === 'scene' ? 'live__toast--scene' : ''}`}>
              <div>
                <p className="live__toast-title">{coach.title}</p>
                <p className="live__toast-text">{coach.text}</p>
              </div>
            </div>
          )}

          <div className="live__serie">
            <p className="v2-label">Série</p>
            <p className="hud-card__big tabular" style={{ fontSize: '0.9375rem' }}>
              1/{series}
            </p>
          </div>

          <div className="live__ex-pill">
            <div className="live__ex-pill-box">
              <p className="live__ex-name">{exercise.display_name}</p>
              <p className="live__ex-sub">{exerciseSubtitle(exercise)}</p>
            </div>
          </div>

          <div className="live__timer">
            <TimerRing secondsLeft={secondsLeft} secondsTotal={durationS} />
          </div>

          <div className="live__player">
            <button type="button" className="player-btn" disabled title="Trocar exercício: volte à pré-configuração">
              <IconPrev className="player-btn__icon" />
            </button>
            {/* Stop e não pause: a sessão de 30s é atômica no servidor (SPEC-009). O botão
                encerra e volta à pré-configuração; pause de verdade é evolução. */}
            <button
              type="button"
              className="player-btn player-btn--main"
              onClick={cameraReady ? encerrar : iniciar}
              aria-label={cameraReady ? 'Encerrar treino' : 'Iniciar treino'}
            >
              {cameraReady ? (
                <IconStop className="player-btn__icon--main" />
              ) : (
                <IconPlay className="player-btn__icon--main" />
              )}
            </button>
            <button type="button" className="player-btn" disabled title="Trocar exercício: volte à pré-configuração">
              <IconNext className="player-btn__icon" />
            </button>
            <button type="button" className="player-btn player-btn--music" disabled title="Música: em breve">
              <IconMusic className="player-btn__icon" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
