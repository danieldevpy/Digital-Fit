// Preferências da pré-configuração (SPEC-014 §3). Mesma casa e mesmo motivo das outras
// preferências: conforto de quem treina, não conta (SPEC-011 garante treinar sem conta).
//
// Série e repetições são METAS COSMÉTICAS na Fase Inicial: alimentam os anéis do HUD
// (denominador do progresso), não a autoridade do servidor — que continua encerrando a
// sessão pelos 30s (SPEC-009). Meta de verdade é a T-045. A duração nem stepper tem
// habilitado: fingir que o servidor obedeceu seria mentir.

const SERIES_KEY = 'digitalfit.series'
const REPS_KEY = 'digitalfit.reps_goal'

export const SERIES_MIN = 1
export const SERIES_MAX = 9
export const DEFAULT_SERIES = 1

export const REPS_MIN = 5
export const REPS_MAX = 30
export const DEFAULT_REPS_GOAL = 15

/** Duração fixa da Fase Inicial — espelho do servidor (SPEC-009). */
export const FIXED_DURATION_S = 30

function clamp(value: unknown, min: number, max: number, fallback: number): number {
  const n = Number(value)
  if (!Number.isFinite(n)) return fallback
  return Math.max(min, Math.min(max, Math.round(n)))
}

function read(key: string, min: number, max: number, fallback: number): number {
  try {
    const raw = window.localStorage.getItem(key)
    if (raw === null) return fallback
    return clamp(raw, min, max, fallback)
  } catch {
    return fallback
  }
}

function write(key: string, value: number): number {
  try {
    window.localStorage.setItem(key, String(value))
  } catch {
    // Sem armazenamento (Safari privado): vale pela sessão atual e pronto.
  }
  return value
}

export function seriesPreference(): number {
  return read(SERIES_KEY, SERIES_MIN, SERIES_MAX, DEFAULT_SERIES)
}

export function setSeriesPreference(value: number): number {
  return write(SERIES_KEY, clamp(value, SERIES_MIN, SERIES_MAX, DEFAULT_SERIES))
}

export function repsGoalPreference(): number {
  return read(REPS_KEY, REPS_MIN, REPS_MAX, DEFAULT_REPS_GOAL)
}

export function setRepsGoalPreference(value: number): number {
  return write(REPS_KEY, clamp(value, REPS_MIN, REPS_MAX, DEFAULT_REPS_GOAL))
}
