// Namespace `report` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`. Tom de relatório: constata, não celebra (T-150).
import type { Report } from '../pt-BR/report'

export const report: Report = {
  'sheet.aria_label': 'Session report',

  'loading.title': 'Wrapping up your workout…',
  'loading.hint': 'Reps counted. Fetching the breakdown…',

  'error.title': 'Workout done',
  'error.hint':
    'I could not load the breakdown for this session. The count above comes from the server and is correct.',

  'reps_label': 'reps',
  'stat.rpm': 'reps/min',
  'stat.valid_time': 'valid time',
  'stat.time_to_target': 'time to target',
  'stat.mode': 'mode',

  'section.pace': 'Pace through the set',
  'section.improve': 'What to improve',
  'clean': 'No warnings in this set. Clean form.',
  'count_suffix': '{n}×',
  'window_label': '{s}s',
  'close': 'Close',

  'reason.completed': 'Set complete',
  'reason.timeout': 'Session ended at the time limit',
  'reason.aborted': 'You ended it early',
  'reason.no_data': 'Ended: we stopped seeing you on camera',
  'reason.target_reached': 'Target reached',
  'reason.unknown': 'Session ended',

  'set_of': 'set {n} of {total}',

  'fetch.failed': 'Could not fetch the report (HTTP {status}).',
}
