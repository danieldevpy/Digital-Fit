# Ideias da conversa de 2026-08-05 (Daniel + amigo)

> Fonte: dois áudios transcritos (`~/Documentos/transcricoes/`) — 19min30s ("Ideias Digital
> fit") e 4min18s ("Segunda rodada de ideias"). Transcrição por `faster-whisper large-v3-turbo`,
> VAD desligado, sobre áudio filtrado (passa-alta 100 Hz + `afftdn` + passa-baixa 7,5 kHz).
>
> **O áudio está clipado, não só ruidoso.** Um ventilador soprava no microfone: a banda 0–60 Hz
> é a mais forte do arquivo (15–30 dB acima da fala) e saturou o pré-amplificador. A amostra
> mediana está em 32.700 de 32.768 e 38,5% das amostras estão no fundo de escala — na prática
> uma onda quadrada. Filtro remove ruído; **não devolve amplitude cortada no teto**. Medido:
> filtragem e modelo maior (`large-v3`) não melhoraram — desligar o VAD melhorou (+26% de
> conteúdo). O que está aqui é o teto do que esse arquivo entrega.
>
> Consequência prática: **trechos continuam ininteligíveis** e as leituras abaixo são
> interpretação com o contexto do projeto. Onde há dúvida real está marcado **(?)**. Os
> timestamps permitem conferir no áudio — e existe uma versão audível em
> `*— LIMPO.flac` para isso. Antes de virar spec, vale o Daniel conferir de ouvido os pontos
> marcados, principalmente os números de preço.

Este arquivo é o equivalente da rodada de ideias de 2026-07-30 que gerou as SPEC-019…022 —
é a **fonte** que as specs novas vão citar, não uma spec.

---

## 1. O que a conversa confirma do que já está desenhado

Nada aqui vira task nova; serve para saber que o rumo tem lastro fora da nossa cabeça.

| Ideia dita no áudio | Onde já vive |
|---|---|
| "Estilo Duolingo comercial, com foguinho" `[06:24]` | SPEC-019, M1 (T-086…T-089) |
| App faz IMC e diz "você está acima do peso" `[12:20]` | SPEC-017 (T-065) — com a fronteira "personalização, nunca prescrição" |
| Adaptar por idade/objetivo, "velho é mais assistencial" `[07:01]` | SPEC-022, ajuste de baixo impacto |
| Grátis × pago, limite no grátis `[12:39]` | SPEC-016 (T-063 feito, T-064 pendente) |
| "Custo de IA tem que não ser caro — no ChatGPT eu pago toda análise de imagem" `[03:07]` | **Já resolvido pela arquitetura**: MediaPipe roda no navegador (edge-first), servidor recebe só keypoints. Custo marginal por sessão ≈ 0. É um argumento de negócio, não uma pendência. |
| "Não posso ficar gravando os outros" `[00:29]` | **Já resolvido**: keypoint-first, vídeo nunca sai do aparelho. Vira argumento de marketing, não feature. |
| Concorrente "só mostra como fazer, não corrige a postura" `[04:16]` | É a tese do produto inteiro (SPEC-007/008) |
| Bonequinho demonstrando na mesma perspectiva da câmera `[04:25]` | T-066 (GIF/vídeo de demonstração) — a exigência nova é **mesma perspectiva da câmera**, não vídeo genérico |

---

## 2. Ideias novas — nenhuma spec cobre hoje

### 2.1 O treino no ritmo da pessoa (a maior da conversa) `[16:52]–[18:20]`

> "O aplicativo vai importar [contar] o que ela tá fazendo. Não é 'você tem 10 segundos pra
> fazer 20 flexões'. O aplicativo conta 1, 2… quando tu acabar, ele entende os 20 agachamentos
> que tu fez, e vai o tempo de descanso, 30 segundos. Vai expirar, próximo exercício, 10
> segundos, tu já vai se posicionar. Se posicionou, o bagulho entendeu que tu tá pronto. Ok, eu
> levanto a mão, tem uma confirmação. Agora começa." … "Um aplicativo que não te apressa e
> também não te atrasa."

É a diferença entre **medir 30 segundos** e **treinar**. Desdobra em quatro comportamentos:

1. **Meta por repetição, não por tempo**: a série acaba quando a pessoa fez as N reps, não
   quando o cronômetro estoura. Idoso demora 3 min, atleta 40 s — os dois terminam a série.
2. **Descanso automático entre séries** (30 s), com contagem visível.
3. **Transição entre exercícios** (~10 s) para se reposicionar.
4. **Confirmação de prontidão por pose** — "levanto a mão" — em vez de tocar na tela. A pessoa
   está a 2 m do celular; tocar na tela quebra o treino.

**Choque com a arquitetura atual, e é preciso decidir com nome:** hoje "sessão de 30 s" é
unidade de *carga* (admission control por semáforo, SPEC-009), e virou também unidade de
*produto*. A SPEC-016 já prevê 30 s–5 min para assinante, então o teto existe — o que não
existe é **série com fim por repetição e descanso entre séries**. É o T-045, que hoje é uma
linha no backlog e precisa virar spec.

O item 4 (prontidão por pose) já tem meio caminho: T-030 (gate de prontidão por pose) e a
SPEC-004 existem. O gesto "mão levantada" é barato porque o `arm_angle` já é calculado.

### 2.2 Modo contado × modo livre `[A2 00:00]`

> "Modo contado e modo livre. O modo livre é quem faz mais em menos tempo. 30 segundos, tá
> contando sozinho… fiz 150, você fez 130. Parabéns, você ganhou."

Dois modos:
- **Contado**: a série do 2.1 — meta de reps, ritmo próprio, foco em execução.
- **Livre**: os 30 s de hoje viram **modo competitivo** — máximo de reps na janela, pontuação,
  comparação. O que hoje é limitação técnica vira modalidade com nome.

Observação de produto: o modo livre é o que o app já sabe fazer. Dar nome a ele custa quase
nada e cria a metade competitiva do produto sem código de motor novo.

### 2.3 Desafio entre duas pessoas (X1) `[09:59]–[10:14]`, `[A2 00:00]`

> "Eu poderia te desafiar no X1, na flexão… vocês começam junto, é como se fosse uma batalha."

Assíncrono resolve 90% (eu faço meu modo livre, te mando o resultado, você tenta bater) e não
exige tempo real, WebSocket compartilhado nem sala. Síncrono é outro produto — fica para depois.
Casa com o card compartilhável (2.5): o desafio *é* o link.

### 2.4 Convite de amigo como mecânica de plano e de crescimento `[14:22]–[15:06]`, `[A2 00:38]–[01:08]`

> "Se você parar pra ver, o Duolingo consome um bagulhinho tipo **vida**, que tem uma hora que
> acaba… Então: convide um amigo e ganhe um mês de premium." … "Se você é premium, ela te dá
> livre acesso de levar quatro pessoas por mês — convidou o amigo moleque, ele viu que o
> bagulho é maneiro, 'caralho, vou pagar essa porra também'." … "Convide um amigo e o segundo
> mês sai com desconto."

Três mecânicas diferentes que a conversa mistura e vale separar:
- **Vidas**: o Free tem um recurso que *acaba* (é a quota diária que a T-063 já implementou —
  falta só ter cara de vida, não de erro 429).
- **Indicação**: quem indica ganha desconto/mês grátis; quem é indicado entra com bônus.
- **Convite premium**: o assinante tem N convites/mês (ele diz "quatro pessoas") que dão
  acesso completo temporário a quem ele convidar. Distribuição paga pelo próprio assinante —
  mais barata que anúncio, e é o degrau "treinar com amigos" da §2.9.

### 2.5 Card compartilhável semanal (auto-divulgação) `[15:54]–[16:11]`

> "O ideal é botar alguma parada que a pessoa auto-divulgue: tira a fotinha legal… quantas
> calorias perdeu, quantos exercícios fez. 'Essa semana tu perdeu X calorias', aí tu posta.
> 'Parabéns, você é o número [N] da semana'."

Card de imagem gerado no cliente (Canvas), com o resumo da semana e a marca. É o canal de
aquisição mais barato que existe para este produto e não depende de nenhum motor novo —
os dados (`SessionResult`, kcal, streak) já existem.

### 2.6 Modo assistido `[00:14]–[00:24]`, `[07:01]–[07:37]`

> "Modo assistido, pode ativar também… se tu é um velhinho que sempre quer fazer modo
> assistido, tu vai lá e ativa. Mas é obrigatório na primeira vez." … "O velho é mais
> interessado quando tem alguém interagindo."

Mais voz, mais instrução, mais lento, mais confirmação. Duas decisões dentro:
- **Ligado por padrão na primeira vez de cada exercício** e depois desligável — que é quase o
  que a SPEC-015 (Guia de primeiro acesso) já faz, mas para o guia, não para o treino.
- **Público idoso é persona explícita**, não caso de borda. Isso muda tom de voz, tamanho de
  fonte e ritmo — e conecta com o ajuste de baixo impacto da SPEC-022.

Depende de coach por voz (T-035), que hoje é uma linha na Fase 3.

### 2.7 Marketplace de professores `[05:10]–[05:26]`, `[09:11]–[11:40]`

> "Um professor online, alguém que grave as aulas, e ganha alguma coisa." … "Você baixa o
> aplicativo: você é aluno ou você é profissional?" … "O profissional atende 20 pessoas ao
> mesmo tempo — botar uma câmera ali pra analisar, 'essa daqui fez errado, já vou corrigir ela
> na próxima aula'." … "Se alguma pessoa famosa do mundo fit fizer um bagulho desse…"

A economia saiu explícita na segunda passada `[11:27]–[11:41]`:

> "A pessoa pagaria pra entrar na aula; o professor ganharia por aluno que estivesse sentado
> online naquele momento ali pagando pra entrar; e a plataforma seria uma porcentagem."

É um **segundo produto** (dois lados, repasse financeiro, moderação de conteúdo, contrato com
professor). A ideia é boa e a conversa está certa sobre o efeito de um influenciador fitness
trazer volume — mas colocar isso na v1 é trocar "lançar" por "construir marketplace".
**Recomendação: fica como Fase 7, depois de existir receita de assinatura.** O que dá para
fazer barato hoje é o **passo zero**: um exercício com o nome/marca de um profissional
convidado, sem repasse e sem painel — mede o apelo antes de construir a máquina.

### 2.8 Analisar vídeo que não é da câmera ao vivo `[02:06]–[02:16]`, `[03:22]`

> "Um vídeo da internet, alguma parada que o aplicativo consiga puxar as informações desse
> vídeo." … "Gravar teu próprio e botar pro computador processar."

Tecnicamente **já existe**: é o `evalctl` (SPEC-012), que roda o pipeline sobre arquivo de
vídeo. Falta só ser produto. Valor real e barato: "grave sua série e mande analisar" para quem
treina na academia e não pode deixar o celular ligado apontado. Não é v1, mas é a menor
distância entre uma ferramenta que já temos e uma feature vendável.

### 2.9 Precificação com opção-isca (o "valor fantasma") `[A2 02:41]–[03:45]`

A segunda passada de transcrição recuperou a analogia inteira, com os números certos:

> "Tu chega no cinema: pote de pipoca pequeno 20 reais, médio 25, e o grande 30. Aí tu fala
> 'porra, 20 eu não pego o pequeno, vou pegar o médio de 25 — mas por 5 reais de diferença pro
> grande, eu vou pegar o grande'. Só que, mano, **o grande não tá barato: o grande tá no valor
> justo. O pequeno é que tá caro.** Isso aqui é um valor fantasma. Tu tá induzindo a pessoa a
> escolher o mais caro."

O ponto não é ter três preços — é que **o plano barato existe para ser recusado**, e o caro é
o que tem preço honesto. É o inverso de como a SPEC-016 está escrita hoje (Free bom e completo,
assinatura como acréscimo).

E `[A2 03:45]–[04:09]`, o modelo iCloud: *"te dá 15 gigas, aí tu gastou, ele deixa tu botar
mais, só que não salva no celular, aí tu tem que pagar mais 5 reais… quando tu vê, tu tá
gastando 200."*

**O diferencial entre os dois planos pagos apareceu, e é concreto** `[A2 01:54]–[02:04]`:

> "15 reais pra você ter os exercícios livres; 20 reais pra você ter os exercícios livres **e
> poder treinar com amigos**."

Ou seja: o degrau do plano de cima é **social** (o X1 da §2.3 + os convites da §2.4), não mais
volume. Isso é bem melhor de vender do que "mais sessões por dia" e amarra três ideias soltas
da conversa num benefício só.

Números ditos, ainda em conflito (a conversa oscila): **R$ 15 / R$ 20**, e antes disso
**R$ 15 normal / R$ 30 premium** `[A2 01:08]`. Prevalece o par 15/20, com o argumento
*"quem paga 15 paga 20 — 5 reais de diferença"* `[A2 01:24]`. E um dos dois discorda de ter
dois planos pagos: *"eu pensei em ter uma assinatura só — grátis e pago"* `[A2 01:29]`,
repetido `[A2 01:40]`.

**Onde isso aterrissa:** a matriz da SPEC-016 tem duas colunas (Free × Assinatura). A ideia da
isca pede três: Free · Plus · Premium, com o Plus existindo para fazer o Premium parecer
barato. O modelo `Plan` da T-073 **já aguenta isso sem migration nenhuma** — plano é linha de
tabela, não constante. É decisão comercial, não de engenharia.

*(Um trecho ficou contraditório na transcrição — `[A2 03:30]` sai como "se a pessoa escolher o
pequeno, tu tá no cano", o que inverte a lógica que ele mesmo acabou de explicar. Quase
certamente é "tu tá no lucro". **Conferir de ouvido.**)*

### 2.10 Âncora de valor contra o personal `[13:02]–[13:34]`

> "O aplicativo que corrige a sua postura, que te ensina a fazer os exercícios de forma certa,
> sem você sair de casa, sem você pagar instrutor particular." … "Pra ter uma aula com
> instrutor por semana vai sair uns 150 [reais por mês]… 300 reais por mês."

Isso é a **copy da landing page**, pronta. A conta que ele faz em seguida `[13:34]`: mil
assinantes × ~R$ 20 = R$ 20 mil/mês, com o custo de servidor já pago hoje. A margem do modelo
edge-first é o que torna essa conta possível — vale escrever isso na página de vendas.

### 2.11 Mês grátis completo `[13:11]`

> "Se você desse um mês grátis completo pra essa parada toda, pra pessoa sentir o gosto."

Trial de 30 dias com tudo liberado. Simples de implementar (`plan_until` já existe no `User`
desde a T-073) — e é decisão comercial: trial longo aumenta conversão e aumenta custo.

### 2.12 Anúncio para ganhar "vida" `[14:39]`

> "Tu pode ficar vendo anúncio pra ganhar a vida."

Mecânica de vidas do Duolingo: sessão extra no Free em troca de anúncio. **Recomendação: não
na v1.** Traz SDK de anúncio, consentimento LGPD e uma segunda fonte de receita para gerir,
tudo antes de existir a primeira. Fica registrado.

### 2.13 Personas concretas que apareceram

- **Concurso militar / barra fixa** `[18:46]`: *"imagina que você tá treinando pra um bagulho
  militar, quer fazer barra… às vezes a gente faz e perde a conta de 30 barras"*. Persona
  ótima (motivação alta, meta clara, conta reps é exatamente a dor) — **mas barra fixa é dos
  exercícios mais difíceis de detectar** (corpo suspenso, oclusão, câmera de lado). Fica no
  roadmap de tiers da SPEC-020, não na v1.
- **Idoso assistido** (2.6).
- **Treino em dupla, um corrigindo o outro** `[15:34]`: *"as pessoas fazem junto pra um corrigir
  o outro… aqui em casa não tem ninguém, e o app tá me corrigindo"*. Não é feature, é o
  **posicionamento**: o app é o parceiro de treino que corrige.

### 2.14 Gravar um movimento e virar exercício `[01:22]–[01:59]`

> "Dá pra eu fazer uma espécie pra quem é assim… criar um exercício. Você vai lá, bota pra
> gravar e vai estar com os pontos. Aí você escolhe… e ela pode usar isso pra fazer o próprio
> exercício dela."

O usuário (ou o professor) grava um movimento e o app passa a contá-lo. Tecnicamente é o
oposto do que a SPEC-020 faz hoje — lá, cada exercício é uma FSM escrita à mão, calibrada
contra corpus, com maturidade medida. Exercício gerado por gravação não tem como ser
`validado` pela bancada.

**Não confundir com a §2.8.** Aquilo é *analisar* um vídeo com uma FSM que já existe; isto é
*criar* a FSM a partir do vídeo. É a ideia mais cara do áudio inteiro (é praticamente
few-shot learning de movimento) e a mais distante do motor atual. Registrada, não priorizada.

### 2.15 Três camadas de conteúdo `[09:39]`

> "Você pode ter a IA com o conteúdo normal que você faz; você pode ter o assistencial, que é
> IA; e você pode ter a aula ao vivo com o professor."

É a arquitetura de produto por trás de metade das ideias soltas: **IA sozinha** (o que existe
hoje) · **IA assistencial** (§2.6, o modo guiado para idoso) · **humano ao vivo** (§2.7). As
três camadas explicam por que o marketplace não é um desvio — é o topo de uma escada que
começa no produto atual. Também explica o preço: cada camada é um degrau de plano.

### 2.16 O treino se monta pelo tempo que a pessoa tem `[16:22]–[16:37]`

> "Quanto tempo você tem? … Tu quer fazer cinco minutos? … Um minuto só (?), tu vai fazer dez
> de cada um, pronto."

Entrada que a SPEC-022 **não tem**: o motor do Treino do Dia hoje pesa objetivo, idade e IMC —
nada sobre tempo disponível. É a variável mais decisiva na prática ("tenho 10 minutos") e a
mais barata de coletar: um seletor de 5/10/20/30 min na tela, sem perfil, sem cadastro.
Vale entrar na SPEC-022 antes dela ser implementada.

### 2.17 Progresso medido por cadência, não por volume `[18:26]–[18:43]`

> "E isso fica no histórico. A pessoa demorou 20 segundos pra fazer 10 polichinelos. Com o
> tempo ela vai se aperfeiçoando… tu fazia 10 em 30 segundos, agora tu faz 15. **A sua média
> de polichinelo na semana ficou tanto.**"

O eixo de progresso que ele quer não é "quantas sessões" nem "quantas calorias" — é
**reps por unidade de tempo**, comparada semana a semana. O dado já existe (`SessionResult`
tem contagem e duração) e ninguém desenha. É provavelmente o gráfico mais barato e mais
convincente que a tela Progresso pode ter, e conecta direto com a §2.1 (se o exercício dura o
tempo da pessoa, cadência é a única medida justa de evolução).

---

## 3. O aviso que o Daniel se deu duas vezes

`[05:28]–[06:13]` — na segunda passada esta parte saiu quase inteira, e é uma sequência de
quatro passos com nome:
> "É muita ideia. A ideia tem que ser organizada **em sequência de crescimento**. Então: teve
> uma versão inicial… dá pra fazer e conseguir a assinatura. Beleza — **agora eu tenho que
> manter as pessoas** no bagulho. Aí tu vai desenvolvendo: pô, eu quero atingir outro tipo de
> cliente, que seriam os profissionais, a pessoa influente… Senão eu não termino alguma coisa
> prática. Você tem que ter uma base primeiro."

Ou seja, ele mesmo já ordenou: **base → assinatura → retenção → profissionais.** A única
correção que eu faria nessa ordem é trocar os dois do meio — *retenção antes de assinatura*,
porque ninguém assina um app que usou uma vez. É exatamente a diferença entre o Bloco 1 e o
Bloco 3 do §5.

`[19:09]`:
> "Tem tanto caso de uso que não dá pra fazer uma coisa que bloqueia as outras. Tu tem que
> fazer uma coisa que sirva pra todo mundo."

As duas frases juntas são o critério de corte deste documento: **a v1 é a base que serve para
todos os casos de uso, não a soma deles.** Tudo em §2.7, §2.8, §2.12 e §2.13 (barra) é
"desenvolvendo depois".

---

## 4. Onde cada ideia entra (proposta de sequência)

Legenda: **V1** = precisa estar no lançamento pago · **V1.1** = logo depois, não bloqueia
receita · **Depois** = registrado, não priorizado.

| # | Ideia | Quando | Vira |
|---|---|---|---|
| 2.1 | Treino no ritmo da pessoa (série/descanso/prontidão) | **V1** | SPEC nova + T-045 |
| 2.2 | Modo contado × modo livre | **V1** | mesma spec de 2.1 |
| 2.9 | Três planos com isca; degrau de cima é social | **V1** | linha do `Plan` (T-073) + tela |
| 2.10 | Copy "sem personal particular" | **V1** | landing (`IndexScreen`) |
| 2.11 | Mês grátis completo | **V1** | `plan_until`, já existe |
| 2.17 | Progresso por cadência (reps/tempo, semana a semana) | **V1** | tela Progresso; dado já existe |
| 2.16 | "Quanto tempo você tem?" monta o treino | **V1** | entra na SPEC-022 antes de implementar |
| 2.5 | Card compartilhável semanal | **V1.1** | task nova de cliente |
| 2.4 | Vidas · indicação · convite premium | **V1.1** | task nova api+client |
| 2.3 | Desafio X1 assíncrono | **V1.1** | task nova, depende de 2.2 e 2.5 |
| 2.6 | Modo assistido (voz, idoso) | **V1.1** | depende de T-035 (voz) |
| 2.15 | Três camadas de conteúdo | — | não é feature, é o mapa dos planos |
| 2.8 | Analisar vídeo enviado | Depois | produtizar `evalctl` |
| 2.7 | Marketplace de professores | Depois (Fase 7) | produto novo |
| 2.12 | Anúncio por vida | Depois | — |
| 2.13 | Barra fixa (militar) | Depois | tier difícil da SPEC-020 |
| 2.14 | Gravar movimento e virar exercício | Depois (caro) | incompatível com maturidade da SPEC-020 |

---

## 5. O caminho até a primeira versão rentável

Ordem por dependência, não por vontade. Cada bloco termina em algo que dá para mostrar.

### Bloco 0 — Fazer o que está no ar contar (pré-requisito de tudo)

Não é polimento: **hoje o app cobra atenção do usuário e entrega um exercício confiável.**

- **T-109 (alta)** — o agachamento está em produção, marcado `validado`, e **conta zero
  repetição em gente de verdade** (Descoberta `[A/T-106]`: 0 de 286 frames cruzam o limiar).
  Lançar cobrando com um exercício quebrado no catálogo é o pior cenário possível.
- **T-104** — `manage.py exercise_health`: taxa de sessão zero-rep por exercício. É o
  instrumento que teria pego o agachamento antes do usuário. Sem ele, o Bloco 0 se repete.
- **T-108** — corpus real de flexão e abdominal → promoção `beta → calibrado`.
- **T-110** — o espaço normalizado é anisotrópico; sem isso, exercício deitado herda o formato
  do vídeo. Entra aqui porque flexão e abdominal são deitados.

**Fim do bloco:** 4 exercícios que contam de verdade (polichinelo, agachamento, flexão,
abdominal), com um comando que prova isso em número.

### Bloco 1 — O motivo de voltar amanhã

- **T-086 / T-087 / T-088** (M1 da SPEC-019): fogo, meta, XP, e a adoção das sessões do
  aparelho no cadastro.

Sem retenção, assinatura não converte: ninguém assina um app que usou uma vez. Este bloco é
pré-requisito **comercial** do pagamento, não técnico.

### Bloco 2 — O motivo de pagar

- **[SPEC-023](../specs/SPEC-023-treino-series-e-ritmo.md)** (ideias 2.1 + 2.2 + 2.17), escrita
  em 2026-08-06 e aguardando revisão: modo contado × livre, série com fim por repetição,
  descanso, gesto de prontidão, cadência como eixo de progresso. Free fica com o modo livre de
  30 s (completo e bom); assinante ganha o treino de verdade. Tasks **T-111…T-116**.
- **T-064** — capacidades da assinatura lendo do `Plan`.

O cadeado precisa ter conteúdo real atrás. Hoje a diferença Free × pago é *quantidade*; depois
deste bloco é *natureza*.

### Bloco 3 — A caixa registradora

- **T-036** — Mercado Pago (PIX + cartão; PIX foi citado explicitamente `[15:09]`), webhook de
  status, `plan`/`plan_until` já existem, LGPD (export/exclusão).
- **T-117** — tela de planos em três colunas (ideia 2.9) e trial completo (2.11).

**Sem este bloco não existe receita.** Ele é curto, mas depende dos anteriores para não vender
uma promessa vazia.

### Bloco 4 — Crescer sem gastar

- **T-119** card compartilhável semanal (2.5) e **T-118** convite de amigo (2.4).

> Os quatro blocos viraram a **Fase 6** do `BACKLOG.md` em 2026-08-06, com os blocos A e B
> apontando para tasks que já existiam (T-104/T-108/T-109/T-110 e T-086/T-087/T-088).

---

## 6. O que decidir antes de escrever spec

1. **Um plano pago ou dois?** A conversa discorda de si mesma `[A2 01:29]` × `[A2 00:38]`.
   Recomendação: **três colunas na tela (Free · Plus · Premium)** com Plus como isca, porque
   custa uma linha de `Plan` e é reversível. O degrau do Premium já tem conteúdo definido pela
   própria conversa — **treinar com amigos** (§2.9), que embrulha X1 e convites.
2. **Preço.** R$ 15 / R$ 20 / R$ 30 foram todos ditos; prevalece o par 15/20. A âncora contra
   o personal (R$ 150–300/mês) sustenta preço maior do que R$ 15. **Conferir de ouvido** —
   é o trecho mais afetado pelo áudio ruim.
3. **Trial de 30 dias completo, ou Free permanente + trial curto?** Os dois foram ditos e são
   estratégias diferentes de conversão.
4. **A sessão de 30 s deixa de ser a unidade de produto?** Ela continua sendo a unidade de
   *carga* (SPEC-009). Precisa estar escrito que as duas coisas se separaram, senão a spec de
   2.1 vai brigar com o admission control.
