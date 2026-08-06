# SPEC-024 — Histórico como Fonte Única & Contrato de Frescor
Status: draft | Camada: client (+ leitura da api existente) | Depende de: SPEC-010, SPEC-011, SPEC-014 | Referência: "progresso e analytics estão inúteis e os dados nunca estão atualizados" (Daniel, 2026-08-06)

## Entidade e responsabilidade

**O conjunto de sessões que o aparelho conhece**, com um dono só no cliente e uma regra
explícita de quando ele é revalidado. Tudo que uma tela de dado acumulado mostra — Progresso,
Analytics e o Perfil — é *derivação* desse conjunto. Nenhuma dessas telas fala com a rede por
conta própria, nenhuma guarda um número seu.

Esta spec não inventa dado novo. Ela conserta duas coisas que já são falsas hoje:

1. **Três verdades para a mesma pergunta.** O Progresso lê `digitalfit.last_report` (uma
   sessão, do `localStorage`), o Perfil lê `GET /api/sessions?mine` (até 50, do servidor) e o
   Analytics não lê nada. Três telas, três respostas para "quanto eu treinei".
2. **O dado envelhece na tela e ninguém o acorda.** `AccountSheet` busca o histórico com
   guarda `historyStatus !== 'idle'`: **uma vez por login, nunca mais**. Quem treina e volta no
   Perfil vê o número de antes. Só logout ou F5 corrigem. Não há, em lugar nenhum do cliente,
   um `visibilitychange` ou revalidação por foco — verificado por varredura, não por memória.

O ponto de partida favorável: `GET /api/sessions?mine` já devolve o **relatório inteiro** de
até 50 sessões (`SessionResult.to_report()` — `exercise`, `created_at`, `rep_count`,
`cadence_rpm`, `cadence_windows`, `rep_durations_ms`, `feedback_counts`,
`scene_warning_counts`). Progresso e Analytics úteis não esperam backend novo; esperam alguém
ler o que já desce pelo fio e é jogado fora.

## Fase Inicial

### Escopo / Comportamento

#### 1. Uma fonte, um dono

Um store de histórico (`web/src/history/`) passa a ser o único dono das sessões conhecidas.
Progresso, Analytics e Perfil leem dele e **só** dele. O `report` do store de sessão continua
existindo para a folha de relatório do fim do treino (SPEC-010) — é a sessão *corrente*, outro
assunto —, mas deixa de ser a base do Progresso.

Duas origens alimentam o store, com precedência declarada:

| Identidade | Fonte da verdade | Papel do local |
|---|---|---|
| Logado | `GET /api/sessions?mine` | carbono para o primeiro paint e para o offline |
| Anônimo | `localStorage` (`digitalfit.history`) | é a única fonte que existe |

**Merge por união de `session_id`, servidor vencendo em conflito** — nunca soma das duas
listas. Somar contaria em dobro toda sessão feita logado (ela está no aparelho *e* no
servidor), e um total de sessões que dobra sozinho é pior que um total desatualizado: o
desatualizado a pessoa desconfia, o dobrado ela acredita.

#### 2. Contrato de frescor (a regra desta spec)

**Toda tela que mostra dado acumulado revalida ao ganhar foco.** "Ganhar foco" é, exatamente,
qualquer um destes três:

- **entrar na tela** — navegar para Progresso/Analytics, ou abrir a folha de Perfil;
- **a página voltar a ficar visível** (`visibilitychange` → `visible`) com uma dessas telas
  aberta — é o caso do celular que ficou no bolso e voltou;
- **uma sessão terminar** — o relatório consolidado invalida o histórico **na hora**, sem
  esperar foco nenhum. É o caso que dói hoje: treinou, foi no Perfil, viu o número de antes.

Três regras de comportamento em cima disso:

- **Stale-while-revalidate.** A tela pinta imediatamente o que já tem e revalida por baixo.
  Nunca há tela branca, spinner por cima de dado bom, nem número que pisca para zero e volta.
- **Debounce de 30 s.** Foco ganho menos de 30 s depois da última revalidação bem-sucedida não
  dispara rede. Quem alterna abas não vira rajada de requisição. A invalidação por fim de
  sessão **ignora o debounce** — ali existe um fato novo, não uma suspeita.
- **Falha não destrói.** Revalidação que falha mantém o dado anterior na tela, com aviso
  discreto. Rede ruim não pode zerar o progresso de ninguém, nem visualmente.

*Alternativa rejeitada: polling por timer.* O dado só muda quando a própria pessoa treina — e
ela treina *neste* aparelho, onde o fim da sessão já é um evento conhecido. Um timer gastaria
bateria e rede num app que já mantém câmera e WebSocket abertos, para descobrir o que o
cliente acabou de fazer.

*Alternativa rejeitada: revalidar a cada render.* Barato de escrever, caro de rodar, e
transforma qualquer re-render do React em requisição. O gatilho é o foco, que é um fato do
usuário, não um detalhe da árvore de componentes.

#### 3. Histórico local do anônimo

`digitalfit.history`: lista de `SessionReport`, gravada no fim de cada sessão, teto de **50**
(o mesmo `HISTORY_LIMIT` do servidor — dois tetos diferentes fariam a mesma pessoa ver
históricos de tamanhos diferentes antes e depois de criar conta), descartando as mais antigas.

Não substitui `digitalfit.last_report`, e isso é de propósito: aquela chave guarda também se a
**folha estava aberta** no F5, que é estado de UI da sessão corrente, não histórico. Fundir as
duas faria um dado de navegação viajar dentro do dado de treino.

**Rótulo honesto, obrigatório**: onde o histórico é local, a tela diz "neste aparelho" e avisa
que limpar o navegador leva embora, com o convite a criar conta. Sem isso, o produto promete
uma permanência que não tem — e a T-087 (adoção das sessões do aparelho no cadastro) é
justamente o que torna o convite verdadeiro.

#### 4. O que cada tela mostra

Tudo abaixo é **derivável de `SessionReport[]`**, sem endpoint novo. O que não for, não entra
(§Fora de escopo).

**Progresso — evolução ao longo do tempo**

- Dias ativos do mês (grade simples de calendário, dia com ≥ 1 sessão marcado).
- Sessões e repetições por semana, últimas 4 semanas.
- Total de repetições por exercício (`exercise` já vem em cada relatório).
- A última sessão em destaque — o que a tela já faz hoje, mantido.

**Analytics — leitura fina e acionável**

- Cadência média por sessão ao longo do tempo, **por exercício** (comparar polichinelo com
  agachamento não significa nada).
- Consistência de ritmo: dispersão de `rep_durations_ms` dentro da sessão, sessão a sessão.
- Correções mais frequentes (`feedback_counts` agregado) e se elas caem com o tempo.
- Avisos de cena (`scene_warning_counts`) — é o único número da tela que gera uma ação
  imediata e concreta ("afaste o celular", "melhore a luz").

**Perfil — o que já existe, fresco**

- Os três totais atuais (sessões, repetições, melhor rep/min), agora revalidados pelo §2.
- A lista de histórico ganha **qual exercício foi feito** — hoje é uma lista de "12 reps" sem
  dizer de quê (é a T-055, cujo dado já viaja ponta a ponta).

#### 5. Honestidade de tendência

Regra vinculante, na linha do `--` da SPEC-014 §Desvios: **abaixo de 2 sessões do mesmo
exercício, nenhuma linha de tendência, média móvel ou comparação é desenhada.** No lugar, a
tela diz o que falta para ela existir ("mais uma sessão de agachamento e o ritmo vira linha").
Um gráfico com um ponto não é um gráfico — é a sugestão de uma tendência que ninguém mediu.

### Fora de escopo (vai para Evolução)

- **kcal, peso, IMC** — dependem do perfil físico (SPEC-017 / T-065). Nenhum kcal na tela
  enquanto o peso for um chute de 70 kg.
- **Fogo, meta diária, XP, conquistas** — são a SPEC-019 (T-086/T-088). Esta spec é o chão em
  que aquela UI se apoia, não a implementação dela.
- **Agregação no servidor** (`GET /api/engagement`, T-086). Na Fase Inicial as agregações são
  puras, no cliente, sobre as ≤ 50 sessões que já chegam. Servidor entra quando o teto de 50
  incomodar ou quando o fogo precisar do fuso SP como autoridade.
- **Paginação / histórico além de 50 sessões**, exportação, comparação entre usuários.
- **Séries e ritmo** (SPEC-023 / T-116): a cadência como eixo de progresso com janela de 4
  semanas nasce lá; aqui ela é só uma leitura do que existe.

### Critérios de aceite

1. Terminar uma sessão e abrir o Perfil **sem recarregar**: o total de sessões sobe em 1.
   (Hoje não sobe — é a regressão que motiva a spec.)
2. Com Progresso aberto, esconder e reexibir a página depois de ≥ 30 s: sai **uma** requisição
   a `/api/sessions?mine` e os números passam a refletir o banco.
3. Repetir o mesmo em menos de 30 s: **nenhuma** requisição nova (debounce), e a tela não
   pisca.
4. Anônimo com 3 sessões no aparelho: Progresso mostra 3, rotuladas "neste aparelho", com o
   convite a criar conta.
5. Revalidação com a rede fora: os números anteriores continuam na tela e aparece aviso
   discreto — a tela nunca fica vazia nem zerada.
6. Logado, com a mesma sessão no local e no servidor: ela é contada **uma** vez.
7. Com 1 sessão de um exercício: nenhuma linha de tendência é desenhada; a tela diz o que
   falta.
8. Nenhum número em tela que não venha de um `SessionReport` — sem kcal, sem fogo, sem peso.
9. Agregações são funções puras, testadas com fixtures de `SessionReport[]`, sem rede e sem
   relógio de verdade.
10. Gates verdes: `npm run lint`, `npm run typecheck`, `npm run test`.

## Fase Evolução

- **Agregação no servidor** com cache por dia (o desenho já está na SPEC-019 §Derivação):
  passa a valer quando o histórico ultrapassar o que cabe numa resposta só.
- **Frescor por push**: o WebSocket da sessão já é um canal aberto; um aviso de "histórico
  mudou" tornaria o debounce desnecessário. Só se pagar — hoje o fim de sessão local resolve
  99% dos casos.
- **Histórico completo com paginação** e filtro por exercício/período.
- **Progresso realista com kcal e peso** (SPEC-017) e **fogo/XP** (SPEC-019) desenhados sobre
  este mesmo store, sem segunda fonte.
- **Reconciliação de conflito**: hoje o servidor simplesmente vence; se um dia o aparelho puder
  ter sessão que o servidor não tem (offline longo), vira sincronização de verdade.

## Eventos (consome / produz)

**Nenhum evento novo.** Esta spec é leitura: consome o `SessionReport` que a SPEC-010 já
consolida e a SPEC-011 já serve. O único "gatilho" novo é local ao cliente — o fim de sessão
invalidando o histórico —, e ele não atravessa o barramento.

## Notas técnicas

- **Sem backend novo na Fase Inicial.** `GET /api/sessions?mine` já entrega tudo
  (`server/api/views.py:296`, `HISTORY_LIMIT = 50`).
- **Agregações puras** em `web/src/history/aggregates.ts`, na mesma filosofia do
  `accountSummary.ts` e da FSM: entra `SessionReport[]` e uma data, sai objeto. Regra, não
  desenho — e por isso testável com um objeto.
- **`AbortController` na revalidação**: sem ele, uma resposta lenta pode pousar por cima de uma
  resposta nova e a tela volta no tempo. O bug clássico de stale-while-revalidate.
- **Dia-calendário no fuso de quem lê**, como o `historyDate()` já faz (diferença de dia, não
  de 24 h). O fogo da SPEC-019 fixa America/Sao_Paulo por outro motivo, e aquela decisão
  continua sendo dela — divergem de propósito: aqui a pergunta é "que dia era para mim", lá é
  "o mesmo dia para todo mundo".
- **Migração do `last_report`**: quem já tem a chave antiga entra no histórico local com uma
  sessão. Nada a apagar, nada a converter.
