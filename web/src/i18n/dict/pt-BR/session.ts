// Namespace `session` — o treino em si (T-149, SPEC-025 Onda 2): a capa e os avisos da câmera
// (`capture/CameraView`, `useCamera`, `useEdgePipeline`), o aquecimento do pipeline
// (`pose/assetWarmup`), a medição do corpo, os conselhos de cena (`scene/sceneQuality`), as
// recusas da admissão (`session/admission`, `useSession`), o CTA de dois degraus
// (`session/startGate`), o HUD (`hud/*`) e as duas telas de `screens/SessionScreen`
// (pré-configuração e treino ao vivo). Fonte da verdade do tipo (SPEC-025 §3.1): `Session` sai
// DESTE arquivo, e `dict/en/session.ts` é tipado por ele.
//
// **O que NÃO está aqui.** Nome e dica do exercício vêm do `catalog`/servidor; o card do
// treinador resolve o texto pelo `code` (T-144/T-152); o rótulo "estimado" do kcal é da T-150.
// E o chip de diagnóstico do `CameraView` (modo, fps, seq, delegate) continua em código cru,
// com `eslint-disable` explicando: é a mesma exclusão que a SPEC-025 §Escopo dá ao painel
// admin — ferramenta de operação, não superfície de quem treina.
export const session = {
  // --- Câmera: estado na capa e falhas de permissão ---
  'camera.status.idle': 'Câmera desligada',
  'camera.status.requesting': 'Pedindo permissão…',
  'camera.status.ready': 'Câmera pronta',
  'camera.status.denied': 'Permissão negada',
  'camera.status.error': 'Erro na câmera',
  'camera.waiting': 'Aguardando…',
  'camera.denied_detail': 'Permissão de câmera negada. Libere o acesso e tente de novo.',
  'camera.open_failed': 'Falha ao abrir a câmera.',
  'camera.video_failed': 'Falha ao abrir o vídeo.',
  // Troca frontal ⇄ traseira (SPEC-027 §A). O rótulo diz a câmera que está NO AR, não a
  // que o toque vai abrir: é o estado que a pessoa confere olhando a imagem.
  'camera.front': 'Frontal',
  'camera.rear': 'Traseira',
  'camera.single': 'Este aparelho tem só uma câmera.',
  'camera.switch_aria': 'Trocar de câmera. Agora: {current}.',
  // Botão de virar (SPEC-027 §F). O rótulo diz o que o toque VAI FAZER — a tela inteira já
  // mostra o estado. `locked` é o aviso que não deixa o botão fingir que resolveu tudo: com a
  // rotação travada o quadro da câmera não girou junto, e é a leitura do exercício que sofre.
  'orientation.to_landscape': 'Deitar a tela',
  'orientation.to_portrait': 'Levantar a tela',
  'orientation.aria': 'Alternar entre tela em pé e tela deitada',
  'orientation.locked': 'Rotação travada: o quadro da câmera não virou junto. Destrave o aparelho para o exercício ser lido certo.',

  // --- Aquecimento do pipeline (T-069): a janela em que o app baixa ~17 MB e a tela ficaria muda ---
  'warmup.title': 'Preparando a análise neste aparelho…',
  'warmup.downloading': 'Baixando o modelo de pose · {progress} (só na primeira vez)',
  'warmup.first_time': 'No primeiro acesso o modelo de pose é baixado; depois fica no aparelho.',
  'warmup.failed': 'Não foi possível preparar a análise de pose neste aparelho.',
  'warmup.measuring': 'Calibrando o dispositivo…',
  // O progresso do download. O número decimal sai do `formatNumber` (`i18n/format.ts`), não de
  // um `.replace('.', ',')` — era exatamente a armadilha do plano §2.6: separador de milhar e
  // de decimal escrito à mão fica preso em português mesmo com a tela inteira em inglês.
  'warmup.size_mb': '{done} MB',
  'warmup.progress': '{percent}% · {done} de {total} MB',
  'pipeline.start_failed': 'Falha ao iniciar o pipeline de pose.',
  // O detalhe (`{reason}`) é a mensagem crua da exceção — diagnóstico, e continua sem tradução
  // pelo mesmo motivo do `errors:api_down_detail`. O que a T-154 consertou aqui foi a MOLDURA:
  // ela era um template literal em português, fora de JSX, e por isso passou pelo
  // `no-literal-string` na T-149 sem ninguém ver (Descoberta `[T-149]`, o portão que faltava).
  'pipeline.start_failed_detail': 'Falha ao iniciar o pipeline de pose: {reason}',

  // --- Medição do corpo (SPEC-004) ---
  'calibrating.title': 'Fique em pé, parado',
  'calibrating.hint':
    'Braços ao lado do corpo e pés juntos. Estamos medindo você — a contagem começa em seguida.',

  // --- Conexão com o servidor ---
  'gateway.offline':
    'Sem conexão com o servidor — a contagem não vai avançar. Verifique sua internet e tente de novo.',
  'gateway.connecting': 'Conectando ao servidor…',
  'mode.cloud_banner': 'Modo cloud · a análise roda no servidor, sem esqueleto sobre a imagem.',

  // --- Conselhos de cena (T-085). A chave é o `SceneCode`, que é contrato; a frase é o valor. ---
  'scene.LUZ_FRACA': 'Está escuro · acenda uma luz',
  'scene.CONTRALUZ': 'A luz está atrás de você · vire-se',
  'scene.SEM_NITIDEZ': 'Imagem sem nitidez · limpe a lente',

  // --- Admissão (SPEC-009): as recusas que quem treina lê na tela. A falha de REDE não está
  // aqui: "API fora do ar" mora no namespace `errors` desde a T-151, numa cópia só. ---
  'admission.cloud_denied': 'Modo cloud indisponível agora — tente em modo edge.',
  'admission.ticket_incomplete': 'Ticket de sessão incompleto (sem ws_url).',
  'admission.no_redis': 'Servidor sem Redis — sessão não pode ser aberta.',
  'admission.http_failure': 'Falha ao abrir a sessão (HTTP {status}).',
  'admission.open_failed': 'Falha ao abrir a sessão.',

  // --- CTA de dois degraus (`session/startGate.ts`) ---
  'cta.start_exercise': 'Iniciar Exercício',
  'cta.opening_camera': 'Abrindo câmera…',
  // A mesma frase serve ao CTA e ao botão da capa da câmera — é o mesmo ato, e são duas
  // superfícies do mesmo degrau. Chave única de propósito: divergirem seria um bug de produto.
  'cta.turn_on_camera': 'Ligar câmera',

  // --- Preparação antes de contar (T-049) ---
  'countdown.label': 'Preparação',
  // `.zero` é o balde OPCIONAL do `resolveFromTable` (T-142): zero não é "0s de preparação", é
  // "sem preparação" — e é o `Intl.PluralRules` que continua mandando no resto.
  'countdown.value.zero': 'sem preparação',
  'countdown.value': '{n}s de preparação',
  'countdown.short.zero': 'Off',
  'countdown.short': '{n}s',
  'countdown.aria': 'Preparação antes de contar: {value}. Tocar para mudar.',

  // --- Zoom ---
  'zoom.label': 'Zoom',
  'zoom.hint': 'Arraste para menos e caiba mais perto da câmera.',
  // `{hint}` recebe a própria `zoom.hint`: o leitor de tela ouve exatamente a frase que está
  // escrita embaixo do slider, e não uma segunda redação que envelheceria sozinha.
  'zoom.aria': 'Zoom da câmera: {value}. {hint}',

  // --- "3, 2, 1" entre o corpo medido e a contagem valer (`hud/GetReady`) ---
  'getready.eyebrow.prepare': 'prepare-se',
  'getready.eyebrow.go': 'valendo',
  'getready.go': 'VAI!',
  // Quebrada em dois porque o nome do exercício e o "VAI!" aparecem em `<strong>` no meio da
  // frase — mesma solução do `view.why.*` da T-148: negrito no markup, frase no dicionário.
  'getready.hint_lead': 'Fique parado. Comece o',
  'getready.hint_mid': 'quando aparecer',

  // --- Rótulos de métrica, compartilhados entre a pré-config, o HUD ao vivo e a StatsBar ---
  'label.exercise': 'Exercício',
  'label.series': 'Série',
  'label.reps': 'Repetições',
  'label.angle': 'Ângulo',
  'label.duration': 'Duração',
  'label.kcal_short': 'Kcal',
  // A unidade escrita, ao lado do número. Igual nas duas línguas hoje — e no dicionário assim
  // mesmo, pelo mesmo motivo do `30s` da T-148: unidade é texto, não número.
  'label.kcal_unit': 'kcal',
  'label.calories': 'Calorias',
  'label.calories_estimated': 'Calorias estimadas',
  // O aviso de que o número saiu de um peso presumido (SPEC-016 critério 3). Mora no `session`
  // e não no `progress` porque quem o desenha é o card de kcal do treino ao vivo — a chave
  // segue a TELA, não o arquivo que a calcula (`session/kcal.ts`, escopo da T-150).
  'label.estimated': 'estimado',

  // --- Card do treinador (`hud/CoachTip`) ---
  'coach.details': 'Ver detalhes',
  'coach.hide': 'Ocultar',
  'coach.no_details': 'Sem detalhes para esta dica',

  // --- Relógio da sessão ---
  'timer.remaining': 'Tempo restante',

  // --- Pré-configuração ---
  'prep.title': 'Pré-configuração',
  'prep.subtitle': 'Vamos preparar seu treino',
  'prep.see_example': 'ver exemplo',
  'prep.mirror': 'Espelhar',
  'prep.duration_soon': 'Duração configurável: em breve',
  'prep.pill_aligned': 'Você já está visível · alinhe-se à guia',
  'prep.pill_turn_on': 'Ligue a câmera para se enquadrar',
  // Conselho de orientação (SPEC-027 §E). Divide o pill com o aviso de cena da T-085 e
  // herda a regra dele: orienta, nunca bloqueia — o CTA não muda.
  'prep.advice_portrait': 'Este exercício rende mais com o celular em pé.',
  'prep.advice_landscape': 'Este exercício rende mais com o celular deitado.',
  'prep.frame_check': 'Quadro cheio',
  'prep.frame_check_aria': 'Ver o quadro inteiro da câmera',
  'prep.frame_check_exit': 'Toque para voltar aos ajustes',
  'stepper.decrease': 'Diminuir {label}',
  'stepper.increase': 'Aumentar {label}',

  // --- Treino ao vivo ---
  'live.title': 'Treino ao Vivo',
  'live.subtitle': '{exercise} • Série 1/{total}',
  'live.stop_aria': 'Encerrar treino',
  'live.start_aria': 'Iniciar treino',
} as const

// `Record<keyof typeof session, string>`, não `typeof session` — o contrato entre `pt-BR` e
// `en` é paridade de CHAVE, não igualdade de valor (ver `dict/pt-BR/shell.ts`).
export type Session = Record<keyof typeof session, string>
