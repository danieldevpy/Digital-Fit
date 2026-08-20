// Namespace `session` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`. Tom de treinador, não tradução literal (T-149): o que a
// pessoa lê durante o treino é instrução, e instrução em inglês é curta e direta.
import type { Session } from '../pt-BR/session'

export const session: Session = {
  'camera.status.idle': 'Camera off',
  'camera.status.requesting': 'Asking for permission…',
  'camera.status.ready': 'Camera ready',
  'camera.status.denied': 'Permission denied',
  'camera.status.error': 'Camera error',
  'camera.waiting': 'Waiting…',
  'camera.denied_detail': 'Camera permission denied. Allow access and try again.',
  'camera.open_failed': 'Could not open the camera.',
  'camera.video_failed': 'Could not open the video.',
  'camera.front': 'Front',
  'camera.rear': 'Rear',
  'camera.single': 'This device has only one camera.',
  'camera.switch_aria': 'Switch camera. Currently: {current}.',
  'orientation.to_landscape': 'Lay screen down',
  'orientation.to_portrait': 'Stand screen up',
  'orientation.aria': 'Switch between upright and sideways screen',
  'orientation.locked': 'Rotation locked: the camera frame did not turn with you. Unlock the device so the exercise reads correctly.',

  'warmup.title': 'Getting the analysis ready on this device…',
  'warmup.downloading': 'Downloading the pose model · {progress} (first time only)',
  'warmup.first_time':
    'The pose model is downloaded on your first visit; after that it stays on your device.',
  'warmup.failed': 'This device could not get the pose analysis ready.',
  'warmup.measuring': 'Calibrating your device…',
  'warmup.size_mb': '{done} MB',
  'warmup.progress': '{percent}% · {done} of {total} MB',
  'pipeline.start_failed': 'Could not start the pose pipeline.',
  'pipeline.start_failed_detail': 'Could not start the pose pipeline: {reason}',

  'calibrating.title': 'Stand still',
  'calibrating.hint':
    'Arms at your sides and feet together. We’re measuring you — counting starts right after.',

  'gateway.offline':
    'No connection to the server — the count won’t move. Check your internet and try again.',
  'gateway.connecting': 'Connecting to the server…',
  'mode.cloud_banner': 'Cloud mode · the analysis runs on the server, with no skeleton over the image.',

  'scene.LUZ_FRACA': 'It’s dark · turn on a light',
  'scene.CONTRALUZ': 'The light is behind you · turn around',
  'scene.SEM_NITIDEZ': 'Blurry image · clean the lens',

  'admission.cloud_denied': 'Cloud mode is unavailable right now — try edge mode.',
  'admission.ticket_incomplete': 'Incomplete session ticket (no ws_url).',
  'admission.no_redis': 'Server without Redis — the session cannot be opened.',
  'admission.http_failure': 'Could not open the session (HTTP {status}).',
  'admission.open_failed': 'Could not open the session.',

  'cta.start_exercise': 'Start Exercise',
  'cta.opening_camera': 'Opening camera…',
  'cta.turn_on_camera': 'Turn on camera',

  'countdown.label': 'Get ready',
  'countdown.value.zero': 'no countdown',
  'countdown.value': '{n}s countdown',
  'countdown.short.zero': 'Off',
  'countdown.short': '{n}s',
  'countdown.aria': 'Countdown before counting starts: {value}. Tap to change.',

  'zoom.label': 'Zoom',
  'zoom.hint': 'Drag down to fit closer to the camera.',
  'zoom.aria': 'Camera zoom: {value}. {hint}',

  'getready.eyebrow.prepare': 'get ready',
  'getready.eyebrow.go': 'live',
  'getready.go': 'GO!',
  'getready.hint_lead': 'Stay still. Start your',
  'getready.hint_mid': 'when you see',

  'label.exercise': 'Exercise',
  'label.series': 'Set',
  'label.reps': 'Reps',
  'label.angle': 'Angle',
  'label.duration': 'Duration',
  'label.kcal_short': 'Kcal',
  'label.kcal_unit': 'kcal',
  'label.calories': 'Calories',
  'label.calories_estimated': 'Estimated calories',
  'label.estimated': 'estimated',

  'coach.details': 'See details',
  'coach.hide': 'Hide',
  'coach.no_details': 'No details for this tip',

  'timer.remaining': 'Time left',

  'prep.title': 'Setup',
  'prep.subtitle': 'Let’s set up your workout',
  'prep.see_example': 'see example',
  'prep.mirror': 'Mirror',
  'prep.duration_soon': 'Configurable duration: coming soon',
  'prep.pill_aligned': 'You’re in frame · line up with the guide',
  'prep.pill_turn_on': 'Turn on the camera to frame yourself',
  'prep.advice_portrait': 'This exercise works better with the phone upright.',
  'prep.advice_landscape': 'This exercise works better with the phone sideways.',
  'prep.frame_check': 'Full frame',
  'prep.frame_check_aria': 'See the camera’s full frame',
  'prep.frame_check_exit': 'Tap to go back to the settings',
  'stepper.decrease': 'Decrease {label}',
  'stepper.increase': 'Increase {label}',

  'live.title': 'Live Workout',
  'live.subtitle': '{exercise} • Set 1/{total}',
  'live.stop_aria': 'End workout',
  'live.start_aria': 'Start workout',
}
