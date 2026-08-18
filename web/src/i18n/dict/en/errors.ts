// Namespace `errors` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`. Falha de rede em inglês é curta e sem drama (T-151).
import type { Errors } from '../pt-BR/errors'

export const errors: Errors = {
  'api_down': 'API is down',
  'api_down_detail': 'API is down: {reason}',
  'login_failed': 'Could not sign you in.',
  'save_failed': 'Could not save.',
  'history_failed': 'Could not load your history.',
  'goal_save_failed': 'Could not save your goal.',
}
