// Namespace `funnel` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`. Tom de treinador, não tradução literal (T-148) — a frase que
// diz onde pôr o celular tem de soar como instrução de quem já montou a cena, não como legenda.
//
// Os termos em negrito de `view.why.*` repetem os rótulos de vista de `dict/en/catalog.ts`
// ("From the side" / "From the front") de propósito: a frase manda comparar as duas opções que
// estão logo acima, na tela, com esses mesmos nomes.
import type { Funnel } from '../pt-BR/funnel'

export const funnel: Funnel = {
  'choose.title': 'Choose your exercise',
  'choose.subtitle_top': 'Quick workouts,',
  'choose.subtitle_em': 'real results',

  'rail.see_all': 'see all',
  'rail.collapse': 'collapse',
  'rail.track_aria': '{category} exercises',

  'card.duration': '30s',

  'demo.alt': 'Demo: {exercise}',

  'picker.aria_label': 'Exercise',

  'guide.kicker': 'Guided example',
  'guide.demo_alt': '{exercise} demonstration',
  'guide.scene_label': 'Set up your scene:',
  'guide.cta': 'Got it, let’s go',
  'guide.skip': 'Skip the example',

  'view.label': 'Which side is the camera on?',
  'view.label_compact': 'Camera',
  'view.group_aria': 'Camera position',
  'view.why.lead': 'Both count your reps.',
  'view.why.profile_term': 'From the side',
  'view.why.profile_text': 'the app also warns you when your hips sag or pike;',
  'view.why.frontal_term': 'from the front',
  'view.why.frontal_text':
    'it counts, but it can’t correct your body line — the camera can’t see your feet from that angle.',

  'vgate.kicker': 'Before you turn the camera on',
  'vgate.title': 'Where are you putting your phone?',
  'vgate.why_lead':
    'Both count your reps — but each one needs the phone somewhere different. With the camera in the wrong spot, your workout can end at',
  'vgate.why_term': 'zero',
  'vgate.why_tail': '.',
  'vgate.dont_show': 'Don’t show this again',
  'vgate.dont_show_hint': 'you can still switch it on the “{card}” card, in the left column',
  'vgate.back': 'Back',
  'vgate.confirm': 'Confirm and turn on camera',
}
