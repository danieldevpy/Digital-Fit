// Pré-configuração + Treino ao Vivo (SPEC-014 §3–4, protótipo "Evolução UI v2").
//
// É UM componente com dois modos porque a CameraView precisa sobreviver à passagem
// pré-config → treino: ela vive num slot estável (`.sess__cam`) e o resto é cromo
// absoluto que troca por cima. Desvios honestos da referência (FC `--`, stop no lugar de
// pause) estão na tabela §Desvios da SPEC-014. O kcal deixou de ser um deles na T-063: ele
// tem MET servido pelo catálogo e tempo real de sessão, e só o peso é premissa — declarada
// na própria tela como "estimado" (SPEC-016, critério 3).
import { useEffect, useState } from 'react'
import { CameraView } from '../capture/CameraView'
import { useT } from '../i18n'
import { FireChip } from '../engagement/FireChip'
import { useEngagementStore } from '../engagement/store'
import { CountdownSetting } from '../hud/CountdownSetting'
import { TimerRing } from '../hud/TimerRing'
import { ViewConfirm } from '../hud/ViewConfirm'
import { ZoomControl } from '../hud/ZoomControl'
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
import { setViewPreference, viewPreference, viewsOf, type ViewId } from '../session/exerciseViews'
import { estadoDoExemplo, temConta } from '../session/guideGate'
import { shouldConfirmView } from '../session/viewGate'
import { estimatedLabel, formatKcal, liveKcal } from '../session/kcal'
import { exercisePreference, guideSeen } from '../session/preferences'
import { ctaDeInicio } from '../session/startGate'
import { useNow } from '../session/useNow'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { useAccountStore } from '../store/account'
import { useSessionStore } from '../store/session'
import { BrandMark } from '../ui/BrandMark'
import { ExerciseIcon } from '../ui/exerciseIcon'
import { IconAngle, IconCamera, IconFlame, IconMirror, IconPlay, IconStop } from '../ui/icons'
import { ViewPicker } from '../ui/ViewPicker'

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
  const t = useT()

  return (
    <div className="prep-cell">
      <p className="v2-label">{label}</p>
      <p className={`prep-cell__value tabular ${small ? 'prep-cell__value--sm' : ''}`}>{value}</p>
      <div className="prep-cell__steppers">
        <button type="button" className="stepper" onClick={onDec} disabled={disabled} title={disabled ? disabledTitle : undefined} aria-label={t('session:stepper.decrease', { label })}>
          −
        </button>
        <button type="button" className="stepper" onClick={onInc} disabled={disabled} title={disabled ? disabledTitle : undefined} aria-label={t('session:stepper.increase', { label })}>
          +
        </button>
      </div>
    </div>
  )
}

export function SessionScreen({ mode }: { mode: 'preparar' | 'treino' }) {
  const t = useT()
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
  const abrirEngajamento = useEngagementStore((state) => state.openSheet)
  const { secondsLeft, durationS } = useCountdown()

  const [series, setSeries] = useState(seriesPreference)
  const [repsGoal, setRepsGoal] = useState(repsGoalPreference)
  // A variação de câmera (T-111). Estado local porque a mesma escolha é editável aqui e no
  // Guia, e a tela precisa se redesenhar no toque — o armazenamento é a memória, não a fonte.
  // `viewOf` guarda de que exercício a escolha atual é; ver o ajuste logo abaixo.
  const [viewId, setViewId] = useState<ViewId | null>(null)
  const [viewOf, setViewOf] = useState<string | null>(null)
  // A trava de confirmação (T-112). `confirmadoPara` guarda o exercício já confirmado NESTA
  // visita: é o que faz a caixa interceptar o "Ligar câmera" e deixar o "Iniciar Exercício"
  // seguinte passar direto, sem perguntar duas vezes o que a pessoa acabou de responder.
  const [travaAberta, setTravaAberta] = useState(false)
  const [confirmadoPara, setConfirmadoPara] = useState<string | null>(null)

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

  // A variação segue o exercício: trocar de exercício não pode carregar junto a escolha de
  // câmera do anterior, e quem volta do Guia tem de ver o que escolheu lá. O ajuste é feito
  // DURANTE o render (padrão de "estado derivado de prop") e não num efeito: num efeito a tela
  // pintaria uma vez com a escolha do exercício anterior antes de se corrigir.
  if (viewOf !== exerciseKey) {
    setViewOf(exerciseKey)
    setViewId(viewPreference(exerciseKey))
  }
  const view = viewsOf(exerciseKey)?.find((v) => v.id === viewId)

  // O destaque do "ver exemplo" (ver `session/guideGate.ts`). Assinado do store, e não lido do
  // token direto, para o destaque apagar sozinho no instante em que a pessoa entra pela folha
  // de conta sem precisar sair da tela e voltar.
  const accountStatus = useAccountStore((state) => state.status)
  const { destacarLink } = estadoDoExemplo({
    temConta: temConta(accountStatus),
    jaViu: guideSeen(exerciseKey),
  })

  const cameraReady = cameraStatus === 'ready'
  const cta = ctaDeInicio(cameraStatus)
  const now = useNow(sceneEntry !== null || feedbackEntry !== null)
  const coach = resolveCoachCard({
    scene: sceneEntry,
    feedback: feedbackEntry,
    defaultTip: exercise.default_tip,
    now,
  })

  const mostraAngulo = exercise.main_angle === 'arm_abduction' && armAngleDeg !== null
  const angulo = mostraAngulo ? `${Math.round(armAngleDeg)}°` : '--'

  // Calorias ao vivo (SPEC-016, critério 3). Quem manda no total são as **repetições** que o
  // servidor contou (T-128); o tempo entra só para medir o ritmo, que dá o multiplicador. MET e
  // cadência de referência vêm do catálogo servido — falta qualquer um dos dois e o card mostra
  // `--`, que continua sendo a resposta honesta.
  const kcal = formatKcal(
    liveKcal({
      met: exercise.met,
      refCadenceRpm: exercise.ref_cadence_rpm,
      reps: repCount,
      elapsedS: durationS - secondsLeft,
    }),
  )

  const iniciar = () => {
    // Portão de quota (SPEC-016, critério 1): o limite tem de aparecer ANTES da câmera. Aqui
    // ele não é a trava — a trava é o `POST /sessions`, e há teste de que pular esta linha não
    // ajuda (`tests/test_quota.py`). O que esta linha evita é a pessoa dar permissão de
    // câmera, esperar o pipeline aquecer e se enquadrar para só então ouvir "não".
    const quota = useAccountStore.getState().quota
    if (quota && !quota.allowed) {
      useAccountStore.getState().blockByQuota()
      return
    }
    // Trava da variação (T-112): exercício com duas montagens de cena não passa daqui sem
    // alguém dizer qual delas vale. Vem ANTES de ligar a câmera porque o próximo gesto de quem
    // confirma é pôr o celular no chão — perguntar depois seria perguntar tarde.
    //
    // Também cobre o caminho de quem trocou de exercício com a câmera JÁ ligada: aí o CTA está
    // em "Iniciar Exercício", e sem esta linha a pessoa entraria no treino sem nunca ter visto
    // a pergunta.
    if (shouldConfirmView(exerciseKey, { confirmadoPara })) {
      setTravaAberta(true)
      return
    }
    // Câmera desligada: o toque LIGA e fica. Não navega (`session/startGate.ts`) — sair da
    // pré-configuração no instante do diálogo de permissão pulava justamente o que esta tela
    // serve para fazer, que é a pessoa se ver e se enquadrar antes de começar.
    if (!cameraReady) {
      cameraControls?.start()
      return
    }
    navigate({ screen: 'treino' })
  }

  /** Confirmou a variação: a trava fecha e o toque original segue seu caminho. */
  const confirmarVista = (id: ViewId) => {
    setViewId(id)
    setConfirmadoPara(exerciseKey)
    setTravaAberta(false)
    // Segue o degrau que a trava interrompeu — ligar a câmera, ou entrar no treino se ela já
    // estava ligada. Sem isto a confirmação custaria um segundo toque no mesmo botão.
    if (!cameraReady) cameraControls?.start()
    else navigate({ screen: 'treino' })
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
                      ? // Com variação, o pill diz onde o CELULAR vai (T-111) em vez de
                        // "alinhe-se à guia": num exercício de chão a silhueta em pé não
                        // ensina nada, e é a montagem da cena que decide se a sessão conta.
                        (view?.phone ?? t('session:prep.pill_aligned'))
                      : // O treino não começa mais com a câmera desligada: o pill diz o passo
                        // que falta em vez de descrever a janela vazia.
                        t('session:prep.pill_turn_on')}
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
            <h1 className="prep__title">{t('session:prep.title')}</h1>
            <p className="prep__sub">{t('session:prep.subtitle')}</p>
            {/* O fogo mora na Início (SPEC-019 §Superfícies): é a tela em que se chega ao
                abrir o app, e o motivo de voltar amanhã tem de estar onde se chega. */}
            <FireChip onOpen={() => abrirEngajamento(true)} />
          </header>

          <div className="prep__side prep__side--left">
            <div className="prep-cell prep-cell--ex">
              <button
                type="button"
                className="prep-cell__ex-main prep-cell--action"
                onClick={() => navigate({ screen: 'exercicios' })}
              >
                <p className="v2-label">{t('session:label.exercise')}</p>
                {/* A figura segue o exercício selecionado (T-082). Mesma classe de antes: o
                    tamanho, o ciano e o glow continuam vindo do CSS, muda só a pose. */}
                <ExerciseIcon exercise={exerciseKey} className="prep-cell__ex-icon" />
                <p className="prep-cell__ex-name">{exercise.display_name}</p>
              </button>
              {/* Para quem tem conta este link é o ÚNICO caminho até o exemplo (ver
                  `session/guideGate.ts`), então ele não pode mais ser um texto de 9px que se
                  perde na coluna. Vira chip com ícone; e enquanto o exemplo daquele exercício
                  não tiver sido visto, respira algumas vezes e sossega — o destaque morre no
                  toque, não no relógio, e nunca volta para o mesmo exercício. */}
              <button
                type="button"
                className={`prep-cell__ex-guide ${destacarLink ? 'prep-cell__ex-guide--novo' : ''}`}
                onClick={() => navigate({ screen: 'guia', exercise: exerciseKey })}
              >
                <IconPlay className="prep-cell__ex-guide-icon" />
                {t('session:prep.see_example')}
              </button>
            </div>

            {/* Logo abaixo do card do exercício, e não perdido na outra coluna: a variação é
                propriedade DAQUELE exercício, e é a segunda decisão de quem chegou aqui —
                antes de série, repetição e preparação, porque é a única que muda o que a
                pessoa faz com o celular antes de deitar no chão. Some sozinha para exercício
                sem variação. */}
            <ViewPicker
              exercise={exerciseKey}
              value={viewId}
              onChange={(id) => setViewId(setViewPreference(exerciseKey, id))}
              compact
            />

            <StepperCell
              label={t('session:label.series')}
              value={String(series)}
              onDec={() => setSeries((v) => Math.max(SERIES_MIN, v - 1))}
              onInc={() => setSeries((v) => Math.min(SERIES_MAX, v + 1))}
            />
            <StepperCell
              label={t('session:label.reps')}
              value={String(repsGoal)}
              onDec={() => setRepsGoal((v) => Math.max(REPS_MIN, v - 1))}
              onInc={() => setRepsGoal((v) => Math.min(REPS_MAX, v + 1))}
            />
            {/* Duração travada nos 30s: a autoridade é o servidor (SPEC-009). Fingir que o
                stepper obedeceu seria mentir — destravamos quando a evolução aceitar. */}
            <StepperCell
              label={t('session:label.duration')}
              value={duracaoFmt}
              disabled
              disabledTitle={t('session:prep.duration_soon')}
              small
            />
          </div>

          <div className="prep__side prep__side--right">
            <button type="button" className="prep-cell prep-cell--action" onClick={toggleMirrored}>
              <span className="prep-cell__mirror">
                <IconMirror className="prep-cell__mirror-icon" />
                <span>{t('session:prep.mirror')}</span>
              </span>
            </button>

            {/* Só com a câmera ligada: antes disso não há track (zoom nativo) nem vídeo
                (fallback por CSS) para ajustar — a escolha ficaria vazia. */}
            {cameraReady && <ZoomControl />}

            {/* Frequência cardíaca saiu das duas telas (decisão pós-teste de 2026-07-30):
                sem sensor o card era só ruído — volta quando houver dado (SPEC-014 §Desvios). */}

            <div className="prep-cell">
              <p className="v2-label">{t('session:label.angle')}</p>
              <p className="prep-cell__value tabular">
                <IconAngle className="prep-cell__hud-icon prep-cell__hud-icon--purple" /> {angulo}
              </p>
            </div>

            {/* Continua `--` na pré-config, e por um motivo que não é preguiça: a sessão
                ainda não começou, então o gasto até agora é zero — e "0,0 kcal" ao lado do
                botão de iniciar lê como promessa quebrada, não como estado inicial. */}
            <div className="prep-cell">
              <p className="v2-label">{t('session:label.calories_estimated')}</p>
              <IconFlame className="prep-cell__hud-icon prep-cell__hud-icon--hot" />
              <p className="prep-cell__value prep-cell__value--sm">
                -- <span className="prep-cell__unit">{t('session:label.kcal_unit')}</span>
              </p>
            </div>

            <CountdownSetting />
          </div>

          {/* A trava (T-112) mora sobre a janela da câmera e acima de todo o cromo: enquanto
              ela está aberta, o único caminho para frente é confirmar. */}
          {travaAberta && (
            <ViewConfirm
              exercise={exerciseKey}
              value={viewId}
              onConfirm={confirmarVista}
              onCancel={() => setTravaAberta(false)}
            />
          )}

          <div className="prep__bottom">
            <div className="prep__cta">
              {/* Dois degraus (`session/startGate.ts`): com a câmera desligada este botão é o
                  interruptor dela, e só quando há imagem ele vira a porta do treino. O ícone
                  acompanha o rótulo — um ▶ ao lado de "Ligar câmera" prometeria treino. */}
              <button type="button" className="v2-cta" onClick={iniciar} disabled={cta.disabled}>
                {cta.label}
                <span className="v2-cta__play">
                  {cta.action === 'iniciar' ? (
                    <IconPlay className="v2-cta__play-icon" />
                  ) : (
                    <IconCamera className="v2-cta__play-icon v2-cta__play-icon--cam" />
                  )}
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
              {t('session:live.title')}
            </p>
            <p className="live__head-sub">
              {t('session:live.subtitle', { exercise: exercise.display_name, total: series })}
            </p>
          </header>

          <svg width="300" height="300" viewBox="0 0 300 300" className="live__orbit v2-orbit" aria-hidden="true">
            <g>
              <circle cx="150" cy="150" r="132" fill="none" stroke="rgba(107,140,255,.5)" strokeWidth="1.5" strokeDasharray="4 10" />
              <circle cx="150" cy="150" r="120" fill="none" stroke="rgba(139,92,246,.35)" strokeWidth="1" strokeDasharray="60 200" />
            </g>
          </svg>

          <div className="hud-card hud-card--reps">
            <p className="v2-label">{t('session:label.reps')}</p>
            <RepsRing count={repCount} goal={repsGoal} />
          </div>

          {/* Timer no topo-direito (onde a referência punha a FC): a 2 metros da tela, reps
              e tempo são os dois números que importam — ficam os dois na linha dos olhos. */}
          <div className="hud-card hud-card--timer">
            <TimerRing secondsLeft={secondsLeft} secondsTotal={durationS} />
          </div>

          <div className="hud-card hud-card--angle">
            <p className="v2-label">{t('session:label.angle')}</p>
            <p className="hud-card__big tabular">{angulo}</p>
            <IconAngle className="hud-card__icon hud-card__icon--purple" />
          </div>

          <div className="hud-card hud-card--kcal">
            <p className="v2-label">{t('session:label.calories')}</p>
            <IconFlame className="hud-card__icon hud-card__icon--hot" />
            <p className="hud-card__big tabular">
              {kcal} <small>{t('session:label.kcal_unit')}</small>
            </p>
            {/* O rótulo aparece só quando há número: sem MET o card mostra `--`, e chamar de
                "estimado" um traço seria estimar o quê? */}
            {kcal !== '--' && <span className="hud-card__note">{estimatedLabel()}</span>}
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
                  aria-label={cameraReady ? t('session:live.stop_aria') : t('session:live.start_aria')}
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
