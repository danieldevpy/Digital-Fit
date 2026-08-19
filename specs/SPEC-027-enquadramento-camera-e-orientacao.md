# SPEC-027 — Enquadramento: câmera e orientação
Status: draft | Camada: client (web/) + contrato | Depende de: SPEC-001, SPEC-003, SPEC-014 | Referência: conversa de 2026-08-19 (Daniel: "um amigo pode querer gravar o outro" + "quando o usuário deixa o celular deitado a UI fica estranha")

## Entidade e responsabilidade

Decide e lembra **de que lado e de que jeito o celular olha**: qual câmera (frontal ou
traseira) e qual orientação (retrato ou paisagem). É dona das duas consequências que caem
disso — o **espelhamento** (que é função da câmera, não gosto) e o **layout** (que hoje
assume retrato em todo lugar) — e da **recomendação de orientação por exercício**, que é o
que impede a ferramenta nova de piorar a análise.

O que ela **não** faz: nada no pipeline de análise. Extração (SPEC-005), normalização
(SPEC-006) e FSM (SPEC-007) não mudam uma linha — desde que o quadro chegue com o mundo em
pé, e a §"Rotação travada" abaixo é justamente sobre o único caso em que ele não chega.

Duas frentes de uso, ambas relatadas:

1. **Alguém filma outra pessoa.** A traseira é a câmera boa do aparelho, quem segura enquadra
   melhor que um celular apoiado, e nesse arranjo o espelho está errado: o operador não está
   se vendo, está vendo outra pessoa de fora.
2. **O celular deitado.** Hoje não existe uma linha de CSS sobre orientação no produto — nem
   `@media (orientation: …)`, nem `matchMedia`. Quatro `height: 100dvh` e uma coluna de
   `max-width: 430px` valem em qualquer tela (SPEC-014), então em paisagem a câmera vira uma
   tira estreita no meio de dois vazios e os cards do HUD, posicionados em px fixos a partir
   do topo e da base (T-071), se encontram no meio dos 390px de altura que sobraram.

## O que já está decidido em outras specs (e não se renegocia aqui)

- **A seleção de câmera é Fase Evolução da SPEC-001** ("Seleção de câmera + espelhamento
  correto; preferência lembrada por usuário"). Esta spec não inventa a ferramenta: ela
  **assume** esse item e escreve o comportamento. A SPEC-001 continua dona do probe e do
  laço de frames — nenhum dos dois muda.
- **Orientação não é problema de normalização.** A T-110 mediu o mesmo corpo em paisagem
  (854×480) e em retrato (576×1024) e a normalização fecha igual — a razão de 3,37× entre os
  formatos é do *enquadramento*, não do dado. Vale registrar porque a leitura apressada da
  T-110 seria "orientação já está resolvida", e ela não está: o que a T-110 provou é que um
  quadro **largo e em pé** normaliza igual a um quadro **estreito e em pé**. Quadro com o
  mundo *deitado* é outro assunto — §Rotação travada.
- **Aviso orienta, nunca bloqueia** (SPEC-003, decisão 1 da T-085). A recomendação de
  orientação desta spec herda a regra inteira: não desabilita o CTA, não impede treinar.
- **A UI não mostra o que o sistema não conseguiu** (regra de honestidade da casa). O botão
  de câmera reflete a câmera que **abriu**, nunca a que foi pedida.

## Fase Inicial

### A. Câmera frontal × traseira

- `getUserMedia` passa a levar `facingMode`. O valor default do produto continua sendo a
  frontal (`user`), que é o arranjo de quem treina sozinho.
- **A intenção é `facingMode`, nunca `deviceId`.** Um `deviceId` aponta para uma lente
  específica — grande-angular, teleobjetiva — e o mapeamento muda entre versões de sistema e
  entre navegadores no mesmo aparelho; `facingMode` é a frase "a que aponta para longe de
  mim", que é o que a pessoa quis dizer. É `facingMode` que se guarda na preferência.
- **Trocar usa `exact`, abrir usa `ideal`.** `{ ideal: 'environment' }` num aparelho sem
  traseira não falha: entrega a frontal em silêncio, e o botão passaria a mentir. Na troca
  vale `{ exact: … }`; `OverconstrainedError` volta para a câmera anterior, e a tela diz que
  o aparelho só tem uma. Na abertura normal vale `ideal`, com o fallback de resolução que a
  SPEC-001 já tem.
- **Quem manda é o track, não o pedido.** Depois de abrir, lê-se `getSettings().facingMode`
  e é *esse* valor que vai para o store e para o botão. Aparelho que ignora a restrição sem
  erro (acontece) fica com a tela certa em vez de um rótulo errado.
- **O controle só existe onde há escolha.** Uma passada em `enumerateDevices()` depois da
  permissão concedida; menos de dois `videoinput` → o botão não é renderizado. Mesmo
  precedente do `ZoomControl`, que só aparece quando o hardware expõe `min < 1` — controle
  que não faz nada é pior que controle ausente, porque ensina que o app está quebrado.
- **Só fora da sessão**, ao lado de Espelhar e Zoom, na pré-configuração. Durante o treino o
  controle não aparece (não é "aparece desabilitado": na tela de treino o espaço é da
  medição, T-071).
  *Alternativa rejeitada — trocar no meio da sessão:* reabrir o stream troca resolução, faixa
  de zoom e, principalmente, o corpo de lugar no quadro; o worker não tem evento para "o
  enquadramento mudou" e contaria a descontinuidade como movimento. A sessão dura 30s —
  parar e recomeçar é mais barato que um contrato novo para consertar 30 segundos.

### B. Espelho é consequência da câmera

- Abrir na **frontal** → palco espelhado (o default de hoje: quem treina de frente espera se
  ver como num espelho). Abrir na **traseira** → palco **sem** espelho.
- O botão Espelhar continua existindo e continua vencendo: a câmera define o default, a
  escolha explícita da pessoa sobrepõe **até a câmera mudar de novo**. Trocar de câmera
  reaplica o default da câmera nova.
  *Alternativa rejeitada — amarrar o espelho à câmera e tirar o botão:* a inferência acerta
  quase sempre, e é exatamente por isso que o caso raro em que ela erra viraria um app
  possuído, sem controle nenhum na tela para desfazer.
- A preferência de espelho **não é persistida hoje** (`mirrored: true` nasce no store a cada
  carga) e continua não sendo. O que se persiste é a **câmera**; o espelho se deduz dela. Um
  segundo estado salvo seria um segundo jeito de a tela abrir errada.

### C. Orientação: quem decide

- A fonte da verdade é `matchMedia('(orientation: landscape)')` — a **forma da viewport**.
  *Alternativas rejeitadas:* `screen.orientation.angle` e `window.orientation` medem o ângulo
  do aparelho, e o layout não é desenhado no aparelho, é desenhado na viewport: num celular
  com rotação travada os dois discordam, e seguir o ângulo desenharia um layout largo dentro
  de uma caixa estreita.
- A troca de orientação **não reabre a câmera**. O stream é o mesmo, a sessão em curso não é
  interrompida, o probe não roda de novo. Girar o aparelho no meio do treino é um evento de
  layout e nada mais.

### D. O que a paisagem faz com o layout

**Divergência declarada da SPEC-014.** A regra "todas as telas do app mantêm aspecto mobile
(coluna ≤ 430px) mesmo no desktop" deixa de valer **em paisagem, e só nas duas telas de
câmera** (pré-configuração e treino ao vivo). Índice, Escolha, Guia, Progresso, Analytics e
Perfil continuam na coluna de 430px em qualquer orientação — são telas de ler e navegar, onde
uma linha de 850px é pior e não melhor. Nas telas de câmera é o contrário: o quadro largo é a
ferramenta, e emoldurá-lo em 430px é jogar fora justamente o que a paisagem oferece.

O recurso escasso em paisagem é a **altura** (~390px num celular comum). Tudo que hoje empilha
na vertical migra para as bordas laterais:

- **Pré-configuração**: cabeçalho (título + subtítulo) e CTA saem da pilha vertical; as duas
  colunas de cards (92px/96px) passam a ocupar as bordas esquerda e direita da tela cheia, e a
  janela da câmera cresce para o quadro inteiro entre elas. O véu da T-167 continua sendo véu
  (não cortina) e continua medindo o cromo real — só que em paisagem o cromo que importa muda
  de eixo.
- **Treino ao vivo**: os cards HUD deixam as posições fixas em px a partir do topo/base e vão
  para as colunas laterais (esquerda: REPETIÇÕES e SÉRIE; direita: TEMPO, ÂNGULO, CALORIAS). O
  topo fica só com o cabeçalho "Treino ao Vivo"; a barra com o stop passa a ser alcançável com
  o polegar de quem segura deitado — canto inferior, não centro da base.
- **A instrução modal continua mandando na tela** (T-071, vinculante): em paisagem também o
  cromo flutuante sai enquanto o servidor mede o corpo.
- **Silhueta-guia**: mantém a proporção (`aspect-ratio: 2/3`), dimensionada pela **altura** e
  centralizada. Esticar a silhueta para preencher o quadro largo ensinaria a caber errado — ela
  é uma afirmação sobre onde o corpo vai, não um enfeite de fundo.
- **Safe area**: em paisagem quem morde a tela é `env(safe-area-inset-left/right)`, e hoje o
  CSS só conhece topo e base. O entalhe do iPhone deitado fica exatamente por cima de uma das
  colunas de cards.

### E. Recomendação de orientação por exercício

- Cada exercício declara a orientação em que ele rende: `retrato`, `paisagem` ou `qualquer`.
  Polichinelo é `retrato` (os braços sobem, e é a altura do quadro que precisa sobrar);
  exercício de chão — flexão, abdominal, Tier C da SPEC-020 — é `paisagem`, e o catálogo já
  sabe disso em texto solto: o comentário de `scene_tip` em `session/catalog.ts` diz "a flexão
  e o abdominal pedem o oposto (celular deitado no chão, de lado)". Esta spec transforma essa
  frase num campo.
- **Onde o campo mora**: é conteúdo de exercício, logo **banco + painel** (SPEC-018, a
  primeira das três naturezas de configuração), espelhado no catálogo embutido do cliente para
  o primeiro paint sem rede. Não é limiar e não é infra.
- **A frase que a pessoa lê é do dicionário do cliente** (namespace `session`), não do banco:
  "Este exercício rende mais com o celular em pé" é texto de UI e vale para qualquer
  exercício da categoria. Nasce nas duas línguas (SPEC-025). O que vem do banco é o
  *valor* (`retrato`/`paisagem`/`qualquer`), não a frase.
- **Aparece só quando discorda** da orientação atual, na pré-configuração, no pill que a T-085
  já usa — e **não** desabilita o CTA, não impede treinar, não vira modal.

### F. O botão de virar, e o caso da rotação travada

O botão manual existe porque a detecção automática tem um buraco real e comum: **celular com
a rotação de tela travada**. Nesse aparelho, virar o celular de lado não muda a viewport, não
dispara `matchMedia`, e o app continua desenhando retrato para alguém que está segurando
deitado.

O que quase ninguém percebe é que, nesse mesmo caso, **o quadro da câmera também não gira**:
o navegador entrega os frames alinhados à orientação da *tela*, que está travada. O resultado
é uma imagem com o mundo deitado — e aí o problema deixa de ser estético:

- a altura do corpo passa a ser medida contra a largura do quadro, e os limiares
  `TOO_FAR`/`TOO_CLOSE` da SPEC-003 (40–95% da altura do frame) passam a significar outra
  coisa;
- a linha dos ombros, que a Evolução da SPEC-003 compara com a horizontal (`CAMERA_TILT`),
  fica a 90°;
- `arm_abduction` (T-044/T-052) é um ângulo lido no plano da imagem — com o mundo deitado ele
  continua *existindo* e passa a estar errado, que é o pior dos dois.

Então o botão tem duas responsabilidades, e a segunda é a que protege o exercício:

1. **Alterna o layout** entre retrato e paisagem, independentemente do que a detecção disse.
   Vale até a orientação real da viewport mudar (aí a detecção volta a mandar) — uma escolha
   manual que sobrevive a um giro de verdade é uma escolha que ninguém consegue desfazer.
2. **Quando ele força paisagem numa viewport que continuou retrato** — ou seja, o caso da
   rotação travada — a tela avisa, na mesma frase, que **destravar a rotação do aparelho é o
   caminho que preserva a leitura do exercício**, e a sessão segue marcada como quadro girado
   (§Eventos). O produto não finge que os dois caminhos são equivalentes.

**Girar o frame antes da pose fica FORA da Fase Inicial**, e a decisão é declarada aqui para
não ser tomada às pressas dentro de uma task: rotacionar cada frame custa um canvas
intermediário no caminho quente, a 15fps, e a SPEC-001 decide `edge`×`cloud` por **latência
por inferência** — um passo a mais ali muda o probe e pode empurrar aparelhos honestos para
cloud. Entra na Evolução com a medição junto, não antes.

### Fora de escopo (vai para Evolução)

- Escolher a **lente** específica da traseira (`deviceId`, grande-angular × teleobjetiva).
- Trocar de câmera **no meio** da sessão.
- **Girar o frame** antes da extração de pose no caso da rotação travada (§F).
- Preferência de zoom **por câmera** — a faixa nativa da traseira costuma ser outra, mas na
  Fase Inicial a preferência salva é só recortada para a faixa da câmera atual. Dois valores
  salvos são dois jeitos de abrir errado; vira Evolução se o teste real mostrar que a traseira
  sempre quer outro número.
- Layout largo **de verdade** para tablet e desktop (paisagem aqui é a de celular).
- Qualquer coisa de vídeo para quem filma (preview, gravação, revisão) — o produto é
  keypoint-first e não guarda imagem.
- Controle de voz / disparo remoto para quem filma sozinho.

### Critérios de aceite

1. Em aparelho com duas câmeras, tocar no controle troca a imagem e `getSettings().facingMode`
   passa a `environment`; recarregar a página abre **direto na traseira** e o palco abre **sem
   espelho**, sem toque nenhum.
2. Com `enumerateDevices()` devolvendo **um** `videoinput`, o controle não é renderizado; com
   dois, é. Teste sobre o mock, nas duas contagens.
3. Pedir `exact: 'environment'` num aparelho sem traseira volta para a câmera anterior, mostra
   a frase de aparelho com uma câmera só, e o botão **continua indicando frontal** — nunca a
   câmera que não abriu.
4. Girar o aparelho (rotação livre) troca o layout **sem** chamar `getUserMedia` de novo
   (espião no mock) e sem interromper a sessão em curso.
5. Em viewport de 850×390, na tela de treino, nenhum card HUD sobrepõe outro nem sai do quadro,
   e a instrução modal da T-071 continua legível. Medido por `getBoundingClientRect`, no
   precedente da T-168 — o desequilíbrio das colunas foi encontrado assim, medindo, não olhando.
6. Em 850×390, na pré-configuração, o CTA e a tab bar são alcançáveis **sem rolagem**.
7. A recomendação de orientação aparece quando a orientação atual discorda da do catálogo, e o
   CTA continua habilitado (herda a decisão 1 da T-085).
8. `session.capability` carrega `facing` e `orientation`, e o relatório da sessão os mostra.
9. **Não-regressão do corpus**: os vídeos do `eval/corpus`, em paisagem e em retrato, mantêm a
   mesma contagem de reps depois de qualquer ajuste de limiar de cena feito por causa desta
   spec. É o critério que responde "sem impactar a qualidade do exercício" com número.

## Fase Evolução

- **Girar o frame para a pose** no caso da rotação travada, com a medição do custo por
  inferência contra o probe da SPEC-001 (§F).
- **Limiares de cena por orientação**: expressar a distância da SPEC-003 em fração da **menor**
  dimensão do quadro, ou declarar faixas por orientação — decidido pela bancada, com corpus nas
  duas orientações (natureza "medição" da SPEC-018: código + bancada, nunca painel).
- **Detectar o mundo deitado sozinho**, pelos próprios landmarks (linha ombro-ombro a ~90° da
  horizontal com o corpo bem visível), e sugerir destravar a rotação sem depender de a pessoa
  achar o botão.
- Seleção da lente da traseira; preferência de zoom por câmera.
- Orientação como parte do **Guia** (SPEC-015): o passo de cena mostra a orientação certa em
  vez de descrevê-la.
- Layout largo para tablet/desktop.

## Eventos (consome / produz)

**Nenhum evento novo.** O enquadramento é atributo da sessão, não fato do domínio de treino.

Mudança **aditiva** em `session.capability` (`workers/shared/events.py` primeiro, como manda a
regra de contrato): dois campos com default vazio, no mesmo padrão do `ua` que já está lá.

| Campo | Valores | Por quê |
|---|---|---|
| `facing` | `user` \| `environment` \| `""` | O dataset (SPEC-010) é o produto. Sessão filmada por outra pessoa tem estatística de enquadramento diferente — e sem o rótulo isso vira ruído não explicado no corpus. |
| `orientation` | `portrait` \| `landscape` \| `landscape_forced` \| `""` | `landscape_forced` é o caso da rotação travada (§F): quadro com o mundo deitado. É o rótulo que permite **excluir** essas sessões de qualquer calibração até a Evolução resolver a rotação do frame. |

Vazio permanece válido: cliente antigo continua sendo aceito sem versão nova de evento.

## Notas técnicas

- `matchMedia('(orientation: landscape)')` com listener, não `resize` — `resize` também
  dispara quando a barra do navegador entra e sai, e cada disparo desses reavaliaria o layout
  inteiro durante o scroll.
- Trocar de câmera reabre o stream, então `applyZoomFromTrack` roda de novo e a faixa de zoom
  da traseira é outra. A preferência salva é recortada nessa faixa nova (`clamp`), como já
  acontece na abertura.
- `enumerateDevices()` antes da permissão devolve entradas sem `label` (e, em alguns
  navegadores, sem contagem confiável). A contagem é feita **depois** de o stream abrir — que é
  o instante em que a permissão já existe e o botão ainda não foi desenhado.
- iPhone expõe várias `videoinput` da traseira (as lentes). A contagem responde "há mais de
  uma", que é a única pergunta que o controle faz; qual delas, ninguém escolhe (§A).
- A janela/véu da T-167 mede o cromo real (cabeçalho e rodapé) para calcular as bordas. Em
  paisagem os elementos medidos mudam de eixo — o cálculo é o mesmo, os `ref` é que passam a
  ser outros.
- Nada disso toca o laço de frames (`createVideoFrameLoop`, rVFC), o watchdog ou o probe.
