// Namespace `funnel` — o caminho da SPEC-015 do lado do APP: Escolha (`screens/ChooseScreen`,
// `ExerciseRails`), Guia (`screens/GuideScreen`), a escolha de variação de câmera
// (`ui/ViewPicker`, `hud/ViewConfirm`) e os dois seletores que sobraram do funil antigo
// (`hud/ExercisePicker`, `ui/ExerciseDemo`). Fonte da verdade do tipo (SPEC-025 §3.1): `Funnel`
// sai DESTE arquivo, e `dict/en/funnel.ts` é tipado por ele.
//
// **O que está aqui é a MOLDURA; o conteúdo do exercício não.** Nome, grupo muscular, passos do
// guia, instrução de cena e rótulo de variação vêm do catálogo (`catalog:`, T-152) ou do
// servidor (T-146) — esta tela só os desenha. É por isso que `guide.demo_alt` interpola
// `{exercise}` em vez de guardar o nome: o nome não é desta camada.
//
// **Frases repetidas com o namespace `site` são repetição de propósito.** "Escolha seu
// exercício" existe nas duas (`site:choose.kicker` na vitrine, `funnel:choose.title` no app) e
// são superfícies diferentes, de bundles diferentes, que podem divergir sem que uma esteja
// errada — compartilhar a chave amarraria a landing à tela de treino por acidente de tradução.
export const funnel = {
  // --- Escolha (ChooseScreen) ---
  'choose.title': 'Escolha seu exercício',
  'choose.subtitle_top': 'Treinos rápidos,',
  'choose.subtitle_em': 'resultados reais',

  // --- Faixas por categoria (ExerciseRails) ---
  'rail.see_all': 'ver todos',
  'rail.collapse': 'recolher',
  // `{category}` é o rótulo já traduzido do grupo (`catalog:category.*`).
  'rail.track_aria': 'Exercícios de {category}',

  // Duração da sessão (SPEC-009) no selo do card, no site e no app. Fica no dicionário e não
  // solto no JSX porque a unidade é escrita, não só número: "30s" e "30 sec" são a mesma
  // sessão em duas línguas.
  'card.duration': '30s',

  // --- Demo visual (ExerciseDemo) ---
  'demo.alt': 'Demonstração: {exercise}',

  // --- Seletor rápido na capa da câmera (ExercisePicker) ---
  'picker.aria_label': 'Exercício',

  // --- Guia (GuideScreen) ---
  'guide.kicker': 'Exemplo guiado',
  'guide.demo_alt': 'Demonstração do exercício {exercise}',
  'guide.scene_label': 'Prepare a cena:',
  'guide.cta': 'Entendi, vamos lá',
  'guide.skip': 'Pular exemplo',

  // --- Escolha da variação de câmera (ViewPicker) ---
  'view.label': 'De que lado fica a câmera?',
  'view.label_compact': 'Câmera',
  'view.group_aria': 'Posição da câmera',
  // A frase do "por quê" é quebrada em pedaços porque o `<strong>` está DENTRO dela e o termo
  // em negrito é o rótulo da vista ("De lado"/"de frente"). Uma chave só com HTML embutido
  // exigiria `dangerouslySetInnerHTML`; um `<strong>` com literal solto no JSX seria
  // exatamente o que o `no-literal-string` desta task veio proibir. Os pares
  // `<vista>_term` + `<vista>_text` mantêm o negrito no markup e a frase no dicionário.
  'view.why.lead': 'As duas contam suas repetições.',
  'view.why.profile_term': 'De lado',
  'view.why.profile_text': 'o app também avisa se o quadril cair ou empinar;',
  'view.why.frontal_term': 'de frente',
  'view.why.frontal_text':
    'ele conta, mas não corrige a linha do corpo — a câmera não enxerga seus pés desse ângulo.',

  // --- Trava de confirmação da variação (ViewConfirm, T-112) ---
  'vgate.kicker': 'Antes de ligar a câmera',
  'vgate.title': 'Onde você vai colocar o celular?',
  // Mesma quebra do `view.why.*`, e o `_tail` existe por causa dela: em pt-BR e en a frase
  // termina logo depois do negrito, mas quem traduzir para uma língua que não termina a
  // oração aí tem onde pôr o resto, sem precisar de chave nova.
  'vgate.why_lead':
    'As duas contam suas repetições — mas cada uma precisa do celular num lugar diferente. Com a câmera na posição errada, o treino pode terminar com',
  'vgate.why_term': 'zero',
  'vgate.why_tail': '.',
  'vgate.dont_show': 'Não mostrar novamente',
  // `{card}` é o rótulo do card compacto (`view.label_compact`), interpolado em vez de escrito
  // à mão: a dica manda a pessoa procurar um card pelo nome, e um nome que não bate com o que
  // está na coluna é pior que dica nenhuma.
  'vgate.dont_show_hint': 'você continua trocando pelo card “{card}”, na coluna da esquerda',
  'vgate.back': 'Voltar',
  'vgate.confirm': 'Confirmar e ligar câmera',
} as const

// `Record<keyof typeof funnel, string>`, não `typeof funnel` — mesmo raciocínio de
// `dict/pt-BR/shell.ts`: o contrato entre `pt-BR` e `en` é paridade de CHAVE, não igualdade de
// valor.
export type Funnel = Record<keyof typeof funnel, string>
