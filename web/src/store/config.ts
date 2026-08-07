// Configuração servida pelo `GET /api/config` (SPEC-018, T-074).
//
// Store separado dos de conta e sessão pela mesma razão que aqueles são separados entre si: o
// catálogo e as capacidades do plano são lidos por telas que não sabem nada de treino (a
// Escolha) e por telas que não sabem nada de conta (a pré-config). Amarrá-los a um dos dois
// faria uma tela depender de estado que ela não usa.
//
// **O default é o do cliente, e ele nunca é apagado.** `catalog` nulo não quer dizer "não há
// exercício": quer dizer "o servidor ainda não falou", e quem lê cai no catálogo embutido
// (`session/catalog.ts`). É o que faz o primeiro paint acontecer sem rede e o app continuar
// utilizável offline — a tela não espera por esta rota para desenhar (SPEC-018 §Como cada
// consumidor lê).
import { create } from 'zustand'

/** Espelho de `Exercise` no `GET /api/config`. Sem `enabled`/`min_plan`: a regra fica no servidor. */
export interface ServerExercise {
  slug: string
  display_name: string
  category: string
  muscle_group: string
  default_tip: string
  main_angle: string
  demo_img: string
  /** Vazio = a frase padrão de cena. Servidor antigo não manda o campo, e isso é suportado. */
  scene_tip?: string
  dot_color: string
  met: number
  /** Ritmo em que o `met` vale (rep/min). Sem ele o MET não vira caloria por repetição. */
  ref_cadence_rpm: number
  maturity: string
  guide_steps: { img: string; text: string }[]
}

export interface PlanCapabilities {
  slug: string
  name: string
  daily_sessions: number
  quota_message: string
  allow_cloud: boolean
  history_limit: number
  kcal_accumulation: boolean
  effects_enabled: boolean
  flags: Record<string, unknown>
}

export interface SessionLimits {
  duration_s: number
  min_s: number
  max_s: number
  countdown_default_s: number
  countdown_max_s: number
}

export interface StepperRanges {
  series_min: number
  series_max: number
  series_default: number
  reps_min: number
  reps_max: number
  reps_default: number
}

/**
 * Texto de um código de feedback (SPEC-008 §1, servido pela SPEC-018 §C).
 *
 * `hint` é opcional porque no catálogo ele é opcional — e o relatório usa só a `message`.
 */
export interface FeedbackText {
  message: string
  hint?: string
}

export interface ServerConfig {
  config_version: number
  plan: PlanCapabilities
  session: SessionLimits
  steppers: StepperRanges
  exercises: ServerExercise[]
  /** Servidor anterior à T-126 não manda o campo; o cliente cai no embutido. */
  feedback?: Record<string, FeedbackText>
}

export interface ConfigState {
  /** `null` = o servidor ainda não falou. Nunca "não há exercício". */
  exercises: ServerExercise[] | null
  plan: PlanCapabilities | null
  session: SessionLimits | null
  steppers: StepperRanges | null
  /** `null` = o servidor ainda não falou. Nunca "este código não tem texto". */
  feedback: Record<string, FeedbackText> | null
  configVersion: number
  apply: (config: ServerConfig) => void
  reset: () => void
}

const DEFAULTS = {
  exercises: null,
  plan: null,
  session: null,
  steppers: null,
  feedback: null,
  configVersion: 0,
}

export const useConfigStore = create<ConfigState>((set) => ({
  ...DEFAULTS,
  apply: (config) =>
    set({
      // Lista vazia é a forma de o servidor dizer "não sei" (banco fora — ver
      // `_catalogo_serializado` no `api/config.py`). Guardá-la como `[]` apagaria a tela
      // Escolha; guardar `null` mantém o catálogo embutido no ar.
      exercises: config.exercises.length > 0 ? config.exercises : null,
      // Mesma leitura do catálogo, e pelo mesmo motivo: dicionário vazio é o servidor dizendo
      // "não consegui ler o YAML" (ver `_mensagens_de_feedback` em `api/config.py`). Guardá-lo
      // como `{}` faria toda frase do relatório virar código na tela.
      feedback:
        config.feedback && Object.keys(config.feedback).length > 0 ? config.feedback : null,
      plan: config.plan,
      session: config.session,
      steppers: config.steppers,
      configVersion: config.config_version,
    }),
  reset: () => set(DEFAULTS),
}))
