// Namespace `catalog` — tipado pelo `pt-BR` (SPEC-025 §3.1): chave faltando, sobrando ou
// renomeada aqui é erro de `tsc`, não bug descoberto em produção com o navegador em inglês.
//
// Tradução em tom de treinador (T-152), não literal — o `code.*` reusa o texto de
// `workers/analysis_worker/feedback/catalog.en.yaml` (T-144) de propósito: é o mesmo aviso dito
// pelo servidor quando há rede, e pelo embutido quando não há; ninguém deveria notar a troca.
import type { Catalog } from '../pt-BR/catalog'

export const catalog: Catalog = {
  'category.cardio': 'Cardio',
  'category.forca': 'Strength',
  'category.core': 'Core',
  'category.mobilidade': 'Mobility',

  'scene.padrao':
    'phone propped up vertically, about 2 meters away, your whole body in frame, with light coming from the front.',
  'scene.chao':
    'phone lying flat on the floor, on its side, about 2 meters away — the screen needs to see your whole body in profile, head to toe.',

  'exercise.jumping_jack.display_name': 'Jumping Jack',
  'exercise.jumping_jack.muscle_group': 'Full body',
  'exercise.jumping_jack.default_tip': 'Keep your core braced and your movements controlled.',
  'exercise.jumping_jack.guide_step.0':
    'Stand facing the camera, your whole body visible, arms at your sides.',
  'exercise.jumping_jack.guide_step.1':
    'Jump, spreading your legs and raising your arms overhead at the same time.',
  'exercise.jumping_jack.guide_step.2':
    'Return to the start on the next jump — each round trip counts one rep.',

  'exercise.squat.display_name': 'Squat',
  'exercise.squat.muscle_group': 'Legs and glutes',
  'exercise.squat.default_tip': 'Sit back with your weight on your heels and your chest up.',
  'exercise.squat.guide_step.0':
    'Feet shoulder-width apart, toes turned slightly out, arms forward for balance.',
  'exercise.squat.guide_step.1':
    'Lower by pushing your hips back, weight on your heels, until your thighs are parallel to the floor.',
  'exercise.squat.guide_step.2':
    'Stand back up by extending your legs without lifting your feet — a full stand-up counts the rep.',

  'exercise.flexao.display_name': 'Push-up',
  'exercise.flexao.muscle_group': 'Chest, shoulders and triceps',
  'exercise.flexao.default_tip': 'Keep your body in a straight line from head to heels, start to finish.',
  'exercise.flexao.guide_step.0':
    'Lay your phone on the floor, on its side, and stand sideways to it — it needs to see you from head to toe.',
  'exercise.flexao.guide_step.1':
    'Start in a plank: hands under your shoulders, arms extended, body in a straight line from head to heels.',
  'exercise.flexao.guide_step.2':
    'Lower by bending your elbows to about 90°, chest close to the floor, then push back up — the full push-up counts the rep.',

  'exercise.abdominal.display_name': 'Crunch',
  'exercise.abdominal.muscle_group': 'Abs',
  'exercise.abdominal.default_tip': 'Curl up slowly using your abs, without pulling on your neck.',
  'exercise.abdominal.guide_step.0':
    'Lay your phone on the floor, on its side, and lie down sideways to it — it needs to see your torso and knees.',
  'exercise.abdominal.guide_step.1':
    'Lie on your back with your knees bent and feet planted, heels close to your hips: the raised knee is the reference point for counting.',
  'exercise.abdominal.guide_step.2':
    'Curl up, lifting your shoulder blades off the floor while keeping your lower back down, then lower back slowly — the full lowering counts the rep.',

  'view.flexao.profile.label': 'From the side',
  'view.flexao.profile.short': 'Side',
  'view.flexao.profile.phone': 'phone lying on the floor',
  'view.flexao.profile.scene_tip':
    'phone lying flat on the floor, on its side, about 2 meters away — the screen needs to see your whole body in profile, head to toe.',
  'view.flexao.profile.guide_step.0':
    'Lay your phone on the floor, on its side, and stand sideways to it — it needs to see you from head to toe.',
  'view.flexao.profile.guide_step.1':
    'Start in a plank: hands under your shoulders, arms extended, body in a straight line from head to heels.',
  'view.flexao.profile.guide_step.2':
    'Lower by bending your elbows to about 90°, chest close to the floor, then push back up — the full push-up counts the rep.',

  'view.flexao.frontal.label': 'From the front',
  'view.flexao.frontal.short': 'Front',
  'view.flexao.frontal.phone': 'phone standing upright, in front of you',
  'view.flexao.frontal.scene_tip':
    'phone standing upright on the floor, in front of you, about 2 meters away — the screen needs to see your shoulders, elbows and hands. Your feet can be out of frame.',
  'view.flexao.frontal.guide_step.0':
    'Prop your phone upright on the floor and face it, with your head pointed toward the screen.',
  'view.flexao.frontal.guide_step.1':
    'Start in a plank: hands under your shoulders, arms extended, body in a straight line from head to heels.',
  'view.flexao.frontal.guide_step.2':
    "Lower by bending your elbows to about 90° and push back up — the full push-up counts the rep. From this view the app counts reps but can't correct your hip line.",

  'coach.title': 'Coach tip',

  'code.OUT_OF_FRAME': 'Get your whole body in frame',
  'code.TOO_FAR': 'Move in closer to the camera',
  'code.TOO_CLOSE': 'Back up from the camera',
  'code.ARMS_TOO_LOW': 'Reach your arms higher overhead',
  'code.LEGS_TOO_CLOSED': 'Widen your stance',
  'code.SQUAT_TOO_SHALLOW': 'Squat down deeper',
  'code.PUSHUP_TOO_SHALLOW': 'Lower deeper on the push-up',
  'code.HIPS_SAGGING': 'Brace your core',
  'code.HIPS_PIKED': 'Drop your hips down',
  'code.CRUNCH_TOO_SHALLOW': 'Curl up a little higher',
  'code.CRUNCH_TOO_FAST': 'Slow it down',
}
