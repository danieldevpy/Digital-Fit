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
import { BrandMark } from '../ui/BrandMark'
import { ExerciseIcon } from '../ui/exerciseIcon'
import { IconAngle, IconFlame, IconMirror, IconPlay, IconStop } from '../ui/icons'

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

/**
 * Anel de progresso de repetições do HUD. Maior que o do protótipo (76px, número 1.5rem):
 * quem treina está a ~2 metros da tela, e a repetição é O número da sessão — tem de ser
 * legível de longe (ajuste pós-teste real de 2026-07-30).
 */
function RepsRing({ count, goal }: { count: number; goal: number }) {
  const R = 34
  const C = 2 * Math.PI * R
  const progress = goal > 0 ? Math.min(count / goal, 1) : 0
  return (
    <div className="hud-ring">
      <svg width="76" height="76" viewBox="0 0 76 76" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="38" cy="38" r={R} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth="5" />
        <circle
          cx="38"
          cy="38"
          r={R}
          fill="none"
          stroke="#4d8cff"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${(C * progress).toFixed(1)} ${C.toFixed(1)}`}
          style={{
            filter: 'drop-shadow(0 0 4px rgba(77,140,255,.9))',
            transition: 'stroke-dasharray .6s',
          }}
        />
      </svg>
      <div className="hud-ring__content">
        <p className="hud-card__big hud-card__big--xl tabular">
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
  const sessionStatus = useSessionStore((state) => state.sessionStatus)
  const sceneEntry = useSessionStore((state) => state.sceneEntry)
  const sceneAdvice = useSessionStore((state) => state.sceneAdvice)
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
        <CameraView compactCover={mode === 'preparar'} checkScene={mode === 'preparar'} />

        {mode === 'preparar' && (
          <div className="prep__overlay">
            {/* A câmera é a tela inteira (T-080); estes quatro painéis é que devolvem a
                moldura, desfocando e escurecendo tudo que está FORA da janela nítida —
                exatamente a área onde os cards flutuam. A janela ficou na largura de sempre:
                quem se enquadrou antes continua enquadrado. */}
            <div className="prep__blur prep__blur--top" />
            <div className="prep__blur prep__blur--bottom" />
            <div className="prep__blur prep__blur--left" />
            <div className="prep__blur prep__blur--right" />

            <div className="prep__window">
              <div className="prep__grid-bg" />
              <div className="prep__scanline v2-scan" />
              <SilhouetteGuide />
              {/* Um canal só de estado da cena (T-085), e não um aviso novo empilhado: o
                  conselho de luz/nitidez toma o lugar da dica de enquadramento enquanto vale.
                  Enquadramento a silhueta-guia já ensina sozinha; lente suja e luz fraca são
                  invisíveis para quem está do outro lado do celular — por isso ganham a vez.
                  Orienta e não bloqueia: o CTA de iniciar continua o mesmo. */}
              <div className={`prep__hint-pill ${sceneAdvice ? 'prep__hint-pill--aviso' : ''}`}>
                <span>
                  {sceneAdvice
                    ? sceneAdvice.text
                    : cameraReady
                      ? 'Você já está visível · alinhe-se à guia'
                      : 'A câmera abre aqui — alinhe-se à guia'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <BrandMark floating />

      {mode === 'preparar' ? (
        <>
          <header className="prep__head">
            <h1 className="prep__title">Pré-configuração</h1>
            <p className="prep__sub">Vamos preparar seu treino</p>
          </header>

          <div className="prep__side prep__side--left">
            <div className="prep-cell prep-cell--ex">
              <button
                type="button"
                className="prep-cell__ex-main prep-cell--action"
                onClick={() => navigate({ screen: 'exercicios' })}
              >
                <p className="v2-label">Exercício</p>
                {/* A figura segue o exercício selecionado (T-082). Mesma classe de antes: o
                    tamanho, o ciano e o glow continuam vindo do CSS, muda só a pose. */}
                <ExerciseIcon exercise={exerciseKey} className="prep-cell__ex-icon" />
                <p className="prep-cell__ex-name">{exercise.display_name}</p>
              </button>
              {/* SPEC-015: o guia só aparece sozinho na primeira vez — depois disso só
                  este link reabre o exemplo, sem repetir o funil. */}
              <button
                type="button"
                className="prep-cell__ex-guide"
                onClick={() => navigate({ screen: 'guia', exercise: exerciseKey })}
              >
                ver exemplo
              </button>
            </div>

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

            {/* Frequência cardíaca saiu das duas telas (decisão pós-teste de 2026-07-30):
                sem sensor o card era só ruído — volta quando houver dado (SPEC-014 §Desvios). */}

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
        // Medindo o corpo (SPEC-004): a instrução central manda, e o HUD sai da frente.
        <div
          className={`live__chrome ${sessionStatus === 'calibrating' ? 'live__chrome--medindo' : ''} ${
            sessionStatus === 'running' || sessionStatus === 'completed' ? 'live__chrome--valendo' : ''
          }`}
        >
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

          {/* Timer no topo-direito (onde a referência punha a FC): a 2 metros da tela, reps
              e tempo são os dois números que importam — ficam os dois na linha dos olhos. */}
          <div className="hud-card hud-card--timer">
            <TimerRing secondsLeft={secondsLeft} secondsTotal={durationS} />
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

          {/* O card SÉRIE flutuante saiu: a informação já vive no subtítulo do topo, e no
              rodapé ele colidia com o pill do exercício (bug visual do teste real). */}
          <div className="live__ex-pill">
            <div className="live__ex-pill-box">
              <p className="live__ex-name">{exercise.display_name}</p>
              <p className="live__ex-sub">{exerciseSubtitle(exercise)}</p>
            </div>
          </div>

          {/* Rodapé único (T-068): a bottom nav do app com o play/stop no meio. O player
              flutuante de 4 botões saiu — ⏮/⏭/música eram placeholders desabilitados e eram
              eles que empurravam o botão principal para baixo dos avisos da câmera e da barra
              do navegador. Trocar de exercício continua sendo papel da pré-configuração.
              Stop e não pause: a sessão de 30s é atômica no servidor (SPEC-009). */}
          <div className="live__bottom">
            <TabBar
              center={
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
              }
            />
          </div>
        </div>
      )}
    </div>
  )
}
