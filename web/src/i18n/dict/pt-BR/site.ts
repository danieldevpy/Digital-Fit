// Namespace `site` — a landing institucional e a tela Sobre (T-147, SPEC-025 Onda 2):
// `site/IndexScreen`, `AboutScreen`, `SiteBar`, `SiteApp`. Fonte da verdade do dicionário
// (SPEC-025 §3.1): o tipo `Site` sai DESTE arquivo, e `dict/en/site.ts` é tipado por ele.
//
// Chaves reaproveitadas entre `IndexScreen` e `AboutScreen` quando o texto É o mesmo na UI
// (o rodapé institucional aparece nas duas telas) — não é acidente, é a mesma frase.
export const site = {
  'nav.enter': 'Entrar',

  'brand.tagline': 'Seu treino. Sua evolução.',

  'hero.badge': 'Inteligência que te move',
  'hero.title_top': 'Treine melhor.',
  'hero.title_bottom': 'Evolua sempre.',
  'hero.copy':
    'O Digital Fit usa visão computacional para analisar seus movimentos em tempo real, contar repetições, corrigir sua execução e classificar o exercício.',
  'hero.image_alt': 'Pessoa treinando com esqueleto de análise neon',

  'feature.realtime.title': 'Análise em Tempo Real',
  'feature.realtime.text': 'Feedback instantâneo enquanto você se movimenta.',
  'feature.count.title': 'Conte Repetições',
  'feature.count.text': 'Contagem precisa de cada repetição ao longo da série.',
  'feature.correct.title': 'Corrija sua Execução',
  'feature.correct.text': 'Dicas visuais para melhorar sua postura e performance.',

  'cta.start': 'Começar Treino',
  'cta.how_it_works': 'Ver como funciona',

  // Mini-HUD decorativo do hero (`aria-hidden`) — números de amostra, mas o nome do
  // exercício e a legenda são texto de verdade.
  'mock.exercise_name': 'POLICHINELO',
  'mock.exercise_sub': 'Cardio • Corpo inteiro',

  'choose.kicker': 'Escolha seu exercício',
  'choose.subtitle_top': 'Treinos rápidos,',
  'choose.subtitle_em': 'resultados reais',

  'footer.tagline': 'Tecnologia de visão computacional para transformar sua forma de treinar.',
  'footer.heading.resources': 'Recursos',
  'footer.heading.about': 'Sobre',
  'footer.heading.support': 'Suporte',
  'footer.link.how_it_works': 'Como funciona',
  'footer.link.exercises': 'Exercícios',
  'footer.link.benefits': 'Benefícios',
  'footer.link.plans': 'Planos',
  'footer.link.who_we_are': 'Quem somos',
  'footer.link.privacy': 'Privacidade',
  'footer.link.terms': 'Termos de uso',
  'footer.link.contact': 'Contato',
  'footer.link.help_center': 'Central de ajuda',
  'footer.link.faq': 'FAQ',
  'footer.link.talk_to_us': 'Fale conosco',
  'footer.link.status': 'Status',
  'footer.copyright': '© 2025 Digital Fit. Todos os direitos reservados.',

  'about.title': 'Sobre o Digital Fit',
  'about.value.privacy.title': 'Privacidade em primeiro lugar',
  'about.value.privacy.text': 'Analisamos keypoints do seu corpo, não guardamos seu vídeo.',
  'about.value.levels.title': 'Para todos os níveis',
  'about.value.levels.text': 'Treinos rápidos e eficientes para iniciantes e avançados.',
  'about.value.evolution.title': 'Evolução constante',
  'about.value.evolution.text': 'Novos exercícios e recursos sendo adicionados sempre.',
  'about.coming_soon': 'Em breve',

  'bar.aria_label': 'Navegação do site',
  'bar.home': 'Início',
  'bar.about': 'Sobre',
  'bar.open_app': 'Abrir o app',
} as const

// `Record<keyof typeof site, string>`, não `typeof site` — mesmo motivo do `dict/pt-BR/shell.ts`:
// o contrato entre `pt-BR` e `en` é paridade de CHAVE, não igualdade de valor.
export type Site = Record<keyof typeof site, string>
