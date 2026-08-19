// Namespace `site` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`. Tom de produto, não tradução literal (T-147) — o inglês
// tem de soar escrito em inglês, não traduzido de outra língua.
import type { Site } from '../pt-BR/site'

export const site: Site = {
  'meta.index.title': 'Digital Fit — Train smarter. Keep evolving.',
  'meta.index.description':
    'Digital Fit uses computer vision to analyze your movements in real time, count your reps, and correct your form.',
  'meta.about.title': 'About Digital Fit — computer vision for better training',
  'meta.about.description':
    'Privacy first, workouts for every level, and constant evolution: what Digital Fit is and how it reads your movement.',
  // Página por exercício (T-165). Não é tradução literal do português: em inglês a busca real é
  // "how to do X properly" / "X form", e o título precisa bater com a frase que a pessoa digita.
  'meta.exercise.title': 'How to do a {nome} correctly — Digital Fit',
  'meta.exercise.description':
    'Learn proper {nome} form step by step, then train with your phone camera counting your reps and correcting your posture in real time.',
  'meta.not_found.title': 'Page not found — Digital Fit',
  'meta.not_found.description': 'The address you asked for does not exist on Digital Fit.',

  'meta.og_image_alt': 'The Digital Fit wordmark beside a neon violet keypoint figure',

  'hint.text': 'This page is also available in English.',
  'hint.cta': 'View in English',
  'hint.dismiss': 'Dismiss',

  'not_found.title': 'This page does not exist',
  'not_found.text': 'The address you opened is not live. The link may be an old one.',
  'not_found.home': 'Go to the home page',

  'exercise.muscles': 'Muscles worked',
  'exercise.how_to': 'How to do it',
  'exercise.step': 'Step {n}',
  'exercise.coach_tip': 'Coach tip',
  'exercise.scene_tip': 'Where to put your phone',
  'exercise.scene_tip_default':
    'Standing up, phone upright, about 2 meters away, with your whole body in frame.',
  'exercise.cta': 'Train {nome} now',
  'exercise.cta_note': 'Free, right in your browser — nothing to install.',
  'exercise.others': 'Other exercises',
  'exercise.how_it_works_title': 'How Digital Fit counts and corrects',
  'exercise.how_it_works_text':
    'Your phone camera tracks 33 points on your body and Digital Fit reads the movement from them — the video never leaves your device and is never recorded.',

  'nav.enter': 'Log in',

  'brand.tagline': 'Your workout. Your evolution.',

  'hero.badge': 'Intelligence that moves you',
  'hero.title_top': 'Train smarter.',
  'hero.title_bottom': 'Keep evolving.',
  'hero.copy':
    'Digital Fit uses computer vision to analyze your movements in real time — counting reps, correcting your form, and identifying the exercise you’re doing.',
  'hero.image_alt': 'Person working out with a neon pose-analysis overlay',

  'feature.realtime.title': 'Real-Time Analysis',
  'feature.realtime.text': 'Instant feedback as you move.',
  'feature.count.title': 'Count Every Rep',
  'feature.count.text': 'Precise rep counting through the whole set.',
  'feature.correct.title': 'Fix Your Form',
  'feature.correct.text': 'Visual cues to improve your posture and performance.',

  'cta.start': 'Start Training',
  'cta.how_it_works': 'See how it works',

  'mock.exercise_name': 'JUMPING JACKS',
  'mock.exercise_sub': 'Cardio • Full body',

  'choose.kicker': 'Choose your exercise',
  'choose.subtitle_top': 'Quick workouts,',
  'choose.subtitle_em': 'real results',

  'footer.tagline': 'Computer vision technology that transforms the way you train.',
  'footer.heading.resources': 'Resources',
  'footer.heading.about': 'About',
  'footer.heading.support': 'Support',
  'footer.link.how_it_works': 'How it works',
  'footer.link.exercises': 'Exercises',
  'footer.link.benefits': 'Benefits',
  'footer.link.plans': 'Plans',
  'footer.link.who_we_are': 'About us',
  'footer.link.privacy': 'Privacy',
  'footer.link.terms': 'Terms of use',
  'footer.link.contact': 'Contact',
  'footer.link.help_center': 'Help center',
  'footer.link.faq': 'FAQ',
  'footer.link.talk_to_us': 'Talk to us',
  'footer.link.status': 'Status',
  'footer.copyright': '© 2025 Digital Fit. All rights reserved.',

  'about.title': 'About Digital Fit',
  'about.value.privacy.title': 'Privacy first',
  'about.value.privacy.text': 'We analyze your body’s keypoints — we never store your video.',
  'about.value.levels.title': 'For every level',
  'about.value.levels.text': 'Quick, effective workouts for beginners and advanced athletes alike.',
  'about.value.evolution.title': 'Always evolving',
  'about.value.evolution.text': 'New exercises and features, added all the time.',
  'about.coming_soon': 'Coming soon',

  'bar.aria_label': 'Site navigation',
  'bar.home': 'Home',
  'bar.about': 'About',
  'bar.open_app': 'Open the app',
}
