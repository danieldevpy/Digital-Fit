// Namespace `progress` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`. As duas telas leem o passado da pessoa; o tom é de leitura,
// não de elogio (T-150).
import type { Progress } from '../pt-BR/progress'

export const progress: Progress = {
  'kicker': 'Progress',
  'title': 'Your training over time',

  'empty.title': 'No workouts recorded yet',
  'empty.text': 'Finish a session and the result shows up here — no account needed.',
  'empty.cta': 'Train now',

  'metric.workouts.one': 'workout',
  'metric.workouts.other': 'workouts',
  'metric.reps': 'reps',
  'metric.days.one': 'day',
  'metric.days.other': 'days',
  'metric.rpm': 'reps/min',
  'metric.duration': 'duration',
  'unit.reps': 'reps',

  'section.last': 'Last workout',
  'section.weeks': 'Last 4 weeks',
  'section.by_exercise': 'By exercise',
  'day_title': 'Trained on {date}',

  'note.local_lead': 'This is the history kept',
  'note.local_strong': 'on this device',
  'note.local_tail': '— clearing your browser takes it away. With an account, it stays.',
  'note.stale': 'Could not refresh just now — something recent may be missing.',

  'analytics.kicker': 'Analytics',
  'analytics.title': 'Training analysis',
  'analytics.open_last': 'Open the analysis of your last workout',
  'analytics.open_last_sub': 'Pace, reps and what to improve — the full session report.',
  'analytics.empty_note':
    'Analysis across sessions grows out of your history. Do a workout and it starts to exist — the analysis of a single session is the report at the end of the workout.',
  'analytics.empty_cta': 'Do a workout to have something to analyze',

  'analytics.section.pace': 'Pace by exercise',
  'analytics.needs_more': 'One more {exercise} workout and the pace becomes a line.',
  'analytics.range.one': 'from {min} to {max} reps/min across {n} workout',
  'analytics.range.other': 'from {min} to {max} reps/min across {n} workouts',

  'analytics.section.weekly': 'Progress over the last 4 weeks',
  'analytics.weekly_note': 'weekly median',
  'analytics.weekly_up': '{pct} faster',
  'analytics.weekly_down': '{pct} slower',
  'analytics.weekly_flat': 'steady pace',
  'analytics.weekly_needs_more': 'Train {exercise} in another week to compare.',
  'analytics.weekly_no_week': 'no workout',

  'analytics.section.consistency': 'Pace consistency',
  'analytics.consistency_note': 'lower is steadier',
  'analytics.consistency_empty':
    'Needs sessions with at least two reps to measure pace variation.',

  'analytics.section.most': 'What shows up most',
  'analytics.empty.corrections': 'No corrections recorded — clean form across the saved sessions.',
  'analytics.section.framing': 'Framing',
  'analytics.empty.scene': 'No scene warnings. The camera saw you well in every session.',

  'analytics.trend.caindo': 'going down across sessions',
  'analytics.trend.subindo': 'going up across sessions',
  'analytics.trend.estavel': 'steady across sessions',
}
