// Namespace `catalog` (T-152, SPEC-025 §Escopo/Onda 2) — o catálogo EMBUTIDO de exercícios
// (`session/catalog.ts`, o fallback offline), as variações de câmera (`session/exerciseViews.ts`)
// e o mapa código→frase do card do treinador (`session/coachCard.ts`, herdado da T-144: ver o
// docstring de `CODE_MESSAGES` lá — este embutido é tudo o que existe sem rede).
//
// Fonte da verdade do tipo (SPEC-025 §3.1): `Catalog` sai DESTE arquivo; `dict/en/catalog.ts` é
// tipado por ele.
//
// O que NÃO está aqui, de propósito: o slug (`cardio`, `flexao`, `profile`, `OUT_OF_FRAME`...) é
// vocabulário de CONTRATO — conquistas, admissão e o worker leem o slug, nunca o rótulo — e
// continua vivendo no código, igual `Category` já guarda `forca` e não `"Força"`. Só o TEXTO que
// a pessoa lê mora aqui.
export const catalog = {
  // Categoria (SPEC-020 §Categorias) — o slug é o contrato, o rótulo é este.
  'category.cardio': 'Cardio',
  'category.forca': 'Força',
  'category.core': 'Core',
  'category.mobilidade': 'Mobilidade',

  // Instrução de cena padrão (todo exercício em pé) e a de chão (T-106/T-107).
  'scene.padrao':
    'celular apoiado na vertical, uns 2 metros de distância, corpo inteiro no quadro e luz vindo de frente.',
  'scene.chao':
    'celular deitado no chão, de lado, a uns 2 metros — a tela precisa ver seu corpo inteiro de perfil, da cabeça aos pés.',

  // O catálogo embutido — quatro exercícios `validado` (T-113).
  'exercise.jumping_jack.display_name': 'Polichinelo',
  'exercise.jumping_jack.muscle_group': 'Corpo inteiro',
  'exercise.jumping_jack.default_tip': 'Mantenha o core contraído e movimentos controlados.',
  'exercise.jumping_jack.guide_step.0':
    'Fique em pé, de frente para a câmera, corpo inteiro visível, braços ao lado do corpo.',
  'exercise.jumping_jack.guide_step.1':
    'Salte abrindo as pernas e levando os braços acima da cabeça, ao mesmo tempo.',
  'exercise.jumping_jack.guide_step.2':
    'Volte à posição inicial no salto seguinte — cada ida e volta conta uma repetição.',

  'exercise.squat.display_name': 'Agachamento',
  'exercise.squat.muscle_group': 'Pernas e glúteos',
  'exercise.squat.default_tip': 'Desça com o peso nos calcanhares e o peito aberto.',
  'exercise.squat.guide_step.0':
    'Pés na largura dos ombros, pontas levemente para fora, braços à frente para equilibrar.',
  'exercise.squat.guide_step.1':
    'Desça empurrando o quadril para trás, peso nos calcanhares, até as coxas ficarem paralelas ao chão.',
  'exercise.squat.guide_step.2':
    'Suba estendendo as pernas sem tirar os pés do chão — subida completa conta a repetição.',

  'exercise.flexao.display_name': 'Flexão de braço',
  'exercise.flexao.muscle_group': 'Peito, ombro e tríceps',
  'exercise.flexao.default_tip': 'Corpo numa linha reta da cabeça aos pés, do começo ao fim.',
  'exercise.flexao.guide_step.0':
    'Deite o celular no chão, de lado, e fique de perfil para ele — ele precisa ver você da cabeça aos pés.',
  'exercise.flexao.guide_step.1':
    'Comece na prancha: mãos abaixo dos ombros, braço estendido, corpo numa linha reta da cabeça aos calcanhares.',
  'exercise.flexao.guide_step.2':
    'Desça dobrando o cotovelo até uns 90°, com o peito perto do chão, e suba estendendo o braço — a subida completa conta a repetição.',

  'exercise.abdominal.display_name': 'Abdominal',
  'exercise.abdominal.muscle_group': 'Abdômen',
  'exercise.abdominal.default_tip': 'Suba com o abdômen, devagar, sem puxar o pescoço.',
  'exercise.abdominal.guide_step.0':
    'Deite o celular no chão, de lado, e deite-se de perfil para ele — ele precisa ver seu tronco e seus joelhos.',
  'exercise.abdominal.guide_step.1':
    'Deite de costas com os joelhos dobrados e os pés apoiados, calcanhar perto do quadril: é o joelho levantado que serve de referência para a contagem.',
  'exercise.abdominal.guide_step.2':
    'Suba encolhendo o abdômen até as escápulas saírem do chão, mantendo a lombar apoiada, e volte devagar — a descida completa conta a repetição.',

  // Variações de câmera da flexão (T-111) — a primeira é o default.
  'view.flexao.profile.label': 'De lado',
  'view.flexao.profile.short': 'Lado',
  'view.flexao.profile.phone': 'celular deitado no chão',
  'view.flexao.profile.scene_tip':
    'celular deitado no chão, de lado, a uns 2 metros — a tela precisa ver seu corpo inteiro de perfil, da cabeça aos pés.',
  'view.flexao.profile.guide_step.0':
    'Deite o celular no chão, de lado, e fique de perfil para ele — ele precisa ver você da cabeça aos pés.',
  'view.flexao.profile.guide_step.1':
    'Comece na prancha: mãos abaixo dos ombros, braço estendido, corpo numa linha reta da cabeça aos calcanhares.',
  'view.flexao.profile.guide_step.2':
    'Desça dobrando o cotovelo até uns 90°, com o peito perto do chão, e suba estendendo o braço — a subida completa conta a repetição.',

  'view.flexao.frontal.label': 'De frente',
  'view.flexao.frontal.short': 'Frente',
  'view.flexao.frontal.phone': 'celular em pé, à sua frente',
  'view.flexao.frontal.scene_tip':
    'celular em pé no chão, à sua frente, a uns 2 metros — a tela precisa ver seus ombros, cotovelos e mãos. Os pés podem ficar fora do quadro.',
  'view.flexao.frontal.guide_step.0':
    'Apoie o celular em pé no chão e fique de frente para ele, com a cabeça na direção da tela.',
  'view.flexao.frontal.guide_step.1':
    'Comece na prancha: mãos abaixo dos ombros, braço estendido, corpo numa linha reta da cabeça aos calcanhares.',
  'view.flexao.frontal.guide_step.2':
    'Desça dobrando o cotovelo até uns 90° e suba estendendo o braço — a subida completa conta a repetição. Desta vista o app conta, mas não corrige a linha do quadril.',

  // Card do treinador (herança da T-144 — ver `session/coachCard.ts`).
  'coach.title': 'Dica do treinador',

  // Feedback embutido, mesmo tom do `catalog.pt-BR.yaml` do worker (T-144) — é o fallback do
  // fallback: sem rede, sem catálogo do servidor, é este mapa que fala.
  'code.OUT_OF_FRAME': 'Apareça inteiro no quadro',
  'code.TOO_FAR': 'Aproxime-se da câmera',
  'code.TOO_CLOSE': 'Afaste-se da câmera',
  'code.ARMS_TOO_LOW': 'Estenda mais os braços acima da cabeça',
  'code.LEGS_TOO_CLOSED': 'Abra mais as pernas',
  'code.SQUAT_TOO_SHALLOW': 'Desça mais no agachamento',
  'code.PUSHUP_TOO_SHALLOW': 'Desça mais na flexão',
  'code.HIPS_SAGGING': 'Contraia o abdômen',
  'code.HIPS_PIKED': 'Abaixe o quadril',
  'code.CRUNCH_TOO_SHALLOW': 'Suba um pouco mais',
  'code.CRUNCH_TOO_FAST': 'Mais devagar',
} as const

// `Record<keyof typeof catalog, string>`, não `typeof catalog` — mesmo raciocínio de
// `dict/pt-BR/shell.ts`: o contrato entre `pt-BR` e `en` é paridade de CHAVE, não igualdade de
// valor.
export type Catalog = Record<keyof typeof catalog, string>
