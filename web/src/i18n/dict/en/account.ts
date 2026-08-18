// Namespace `account` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`. Tom de conta: direto e sem burocracia (T-151).
//
// Os baldes `.one`/`.other` existem nos dois idiomas com a mesma chave e regras próprias — quem
// escolhe é o `Intl.PluralRules` do locale, nunca um `if` no componente.
import type { Account } from '../pt-BR/account'

export const account: Account = {
  'action.create_account': 'Create account',
  'action.login': 'Log in',
  'action.have_account': 'I already have an account',
  'action.create_one': 'Create an account',
  'action.close': 'Close',
  'action.not_now': 'Not now',

  'sheet.aria_label': 'Your account',
  'field.name': 'Name (optional)',
  'field.email': 'Email',
  'field.password': 'Password',
  'submit.busy': 'One moment…',
  'greeting': 'Hi, {name}',

  'stored.suffix.one': 'workout saved',
  'stored.suffix.other': 'workouts saved',
  'stored.tail': 'on this device — clearing your browser takes them away. With an account, they stay.',

  'plan.remaining': '{n} left',
  'quota.exhausted_title': 'You trained a lot today 🎉',
  'quota.last_title': 'Last session of the day',
  'quota.last_anon': '1 free session left today. With an account, you get more.',
  'quota.last_account': '1 session left today. With a subscription, it never runs out.',
  'quota.count': '{used} of {limit} sessions today',
  'quota.renew': 'Renews at {time}',
  'quota.renew_tomorrow': 'Renews tomorrow at {time}',
  'quota.upsell_soon': 'Subscription coming soon — and then the limit goes away.',

  'date.today': 'today {time}',
  'date.yesterday': 'yesterday {time}',
  'date.other': '{date} {time}',

  'totals.sessions': 'sessions',
  'totals.reps': 'reps',
  'totals.best_rpm': 'best reps/min',
  'history.title': 'History',
  'history.loading': 'Loading…',
  'history.load_failed': 'Could not load your history right now.',
  'history.local': 'Showing what is saved on this device.',
  'history.stale': 'Could not refresh just now — something recent may be missing.',
  'history.empty': 'No sessions yet. Tap the middle button to train for 30 seconds.',
  'history.item_reps': '{n} reps',

  'logout.ask': 'Log out on this device?',
  'logout.cancel': 'Cancel',
  'logout.confirm': 'Log out',

  'fire.aria': '{days}, {goal}{where}',
  'fire.aria_pending': 'Streak still loading',
  'fire.days.one': '{n} day in a row',
  'fire.days.other': '{n} days in a row',
  'fire.aria_goal': 'daily goal {done} of {target}',
  'fire.aria_local': ', saved on this device only',
  'fire.ghost_title': 'On this device only',

  'xp.total': '+{n} XP',
  'xp.part': '+{n}',
  'xp.session': 'session',
  'xp.reps': 'reps',
  'xp.clean': 'clean',

  'eng.section_aria': 'Open the consistency panel',
  'eng.sheet_aria': 'Your engagement',
  'eng.title': 'Your consistency',
  'eng.streak': 'streak',
  'eng.best': 'best',
  'eng.xp': 'XP',
  'eng.level': 'level',
  'eng.days.one': 'day in a row',
  'eng.days.other': 'days in a row',
  'eng.best_label': 'Best streak:',
  'eng.ghost_title': 'Your streak lives on this device only',
  'eng.ghost_text':
    'Clearing your browser takes your streak away. An account keeps what you have trained — and it is free.',
  'eng.cal_day': '{n}',
  'eng.cal_day_active': '{n}, trained',
  'eng.days_trained.one': 'day trained this month',
  'eng.days_trained.other': 'days trained this month',
  'eng.goal_today': 'Today’s goal',
  'eng.protections': 'Streak protections used this month:',
  'eng.protections_count': '{used} of {total}',
  'eng.goal_label': 'Daily goal',
  'eng.goal.casual': 'Casual',
  'eng.goal.regular': 'Regular',
  'eng.goal.intenso': 'Intense',
  'eng.sessions.one': 'session',
  'eng.sessions.other': 'sessions',

  'ach.title': 'Achievements',
  'ach.earned': 'earned',
  'ach.locked': 'locked',
  'ach.toast_title': 'New achievement',
  'ach.toast_close_aria': 'Dismiss notice',
}
