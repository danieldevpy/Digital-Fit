# DEVLOG — Digital Fit

> Registro de sessões de trabalho. Entradas mais recentes no topo.
> Formato: data · task(s) · o que foi feito · decisões · pendências geradas.

---

## 2026-08-06 (38) · T-127 — o rumo de uma correção passa a comparar treinos comparáveis

O terceiro achado de ler as telas do M0 com o catálogo de hoje. `contagens()` parte as sessões
ao meio no tempo e compara a média por sessão das duas metades — honesto com um exercício,
mentiroso com quatro.

**O caso.** Quem agachou em agosto e trocou para flexão em setembro lia "desça mais no
agachamento — **diminuindo** entre as sessões". Não diminuiu: as flexões entravam no
denominador como sessões em que a correção não apareceu. A tela informava mudança de catálogo
como se fosse mudança de corpo — exatamente o número que a SPEC-014 §Desvios manda não mostrar.

**A regra nova.** O rumo de um aviso só compara sessões dos exercícios em que **aquele aviso já
apareceu**. Duas consequências de desenho:

- **O conjunto de exercícios é observado, não declarado.** Nada de um mapa "código → exercícios
  que o emitem" no cliente: ele envelheceria a cada exercício novo, e o cliente não sabe (nem
  deve saber) o que cada FSM emite. Ele lê o que o histórico mostra.
- **Isso reaplica o gate de honestidade num escopo menor**, e de graça: com duas sessões de
  agachamento e uma de flexão, o agachamento ganha rumo e a flexão não. Antes a flexão herdava
  um rumo do tamanho da amostra alheia.

**O total continua sendo do histórico inteiro.** Só o *rumo* é restrito: "quantas vezes isso me
aconteceu" é uma pergunta sobre tudo o que fiz; "estou melhorando nisso" é uma pergunta sobre o
exercício em que isso acontece.

**Gates.** `npm run lint`, `npm run typecheck`, `npm run test` (490, +3), `npm run build`.

**Pendências.** A forma deste erro se repete em qualquer agregação futura que cruze exercícios
— registrado como Descoberta `[T-127]`, com o XP da SPEC-019 e a comparação de cadência da
SPEC-023 §6 como os próximos candidatos.

---

## 2026-08-06 (37) · T-055 — o histórico diz qual exercício foi feito

Task antiga (estava no backlog desde a Fase 2), destravada pelo mesmo motivo que as outras
duas: com quatro exercícios contando, "12 reps" numa lista deixou de ser uma linha legível.

**Três telas.**

- **Relatório**: nome do exercício acima do motivo de encerramento. Faz mais falta agora do que
  quando a task nasceu — o relatório pode ser reaberto do Progresso e do Analytics, longe do
  treino que o gerou.
- **Perfil**: cada linha do histórico ganha o exercício sobre a data, empilhados numa coluna.
  Quatro campos lado a lado quebrariam o nome no meio numa folha estreita.
- **Progresso**: o "último treino" passa a sair do **store de histórico**.

**O último treino era a última brecha da SPEC-024 §1.** A T-124 manteve aquele card lendo o
`report` do store de sessão, que é a sessão *corrente deste aparelho*. Quem entrasse na conta
em outro celular via 50 sessões na tela e nenhum "último treino": o `last_report` local estava
vazio. Agora é `sessions[0]` — a lista já chega ordenada da mais recente —, e o card ganhou a
data, que antes seria redundante e agora é necessária.

**Sem teste automatizado, e declarado.** As três mudanças são apresentação em componente React,
e a suíte web roda sem DOM (`environment: 'node'`). O que dava para testar como regra já é
testado: `getExercise` com slug desconhecido (T-074) e a ordem do histórico (T-121).

**Gates.** `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`.

**Pendências.** Verificação visual em navegador continua pendente desde a T-124/T-125 — e agora
inclui a linha de duas alturas do Perfil e o nome no topo do relatório.

---

## 2026-08-06 (36) · T-126 — o relatório para de falar em CAIXA ALTA

Continuação do M0, olhando as telas novas com o catálogo de **hoje** em vez do de quando elas
foram escritas. O primeiro achado não estava no Progresso nem no Analytics: estava no relatório
do fim do treino, e está em produção desde que o agachamento entrou.

**O sintoma.** `textForCode` conhecia cinco códigos — os três de cena e os dois do polichinelo.
O Tier C trouxe seis códigos de execução (`SQUAT_TOO_SHALLOW`, `PUSHUP_TOO_SHALLOW`,
`HIPS_SAGGING`, `HIPS_PIKED`, `CRUNCH_TOO_SHALLOW`, `CRUNCH_TOO_FAST`) e nenhum tinha frase. Em
"o que melhorar", quem terminava um agachamento lia `SQUAT_TOO_SHALLOW`: o nome da constante,
em caixa alta, depois de suar. A T-125 só ampliou o alcance ao pôr as mesmas contagens numa
segunda tela.

**Por que ninguém viu.** O HUD ao vivo nunca dependeu daquele mapa — o `feedback.issued` chega
com a frase pronta do catálogo do worker. E o único exercício que contava de verdade era o
polichinelo (`[A/T-106]`), cujos dois códigos por acaso estavam no mapa. Duas coincidências
sustentando uma tela.

**A correção, em três degraus.**

1. **`web/src/lib/events.ts` volta a ser espelho.** O arquivo se declara espelho de
   `events.py` e estava parado na Fase 0: o `Code` de lá cresceu, o de cá não.
2. **`GET /api/config` passa a servir o catálogo de texto** (`_mensagens_de_feedback`), lido do
   **mesmo** `catalog.pt-BR.yaml` que o motor carrega. É o que a SPEC-018 §C já prometia —
   "as frases que a pessoa lê suando; você vai querer reescrevê-las sem deploy" — valendo
   também para o relatório, e não só para o HUD.
3. **`textForCode` fica com três degraus**: servidor, embutido completo, o próprio código.

**Decisões.**

- **Não copiei as frases para o bundle.** Seria a mesma decisão que causou o bug, só que maior:
  dois arquivos de texto para manter em sincronia. O embutido continua existindo (primeiro
  paint, offline), mas agora está **completo**, e o servidor vence quando chega — a mesma
  doutrina do catálogo de exercícios da T-074.
- **O último degrau continua feio de propósito.** Código desconhecido aparece como código. Foi
  assim que este bug foi descoberto, e um "—" educado no lugar o teria escondido para sempre.
- **`lru_cache` no lado do servidor**, e não cache do Django: o YAML é do deploy, não do banco.
  Mudou o arquivo, mudou o processo. Falha na leitura devolve `{}` e o cliente cai no embutido
  (P2 da SPEC-018: configuração indisponível nunca derruba resposta).
- **Dicionário vazio no payload é lido como "não sei"**, igual à lista vazia do catálogo: o
  store guarda `null` em vez de `{}`, senão um soluço do servidor faria toda frase do relatório
  virar código na tela.
- **`TOO_FAR` mudou de texto**, e isto é conserto e não estilo: o cliente dizia "afaste-se
  menos: você está longe demais" enquanto o HUD, ao vivo, dizia "aproxime-se da câmera". Duas
  vozes para o mesmo aviso, uma delas dizendo o contrário do movimento pedido.

**O gate que fecha a porta.** `todo código do contrato tem texto embutido` percorre
`Object.values(Code)` e exige frase para cada um. Código novo em `events.ts` sem frase quebra o
teste — não a tela de quem acabou de treinar. Do lado do servidor, dois testes: o payload cobre
todo `Code`, e payload e motor leem o mesmo catálogo (a promessa do `[A/T-051]`, aplicada a
texto).

**Gates.** `npm run lint`, `npm run typecheck`, `npm run test` (487, +4), `uv run ruff check .`.

**Sobre o `pytest` desta sessão.** Redis e Postgres não estão de pé nesta máquina (nenhum
contêiner do compose rodando), e sem eles a suíte inteira erra na conexão — nada a ver com esta
task. Rodou em duas partes que juntas a cobrem: `DJANGO_DB_SQLITE=1 DJANGO_CACHE_LOCMEM=1 uv
run pytest` passa tudo **exceto** `test_settings_leem_ambiente`, que falha por causa do próprio
override (ele afirma que o settings lê Postgres do ambiente); e esse teste passa sozinho com
`DJANGO_CACHE_LOCMEM=1`. Vale subir o compose antes do próximo gate de verdade.

**Pendências.** Nenhuma nova. A `hint` viaja no payload e ainda não tem consumidor — o
relatório mostra só a `message`; ela está lá porque o catálogo a tem e cortá-la obrigaria a
mexer no servidor de novo quando a tela quiser explicar o "como".

---

## 2026-08-06 (35) · T-125 — o Analytics para de prometer e começa a medir

Última task do M0. A tela era um card e três bullets dizendo o que viria; agora tem quatro
blocos, todos sobre `SessionReport[]`: **ritmo por exercício** (linha), **constância do ritmo**
sessão a sessão, **o que mais aparece** (correções + rumo) e **enquadramento** (avisos de cena).

**O gate de honestidade fica visível, e é o melhor da tela.** Exercício com uma sessão só não
ganha gráfico: ganha a frase "mais um treino de agachamento e o ritmo vira linha", **no lugar**
do desenho e não abaixo dele. Isso não é um `if` que alguém precisou lembrar — o `tendencia`
viaja dentro da série desde a T-123, e quem desenha recebe o aviso junto com os pontos.

**Decisões.**

- **Linha em `<polyline>` SVG, sem biblioteca.** São pontos num path; trazer um motor de
  gráfico engordaria o bundle de um app que já roda inferência de pose no celular. Custo
  medido: o bundle foi de 263,20 kB para 268,21 kB (79,74 → 80,91 kB gzip) — 5 kB para as duas
  telas novas inteiras.
- **`vector-effect: non-scaling-stroke`** é obrigatório com `preserveAspectRatio: none`: sem
  ele o traço engrossaria junto com o eixo esticado e viraria uma faixa.
- **Escala é o intervalo da própria série**, como o `cadenceBars` do relatório já fazia: escala
  fixa achataria a variação que o gráfico existe para mostrar. Série constante desenha no meio
  — dividir por zero mandaria a linha para fora do quadro.
- **Constância vira `±X%`, não coeficiente de variação.** "±12%" é uma frase que alguém entende
  sobre o próprio treino; "0,12" é um número de estatística. Sessão com menos de duas
  repetições não entra na lista, pela mesma razão do `null` na T-123.
- **Correções e avisos de cena têm a MESMA forma**, seguindo o precedente do `improvements()`
  do relatório: para quem treinou, "suba mais os braços" e "você saiu do quadro" são a mesma
  pergunta — o que eu faço diferente da próxima vez.
- **Verde para correção que diminui, âmbar para a que aumenta, nada de vermelho.** Isto é
  treino, não erro de sistema; e o rumo só aparece quando existe (uma sessão não tem duas
  metades para comparar).
- **Reaproveita os contêineres do Progresso** (`prog__section`, `prog__exercicios`) de
  propósito: são a mesma família de informação, e dois tratamentos fariam parecer dois
  produtos.

**Medições**: lint, typecheck, 483 testes web e build de produção verdes. CSS 46,18 kB
(9,10 kB gzip).

**Pendência declarada, a mesma da T-124**: **sem verificação visual em navegador** — a extensão
do Chrome não está conectada nesta sessão. Comportamento e dados estão cobertos por teste; o
layout (linha SVG esticada, barras percentuais, grade de 7 colunas) foi verificado por build e
leitura. É o tipo de coisa que só o celular desmente.

---

## 2026-08-06 (34) · T-124 — o Progresso deixa de ser uma sessão

A tela mostrava **um** treino (`digitalfit.last_report`) e um parágrafo dizendo que histórico,
sequência de dias e evolução por semana eram "em breve" — com a nota de cabeçalho invocando a
régua da SPEC-014 §Desvios. A nota estava certa quando foi escrita. O que mudou não foi a
régua: é que o dado passou a existir e ninguém tinha voltado para ligá-lo.

Agora: três números no topo (treinos, repetições, dias), **grade do mês**, **quatro semanas em
barras**, **totais por exercício**, e o último treino como destaque no fim — onde ele passa a
ser o detalhe, não a tela inteira.

**Decisões de desenho.**

- **Mês de calendário, não "últimos 30 dias".** Mesma razão da semana de calendário na T-123: a
  pessoa lê o mês em que está, e uma janela deslizante faria o mesmo treino mudar de lugar todo
  dia. A grade abre na segunda, casando com `inicioDaSemana`.
- **Dia com treino é roxo cheio, não contorno.** À distância de um braço — que é como o produto
  é usado — a borda some e a grade vira ruído uniforme. Hoje ganha um `outline` azul, que é
  informação diferente e por isso forma diferente.
- **Semana sem treino fica com o trilho vazio**, não com uma barra de 1px: o zero tem de
  parecer zero. É a mesma família de decisão do `--`.
- **A escala das barras é a maior semana da própria pessoa**, não um alvo. Não existe meta
  nesta spec (meta é SPEC-019), e inventar um teto viraria uma cobrança que ninguém combinou.
- **Zero cálculo no componente.** Tudo vem de `history/aggregates.ts`. A única função de data
  aqui é `chaveDoDia`, e ela existe para casar com o formato do `diaLocal` — as duas pontas têm
  de gerar a mesma chave, senão a grade não acende.
- **Nenhuma cor nova**: só tokens da SPEC-014.
- **O rótulo "neste aparelho"** aparece quando a fonte é local, com o convite a criar conta —
  e o aviso de "não consegui atualizar" quando a fonte é o servidor e a última revalidação
  falhou. É o critério 5 aparecendo na tela que a spec nomeia.

**Sem kcal e sem fogo.** Os dois cabiam visualmente e nenhum dos dois é derivável do que se
mede hoje: kcal precisa do peso (SPEC-017) e fogo precisa da regra de sessão válida e do fuso
fixo (SPEC-019). Antecipar qualquer um dentro de uma task de Fase Inicial é exatamente o que a
AGENTS §3 proíbe.

**Medições**: lint, typecheck e 483 testes web verdes; `npm run build` fecha em 268 ms com CSS
de 45,35 kB (8,90 kB gzip) e o bundle do app em 263,20 kB (79,74 kB gzip).

**Pendência declarada**: **não houve verificação visual em navegador**. A extensão do Chrome
não está conectada nesta sessão ("Browser extension is not connected"), então o layout foi
verificado por build e por leitura, não por medição de geometria como manda o quirk registrado
para este projeto. O que está em risco é layout, não comportamento — mas a grade de 7 colunas e
as barras com altura percentual são exatamente o tipo de coisa que só o aparelho real desmente.
**Vale um olhar no celular antes de considerar a tela pronta.**

---

## 2026-08-06 (33) · T-123 — as leituras do histórico, puras

`history/aggregates.ts`: nove funções, nenhuma lê relógio, rede ou store. "Hoje" é parâmetro,
como manda a doutrina de derivação (`context/conventions.md`). 28 testes, sem mock de tempo.

**A decisão que evita uma briga futura: o nome `diasComTreino`.** A SPEC-024 §4 pede a grade do
mês marcando o dia em que a pessoa treinou. A SPEC-019 tem **"dia ativo"** como vocabulário
vinculante, e lá ele exige sessão *válida* (`rep_count ≥ 1`, "senão abrir a câmera por 30 s vira
fazenda de fogo"). São conceitos diferentes com a mesma cara. Chamar este de "dias ativos"
garantiria o pior desfecho no M1: o fogo acendendo num dia que esta grade não marcou, ou o
contrário, e ninguém sabendo qual das duas está errada. Dois nomes, dois conceitos.

**Outras decisões.**

- **Semana de calendário (segunda a domingo), não janela de 7 dias corridos.** A pessoa compara
  com o que ela chama de semana; uma janela deslizante faria o mesmo treino mudar de semana a
  cada dia que passa. Semana vazia entra com zero — o buraco é a informação.
- **Cadência nunca mistura exercícios.** rep/min de polichinelo e de agachamento são grandezas
  de movimentos com duração diferente: a linha misturada oscilaria conforme o que a pessoa
  escolheu treinar, não conforme ela melhorou.
- **Consistência de ritmo é relativa à própria média** (coeficiente de variação), não em ms.
  300 ms de desvio é muito num polichinelo e pouco num agachamento — é a mesma doutrina das
  features da FSM, razão contra si mesmo. Teste cobre: rápido e lento igualmente regulares
  empatam.
- **`null` com menos de duas repetições**, em vez de `0`. Zero afirmaria regularidade perfeita
  que ninguém mediu — a régua do `--` aplicada a um número derivado.
- **Rumo das correções compara MÉDIA POR SESSÃO**, não total absoluto. Quem treinou o dobro de
  vezes acumularia o dobro de correções sem ter piorado em nada. Tem teste dedicado: total
  recente maior, média por sessão menor, resposta "caindo".
- **Margem de 10% antes de chamar de mudança.** Sem ela, 2 contra 2,1 viraria "está piorando", e
  a tela informaria ruído de amostra como notícia sobre o corpo de alguém.
- **`tendencia: boolean` dentro da própria série**, em vez de um `if` na tela. É o critério 7
  (gate de honestidade) tornado difícil de burlar: quem for desenhar a linha na T-125 recebe o
  aviso junto com os pontos, e não precisa lembrar da regra.
- **Relatório antigo sem `feedback_counts`/`scene_warning_counts` não derruba nada** — os campos
  entram com `?? {}` e há teste.

**Gates**: lint, typecheck e 483 testes web verdes (28 novos). Python não tocado.

**Critérios da SPEC-024 nesta task**: 7 (gate de honestidade, testado nos dois lugares onde
existe — série de cadência e rumo das correções), 9 (tudo puro, sem rede e sem relógio de
verdade), 10 (gates). Nenhuma tela mudou: T-124 e T-125 é que consomem isto.

**Pendências geradas**: nenhuma.

---

## 2026-08-06 (32) · T-122 — o dado acorda quando alguém olha

Os três gatilhos do contrato de frescor, ligados. O que não existia em `web/src` antes desta
task: **um `visibilitychange`**. Nenhum. Quem guardava o celular no bolso e voltava não
remontava componente nenhum, e a tela ficava com o número de quando o aparelho foi guardado.

**Os três, e onde cada um mora.**

| Gatilho | Onde | Passa pelo debounce? |
|---|---|---|
| entrar na tela | `useFreshHistory()` (Progresso, Analytics, Perfil) | sim |
| página voltar a ficar visível | mesmo hook, `visibilitychange` | sim |
| fim de sessão | `applyReport` em `store/session.ts` | **não** |

O terceiro não mora numa tela de propósito: ele não depende de haver tela aberta. E ignora o
debounce porque ali houve um **fato novo**, não uma suspeita — esperar 30 s para mostrar o
treino que a pessoa acabou de fazer é literalmente a queixa que originou a spec.

Entrou um quarto, que a task não enumerava e sem o qual o contrato tem buraco: **troca de
identidade**, no `AppShell`. Depende de `contaId` **e** de `status` porque nenhuma das duas
cobre a outra — sair da conta mantém o id em `null` e muda só o status; trocar de conta mantém
o status em `authenticated` e muda só o id.

**Decisões.**

- **Debounce de 30 s.** Foco é barato de ganhar: alternar entre Progresso e Analytics, ou
  entre abas, ganharia foco várias vezes por minuto em cima de um dado que só muda quando a
  própria pessoa treina — e esse caso tem gatilho próprio.
- **Abortar não é falhar.** O `catch` do `refreshHistory` distingue os dois: pedido substituído
  sai calado, porque marcar `loadError` ali acenderia o aviso de "pode estar velho" justamente
  no instante em que um dado mais novo está a caminho. Testado com uma resposta segurada à mão.
- **`fetchHistory` ganhou `signal`** (parâmetro opcional, aditivo — nenhum chamador existente
  mudou). O `AbortController` é o que impede a resposta lenta de pousar por cima da recente e
  fazer a tela voltar no tempo; o bug clássico de stale-while-revalidate.
- **`deveRevalidarAoMudarVisibilidade` é função exportada**, não `if` dentro do hook. O
  `visibilitychange` dispara nas duas pontas e só a volta interessa; a suíte roda em
  `environment: 'node'` e sem extrair a regra ela só seria verificável à mão, num celular.
- **O hook entrou no Progresso e no Analytics agora**, antes de as telas desenharem o histórico
  (T-124/T-125). Deixar para depois faria a tela nova nascer com o defeito que a spec conserta.
- **O aviso de falha é discreto** ("Não consegui atualizar agora — pode faltar algo recente") e
  só aparece com dado bom na tela. O número não está errado, só pode não ser o último; um erro
  em vermelho por causa de um Wi-Fi ruim assustaria à toa.

**Medições.** `npm run lint`, `npm run typecheck`, `npm run test` (455 testes, 44 arquivos),
`uv run ruff check .` e `uv run pytest` verdes. Python não foi tocado.

**Critérios da SPEC-024 nesta task**: 2 e 3 verificados em `refresh.test.ts` — uma requisição
depois de `FRESH_MS`, nenhuma antes, e `force` furando a janela. 5 verificado nos dois lados
(store e refresh). O ramo do `AbortController` tem teste próprio, com a primeira resposta
segurada até a segunda aterrissar.

**Pendência declarada, não escondida**: o *fio* do `visibilitychange` (addEventListener no
`document` real e a limpeza no unmount) **não tem teste** — a suíte roda sem DOM e o projeto
não tem setup de teste de componente React. A regra que ele carrega tem teste; o registro do
ouvinte foi verificado por leitura. Vale um teste de verdade no dia em que houver DOM na
suíte, e isso é decisão de infraestrutura, não desta task.

---

## 2026-08-06 (31) · T-121 — o histórico ganha dono, e o visitante ganha passado

Primeira task do M0. Entra `web/src/history/` com quatro arquivos e sai a segunda verdade:
`store/account.ts` não guarda mais `history`/`historyStatus`.

**O que ficou onde, e por quê.**

- `localHistory.ts` — `digitalfit.history`, teto `HISTORY_CAP = 50`. Todo acesso passa por
  aqui pelo motivo do `auth/storage.ts`: o `localStorage` **falha de verdade** (Safari privado
  lança ao escrever), e um `setItem` solto derrubaria o fim do treino por causa de um registro
  de progresso. Teste cobre o caso (`readOnly: true` não lança).
- `merge.ts` — puro, sem import de store nenhum. União por `session_id`, servidor vencendo,
  ordenado por `created_at` desc, cortado no teto.
- `store.ts` — zustand, dono das sessões conhecidas.
- `refresh.ts` — a única porta para a rede. Fica fora do store porque o store guarda estado e
  isto conhece **identidade**; sem essa fronteira um teste de merge precisaria de `fetch`.

**Decisões.**

- **`record` no `applyReport`, não numa tela.** É o único lugar por onde todo relatório
  consolidado passa — `session.report.ready` e o repique do `waitForReport` chegam os dois
  nele. Pôr numa tela faria o histórico do visitante depender de ele ter aberto o Perfil.
  Efeito colateral: **o critério 1 da spec já está atendido nesta task**, sem esperar a T-122.
  A sessão entra na lista no instante em que o relatório existe; o Perfil lê o store e sobe.
- **`record` idempotente por `session_id`, substituindo.** O relatório chega duas vezes e as
  duas entradas contariam o mesmo treino. Substitui em vez de ignorar porque a segunda versão
  é a mais consolidada.
- **`loadError` separado do `status`.** São duas perguntas — "tenho o que mostrar?" e "o que
  mostro pode estar velho?" — e colapsá-las obrigaria a escolher entre esvaziar a tela e mentir
  que está tudo fresco. `status: 'error'` só quando **não há nada** na tela; com dado, a falha
  vira `loadError` e a lista fica. É o critério 5, já implementado e testado aqui.
- **`startLoad` não mostra "carregando" em cima de dado bom** — metade do
  stale-while-revalidate da T-122 já nasce aqui, porque é onde a máquina de estados mora.
- **`setUser` e `reset` chamam `history.reset()`.** A regra ("trocar de identidade não mostra
  as sessões de quem estava antes") continua sendo do store de conta mesmo com o dado tendo
  mudado de casa. `reset` não apaga: recai no local, que é de quem usou **o aparelho**.
- **A migração do `last_report` não sobrescreve** um histórico que já existe, e o `last_report`
  continua existindo para o seu outro trabalho — lembrar se a folha estava aberta no F5.

**O rótulo honesto, onde ele coube.** O Perfil do visitante é um formulário de login, e não
virou painel: ganhou **uma linha** — "3 treinos guardados neste aparelho — limpar o navegador
leva embora. Com conta, ficam." Ela é o CTA de conta mais verdadeiro que existe hoje, e é o
único honesto enquanto a T-087 (adoção das sessões do aparelho no cadastro) não existir. O
painel desses números é o Progresso, na T-124. No Perfil do logado, a linha "Mostrando o que
está guardado neste aparelho" só aparece quando o servidor não respondeu.

**Gates**: `npm run lint`, `npm run typecheck`, `npm run test` (443 testes, 42 arquivos — 38 nos
novos e nos tocados), `uv run ruff check .` e `uv run pytest` verdes. Python não foi tocado;
rodado para não confundir o estado desta task com o do T-108 em andamento (também verde).

**Critérios da SPEC-024 nesta task**: 1 (teste em `store/session.test.ts` — a sessão entra na
hora), 5 (`store.test.ts` — falha mantém a lista), 6 (`merge.test.ts` — conta uma vez), 9
(tudo puro, sem rede e sem relógio de verdade), 10 (gates). Os critérios 2 e 3 são da T-122; o
4 depende do Progresso (T-124) — o dado local existe e é testado, a tela ainda não o desenha.

**Pendências geradas**: nenhuma task nova. Registrada uma Descoberta sobre sessões que só o
aparelho tem quando há conta.

---

## 2026-08-06 (30) · SPEC-024 — o histórico tem três verdades e nenhuma acorda

O Daniel: *"progresso e analytics… está na hora de ter uma utilidade maior e também sempre que
você focar neles os dados estarem atualizados, isso eu digo para todas as páginas que têm dados
e histórico, incluindo o perfil. Elas estão inúteis."*

**A varredura confirmou as duas metades da queixa, e a segunda é pior que a primeira.**

- *Inúteis*: `ProgressScreen.tsx:22` lê só `digitalfit.last_report` — **uma** sessão, do
  `localStorage`. `AnalyticsScreen.tsx` não lê dado nenhum: é um card e três bullets de "em
  breve". As duas telas foram escritas assim de propósito (a nota de cabeçalho invoca a régua
  de honestidade da SPEC-014 §Desvios, e estava certa **na época**) — o que mudou é que o dado
  passou a existir e ninguém voltou para ligá-lo.
- *Desatualizados*: `AccountSheet.tsx:176` busca o histórico com guarda
  `if (historyStatus !== 'idle') return`. Uma vez por login, **nunca mais**. Treinou, voltou no
  Perfil, vê o número de antes; só logout ou F5 corrigem. E não existe um `visibilitychange` em
  lugar nenhum de `web/src` — verificado por grep, não por memória.

**A descoberta que muda o tamanho do trabalho**: `SessionResult.to_report()`
(`server/api/models.py:539`) já devolve o relatório **inteiro** de até 50 sessões em
`GET /api/sessions?mine` — `exercise`, `created_at`, `cadence_windows`, `rep_durations_ms`,
`feedback_counts`, `scene_warning_counts`. Progresso e Analytics úteis não esperam backend
novo; esperam alguém ler o que já desce pelo fio e é descartado na tela. Por isso a Fase
Inicial da spec é **cliente puro**.

**Decisões (e o que foi rejeitado):**

- **Anônimo tem histórico local** (`digitalfit.history`, teto 50 = o `HISTORY_LIMIT` do
  servidor). Escolha do Daniel entre as duas alternativas apresentadas; a outra era "só com
  conta", mais simples e melhor funil, descartada porque hoje a maioria dos usuários é anônima
  e as telas continuariam vazias para quase todo mundo. Teto igual ao do servidor de propósito:
  dois tetos fariam a mesma pessoa ver históricos de tamanhos diferentes antes e depois do
  cadastro.
- **Merge por união de `session_id`, servidor vence — nunca soma.** Somar contaria em dobro
  toda sessão feita logado. Um total desatualizado a pessoa desconfia; um total dobrado ela
  acredita.
- **Frescor por foco, não por timer.** Polling rejeitado: o dado só muda quando a própria
  pessoa treina, e ela treina *neste* aparelho, onde o fim de sessão já é um fato conhecido —
  um timer gastaria bateria e rede num app que já mantém câmera e WebSocket abertos para
  descobrir o que o cliente acabou de fazer. Revalidar a cada render também rejeitado: põe o
  gatilho na árvore do React em vez de num fato do usuário.
- **Debounce de 30 s, exceto no fim de sessão** — ali existe fato novo, não suspeita.
- **`last_report` não é fundido no histórico**: aquela chave guarda também se a folha estava
  aberta no F5, que é estado de navegação. Fundir faria um dado de UI viajar dentro do dado de
  treino.
- **Gate de honestidade**: abaixo de 2 sessões do mesmo exercício, nenhuma tendência é
  desenhada. Gráfico com um ponto não é gráfico — é a sugestão de uma tendência que ninguém
  mediu. É a régua da SPEC-014 §Desvios aplicada a série temporal.
- **Fuso**: dia-calendário de quem lê (como o `historyDate()` já faz), divergindo **de
  propósito** do America/Sao_Paulo fixo que a SPEC-019 escolhe para o fogo. Aqui a pergunta é
  "que dia era para mim"; lá é "o mesmo dia para todo mundo".

**Posição no plano**: entra como **M0 da Fase 5, antes do M1**. O fogo/meta/XP do M1 são
leituras do histórico — construir aquela UI sobre um dado que não atualiza seria pôr contador
novo em cima de fundação torta. T-121…T-125, com T-123 paralela a T-122.

**Pendências geradas**: nenhuma task nova fora do M0. T-055 (histórico diz qual exercício)
ganhou relevância — ajuda o M0 e não o bloqueia. T-087 (adoção das sessões do aparelho no
cadastro) é o que torna verdadeiro o CTA de conta que o rótulo "neste aparelho" oferece.

**Status**: `draft`, aguardando revisão do Daniel. Nada implementado.

---

## 2026-08-06 (28) · T-120 — o treino só começa com a câmera ligada

Pedido direto do Daniel, em paralelo à SPEC-023. O CTA da pré-configuração fazia duas coisas
num toque só: `cameraControls.start()` **e** `navigate({ screen: 'treino' })`, na mesma linha.
Quem chegava com a câmera desligada — todo mundo, na primeira vez — saía da pré-configuração
no instante em que o navegador abre o diálogo de permissão. O treino começava por cima do
popup, e enquadramento, espelhar, zoom e o aviso de cena da T-085 passavam batidos. Com
permissão negada era pior: navegava igual, para uma tela de treino sem imagem nenhuma.

- **A regra virou função pura** (`web/src/session/startGate.ts` + teste), como o portão de
  partida da T-069: `ctaDeInicio(cameraStatus)` devolve ação, rótulo e travamento. `ready` é o
  **único** estado cuja ação é `iniciar` — e isso é o que o teste cobra, varrendo os outros
  quatro. Regra de ordem se testa com tabela de estados; montar React aqui não provaria mais.
- **`denied` e `error` continuam clicáveis**, com o mesmo rótulo de `idle`. O motivo da falha
  já está escrito na capa da `CameraView`; o que sobra ao botão é a única saída útil, que é
  tentar de novo depois de liberar a permissão. Só `requesting` desabilita — enquanto o
  navegador decide, tocar de novo não reabre nada.
- **A ordem do portão de quota não mudou** (SPEC-016, critério 1): o limite é verificado antes
  de tudo, inclusive antes de ligar a câmera. Quem esgotou não dá permissão para ouvir "não".
- **Efeito colateral bom no treino**: o mesmo `iniciar` é o play do FAB da tela de treino
  quando a câmera caiu. Antes ele navegava para a tela onde já se estava; agora liga a câmera
  e fica, que é o que aquele botão sempre quis dizer.
- Ajustes de texto e forma: o pill da janela dizia "A câmera abre aqui — alinhe-se à guia"
  (descrição de janela vazia) e passou a dizer "Ligue a câmera para se enquadrar"; o ícone do
  CTA acompanha o rótulo (▶ só quando é treino mesmo — um play ao lado de "Ligar câmera"
  prometeria o que o toque não faz); `.v2-cta:disabled` perde o glow e mantém o texto legível.
- Gates: `npm run lint`, `npm run typecheck` e `npm run test` verdes (39 arquivos, 416 testes,
  4 novos). Verificado no navegador: com a permissão bloqueada, o toque no CTA mantém a rota
  em `preparar` (`location.hash` vazio) e mostra "Permissão negada" — que é exatamente o caso
  que antes ia parar num treino cego. O caminho com câmera concedida não é testável no browser
  controlado (sem dispositivo); fica para a passada no aparelho real.
- Spec atualizada junto (AGENTS: a spec vence): SPEC-014 §3, critério 3 e Revisão 2026-08-06.

---

## 2026-08-06 (26) · O exemplo guiado passa a depender de quem é — e duas regressões das faixas

### O exemplo por identidade, não por histórico

A regra da SPEC-015 era "uma vez por exercício, para todo mundo". Ela tratava o exemplo como
**onboarding** — algo que se consome e se encerra. Só que ele não é isso: ele é a instrução de
ENQUADRAMENTO, e enquadramento errado não deixa a pessoa insegura, deixa a sessão zerada (a
T-106 gastou uma task inteira nisso). "Já viu uma vez" nunca foi a mesma pergunta que "já sabe".

O eixo virou a identidade (`session/guideGate.ts`):

- **sem conta** → o exemplo abre toda vez que a pessoa TROCA de exercício;
- **com conta** → nunca abre sozinho; o link "ver exemplo" se destaca enquanto aquele
  exercício não tiver sido visto, e emudece depois.

Decisões:

- **Trocar de exercício, e não cada sessão.** O pedido original era "sempre que for treinar",
  mas o app abre direto na pré-config — o gatilho teria que ir para o botão de play, virando
  pedágio de todo treino. Fricção que a conta remove é o que a SPEC-011 recusa por escrito, e o
  `preferences.ts` já dizia em comentário que isso seria "uma pequena punição por não se
  cadastrar". Séries repetidas não passam pelo funil e continuam livres.
- **As duas decisões saem da MESMA função.** Separadas, divergiriam até existir o absurdo — o
  exemplo abre sozinho *e* o link pisca pedindo que o abram. Há um teste que varre as quatro
  combinações só para provar que esse estado não é representável.
- **Antes do `fetchMe`, quem responde é o refresh guardado.** O status nasce `unknown` e a
  ponte `#/ex/<slug>` do site dispara o funil num efeito de boot. Esperar a rede ali abriria o
  exemplo na cara de quem tem conta, vindo do site — o incômodo que a mudança existe para tirar.
  Refresh vencido faz alguém deslogado perder o exemplo automático; é o erro barato dos dois,
  porque o link continua na tela, destacado.
- **O `guide_seen` continua sendo gravado.** Deixou de decidir a abertura para decidir o
  destaque — inclusive para quem vira assinante depois: exercício que já viu como anônimo
  nasce sem destaque.
- **O link virou chip.** Era texto sublinhado de 9px; para quem tem conta ele agora é o ÚNICO
  caminho até o exemplo, e o que ninguém enxerga não é um caminho. 74×36px com ícone. O
  destaque respira 2,2s × **3 e para** — contagem finita porque animação infinita numa tela
  onde se fica parado esperando a câmera vira tique, o oposto de "não invasivo".
  `prefers-reduced-motion` recebe a borda acesa, sem pulso.

### Duas regressões da entrada (25), achadas medindo no navegador

1. **As fotos da Escolha não carregavam — nenhuma.** `loading="lazy"` herdado do card antigo:
   dentro de um contêiner com `overflow-x: auto` o Chrome nunca dispara o carregamento
   (`currentSrc` vazio, `complete: false`, com o card visível na tela). Provado nos dois
   sentidos: imagem idêntica sem `lazy` carrega, e remover o atributo em runtime carrega na
   hora. O `lazy` virou opt-in no `ExerciseDemo`, com a armadilha documentada; só a vitrine do
   site liga, onde a rolagem é a do documento e o adiamento funciona de verdade.
2. **A media query media a tela errada.** `@media (min-width: 700px)` para agrandar o card
   casava com o MONITOR, não com o quadro: o app vive dentro do `.app__phone`, que é
   `max-width: 430px` em qualquer tela. No desktop dava cards de 196px num quadro de 430px —
   um layout que nenhum celular veria. Removida, com um comentário no lugar dizendo que o
   instrumento correto seria container query.

Medido depois das duas: 4/4 imagens carregadas, card de volta a 160px, e a Escolha inteira
cabendo **sem rolagem** (800px de conteúdo em 800px visíveis, com 4 exercícios).

Gates: `typecheck`, `lint`, `build` limpos; `vitest` 412/412 (+10 em `guideGate.test.ts`).

Pendências geradas:

- **A SPEC-015 agora contradiz o código.** Ela diz "o guia só aparece sozinho na primeira vez";
  o código diz "depende de ter conta". O AGENTS manda comportamento nascer de spec — falta a
  revisão da SPEC-015 (ou uma SPEC nova) para o texto voltar a valer.
- **A rota de quem TEM conta não foi verificada ponta a ponta.** Sem backend local o `fetchMe`
  falha e o status resolve para `anonymous` — comportamento correto, mas impede o teste real.
  Cobertura hoje é só unitária (10 casos).
- **O `ExercisePicker` troca de exercício sem passar pelo funil.** Hoje é inofensivo (fica
  oculto na pré-config pelo `compactCover`, só aparece na capa do treino antes da câmera subir),
  mas é uma segunda porta para a mesma decisão. Se um dia voltar a aparecer, o exemplo não abre.
- **As fotos são 900×900 numa caixa 138×92**: com `contain` sobram 23px de vazio de cada lado.
  `aspect-ratio: 1` resolveria (foto a 138×138, zero barra) ao custo de ~45px por card. Decisão
  do Daniel, ainda não tomada.

---

## 2026-08-05 (25) · T-091 (metade layout) — a Escolha vira faixas por categoria

A tela Escolha empilhava um card de ~305px por exercício. Com dois exercícios aquilo cabia na
tela; com os quatro de hoje já são ~1.220px de rolagem, e o Lote 1 da SPEC-020 (T-092…T-095)
mais o wall sit levariam a ~3.000px — a tela deixaria de ser uma escolha e viraria um catálogo
que se percorre.

**A troca que resolve não é encolher o card, é trocar o eixo.** Cada categoria virou uma faixa
horizontal (`screens/ExerciseRails.tsx`): a altura da tela passou a escalar com o número de
CATEGORIAS — vocabulário fechado em código, quatro — e não com o de exercícios. Estimativa pelo
box model: ~630px hoje, ~850px com dez exercícios. A rolagem lateral fica dentro da categoria,
que é onde a comparação de verdade acontece ("qual cardio eu faço hoje?"), não entre elas.

Decisões:

- **O card grande não morreu, virou do site.** `ExerciseCards` agora é exclusivo do Index, onde
  a foto grande é o argumento de venda e rolar é o comportamento esperado de uma página de
  marketing. Com o app fora, sumiram os props `grid`/`openInApp` e o ramo de botão.
- **"ver todos" existe porque a faixa esconde.** É a fraqueza conhecida do formato: o que está
  fora do quadro não se anuncia. O botão abre a categoria numa grade — e só aparece com mais de
  2 exercícios, senão prometeria revelar o que já está à vista. O limite é constante e não
  medido por JS de propósito: medido, o botão apareceria e sumiria na rotação do aparelho.
- **A faixa sangra até a borda da tela** (`margin-inline: -16px`). Card cortado na margem é o
  que anuncia que há mais para o lado; terminando alinhada ao texto, a faixa lê como fileira
  completa. Junto vai `overscroll-behavior-x: contain`, senão o gesto lateral vira "voltar".
- **`groupByCategory` é regra pura no `catalog.ts`, não lógica na tela.** A ordem em que as
  categorias se apresentam é conteúdo, igual ao `CATEGORY_LABELS`. E é a única parte disto que
  dá para cobrar por teste — a suíte do web roda em `node`, sem DOM.
- **Categoria desconhecida vira seção com o slug cru, e não some.** O servidor pode servir
  categoria que este cliente não conhece; engolir o exercício aqui seria o `[A/T-051]` de volta
  pelo outro lado — existe no servidor, a admissão aceita, e a tela não mostra. Feio é
  aceitável; sumir é bug.
- **`ui/ExerciseDemo.tsx`**: a regra "sem foto, desenha a figura" agora existe uma vez só. Ela
  passou a valer em duas telas com visuais diferentes, e escrita duas vezes se perde uma —
  exercício novo chega antes da foto, e a tela que esqueceu o fallback põe ícone de imagem
  quebrada no lugar da pose.

Gates: `typecheck`, `lint`, `build` limpos; `vitest` 402/402 (7 novos em `catalogGroups.test.ts`).

Pendências geradas:

- **O T-091 continua `todo`** — esta entrada entrega só a metade layout. Cadeados com motivo
  (progressão ≠ plano ≠ conta) e selo Laboratório 🧪 dependem do eixo maturidade da T-090.
- **A trilha Fundamentos (T-097) pede uma seção no TOPO da Escolha.** As faixas deixam o lugar
  livre, mas ninguém verificou se anel de progresso + cadeado cabem no card da faixa ou se a
  trilha precisa do card grande de volta. Decidir quando a T-097 chegar.
- **Não foi verificado em aparelho.** Os números de altura são do box model do CSS, não medidos.

---

## 2026-08-05 (24) · T-106/T-107 — os exercícios de chão ganham foto (e o hero perde 1,8 MB)

Os dois exercícios de chão subiram sem foto de demonstração, caindo na figura do exercício. A
figura é o fallback certo, mas não é o produto: ao lado do polichinelo e do agachamento
fotografados, os dois novos pareciam inacabados. Quatro fotos geradas no Kairogen
(`nano-banana-pro`, 6 créditos cada, dentro do teto de 7 pedido), no mesmo padrão das que já
existiam: 900×900 JPEG, 89–96 KB, ginásio escuro, esqueleto neon, grade cyan no chão.

**A decisão de conteúdo que importa: as quatro fotos são de PERFIL, com a câmera no chão.** A
demo do Guia é a primeira coisa que ensina o enquadramento, e enquadramento errado num
exercício de chão não é estética — é a sessão inteira sair zerada (a validação de cena mede a
extensão do corpo no eixo horizontal, e de frente uma flexão é um corpo encolhendo contra a
lente). Uma foto frontal aqui seria uma instrução errada com cara de instrução certa.

**Sobre gerar as fases certas.** As duas primeiras tentativas de "fundo da flexão" saíram em
prancha: com uma imagem de referência em prancha, o modelo preserva a pose e ignora a
instrução de dobrar o cotovelo. O que funcionou foi **abandonar a referência** e descrever a
cena inteira em texto, com a pose descrita espacialmente ("peito a 5 cm do chão", "ombros mais
baixos que os cotovelos", "antebraços verticais"). Com a fase certa em mãos, aí sim a
referência serve — o topo da flexão e o topo do crunch saíram de primeira usando a imagem
irmã como referência, e é o que garante que o par tenha o mesmo homem, a mesma cena e o mesmo
enquadramento. Custo total: 30 créditos, 5 gerações, 4 aproveitadas.

**O hero da landing.** A imagem da atleta estava em `herofamale.png` com **1,9 MB** — 21× o
peso das outras, num PNG, na primeira tela que qualquer visitante abre. Virou
`hero-female.jpg`, 900×900, 91 KB, mesmo tamanho renderizado. O PNG original fica fora do
repositório (não versionado): é o negativo, não o produto.

**Duas coisas que a verificação no app revelou, e que valem mais que as imagens:**

1. **Quem coloca foto em produção é a migration, não o `catalog.ts`.** Com a API no ar, o
   cliente usa o catálogo do SERVIDOR (o `[A/T-051]` resolvido pela T-074) — o `catalog.ts` é
   só o default embutido para o primeiro paint e o modo offline. Editar o cliente e esquecer a
   migration deixaria a foto invisível para todo mundo que tem rede. Por isso a `0013` existe,
   e por isso ela só preenche quem está com o campo **vazio**: um `demo_img` já trocado pelo
   painel não pode ser sobrescrito por deploy.
2. **Mudança de dado por migration não invalida o snapshot de configuração.** A `0013` alterou
   o banco e o `GET /api/config` continuou servindo a foto vazia: a invalidação normal é por
   `post_save`, que uma migration com modelo histórico não dispara. Não é bug — o próprio
   `config.py` documenta o TTL de 5 minutos justamente para este caso, e no deploy o processo
   reinicia de qualquer forma. Vale saber ao testar: ou espera 5 minutos, ou reinicia a API.

**Verificação:** os quatro cards da Escolha desenham foto (nenhuma imagem quebrada, `900×900`,
mesma altura de card); o Guia dos dois de chão mostra demo + três passos ilustrados + a frase
de cena correta; `GET /api/config` devolve os quatro `demo_img` preenchidos depois da migration.
Gates: `ruff` limpo, pytest verde (menos a falha pré-existente do `test_smoke`), web
lint/typecheck/test verdes (395).

---

## 2026-08-05 (23) · T-106 — a flexão contava braço levantado: o porteiro de postura

Teste em produção, no mesmo dia: *"dependendo da posição ele já contava, quando levantava ele
contava, meio que parece que ele conta diferentes posições"*. Reproduzido no gerador antes de
qualquer conserto: **pessoa em pé levantando e baixando os braços 10 vezes = 10 flexões
contadas.**

A causa é uma só, e é de desenho. A feature mede a altura do ombro sobre o pulso, e ela vale:

- **+0,734 torsos** em pé com os braços baixos;
- **+1,147 torsos** na prancha;
- **−0,734 torsos** em pé com os braços no alto.

Ou seja: em pé, baixar os braços é indistinguível de estar na prancha, e levantá-los é
indistinguível de descer a flexão. A feature media a coisa certa e **nunca perguntava quem
estava sendo medido**. O `ready_pose` sabia a diferença, mas ele só serve ao gate de prontidão
(SPEC-004, ainda não ligado) — a FSM nunca o consultava.

**O conserto: um porteiro de postura antes da FSM**, com duas perguntas escolhidas por medição,
as duas razões no mesmo eixo (imunes à anisotropia do `[A/T-106]`):

| situação | tronco `dx/dy` | mão↔chão | passa? |
|---|---|---|---|
| prancha | 2,46 | 0,13 | sim |
| flexão no fundo | 3,86 | 0,18 | sim |
| flexão de joelhos | 1,56 | 0,13 | sim |
| em pé, braços baixos | 0,00 | 1,78 | **não** |
| em pé, braços no alto | 0,00 | 3,78 | **não** |
| agachado | 0,00 | 1,23 | **não** |

Limiares em 1,2 e 0,5, no meio de uma folga de ordem de grandeza — a decisão não é apertada
entre 1,1 e 1,3, é 0,0 contra 2,5, e é isso que a faz sobreviver a ruído e câmera torta.

**Decisões do conserto:**

- **Frame fora de posição congela E descarta a tentativa**, silenciosamente. Não é o mesmo que
  `degraded` (dado ruim): quem se levantou não fez uma repetição incompleta, fez outra coisa —
  e criticar a execução de quem está saindo do chão seria ruído. Entrou `frames_off_posture` no
  `summary()`, separado de `frames_degraded`, porque é a primeira pergunta a fazer quando uma
  sessão de flexão volta zerada.
- **A referência da prancha só cresce com o porteiro aberto.** Sem isso, os frames em pé (0,73)
  entrariam na mesma referência dos de prancha (1,15) e a profundidade passaria a ser medida
  contra um corpo que ninguém fez.
- **A referência passou a exigir dois frames seguidos** (`min` com o frame anterior). Um único
  frame em que o modelo erra o ombro inflaria a prancha para sempre, e daí em diante nenhuma
  flexão de verdade voltaria a marcar 1,0. O primeiro frame ainda vale por si: semear baixo é
  inofensivo (a referência só cresce), semear alto é o que a persistência impede.
- **Flexão de joelhos entrou no gerador** (`PushUpPose(on_knees=True)`). O porteiro usa como
  "chão" o ponto mais baixo da perna — joelho ou tornozelo —, e essa promessa estava no
  comentário sem fixture nenhuma por trás. Agora tem: 10/10 reps, zero frame fora de posição.
- **O abdominal NÃO ganhou porteiro**, porque não tem o bug — e isso foi medido, não suposto: em
  pé o joelho fica sempre abaixo do quadril, então a referência sai negativa (−0,52 em pé,
  −0,32 agachado, −0,37 na marcha, contra o mínimo de +0,25) e a feature devolve zero. Inventar
  um porteiro sem reprodução seria calibrar contra nada. O que entrou foi o **teste** que
  transforma a proteção de acidente em invariante: quem trocar a referência do joelho descobre
  no pytest, não em produção.

**Verificação:** o caso relatado vai de 10 reps para 0; em pé parado, agachando e marchando
também dão 0; e o caminho realista (chega em pé → 6 flexões → levanta) conta exatamente 6,
tanto na FSM quanto pelo `evalctl` com calibração (10/10). Nenhum teste antigo mudou de
resultado.

---

## 2026-08-05 (22) · T-106/T-107 — flexão e abdominal, e a descoberta de que o agachamento não conta

Dois exercícios de chão (SPEC-020 **Tier C**), a capacidade de motor que o Tier C exigia, e uma
medição que deveria mudar a prioridade do backlog.

### A descoberta, primeiro, porque ela é maior que a task

**O agachamento está no ar, `validado`, e não conta uma única repetição em gente de verdade.**

Antes de escolher qualquer limiar, rodei o pipeline REAL sobre o corpus que já existe — vídeo →
MediaPipe → `normalize()` → `SquatAnalyzer.features()`. Uma pessoa **em pé** lê:

| vídeo | `hip_height` em pé (mediana) | frames que o squat leria como agachado |
|---|---|---|
| polichinelo-01 | 1,310 torsos | 0 / 124 |
| polichinelo-02 | 1,609 torsos | 0 / 61 |
| polichinelo-03 | 1,440 torsos | 0 / 101 |

O limiar de "agachado" é **0,72**, calibrado contra um boneco sintético que diz que em pé se lê
1,02 (perna de 1,05 torsos; gente real tem ~1,7). Descendo na mesma proporção que o gerador
(×0,62), um agachamento paralelo de verdade chega a ~0,89 — nunca cruza o limiar. O módulo
avisava por escrito que os números vinham do gerador e "errar para menos é o lado seguro"; a
medição mostra que o lado seguro também é o lado que não conta. Virou **T-109 (alta)** e
Descoberta `[A/T-106]`.

Junto veio uma segunda: **o espaço normalizado é anisotrópico**. O MediaPipe divide `x` pela
largura e `y` pela altura, então a mesma largura de ombros lê 0,352 torsos no vídeo em paisagem
e 1,188 no vídeo em retrato (razão 3,37; o formato do quadro sozinho prevê 3,16). Os dois
exercícios existentes escapam por acidente — `ankle_spread` é razão de dois horizontais,
`hip_height` é vertical sobre um torso quase vertical. Num corpo **deitado** o acidente acaba: o
torso é horizontal e o movimento é vertical. Virou T-110.

### O que essas duas medições fizeram com o desenho dos exercícios novos

A regra que os dois módulos seguem, e que é a resposta às duas descobertas: **feature é razão
entre duas medidas do mesmo eixo do mesmo corpo, nunca constante em torsos**.

- **Flexão** — `depth` = altura atual do ombro sobre a mão ÷ a maior altura que ESTA pessoa
  mostrou na sessão (a prancha dela). Cancela o torso, o formato do vídeo, a distância da câmera
  e o tamanho da pessoa. Sobra "quanto do seu próprio braço você dobrou".
- **Abdominal** — `lift` = subida do ombro ÷ altura do joelho. Aqui a referência **não precisa de
  memória**: o joelho dobrado com o pé apoiado é uma altura vertical estável que existe em todo
  frame, inclusive no primeiro. É por isso que o joelho dobrado virou requisito de medição no
  Guia, e não detalhe de execução.

Limiares escolhidos por tabela medida no gerador (as duas estão nos docstrings dos módulos):

| flexão — cotovelo | `depth` |   | abdominal — tronco | `lift` |
|---|---|---|---|---|
| 172° (prancha) | 1,000 |   | 4° (deitado) | 0,097 |
| 130° | 0,909 |   | 20° | 0,474 |
| 115° | 0,846 |   | 25° | 0,586 |
| 100° | 0,768 |   | 30° (crunch cheio) | 0,694 |
| 90° (fundo) | 0,709 |   | 40° | 0,892 |

Descer conta em `depth < 0,82` (~107° de cotovelo) e subir conta em `lift > 0,52` (~22° de
tronco). Os 90° de cotovelo e os 30° de tronco não são invenção: são o padrão de execução que
NASM/ACE descrevem (flexão até ~90° ou peito perto do chão; crunch até as escápulas saírem do
chão, lombar apoiada). Os limiares ficam um pouco **abertos** em relação ao padrão de propósito —
um `beta` que não conta nada nunca recebe corpus para deixar de ser `beta`, que é exatamente
como o agachamento chegou onde chegou.

### A capacidade de motor que o Tier C exigia

A SPEC-007 manda parar e registrar quando um exercício novo precisa de mudança fora de
`exercises/`. Precisou, e a lacuna era real: **a validação de cena mede distância pela altura
cabeça→tornozelo**, e numa flexão a cabeça e o tornozelo ficam quase na mesma altura. A medida
dá ~0, e o produto pediria "aproxime-se" a sessão inteira com o enquadramento perfeito.

Resolvido pelo contrato, não por tabela de slug: `Posture` (`standing`/`floor`) entrou no
`scene_hints()` do analisador, o `SceneValidator` passou a ler dali a postura e a faixa, e o
router liga os dois na abertura da sessão. Default = `standing` com a faixa da SPEC-003, então
**nenhuma sessão existente muda de resultado** — há teste cobrando isso.

O mesmo problema tinha uma versão de texto que teria estragado a sessão do usuário: a tela do
Guia dizia, fixo, "celular apoiado na vertical, uns 2 metros". Virou `scene_tip` por exercício
(coluna, editável no painel), com a frase antiga de fallback.

### Decisões menores, com o motivo

- **Nada de sinal de qualidade para "puxar o pescoço" no abdominal.** Era o candidato óbvio (a
  literatura cita muito), mas o boneco não sabe assinar o sentido dele: cabeça flexionada num
  corpo deitado gira o nariz por cima do peito, e o sinal na projeção lateral muda conforme onde
  a cabeça pivota. Sondei e o valor foi na direção contrária à intuição. Sinal que o gerador não
  sabe assinar não vira limiar — o erro de execução que sobrou é a **cadência**
  (`CRUNCH_TOO_FAST`, < 800 ms por rep), que se mede com relógio e não com geometria.
- **Crítica de postura sai JUNTO com a repetição, não no lugar dela.** Quadril caído é uma flexão
  que aconteceu e foi mal feita; rep rasa é uma flexão que não aconteceu. `HIPS_SAGGING` e
  `CRUNCH_TOO_FAST` acompanham o `rep.detected`; `PUSHUP_TOO_SHALLOW` e `CRUNCH_TOO_SHALLOW`
  substituem-no. É a distinção que os dois primeiros exercícios não precisaram fazer.
- **`HIPS_SAGGING` e `HIPS_PIKED` são dois códigos, não um com sinal.** O conserto é oposto
  ("contraia o abdômen" × "abaixe o quadril") e um código só obrigaria o texto a falar dos dois.
- **A flexão nunca lê fase inicial `PEAK`.** A referência da prancha é o próprio primeiro frame,
  então `depth` vale 1,0 por construção. Quem começa a captura no fundo perde **uma** repetição —
  troca deliberada, e é a que o contrato de `initial_phase` manda fazer ("rep fantasma é pior que
  rep perdida"). O abdominal não tem esse limite, porque a referência dele existe no frame 1.
- **Os dois nascem sem foto de demonstração.** `demo_img` vazio virou estado suportado: a tela
  desenha a **figura** do exercício em vez de apontar para um arquivo que não existe. Antes, um
  `src` vazio renderizava ícone de imagem quebrada. Trocar por foto depois é edição no painel.
- **Gerador com proporções próprias para o corpo deitado**, medidas no corpus (braço 1,15 torsos,
  perna 1,65 — contra 0,75 e 1,05 do boneco em pé). Não corrigi o boneco em pé: mexer nele muda
  toda fixture do polichinelo e do agachamento, e essa correção é a T-109.

### O que fica pendente, e o que precisa de decisão

- **`beta` está visível para todo mundo, porque a T-090 não existe ainda.** A SPEC-020 diz que
  `beta` só aparece com `is_admin`, mas a regra que lê `Plan.min_maturity` é a T-090, que está
  `todo`. Na prática, subindo assim, os dois exercícios aparecem no catálogo de qualquer usuário
  com o selo `beta` no payload e nenhuma tela mostrando esse selo (T-091 também `todo`). Foi a
  escolha consciente para permitir teste em produção; desfazer é um clique em `enabled` no
  painel, que é exatamente para isso que a coluna existe.
- **Nenhum vídeo real por trás dos limiares.** O guia de gravação dos dois exercícios já está em
  `eval/corpus/README.md`, com as três diferenças que importam (celular deitado, countdown na
  posição do exercício, calcanhar perto do quadril) e a nota sobre corpus público com `pushup`/
  `situp` já rotulados. Promoção a `calibrado` é a T-108.
- **Não testado em aparelho.** A verificação foi feita no navegador (catálogo, cards, Guia); o
  caminho câmera → worker com uma pessoa deitada de verdade é o que a T-108 vai exercitar.
- **`main_angle` continua `none` nos dois.** De lado, o ângulo do cotovelo é honesto e daria uma
  barra de métricas de verdade — mas o cliente só sabe desenhar abdução de braço, e ampliar a
  união é a Descoberta `[A/T-074]`, que já previa este momento.

**Gates:** `ruff check` + `ruff format` limpos; `pytest` verde (só `test_smoke::test_settings_leem_ambiente`
falha, e é contradição pré-existente entre o teste e o `conftest` — Descoberta `[A/T-106]`);
`npm run lint`/`typecheck`/`test` verdes (395 testes, incluindo o de figura da T-082, que passou
a cobrar as duas figuras novas); `evalctl` conta 12/12 nos dois exercícios pelo caminho da
bancada, com calibração.

---

## 2026-08-01 (21) · T-063 — o Free ganha limite, e o limite ganha uma tela honesta

Quota diária por plano no servidor (`429 quota_exceeded`), sheet de limite com contagem e hora
de renovação, e kcal ao vivo no HUD. Fecha os quatro critérios da Fase Inicial da SPEC-016 — e
é o primeiro produto a **consumir** o `Plan` que a T-073 deixou pronto sem ligar nada.

**O que muda para quem usa:** a conta Free passa a ter 10 sessões por dia (a "proposta inicial"
da spec), a 11ª é recusada pelo servidor, e a tela avisa **antes de a câmera abrir**. O card
CALORIAS deixa de ser `--` durante o treino.

**Decisões, e o que foi rejeitado:**

- **`trial.py` virou `quota.py`, e a regra ficou uma só.** A SPEC-018 §A já dizia o que fazer:
  *"a identidade do contado muda, a regra não"*. Um módulo chamado "trial" contando as sessões
  de quem tem conta seria o convite a escrever o segundo contador — e dois contadores da mesma
  regra divergem no dia em que só um for corrigido. A chave do visitante continua `trial:` e
  **não** foi renomeada: renomeá-la zeraria o contador de todo mundo no deploy, dando um dia
  grátis a mais justamente a quem já tinha esgotado.
- **O piso do código do Free é 10, não 0.** Escrevi `0` (ilimitado) primeiro, para "degradar
  sem travar ninguém", e é a escolha errada: um soluço de Postgres entregaria sessões
  ilimitadas a todo mundo, em silêncio, até alguém olhar a fatura da VPS. Piso é *"o produto de
  ontem"*, e o produto de ontem tem limite. Há teste cobrando que a constante e a linha do
  banco digam o mesmo número.
- **Rota nova (`GET /api/quota`) em vez de um campo no `GET /api/config`.** O config seria o
  lugar óbvio e seria um bug: aquela resposta é cacheada por ETag de (versão, plano,
  `is_admin`), e nenhum dos três muda quando o contador anda — o `used` congelaria no primeiro
  valor do dia e a tela diria "restam 7" para sempre. Número errado na tela é pior que número
  nenhum (SPEC-014).
- **O pré-voo não é a trava, e há teste disso.** A spec é explícita: *"a UI apenas reflete e
  vende o upgrade, nunca é a única barreira"*. `test_pular_o_pre_voo_nao_ajuda` e
  `test_limite_no_corpo_da_requisicao_e_ignorado` existem porque o critério 4 é o mais fácil de
  fingir que se testou — um teste do caminho normal prova que o caminho normal funciona, não
  que não há outro.
- **Dois códigos de recusa, não um.** `trial_exhausted` (crie conta, resolve hoje) e
  `quota_exceeded` (a conta é que chegou ao limite). Um código só obrigaria o cliente a olhar
  se há usuário para escolher a mensagem — e o servidor já sabe. Convidar quem já tem conta a
  criar conta seria um conselho impossível de seguir.
- **A hora de renovação é formatada no cliente, a partir do instante.** O servidor conta o dia
  em UTC; escrever "renova à meia-noite" mentiria para quem está no Brasil, onde o contador
  vira às 21 h. Mandar o `resets_at` e formatá-lo no navegador mantém as duas coisas
  verdadeiras — e a tela de fato exibiu `Renova amanhã às 21:00`.
- **Não há botão de assinar.** A spec pede o CTA "ainda sem checkout — lista de espera/em
  breve", e um botão que não leva a lugar nenhum seria a primeira afordância inventada de um
  app cuja regra é mostrar `--` quando não há dado. Enquanto o checkout não existe, o convite é
  uma frase.
- **Kcal ao vivo não contradiz "a UI nunca mostra número inventado".** A regra proíbe número
  que o servidor não forneceu — e é por ela que FC continua `--`. Aqui os dois insumos que
  decidem o resultado vêm de fora do cliente: o MET é dado do catálogo servido (T-074, editável
  no painel) e o tempo é o da sessão que o servidor admitiu. O que o cliente põe de si é o
  peso, e ele entra marcado como `estimado` justamente por ser a única parte que não sabemos.
  **Sem MET não há conta e não há número** — volta `--`, sem a ressalva.
- **`message` vazio quando o plano é ilimitado.** Achado ao ler o corpo do assinante no `curl`:
  a resposta carregava "suas sessões de hoje acabaram" para quem não tem limite. Frase falsa
  esperando um consumidor descuidado que a exiba.

**Corrigido no navegador, não no editor:** o chip do Perfil dizia `0 de 10 hoje` (restantes) ao
lado do bloco que dizia `10 de 10 sessões de hoje` (usadas) — dois significados para a mesma
forma, na mesma tela. Só apareceu com a conta esgotada na tela real; virou `restam 0`.

**Verificação no stack real** (containers `digital-fit`, conta criada pela própria API):

| O que | Como | Resultado |
|---|---|---|
| Critério 1 — a 11ª é recusada | 11 `POST /api/sessions` numa conta Free nova | 10× `201` (`used` 1→10), a 11ª `429 quota_exceeded` |
| Critério 1 — antes da câmera | clicar "Iniciar Exercício" com 10/10 no app | sheet abriu, `video.srcObject` **nulo**, rota ficou na pré-config |
| O texto que a pessoa lê | DOM da folha de conta | "Você treinou muito hoje 🎉" · "10 de 10 sessões de hoje" · "Renova amanhã às 21:00" |
| Critério 2 — assinante | trocar o plano da MESMA conta esgotada e repetir | 3× `201`, `unlimited: true`, contador parado em `10` |
| Critério 4 — forjar o cliente | `X-Device-Id` novo + `daily_sessions: 999` no corpo | `429` — a chave da conta não tem aparelho dentro |
| Critério 4 — pular o pré-voo | `POST` direto, sem `GET /api/quota` | `429` |
| Chave e prazo do contador | `redis-cli` | `df:quota:{id}:2026-08-01` = `10`, TTL 172 706 s (48 h) |
| Critério 3 — MET real na mão do cliente | ler o catálogo servido no `localStorage` | polichinelo `met 8` → 4,9 kcal/30 s; agachamento `met 5` → 3,1 |
| Critério 3 — o card no HUD | rota `#/treino` no navegador | `0,0 kcal` + `estimado` — prova que o MET servido chegou ao componente |
| Critério 3 — sem MET, `--` | `docker compose stop api` + catálogo local apagado | `-- kcal`, **sem** a ressalva "estimado" |
| Custo do pré-voo | `performance.getEntriesByType('resource')` | 3 chamadas no boot — o mesmo que o `GET /api/config` que já existia |

O que **não** foi observado ao vivo: o kcal subindo durante uma sessão de verdade. O navegador
controlado não tem câmera, então o HUD foi visto com a sessão parada (`0,0`) — o que prova a
ligação (MET servido → componente), não o movimento. A fórmula tem teste de unidade com o
número conferido à mão; o movimento fica para o próximo teste no celular.

Gates: `ruff` limpo, `pytest` 678 verdes (+16), `npm run lint`/`typecheck`/`test` verdes (395,
+18), `makemigrations --check` sem drift, `manage.py check` com o painel ligado sem issues.

**Pendências e efeitos colaterais:** o banco de dev ficou com ~27 sessões de verificação, três
contas `t063-*` e a versão de configuração em `6` (o contador só anda para frente). Nenhuma
tela soma kcal entre sessões — conferido por busca em `ProgressScreen`, `AnalyticsScreen` e
`report/`, e garantido por construção: `session/kcal.ts` não tem estado. O acúmulo é capacidade
de assinante (`kcal_accumulation` no `Plan`) e é a T-064, junto com o peso real da T-065 —
enquanto ele não chega, os 70 kg continuam premissa declarada na tela.

## 2026-07-31 (20) · T-075 — o relatório passa a dizer sob qual configuração a sessão nasceu

`session.started` ganha `config_version` (aditivo, default `0`), a API carimba a versão que
valia na admissão, e o `SessionResult` guarda o carimbo. Fecha o critério 8 da SPEC-018 — o
último em aberto da Fase Inicial dela.

**A pergunta que este campo responde** é de suporte, não de produto: "este treino rodou antes ou
depois de eu mexer na configuração?". Até aqui a resposta era cruzar o horário do `LogEntry` do
painel com o `created_at` do relatório no olho. Agora é uma coluna, e o painel filtra por ela.

**Decisões, e o que foi rejeitado:**

- **Carimbo, não consulta.** O relatório copia a versão que veio no evento; nunca lê
  `SiteConfig` na hora de gravar. Ler o banco pareceria certo em todo teste feito no mesmo
  minuto e mentiria sobre toda sessão de ontem — e quebraria a promessa da SPEC-010 (relatório
  derivável 100% por replay, o mesmo motivo pelo qual o worker não tem ORM).
- **`config_version` sai de `caps` sozinho, sem parâmetro.** Duração e countdown são escolha da
  admissão (o cliente pede, o plano limita) e por isso viajam como argumento explícito. A versão
  não é escolha, é **procedência** da resolução que produziu `caps`. Fosse mais um parâmetro,
  esquecê-lo carimbaria `0` numa sessão cuja config veio do banco — e o relatório mentiria em
  silêncio, que é o defeito que o campo existe para eliminar.
- **Valor torto vira `0` em vez de derrubar o evento.** Um `_as_int` estrito recusaria o
  `session.started` inteiro, levando junto **exercício e modo** — que é o que o relatório de
  fato precisa. Metadado não pode custar o relatório; mesma escolha já feita para o countdown.
- **`0` significa "não registrada", e cobre três casos de propósito**: sessão anterior a esta
  task, builder que subiu no meio da sessão (não viu a abertura) e configuração fora do ar na
  admissão (P2). Nos três a resposta honesta é a mesma; carimbar a versão de agora seria pior.
- **Nenhuma tela do usuário mostra o número.** A SPEC-014 é vinculante para a UI e não pede
  número novo lá; quem pergunta é o operador, no painel. O tipo do cliente ganhou o campo mesmo
  assim, porque `sessionReport.ts` se declara espelho do `to_report()` — e espelho com campo
  faltando é o `[A/T-051]` recomeçando.

**Verificação no stack real** (containers `digital-fit`; o `df-teste` da sessão paralela seguiu
de pé nas portas +10):

| O que | Como | Resultado |
|---|---|---|
| Carimbo no evento | `POST /api/sessions` e ler `events.analysis` no Redis | `{… 'countdown_s': 3, 'config_version': 4}`, com `SiteConfig.version = 4` |
| Uma edição no painel entre duas sessões | salvar o plano `anon` (bump 4 → 5) e abrir a segunda | os relatórios saíram `config_version = 4` e `= 5` |
| O carimbo é do passado | com o banco já em `5`, reler o relatório da sessão antiga | continuou `4` |
| Migration | `migrate` → `migrate 0008` → `migrate` no Postgres do compose | aplica **e reverte** limpa |
| Painel | `manage.py check` com `DJANGO_ENABLE_ADMIN=1` + o teste que abre a changelist | sem issues, 200 |

Gates: `ruff` limpo, `pytest` 662 verdes, `npm run lint`/`typecheck`/`test` verdes (377),
`makemigrations --check` sem drift. **Sem passada de navegador**: a mudança no cliente é uma
linha de tipo (apagada na compilação) e nenhuma tela lê o campo — não havia o que observar lá
que o `curl` no stack real não tenha mostrado melhor.

**Pendências:** a Fase Inicial da SPEC-018 está inteira — critérios 1…11 cobertos. Ficaram no
stack de dev duas sessões de verificação e a versão de configuração em `5` (o contador só anda
para frente; desfazê-lo seria mentir para ele).

## 2026-07-31 (19) · T-074 — o catálogo passa a ter dono, e a admissão passa a travar

`Exercise` + `ExerciseGuideStep` no painel com a trava de slug, `exercises_for()` como
resolvedor único, `GET /api/config` servindo catálogo e capacidades, e o cliente consumindo. É
o fim do `[A/T-051]`: "o catálogo do cliente e o registro do servidor podem divergir sem
ninguém ver".

**A descoberta mais incômoda veio antes de codar**: `POST /api/sessions` não travava **nada**
além de `exercise in EXERCISES`. Desligar um exercício no painel o tiraria da tela e deixaria a
porta aberta para quem chamasse a API direto. A T-074 original nem mencionava admissão — foi a
revisão da Fase 0 que a colocou no escopo, e ela era mesmo o buraco.

**Decisões, e o que foi rejeitado:**

- **Um resolvedor, duas perguntas.** `exercises_for()` serve o catálogo *e* a admissão. Duas
  listas montadas por dois códigos divergiriam do pior jeito: um card na tela que o
  `POST /sessions` recusa. O teste central percorre o que o `GET /api/config` devolveu e abre
  sessão de cada um — se divergirem, ele quebra.
- **Degradação assimétrica, de propósito.** Sem catálogo no banco, `exercises_for` devolve o
  registro de código (comportamento de ontem). Mas a exclusividade por plano falha **fechada**:
  `min_plan` sem ordem resolvível some. Fechar tudo esvaziaria a tela Escolha num soluço de
  banco; abrir a exclusividade entregaria conteúdo pago. Cada lado falha para o lado certo dele.
- **O servidor SUBSTITUI o catálogo do cliente, não completa.** Exercício que o servidor não
  listou está desligado ou fora do plano; mantê-lo por herança do embutido recriaria exatamente
  o card que a admissão recusa.
- **Lista vazia quer dizer "não sei", não "não há exercício".** É o que o servidor manda com o
  banco fora, e o cliente guarda `null` em vez de `[]` — guardar `[]` apagaria a tela Escolha
  por causa de um soluço. Card em branco seria pior que card nenhum.
- **Categoria virou slug na migration, convertida e não copiada.** O cliente guardava `'Cardio'`
  e `'Força'` (strings de exibição); o rótulo agora é derivado por `categoryLabel()`. Copiar
  quebraria as conquistas da SPEC-019 e o mix da SPEC-022 em silêncio.
- **403 e não 404 na recusa por plano**: o exercício existe, o acesso é que não. E não 400,
  porque o corpo da requisição está correto — mudou a permissão, não a sintaxe.
- **`slug` vira somente-leitura depois de criado.** O `clean()` pega slug inexistente, mas não
  pega um slug VÁLIDO trocado por outro slug VÁLIDO — que é como se perde a ficha de um
  exercício, sem erro nenhum na tela.

**Dois defeitos que só o navegador mostrou** (e que `curl` e teste com `fetch` dublado
aprovavam):

1. **O `ETag` nunca chegava ao JavaScript.** Cross-origin, `resposta.headers.get('ETag')` volta
   `null` sem `Access-Control-Expose-Headers`. Medido: `localStorage` ficava vazio depois de
   três buscas bem-sucedidas. Sem erro nenhum — só o payload inteiro descendo para sempre. O
   CORS ganhou `Expose-Headers: ETag` e `If-None-Match` na lista do preflight, com dois testes.
2. **O ETag era decoração mesmo depois disso.** O `If-None-Match` só saía se houvesse catálogo
   em memória (senão um 304 deixaria o app sem catálogo) — e no boot o store nasce vazio, então
   nunca saía. A correção é hidratar do `localStorage` antes de falar com a rede: boot lê o
   disco, revalida, e o caso comum custa uma resposta sem corpo. Medido no navegador: 1954 bytes
   → `304`.

Também medido: o boot fazia **duas** buscas de config porque o efeito dependia de
`account.status`, que muda `unknown → anonymous` sem o plano mudar. Passou a depender do **id**
da conta — que no boot anônimo não muda, e na troca de conta muda.

**Verificação no stack real** (containers `digital-fit`, com o `df-teste` da sessão paralela
rodando em paralelo nas portas +10):

| O que | Como | Resultado |
|---|---|---|
| CA 3 da SPEC-018 + a metade que faltava | desligar `squat` no painel e chamar a API | catálogo encolheu para `['jumping_jack']` e `POST /sessions` devolveu **403 `exercise_unavailable`**, sem restart |
| Headers da resposta | `curl -i` | `ETag`, `Cache-Control: private, must-revalidate`, `Vary: Authorization` |
| Revalidação | `curl -H "If-None-Match: …"` | `status=304 bytes=0` |
| Painel → tela | renomear `squat` e recarregar o app | card passou a ler "Agachamento livre / Pernas, glúteos e core" |
| Rótulo de categoria | ler o DOM | `cardio → Cardio`, `forca → Força` |

Os dados de dev que mexi para medir foram restaurados ao final.

Gates: `ruff` limpo, `pytest` 644 verdes, `npm run lint`/`typecheck`/`test` verdes (377).
**Screenshot não foi possível** — trava neste browser controlado (quirk conhecido); tudo acima
foi medido por JS no DOM e por `curl`, que é o caminho que este projeto já usa.

**Pendências:** critérios 3, 4, 10 e 11 da SPEC-018 agora estão cobertos; o 8 (`config_version`
no relatório) segue com a T-075. Duas descobertas no BACKLOG: figura de pose de exercício que só
existe no servidor, e a divergência silenciosa entre o `main_angle` aberto do servidor e o
fechado do cliente.

## 2026-07-31 (18) · T-073 — configuração de negócio vira dado, sem mudar produto nenhum

`Plan` + `SiteConfig` + `User.plan/plan_until` + `capabilities_for()`, e a admissão passando a
resolver quota, duração, countdown, TTL e cloud por eles. A prova de que a task deu certo é
**nada ter mudado**: 623 testes verdes, e vários deles comparando o valor resolvido com a
constante que existia antes.

**Escopo travado antes de codar.** Entrou: os dois modelos, as duas telas de painel, o
resolvedor com cache, a migration de dados e a ligação na admissão. Não entrou: `Exercise` e
`GET /api/config` (T-074), `config_version` no evento (T-075), quota do Free e faixa de duração
do assinante (T-063/T-064), `FeedbackMessage` (Evolução da SPEC-018).

**Decisões, e o que foi rejeitado:**

- **`free.daily_sessions = 0` (ilimitado) na migration.** Hoje conta logada não tem quota
  nenhuma; a SPEC-016 propõe 10/dia e quem liga é a T-063. Entregar o limite novo já na
  migration faria a T-073 mudar o produto no dia do deploy, escondida atrás de "só
  infraestrutura". O teste `test_conta_logada_continua_sem_quota` existe para segurar isso.
- **O piso do código é por plano, não global** (`_FLOOR_PLAN`). Com o banco fora, o anônimo
  precisa cair em 3 sessões e na mensagem do trial — um piso único devolveria "ilimitado" para
  o visitante e abriria o funil inteiro justo quando o banco está ruim.
- **`capabilities_for` não levanta exceção, e o `except Exception` largo é intencional.** É o P2
  escrito como fluxo de controle: cache fora → consulta direta; banco fora → constante de
  ontem. A alternativa (deixar subir) é derrubar um treino por causa de configuração.
- **Expiração de assinatura resolvida na leitura, não por job.** Um cron que rebaixasse contas
  seria um segundo lugar onde o plano é decidido, e o dia em que não rodasse ninguém notaria.
- **O bump da versão usa `queryset.update()`.** `instance.save()` dispararia `post_save` de
  novo — a diferença entre um contador e um laço. Tem teste (`..._nao_entra_em_laco`).
- **Snapshot do catálogo inteiro de planos, não de um plano.** São três linhas e a consulta é a
  mesma; assim trocar o plano de uma conta não precisa de invalidação própria — o que muda é o
  ponteiro no `User`, lido a cada requisição.
- **TTL de 5 min no snapshot além do signal.** O signal é o caminho normal; o TTL é a rede para
  o que ele não cobre — `manage.py shell` com `.update()`, que não dispara `post_save`.
- **Plano não se apaga pelo painel.** `User.plan` é `SET_NULL`: apagar o `free` esvaziaria
  contas em silêncio, sem erro na tela. E `slug` vira somente-leitura depois de criado, porque
  o resolvedor procura `anon` por nome — renomear faria tudo cair no piso sem ninguém ver.
- **`CloudSlots` ganhou `grace_ms` como parâmetro** (default = a constante). O worker continua
  sem saber que existe banco (ADR-008); quem resolve capacidade é a API e passa o número.

**Medições e verificações (critérios da SPEC-018, um a um):**

| # | Critério | Como foi verificado |
|---|---|---|
| 1 | mudar `daily_sessions` vale sem restart | `test_editar_o_plano_no_painel_muda_a_admissao_sem_restart` — POST no formulário do painel → `capabilities_for` já devolve o novo valor |
| 2 | Postgres/Redis fora e a sessão ainda nasce | `test_banco_fora_do_ar_nao_levanta_e_devolve_o_piso` + `test_cache_fora_do_ar_cai_para_o_banco` (derrubados de propósito) |
| 5 | painel não responde no gateway | coberto pela T-072, ainda verde |
| 6 | só `is_staff` entra | coberto pela T-072, ainda verde |
| 7 | auditoria com autor e data | `LogEntry` conferido na edição de `Plan` |
| 9 | suíte com config vazia | `test_plano_apagado_da_tabela_cai_no_piso_do_proprio_slug` |

Gates: `ruff check` limpo, `pytest` 623 verdes, `manage.py check` sem issues,
`makemigrations --check` sem drift, e as migrations 0005/0006 aplicam **e revertem** limpas.
`web/` não foi tocada (nem podia: há alteração de UI em paralelo), então os gates do npm não
se aplicam. **Não abri o painel no navegador** — as telas novas são exercitadas por requisição
(`GET` 200 na lista e no change de `Plan` e `SiteConfig`), que é o que a lição do
`ContaCreateForm` da T-072 pedia, mas não é a mesma coisa que olhar.

**Pendências:** critérios 3, 4, 8, 10 e 11 da SPEC-018 são T-074/T-075 e continuam abertos.
Duas descobertas no BACKLOG: o dublê `admissao_falsa` que engole os kwargs da view (armadilha
para a próxima task que acrescentar argumento) e `Plan.history_limit`, coluna que existe e
ninguém lê ainda — é da T-064.

## 2026-07-31 (17) · Fase 0 da Fase 5 — revisão das SPEC-019…022 e reescrita de T-073/T-074

Alinhamento antes de codar: revisar as 4 specs em `draft` e garantir que o escopo do admin
(T-073/T-074) carrega o contrato que M1…M4 vão consumir. As quatro passaram a `approved`.
Comecei conferindo o código em vez de confiar no texto — duas premissas do BACKLOG caíram e duas
se confirmaram.

**Verificado (e o que mudou por causa disso):**

- `SessionResult.exercise` **já existe** (`server/api/models.py`). Confirma "T-055 ajuda mas não
  bloqueia": conquista `centena`, progresso de trilha e item do treino do dia estão de pé sem ela.
- O report-builder é `python manage.py report_builder` (compose). Confirma a aposta da SPEC-019 de
  que o `post_save` de `SessionResult` dispara num processo com ORM e Redis compartilhado.
- **`POST /api/sessions` não trava nada** além de `exercise in EXERCISES` (`sessions.py`). Não
  havia gancho de `enabled`/plano em lugar nenhum, e T-074 não mencionava admissão — mas o CA 3 da
  SPEC-018 a exige e o T-090 a pressupunha. Virou escopo explícito da T-074.
- **O `Plan` não tinha onde guardar 3 capacidades** que as specs já haviam atribuído a ele.

**Decisões (com as alternativas rejeitadas):**

- **Todas as colunas novas em T-073/T-074, não nos marcos.** `Plan` +
  `streak_protections_month`/`min_maturity`/`daily_workout`; `Exercise` + `met`/`maturity` e
  `category` como *choices*. Rejeitado "cada marco traz a sua": seriam 4 migrations e o
  `GET /api/config` mudaria de forma duas vezes depois de o cliente já lê-lo. O preço aceito é
  T-073/T-074 maiores, carregando coluna que só é usada depois — o comportamento continua com a
  spec dona.
- **`category` é código, não dado editável — a SPEC-018 cedeu para a SPEC-020.** A 018 a listava
  como apresentação; mas conquistas (019) e o mix por objetivo (022) consomem os *slugs*. Pior, a
  coluna nasce na T-074 populada com as strings de exibição de hoje (`'Cardio'`, `'Força'`): a
  migration **converte**, não copia, senão o primeiro consumidor a agrupar não acha nada.
- **`GET /api/config` é privado e o ETag precisa saber.** Com a SPEC-020 o payload varia por plano
  (o assinante vê o Laboratório). ETag só sobre `config_version` faria um proxy servir a resposta
  do assinante para o próximo Free — vazamento silencioso que fura o CA 1 da 020. Ficou
  `Cache-Control: private` + ETag por (versão, plano, `is_admin`).
- **XP só lê `SessionResult`.** O bônus "+15 meta batida" (019) e o "+25 treino do dia" (022) liam
  perfil **mutável**: trocar a meta ou o objetivo reescrevia quais dias passados contavam, e o XP
  histórico saltava sozinho — contradizendo, no único lugar onde importa, a promessa de
  recomputabilidade da 019. Rejeitado persistir a meta vigente por dia (primeiro estado
  não-derivável da spec, comprado por um bônus cosmético). A meta continua como anel do dia e
  gatilho de conquista; o treino do dia mantém a conquista `treino-do-dia-7`. Se um dia o bônus
  for necessário, o caminho é `daily_workout_done(user, date)` persistido — está na Evolução.
- **A chave de cache do engajamento leva a data**: `df:eng:{user}:{data_sp}`, TTL até a virada.
  Uma chave sem data só é invalidada por sessão nova, mas o payload muda **sozinho à meia-noite** —
  quem treinou 23h50 veria o fogo de ontem até treinar de novo, isto é, até deixar de precisar.
- **Downgrade nunca apaga fogo antigo** (regra do piso: `max(plano_atual, free)` para dias fora do
  mês corrente). Sem isso, vencer a assinatura derrubava proteções de 2 para 1 e um fogo de 40 dias
  virava 12 — churn produzido pela própria mecânica de retenção, no momento da renovação.
- **Trilha v1 aceita passo `calibrado`.** Com `validado`, os 4 do Lote 1 (que nascem `beta` e o
  T-096 leva só a `calibrado`) nunca abririam: a Fundamentos fecharia o M2 com 4 de 6 passos
  trancados para sempre — a "meia-mecânica no ar" que a Fase 5 proíbe por escrito. `beta` segue
  fora. Consequência registrada na spec: no M2 a Fundamentos do **Free** é curta (Laboratório é
  benefício de assinante), e por isso a tela precisa distinguir cadeado de progressão de cadeado
  de plano.
- **`PROTOCOL_VERSION` não sobe na SPEC-021** — decidido na spec em vez de deixar para a task. A
  mudança é aditiva nos dois lados; subir por mudança aditiva treina o projeto a ignorar o número.
- **Grandfathering declarado**: `jumping_jack` e `squat` nascem `validado` por decisão, não por
  medição (o squat nem corpus tem — T-053). Aplicar o critério retroativamente deixaria o Free sem
  exercício nenhum no dia da T-074. Está escrito na SPEC-018 para ninguém ler o selo como evidência.

**Pendências geradas:**

- **T-104** (nova): `manage.py exercise_health` — `validado` exige taxa de zero-rep < 20% e o
  instrumento não existia; sem ele, promoção de maturidade é opinião. Serve também para rebaixar.
- A SPEC-018 continua `draft` embora a T-072 já esteja `done` e T-073/074 sejam dela. Vale uma
  passada de status próprio.
- A dívida do grandfathering tem nome e dono: T-053 (corpus do agachamento) e a passada manual
  pendente da T-040 (paridade edge×cloud×browser).

## 2026-07-30 (16) · docs+skills — O novo rumo vira documentação oficial e skills de agente

Continuação da sessão (15): o Daniel pediu para **finalizar a documentação** assumindo a Fase 5
como o rumo do projeto, e criar **skills** que orientem agentes a executar cada spec/task com
entrega confiável e testável.

- **ARCHITECTURE.md v0.3**: §1 ganhou o "Rumo atual" (as duas teses: fábrica de exercícios
  com maturidade mensurável; engajamento como derivação, não estado) e §9 ganhou as Fases 4
  (entregue) e 5 (os 4 marcos M1–M4 com raias e pré-requisitos).
- **context/project.md**: rumo no topo, specs 018–022 na tabela de entidades, skills na lista
  de documentos — é o arquivo que toda sessão lê primeiro, então o rumo mora nele.
- **context/conventions.md**: duas seções novas com força de convenção — "Derivação"
  (derivação pura, fuso SP do engajamento vs UTC da quota, `XP_FORMULA_V`, cache nunca é
  fonte) e "Exercícios & maturidade" (checklist, escada, feature importada nunca copiada,
  "o eixo Z mente").
- **Skills em `.claude/skills/`** (versionadas no repo — viajam com o projeto e qualquer
  agente Claude Code as descobre):
  - `df-executor` — executa T-XXX: contexto mínimo na ordem certa, escopo travado ANTES de
    codar (Entra/Não entra/Descobertas), critérios de aceite viram testes ou verificações
    medidas, gates obrigatórios, DEVLOG com decisões, commit. Inclui a lista "O que NUNCA
    fazer" (antecipar Evolução, done com gate vermelho, segundo escritor do Postgres, mexer
    em limiar calibrado fora de task de calibração, número inventado em tela).
  - `df-exercise` — a fábrica: classificação por tier antes de codar, checklist DoD da
    SPEC-020 em 7 passos com caminhos reais, comandos do `evalctl`, escada de maturidade com
    evidência exigida por promoção, anti-padrões ("calibrar na própria webcam é beta").
  - `df-spec` — o padrão da casa em 8 regras (Fase Inicial mínima, decisões com dono e
    alternativa rejeitada, critérios mensuráveis, honestidade de UI, derivação primeiro, as
    três naturezas de configuração, eventos aditivos, orçamento da VPS) + desdobramento em
    tasks com raias e marcos funcionais.
- **AGENTS.md** aponta as skills como a forma operacional do fluxo (o fluxo manual continua
  sendo a fonte); **prompts/executor.md** marcado como superseded para agentes com skills;
  **README** ganhou o parágrafo de skills e do rumo.
- **Decisão**: skills no repo (`.claude/skills/`) e não em `~/.claude` — orientação de agente
  é parte do projeto, versiona com ele e vale para qualquer máquina/agente que clonar.
- **Pendências**: nenhuma nova; as da sessão (15) seguem (revisão das specs em draft).

## 2026-07-30 (15) · SPEC-019…022 — Do MVP ao produto de retenção (o "foguinho" e a fábrica de exercícios)

Sessão de projeto, não de código. Pedido do Daniel: pensar o produto à la Duolingo — recursos
crescentes por role (deslogado/free/assinante), uso diário ("foguinho"), seções/categorias, e
a lista de exercícios do mais fácil ao mais difícil sabendo que os difíceis pedem mais teste.
Saíram 4 specs (draft, aguardando revisão dele uma a uma) + a Fase 5 no BACKLOG (T-086…T-103,
4 marcos, 3 raias paralelas).

- **SPEC-019 Engajamento**: fogo/meta/XP/conquistas como **derivação pura** de
  `SessionClaim`+`SessionResult` — nenhum worker novo, nenhum contador para dessincronizar,
  ADR-008 intacto. Decisões com dono: virada do dia em America/Sao_Paulo fixo (diverge da
  quota da 016, de propósito — meia-noite UTC é 21h no Brasil e mataria a mecânica); fogo ≠
  meta (fogo = 1 sessão válida, meta é pessoal — meta agressiva não pode queimar constância);
  proteção de streak é **regra derivada** (N dias perdoados/mês), não item de inventário;
  sessão de 0 reps não conta nada (anti-farm); XP com bônus de execução limpa — o que o
  Duolingo não tem e o feedback engine dá de graça. Fogo fantasma do anônimo em localStorage +
  **adoção das SessionClaim do device no cadastro** (o fogo e o histórico sobrevivem à conta —
  a promessa do README vira literal).
- **SPEC-020 Catálogo**: o insight organizador é **dificuldade física ≠ dificuldade de
  detecção** — o roadmap ordena pelo eixo técnico em tiers (A: em pé/frontal/cíclico → A2:
  salto/assimetria → B: isométrico → C: chão → D: composto), e cada tier é uma capacidade do
  motor que destrava um LOTE. Escada de maturidade mensurável pela bancada
  (`beta`→`calibrado`→`validado`), Laboratório 🧪 = assinante beta-tester que gera corpus.
  Lote 1: marcha, elevação de braços, high knees, sumô (dois reusam features existentes).
  Trilha Fundamentos com progresso derivável (sem tabela de progresso).
- **SPEC-021 Isométricos**: modalidade `hold` (relógio de tempo válido com histerese, soma
  trechos, `degraded` congela, `hold.progress` no contrato, colunas aditivas no
  `SessionResult`). Primeiro exercício: wall sit — reusa a altura de quadril do squat, adia a
  prancha (hold+chão misturaria duas novidades). Habilita o "dia leve" que guarda o fogo.
- **SPEC-022 Treino do Dia**: seleção diária determinística (seed usuário+data) por objetivo,
  com ajuste de baixo impacto por idade/IMC declarados — personalização de treino, nunca
  prescrição de saúde. Assinante completo; Free vê as categorias do dia como teaser honesto.
- **Pendências geradas**: as 4 specs em `draft` esperam a revisão do Daniel; a Fase 5 depende
  de T-073/T-074 (Plan + catálogo servido) para o M2 e de T-063/T-064 para o gate do M4.
  Missões, ligas e push ficaram explicitamente em Evolução (cada um tem custo próprio).

## 2026-07-30 (14) · T-085 — Aviso de cena: o que a pessoa não vê do outro lado do celular

Pedido do Daniel na mesma conversa do probe: "celular a gente sempre suja a câmera, deixa
iluminação baixa e tal" — um aviso que orienta, **não impede**, e só na tela de Início, onde a
câmera já abre para teste antes de ir treinar.

- **Escopo travado antes de codar**: orienta e nunca bloqueia (o CTA não muda); só na
  pré-configuração; um canal só — o pill que já existe dentro da janela da câmera, que passa a
  mostrar o conselho no lugar da dica de enquadramento enquanto ele valer. Enquadramento a
  silhueta-guia já ensina sozinha; luz e lente suja são o que ninguém enxerga de onde está.
- **Roda no cliente porque SÓ pode rodar lá**: no modo edge nenhum pixel sobe (keypoint-first),
  então o servidor não tem o que olhar. Amostra de 160×120, 1×/s, num canvas fora do DOM —
  ~19k pixels contra as 15 inferências de pose por segundo que rodam no mesmo vídeo.
- **Os limiares saíram de medição, e a medição mudou o desenho duas vezes.** Sem corpus de cena
  ruim (o Daniel não quer gravar agora), o que deu para fazer foi medir os 3 vídeos do
  `eval/corpus` como estão e em variantes sintéticas (escurecidas ×0,25, borradas com boxblur 6)
  via ffmpeg, com exatamente as contas do cliente:

  ```
  vídeo            luz    estourado  varLaplaciano
  01 como está    244,6      92,8%          1792
  01 escurecido    60,9       0,0%           119
  01 borrado      244,7      89,2%           173
  02 como está    136,7       0,0%          2627
  02 borrado      136,7       0,0%           373
  03 como está    124,4       0,6%          2003
  03 borrado      124,2       0,6%           559
  ```

  - **Normalizar o laplaciano pelo contraste não serve para comparar cenas.** Era o meu plano
    inicial, porque a razão `varLap/contraste²` é imune à luz (o vídeo 01 vai de 1,32 a 1,40 ao
    ser escurecido). Só que entre cenas ela é inútil: o vídeo 03 **nítido** dá 0,15 e o vídeo 01
    **borrado** dá 0,16 — o limiar reprovaria a cena boa. A nitidez passou a usar o laplaciano
    cru, com **luz boa como pré-condição** — que é o que impede confundir escuro com borrado,
    já que escurecer também derruba o laplaciano (1792 → 119).
  - **Estouro alto não é contraluz.** O vídeo 01 tem 92,8% de pixels saturados e é cena BOA:
    fundo claro com a pessoa bem iluminada (o centro mede 244 também). Contraluz é fundo claro
    com sujeito ESCURO — a regra passou a olhar o centro do quadro, onde a silhueta-guia põe o
    corpo. Sem isso, o primeiro vídeo do corpus levaria um aviso errado.
- **Debounce de 2 amostras para acender E para apagar** (SPEC-003 pede 1s para ligar; nós
  amostramos 1×/s): alguém passando na frente da luz não dispara nada, e uma amostra boa solta
  não apaga um aviso que continua valendo.
- **A mensagem não afirma a causa.** Imagem sem detalhe pode ser lente suja, foco errado ou
  pouca luz; "Imagem sem nitidez · limpe a lente" pede a ação que resolve os três e custa 5
  segundos. Frases do tamanho da que já vive no pill (38 caracteres) — ele mora dentro da janela
  de 202px, e um parágrafo ali viraria outro problema.
- **Testes**: 15 novos em `sceneQuality.test.ts`, com os dois casos do corpus virando teste —
  "estouro alto com centro claro NÃO é contraluz" e "no escuro a queixa é a luz, nunca a
  nitidez". Mais parede lisa não virando acusação de lente suja.
- **Gates**: lint, typecheck e 360 testes verdes.
- **Não verificado**: a aparência do aviso em aparelho real. A extensão do browser caiu no meio
  da sessão, então a checagem visual (e o disparo com câmera de verdade) fica para o teste no
  celular. O risco de layout foi tratado na origem, encurtando as frases.
- **Pendências** (em Descobertas): faltam corpus de cena ruim e as métricas dentro do `evalctl`
  para o limiar sair da bancada e não de um script solto; e o aviso não é anexado ao relatório,
  que é o que a SPEC-003 pede para todo warning — sem isso a cena real dos usuários é invisível.

---

## 2026-07-30 (13) · T-084 — O probe media a câmera e culpava o aparelho

Relato do Daniel: iPhone bom, câmera boa, e o app escolhendo CLOUD quase sempre. A causa
estava numa linha do `measureProbeFps`:

```ts
if (video.currentTime !== lastVideoTime) { detectPose(...); frames += 1 }
probeFps = frames * 1000 / elapsed
```

- **O número só sobe quando chega frame novo.** Ou seja, `probeFps = min(fps da câmera,
  throughput do modelo)` — e no iPhone quem ganha essa disputa costuma ser a câmera: com pouca
  luz o iOS alonga a exposição e entrega 12–15fps. O probe lia 12, comparava com o limiar de 12
  e reprovava o APARELHO por causa da iluminação da SALA. `frameRate: {ideal: 30}` é dica, não
  garantia.
- **E o remédio era pior que a doença.** Cloud analisa JPEG de 320px a 10fps: cena escura fica
  PIOR lá, não melhor. Fora que são 3 vagas no semáforo (SPEC-009) — telefone capaz ocupando
  slot é slot faltando para quem precisa. Fica a regra: **cena ruim nunca é argumento para
  trocar de modo; é argumento para consertar a cena.**
- **A régua nova é latência**: mediana de ms por `detectForVideo`, que não depende da cadência
  da fonte. `fpsSustentavel = 1000 / mediana`. As 3 primeiras inferências saem da conta
  (compilação de shader chega a centenas de ms cada) e a janela estica de 2s para até 3s
  enquanto não houver 8 amostras — antes de estimar capacidade com quatro amostras, esperar
  mais 1s é barato.
- **Duas medidas, dois nomes.** A cadência da câmera continua medida, agora via
  `presentedFrames` do rVFC — contador do COMPOSITOR, que continua andando quando pulamos
  frames. Contar as nossas chamadas mediria o nosso gargalo e chamaria isso de "câmera lenta".
  Onde não há rVFC o número vira um piso, e o `cameraFpsSource` diz isso na cara: o aviso de
  cena da T-085 não pode acusar luz fraca em aparelho devagar.
- **O laço passou a ser o mesmo do pipeline** (`createVideoFrameLoop`, rVFC — como a SPEC-001
  já pedia). O probe tinha um `requestAnimationFrame` próprio, que é cadência de REPAINT: ele
  media o modelo através do compositor, e a tela onde o probe roda é a pré-configuração, com
  grade, varredura e — desde a T-080 — quatro painéis de desfoque sobre vídeo ao vivo.
- **Watchdog obrigatório junto do rVFC**: sem frame de câmera o callback nunca dispara e a
  promessa nunca resolveria — o app ficaria preso em "calibrando o dispositivo", sem erro e sem
  saída. Tem teste.
- **`sem_medida` agora vale EDGE, não CLOUD.** Ausência de evidência não é evidência contra: sem
  frame de câmera não há o que mandar ao servidor tampouco, então cloud não remedia esse caso.
  Falha COM exceção continua indo para cloud, onde o servidor é alternativa real. Mudança de
  regra registrada na SPEC-001.
- **Motivo da decisão exposto** (`probe_ok`, `probe_lento`, `sem_webgl`, `sem_simd`,
  `probe_falhou`, `sem_medida`) e visível no chip de diagnóstico junto dos dois fps. Sem isso,
  "meu aparelho vai para cloud" não tinha diagnóstico possível em campo.
- **Bug pequeno, efeito grande no iOS**: `detectWebgl()` criava um canvas, pegava contexto WebGL
  e nunca o devolvia. Roda a cada montagem do pipeline (parar/iniciar câmera, entrar e sair do
  treino), e o Safari de iPhone tem orçamento apertado de contextos vivos — contexto vazado aqui
  derruba o delegate GPU do MediaPipe mais adiante, que cai para CPU, que mede baixo, que vai
  para cloud. Agora chama `WEBGL_lose_context`.
- **Testes**: `runProbe.test.ts` novo, com câmera falsa. O caso central é "câmera a 10fps +
  modelo a 5ms" — a régua antiga reprovaria, a nova aprova e ainda reporta a câmera lenta em
  separado. Mais: modelo lento acusa modelo lento; frames apresentados contam mesmo quando não
  processados; sem frame nenhum resolve com `samples: 0`; exceção marca `failed`.
- **Gates**: lint, typecheck e 345 testes verdes.
- **Pendências** (em Descobertas do BACKLOG): o contrato tem campo para UM fps, então o fps de
  câmera não sobe — sem telemetria não há como calibrar o limiar de 12fps com dado real; e o
  próprio limiar sobreviveu à troca de régua sem revisão, o que é dívida consciente.

---

## 2026-07-30 (12) · T-082 — Figura de exercício por slug (e a trava para exercício novo)

O Daniel gostou do bonequinho neon e reparou que só havia o de polichinelo: o Agachamento
mostrava, no card Exercício da pré-configuração, um boneco de braços pro alto. Pedido em duas
partes — trocar a figura do card **e** deixar o mecanismo pronto para exercícios futuros.

- **A causa não era o desenho, era o reaproveitamento.** O card usava `IconLogo`, que é a
  assinatura da marca da T-081. Um componente servindo a dois donos (marca fixa por decisão de
  produto; figura que deve variar por exercício) só podia obedecer a um. Agora são famílias
  separadas: `IconLogo` continua sendo a marca, e a seção "figuras de exercício" do
  `ui/icons.tsx` traz `IconExJumpingJack`, `IconExSquat` e `IconExStanding`. A do polichinelo
  nasce com os mesmos pontos do logotipo — duplicação aceita de propósito, para a próxima
  mudança no logotipo não mexer numa pose de exercício.
- **`ui/exerciseFigures.ts` é o registro, e é o único lugar onde se adiciona.** Slug → figura,
  mais `FIGURA_PADRAO` (a neutra em pé). O componente `ui/exerciseIcon.tsx` só faz a ponte com
  o JSX; a separação em dois arquivos veio do aviso de fast refresh do ESLint (módulo que
  exporta componente E constante) e saiu melhor: o registro sendo dado puro é o que deixa o
  teste lê-lo sem renderizar nada — a suíte roda em `environment: node`, sem DOM.
- **A parte que o Daniel pediu de verdade: exercício novo ser "reconhecido".** É o
  `ui/exerciseIcon.test.ts`, que cruza `EXERCISE_KEYS` com `EXERCISE_FIGURES` nas duas direções
  (exercício sem figura, figura órfã) e falha nomeando o slug. Conferido injetando um `flexao`
  falso no catálogo: `exercícios sem figura em EXERCISE_FIGURES: flexao`. O bug consertado aqui
  é de processo — o agachamento entrou no catálogo em T-051 e nada no repositório lembrava que
  faltava desenhar a pose dele. Ponteiro para o registro também no cabeçalho do `catalog.ts`,
  que é onde a pessoa chega primeiro.
- **A medição derrubou o meu próprio desenho.** O primeiro agachamento tinha joelhos dobrados
  para fora, corretos, e razão largura/altura 0,65 contra 0,60 do polichinelo — a 22px as duas
  silhuetas eram a mesma mancha. O que distingue figura pequena é a proporção, não o traço.
  Cabeça foi de `cy=4.5` para `cy=7`, pés e braços abriram: **17×22 contra 14×23,5, razão 0,77
  contra 0,60**, topo começando 2,5 unidades mais abaixo. A regra que fica está no comentário
  da `IconExSquat`.
- **Verificação no caminho real** (`/app/#/preparar`, trocando `digitalfit.exercise` no
  localStorage), não só no componente: com `squat` o card renderiza `cy=7` e silhueta de razão
  0,77; com `jumping_jack`, `cy=4.5` e o `d` do X. Nos dois, 22×26px, `rgb(77,210,255)` e o
  mesmo `drop-shadow` — nenhuma linha de CSS foi tocada, a classe `.prep-cell__ex-icon`
  continua mandando. `computer screenshot` travou de novo (quirk já conhecido); a evidência é
  `getBBox`/`getComputedStyle`.
- **Gates**: `npm run lint`, `npm run typecheck` e `npm run test` (32 arquivos, 331 testes)
  verdes. Nada de Python foi tocado.
- **Pendências geradas**: a silhueta-guia da câmera continua em pose de polichinelo para todo
  exercício — é uma instrução na tela, não decoração, e incomoda mais que o card; proposta
  T-083. E a asserção de proporção mínima entre figuras, quando houver uma terceira. Ambas em
  Descobertas do BACKLOG.

---

## 2026-07-30 (11) · T-079/T-080/T-081 — Melhorias de UI pedidas pelo Daniel

Três pedidos depois de usar o app: o histórico do Perfil comendo a tela, o "Sair" parecendo o
botão certo de tocar, a câmera da pré-configuração pequena demais e o app sem marca.

- **T-080 · A câmera passou a ser a tela inteira e a moldura virou um recorte.** O vídeo vai a
  `inset: 0` e quatro painéis com `backdrop-filter: blur(16px) brightness(.42)` desfocam tudo
  que está fora da janela nítida. Os cards não se mexeram um pixel — passaram a flutuar sobre a
  área desfocada, que é justamente o que lhes dá contraste. Medido no browser: janela nítida
  202×719 no mesmo lugar de antes, painéis cobrindo 64px em cima, 150 embaixo e 112/116 nas
  laterais, colunas intactas em 92/96.
  - **Quatro retângulos e não um painel com máscara**: máscara sobre `backdrop-filter` ainda é
    terreno instável no Safari de iOS e o custo de desfoque é o mesmo (a área somada é a mesma
    tela). O preço é a janela ter cantos quase retos (8px em vez de `--radius-cam`): com raio
    grande, os cantos vazariam imagem nítida por fora da borda. Está em §Desvios da SPEC-014.
  - **`-webkit-backdrop-filter` explícito** nestes painéis (o resto do arquivo usa só a forma
    sem prefixo): o Safari só dispensou o prefixo na versão 18, e o produto é usado no celular.
    Sem ele o painel vira vidro chapado — legível, mas sem câmera atrás.
  - **A armadilha da T-071 voltou de outra porta**: com o palco valendo a tela toda, os avisos
    da CameraView (`bottom: 46px`) pousariam sobre a tab bar — o mesmo bug que já custou dois
    consertos no treino. Ficaram presos à janela nítida (`.sess__cam--prep .stage__banner`).
  - **`isolation: isolate` no `.sess__cam`** por duas razões: os overlays internos têm
    `z-index` entre si e não podem passar por cima dos cards (irmãos DEPOIS no DOM), e o
    contexto vira o backdrop root — o que os painéis desfocam é a câmera, e só ela.
- **T-079 · Perfil.** Histórico virou janela de 182px com rolagem própria (~4 linhas e meia; a
  meia linha é o que diz "tem mais aqui embaixo") e contagem de sessões no título da seção.
  E a hierarquia dos botões foi invertida: **Fechar** é o primário preenchido, **Sair da conta**
  é texto discreto em `--hot`, atrás de uma linha separadora e de uma confirmação de dois
  toques. A regra que fica: num painel, o botão preenchido é a ação que a pessoa veio fazer —
  ação destrutiva não usa a forma do primário.
- **T-081 · Assinatura da marca** (`ui/BrandMark.tsx`) em Escolha, Guia, Pré-config, Treino,
  Progresso, Analytics, Perfil e Relatório. Discreta por construção (caps de 8px, opacidade
  .34) e sem espaço próprio no layout: nas telas de conteúdo ocupa a linha que já era margem do
  título; sobre a câmera flutua no topo-esquerdo, na faixa que o cabeçalho centralizado deixa
  livre — medido, a marca acaba em x=86 e o cabeçalho começa em x=158. `aria-hidden`: é
  decoração, não navegação, e o nome do app já está no `<title>`.
- **Gates**: `npm run lint`, `npm run typecheck` e `npm run test` (31 arquivos, 329 testes)
  verdes. Geometria conferida por medição no browser (`getBoundingClientRect`), não por
  screenshot.
- **Pendência**: o desfoque só se julga com câmera de verdade — a validação de aparência fica
  para o teste no celular. Se o custo do `backdrop-filter` sobre vídeo ao vivo pesar em aparelho
  fraco, o caminho barato é baixar o raio de 16px para ~10px antes de trocar de técnica.

---

## 2026-07-30 (10) · T-077 — O relatório errado: a sessão era ressuscitada por frames atrasados

O Daniel fez 20 repetições e o banco gravou "4 reps · no_data". O relatório da sessão vinha
errado havia tempo, e o log do worker contou a história inteira:

```
19:00:07  aberta (jumping_jack, edge, 30s)
19:00:09  calibrada
19:00:39  encerrada pelo servidor (completed) com 26 reps   ← a contagem estava CERTA
19:00:39  aberta por pose.frame (sem session.started)       ← 71 ms depois, ressuscitou
19:00:40  calibrada
19:00:53  encerrada pelo servidor (no_data) com 4 reps      ← sobrescreveu o relatório bom
```

- **A causa é a junção de três decisões, cada uma correta sozinha.** (1) O worker abre sessão
  ao receber `pose.frame` sem `session.started`, para que corrida de eventos não custe
  repetição. (2) O cliente segue capturando depois do fim — o `session.completed` ainda tem de
  atravessar Redis, gateway e WebSocket, e a câmera não para sozinha. (3) O report-builder faz
  upsert por `session_id`, que é o que torna o relatório reproduzível por replay (SPEC-010).
  Juntas: o frame atrasado abre uma sessão com o MESMO id, ela conta o que a pessoa fizer
  depois do "pare", morre de `no_data` 10 s depois e o upsert troca o relatório bom pelo ruim.
- **Havia um teste defendendo a causa.** O `test_frames_depois_do_fim_abrem_sessao_nova_do_zero`
  existe desde a T-009 com a justificativa certa ("não pode somar repetição a uma sessão
  encerrada") e a conclusão errada. Reescrito: agora exige que o frame seja DESCARTADO, e olha
  para as três coisas ao mesmo tempo (nenhuma sessão viva, um único `session.completed`,
  nenhuma repetição a mais).
- **Conserto no servidor**: lápide de sessão encerrada (`ENDED_MEMORY_MS = 120 s`) marcada em
  TODO caminho que remove a sessão — inclusive o `tick`, que é por onde o caso real passou (o
  timer autoritativo dos 30 s). A memória é podada por tempo, não por quantidade: por número, o
  esquecido seria justamente o mais antigo, que é quem já não recebe frame.
- **Conserto no cliente** (economia, não garantia): `streamsFrames(status)` — a condição de
  enviar deixa de ser "tem `sessionId`" e passa a ser o estado da sessão. O id sobrevive de
  propósito ao fim (a tela do relatório precisa dele), e era esse detalhe que mantinha o loop
  transmitindo. Vale para os dois caminhos, edge e cloud (neste, cada frame é um JPEG).
- **Verificado no stack de pé**, e não só na suíte: 20 reps sintéticas + 67 frames atrasados →
  `descartando frames atrasados` no log, **um** relatório no Postgres, `20 reps · completed ·
  20400 ms`. As linhas de teste foram apagadas depois.

Descoberta grande no caminho, registrada e não consertada aqui: `duration_ms` mistura o relógio
do servidor (`session.started`) com o do navegador (`session.calibrated`, frames) — sai errado
em silêncio e, com relógios muito distantes, mata o report-builder com `DataError: integer out
of range`. Foi assim que apareceu: publiquei o repro com dois relógios e derrubei o processo.
**T-078.**

Gates: `ruff check` + `pytest` (593) e `npm run lint`/`typecheck`/`test` (329) verdes.

---

## 2026-07-30 (9) · T-072 — O painel existe (e o gateway não o serve)

Primeira task da SPEC-018: ligar o admin do Django e mais nada. Nenhum modelo de configuração
entra aqui — `Plan` e `Exercise` são T-073/T-074.

- **O que ligar custou, medido e não estimado**: 3 apps (`admin`, `sessions`, `messages`), 5
  middlewares, e os `context_processors` que estavam **vazios** (`settings.py`) — sem
  `auth`/`messages` ali o Django recusa subir (`admin.E402`/`E403`). Os apps entram
  incondicionalmente, e só a ROTA é condicional: apps atrás de `DJANGO_ENABLE_ADMIN` dariam
  estado de migration diferente por processo, e o sintoma seria um `django_session` que não
  existe justamente na máquina onde alguém acabou de ligar o painel.
- **`is_staff` é campo novo, não apelido de `is_admin`.** As contas que já têm `is_admin` foram
  concedidas sob a promessa escrita, no próprio modelo, de que a flag "não dá acesso a dado de
  ninguém". Unir as duas promoveria em silêncio quem já a tinha. Tem teste dizendo isso.
- **`has_perm`/`has_module_perms` no `User` em vez de `PermissionsMixin`**: respondendo pela
  conta inteira, o `ModelBackend` nunca é consultado e `auth_permission`/`auth_group` continuam
  sendo as tabelas vazias de `[A/T-022]`. Consequência aceita: quem entra no painel vê tudo que
  está registrado — granularidade entra junto com o mixin, se houver um segundo perfil.
- **Migration antiga precisou de `run_before`.** O `LogEntry` do admin tem FK para o
  `AUTH_USER_MODEL`, e a `swappable_dependency` aponta para a PRIMEIRA migration do app — que
  aqui é a `0001`, de quando ainda não havia usuário (a conta nasceu na `0002`). Sem ordenar,
  `admin.0001` roda antes de existir `api.user` e o `migrate` morre com "Related model
  'api.user' cannot be resolved".
- **A trava do gateway é do processo, não da variável** (`core/admin_gate.py`): o `ROOT_URLCONF`
  é o mesmo para os dois, e separar só por env cairia no dia em que alguém movesse
  `DJANGO_ENABLE_ADMIN` para o bloco compartilhado do compose. Verificado no compose de pé:
  `:8001/painel/` → 404, `:8001/healthz` → 200.
- **`is_staff` é somente leitura dentro do painel.** Conceder painel é a única escalada que o
  painel não faz sozinho; sai por `admin_tools --panel-on`, que exige shell. `is_admin`, esse
  sim, o painel concede.
- **`SessionResult`/`SessionClaim`/`LogEntry` entram somente leitura.** Editar um relatório à
  mão criaria uma linha que nenhum replay reproduz — a SPEC-010 promete o contrário.
- **Estáticos por whitenoise + `collectstatic` no build da imagem**, e não pelo nginx: o nginx
  da frente é o do Daniel e não é versionado aqui. Verificado no ar: `/static/admin/css/base.css`
  responde 200 com 22 kB.
- **Verificado no caminho real**, com o compose de pé: login por cookie + CSRF, índice do painel,
  troca de senha, `add` de conta, `sessionresult/add/` → 403, `/admin/` → 404. A conta de teste
  foi apagada ao fim.

Duas descobertas grandes, ambas no BACKLOG: a suíte **não** roda em SQLite (roda no Postgres do
compose, e a CI provavelmente está vermelha — T-076), e teste de formulário não cobre tela de
admin (o `add` de conta respondia 500 com o formulário passando nos testes).

Gates: `ruff check` + `ruff format --check` + `pytest` (591 testes) verdes; imagem do server
buildando com `collectstatic`.

---

## 2026-07-30 (8) · SPEC-018 + ADR-011 — Painel de administração e plano de configuração

Sessão de projeto, sem código. O Daniel quer trazer configuração (recursos do Free, do pago
etc.) para o admin do Django; o pedido virou spec completa.

- **O admin não existia por decisão, não por esquecimento.** `api/models.py:64` e a descoberta
  `[A/T-022]` registram o corte: `AbstractBaseUser` sem `PermissionsMixin`, `contrib.auth` só
  pelos hashers, "não há admin nem permissões". A decisão estava certa para o projeto de então —
  todo parâmetro era ou calibrado contra corpus (muda por commit e bancada) ou infra (muda por
  env). A SPEC-016 cria a primeira categoria nova: capacidade de plano é decisão comercial. Daí
  ADR-011 como *mudança de premissa*, não como correção de erro.
- **A restrição que desenhou tudo**: workers não têm ORM (ADR-008) e a SPEC-010 promete relatório
  derivável 100% por replay. Config lida do banco pelo worker faria o mesmo replay dar resultados
  diferentes, em silêncio. Regra da spec: **resolve na API, carimba no `session.started`** — que
  já é como `duration_s` e `countdown_s` funcionam. Para o que não é por sessão (textos de
  feedback), o caminho é snapshot no Redis escrito pelo Django, e fica para a Fase Evolução.
- **Fronteira explícita do que NÃO entra no painel**: limiares de FSM e de cena, normalização e
  filtros — a bancada da SPEC-012 varre os defaults do código, e valor mudado por formulário não
  tem fixture, muda contagem em silêncio e contamina o Parquet. Se um dia precisar variar, é
  perfil versionado carimbado na sessão, não campo solto.
- **Custo de ligar o admin levantado no código**, não estimado: 3 apps, 4 middlewares,
  `context_processors` hoje vazio (`settings.py:70`, o admin recusa subir sem `auth`/`messages`),
  `is_staff` novo no `User`, estáticos sem whitenoise nem rota no nginx, e `ROOT_URLCONF`
  compartilhado com o gateway — sem gate, o painel apareceria no processo de WebSocket.
- **`is_staff` novo em vez de reusar `is_admin`**: o docstring de `is_admin` promete que a flag
  "não dá acesso a dado de ninguém". Contas já concedidas sob essa promessa não podem virar
  acesso ao painel retroativamente.

Pendências geradas: T-072 (ligar o admin), T-073 (`Plan` + resolvedor), T-074 (`Exercise` +
`GET /api/config`), T-075 (`config_version` no evento e no relatório). T-063 e T-064 foram
reescritas para ler do `Plan` em vez de nascerem com constante nova — se forem feitas antes da
T-073, terão de ser reabertas.

---

## 2026-07-30 (7) · T-071 — Porcentagem de volta e o HUD do treino sem colisao

Dois ajustes pedidos pelo Daniel depois de o gzip entrar em producao, com foto do celular.

- **A porcentagem sumiu porque o gzip funcionou.** Meu guarda da T-070 zera o total quando a
  resposta vem comprimida (`Content-Length` e tamanho de rede; os bytes contados saem do stream
  descomprimido). Com gzip ligado, isso passou a valer sempre — e sobrava "3,4 MB baixados", sem
  denominador. Verificado que nao ha saida pelo servidor: sob gzip o nginx responde SEM
  `Content-Length` nem no GET nem no HEAD, e o `fetch` do browser proibe pedir `identity`
  (`Accept-Encoding` e cabecalho proibido).
- **Conserto**: o tamanho passa a vir de quem conhece os arquivos — o build.
  `scripts/setup-mediapipe.mjs` escreve `public/pose-assets.json` (nome → bytes DESCOMPRIMIDOS),
  e o cliente casa por basename, nao pela URL inteira, porque o caminho do wasm sai do
  FilesetResolver e pode vir absoluto ou com query. O `Content-Length` por HEAD fica como
  fallback para o caso sem manifesto e sem compressao. Total real medido: **16,5 MB** — o mesmo
  numero que o Daniel viu no waterfall.
- **O HUD embaralhado tinha uma causa de unidade.** A pilha do rodape e em px a partir de baixo,
  mas os cards de angulo/calorias estavam em `top: 46%`. Em tela alta os 46% caiam exatamente
  sobre a faixa dos avisos: na foto, o texto do modo cloud sai por baixo dos dois cards,
  ilegivel. Agora os quatro cards ficam em px fixos (64 e 188), o que torna a distancia entre os
  grupos independente da altura do aparelho — e agrupa os numeros no terco de cima, que serve ao
  objetivo de ler a 2 metros e deixa o meio da imagem livre.
- **Instrucao modal passou a mandar na tela.** `stage__prepare` ganhou `z-index` (os avisos do
  palco vinham depois no DOM e pintavam por cima da frase "Bracos ao lado do corpo…") e, durante
  a medicao, o cromo flutuante sai: cards, pill e aro somem. Todos mostravam `0`, `--` e o tempo
  cheio — nada contava ainda, e juntos eram o que tornava a tela ilegivel. Ficam o cabecalho, o
  toast do coach (que explica POR QUE a medicao nao fecha — na foto, "voce saiu do quadro") e a
  barra com o stop.
- **Aviso de cloud encurtado**: a versao longa explicava probe, extracao no servidor e ausencia
  de esqueleto em tres linhas. O "por que" e diagnostico e ja vive no chip de dev (o `*` de
  `forced`); no produto ficou uma linha com o que muda para quem treina. Tambem sai de cena
  durante a medicao.
- Medido no browser com todos os elementos presentes ao mesmo tempo, nos dois estados: medindo
  (cards/pill/aro ocultos, nada por cima da instrucao) e em andamento (folgas de 12 a 350px,
  nada por cima do aviso de cloud). Manifesto verificado no dev server, no `dist` e servido pelo
  nginx (200, `application/json`).
- A foto tambem confirmou, de passagem, o que a T-069 levantou como hipotese: **o aparelho do
  Daniel esta caindo em modo CLOUD** ("a analise roda no servidor") e recebendo `OUT_OF_FRAME`
  por estar perto demais da camera. Nao e bug — e o probe decidindo — mas explica a ausencia de
  esqueleto na tela dele.
- Gates: `tsc -b`, `eslint`, `vitest` 326/326 (3 novos em `assetWarmup`), build.

### Fechamento da sessão

Documentação varrida no fim: `docs/DEPLOY.md` ganhou a política de cache por caminho (a pergunta
"por quanto tempo o cache vale" tem resposta em quatro camadas, e `max-age=3600` NÃO significa
rebaixar em 1h — significa revalidar com `304` de 0 bytes); `web/README.md` foi corrigido, porque
dizia que `npm run dev` sobe o app em `localhost:5173` e desde a T-067 a raiz é o SITE (o app está
em `/app/`), além de ter a árvore de `src/` atualizada e o aviso morto sobre `hud/placeholders.ts`
substituído pela regra que vale hoje; o README da raiz aponta os dois bundles.

Gates finais de toda a stack: web (`tsc -b`, `eslint`, 326/326, build) e Python (`ruff` limpo,
`pytest` 577 passando) — o núcleo Python não foi tocado nesta sessão e continua verde.

Estado para a próxima sessão: T-067…T-071 done. Pendências no BACKLOG §Descobertas, em ordem de
valor: pré-carregar WASM/modelo antes da câmera (a maior melhoria de percepção que sobrou no
funil), gerar os `.gz` no build para o `gzip_static` pagar, capa da câmera desligada repetindo
escolhas no `#/treino`, caminho do WASM sem versão impedindo `immutable`, e `pose-assets.json` sem
política de cache. Nada bloqueia treinar.

## 2026-07-30 (6) · T-070 — A compressao nao existia em producao: `gzip_http_version` x `proxy_pass`

O Daniel testou depois do commit anterior: total ainda 16 MB, e recarregar a pagina baixava o
WASM de novo. Perguntou se o nginx da VPS afetava algo. Afetava — era a causa.

- **Causa raiz, reproduzida localmente em um comando**: `gzip_http_version` vale **1.1** por
  default, e `proxy_pass` fala **HTTP/1.0** com o upstream por default. Atras do nginx da VPS, o
  nginx do container RECUSAVA comprimir tudo — nao so o `.wasm`, tambem o CSS e o JS que a config
  antiga achava que comprimia desde sempre. Medido com o mesmo arquivo e a mesma config:
  HTTP/1.1 direto → `Content-Encoding: gzip`, 3,2 MB; HTTP/1.0 → 11.532.084 bytes, **o mesmo
  numero do waterfall do celular**. Foi o `curl --http1.0` que fechou o caso.
- **Licao sobre a minha verificacao anterior**: eu testei a config com `curl` HTTP/1.1 direto no
  container e declarei "verificado na imagem real". Estava certo sobre a imagem e errado sobre o
  CAMINHO — em producao ninguem fala HTTP/1.1 com aquele container. Verificar o componente nao e
  verificar a integracao.
- **Conserto**: `gzip_http_version 1.0` + `gzip_proxied any` (este cobre o vizinho: com `off`, o
  default, nginx nao comprime requisicao com cabecalho `Via` — o que aparece no dia em que um CDN
  entrar na frente) + `gzip_vary on` (com proxy no meio, resposta comprimida tem de se anunciar
  como variante). Verificado por HTTP/1.0 e com `Via` presente: 3,2 MB nos dois.
- **O cache tambem era o tamanho, nao o header.** O servidor esta correto: requisicao condicional
  devolve `304` com 0 bytes (verificado no `.wasm` e no `.task`). O que acontecia e que o
  navegador nunca GUARDAVA a entrada — o cache de disco do Chromium recusa entradas acima de uma
  fracao do tamanho total, e 11,5 MB passa desse limite. A prova estava no proprio waterfall do
  Daniel: com as MESMAS diretivas de cache (e o mesmo bloco `location`) e na mesma visita, o
  modelo de 5,5 MB voltava de `disk cache` em 15 ms e o WASM de 11,5 MB era baixado inteiro. A
  unica variavel era o tamanho. Comprimido (3,2 MB) ele cabe e passa a ser guardado — ligar o
  gzip nao e so "primeiro acesso mais rapido", e o que faz existir um segundo acesso barato.
- Nada a mudar no nginx da VPS: `proxy_http_version 1.1` no `location /` seria equivalente e vale
  pelo keepalive, mas o conserto no container cobre qualquer proxy — inclusive um que o projeto
  nao controla.

## 2026-07-30 (5) · T-070 — O mesmo WASM baixado duas vezes (regressão da T-069)

Waterfall do primeiro acesso trazido pelo Daniel:

```
vision_wasm_internal.wasm   11.532 kB   33,25 s
vision_wasm_internal.wasm   11.532 kB   40,07 s
```

- **Regressão minha, na T-069.** O MediaPipe baixa o WASM DENTRO de `createFromOptions`. Como
  `createEdgePoseLandmarker` tenta GPU e depois CPU, e o prazo de 12s corta a primeira tentativa
  enquanto o download dela ainda está no ar, a segunda tentativa começava um SEGUNDO download do
  mesmo arquivo de 11,5 MB. Os dois dividiam a banda — daí 33s e 40s — e um deles ia para o lixo
  (`aoChegarTarde` fecha o landmarker que chega tarde, mas os bytes já foram gastos).
- **Conserto**: `pose/assetWarmup.ts` tira o download de dentro da tentativa. Baixa uma vez, em
  sequência, para o cache HTTP; só então as tentativas de delegate acontecem — e passam a custar
  compilação, não rede. O `fileset` é resolvido UMA vez e reaproveitado nas duas tentativas: é
  dele que sai `wasmBinaryPath`, o caminho exato do binário, sem adivinhar qual dos três `.wasm`
  do diretório o navegador vai querer (confirmado na `vision.d.ts` do pacote).
- **O prazo continua**, e agora é seguro: com os bytes em cache, tentar CPU depois da GPU não
  custa outro download. Era o aquecimento que faltava para o prazo da T-069 não ter efeito
  colateral.
- **Progresso na tela**: com o download nas nossas mãos, a tela passou a dizer quanto falta
  ("43% · 7,4 de 17,3 MB"). São 17 MB no primeiro acesso; a diferença entre isso e uma tela muda
  é a diferença entre esperar e achar que travou.
- Cuidado que evitou um bug futuro: `Content-Length` é o tamanho NA REDE e os bytes contados
  saem do stream já descomprimido. No dia em que o gzip do `.wasm` for ligado, comparar os dois
  daria "340%" — 11,0 MB lidos contra 3,2 MB anunciados. `totalBytes` devolve `null` quando vê
  `Content-Encoding`, e `warmupLabel` mostra só os MB recebidos quando o total não descreve o
  que está sendo lido.
- Falha de aquecimento nunca sobe: se a rede oscilar ou o `fetch` for bloqueado, o MediaPipe
  baixa por conta própria como sempre fez. Este módulo é otimização e informação, não um novo
  ponto de falha no caminho de treinar.
- Gates: `tsc -b`, `eslint`, `vitest` 323/323 (9 novos em `assetWarmup`), build.
- Confirmado no waterfall do Daniel: a compressão do `.wasm` **não** estava ativa (11.532 kB
  transferidos = tamanho cru).
- **Compressão aplicada em seguida, a pedido dele**, no `docker/web-nginx.conf`: `gzip_static on`
  (serve `.gz` pronto quando existir) + `application/wasm` no `gzip_types` (rede de segurança que
  comprime na hora). Verificado NA IMAGEM `nginx:1.27-alpine`, não no papel: `nginx -V` tem
  `--with-http_gzip_static_module` (sem isso a diretiva derrubaria o container), `nginx -t` passa
  sem avisos, o `dist` real servido devolve `Content-Encoding: gzip` com **3,2 MB** contra 11,0,
  o descomprimido é byte a byte idêntico ao original, o `.task` continua sem comprimir e o
  fallback de rota do `/app/` segue respondendo 200. O bloco `types` próprio saiu: o mime.types
  do nginx 1.27 já traz `application/wasm` (linha 55), e declarar de novo só geraria aviso de
  extensão duplicada.

## 2026-07-30 (4) · T-069 — "Paramos de te ver na câmera" não era a câmera

O Daniel trouxe o teste que fechou o diagnóstico: **em aba anônima nunca conseguia treinar; em
aba normal funcionava, na mesma posição e no mesmo aparelho.** Trocar de aba consertava.

- **O que a aba anônima elimina**: pose-worker morto ou modo cloud quebrado derrubariam as duas
  abas (mesmo servidor). Trial/conta daria erro explícito e abriria a folha de conta.
  Enquadramento não se conserta trocando de aba. Sobra cold start — e aba anônima é cold start
  permanente: cache HTTP vazio **e** sem cache de shader da GPU em disco.
- **Causa raiz**: a sessão era pedida em `cameraStatus === 'ready'`, o MESMO sinal que dispara o
  carregamento do pipeline. O servidor conta os 10s de `no_data` desde a admissão (SPEC-009),
  e entre a câmera abrir e o primeiro `pose.frame` sair o cliente ainda precisa baixar 11,5 MB
  de WASM + 5,8 MB de modelo, compilar, inicializar a GPU e gastar 2s no probe. Com cache
  frio o prazo estourava antes do primeiro frame — e a mensagem culpava a câmera por não ver
  ninguém que estava ali, parado, no lugar certo.
- **Conserto (o estrutural)**: `session/pipelineGate.ts` — `podeAlimentarSessao()` exige
  landmarker de pé e probe decidido, e é ele que liga o `useSession`. Quem pede a sessão declara
  que pode alimentá-la; registrado como contrato na SPEC-009 §critério 4 e na SPEC-001.
- **Segundo buraco, achado no caminho**: `createEdgePoseLandmarker` caía para CPU só quando a
  GPU **rejeitava**. Inicialização de GPU que trava não rejeita — ficava pendente para sempre,
  sem fallback e sem erro. Agora toda criação tem prazo de 12s (`lib/deadline.ts`), e o valor
  que chega tarde é fechado (dois contextos de GPU vivos seria pior que nenhum). Prazo
  deliberadamente generoso: depois do portão, lentidão não é mais fatal — o prazo existe para
  pegar "travado", não "devagar". Cortar em 4s empurraria para CPU um aparelho que ia funcionar,
  e CPU costuma medir < 12fps no probe, o que jogaria a sessão para CLOUD sem necessidade.
- **Terceiro**: a tela ficava MUDA durante o aquecimento — justamente a janela de vários
  segundos do primeiro acesso. Agora diz "Preparando a análise neste aparelho…" com a nota de
  que o modelo é baixado uma vez, "Calibrando o dispositivo…" no probe, e a falha aparece em vez
  de virar espera infinita.
- Medições que sustentam o diagnóstico (não estimativas): 11.532.084 bytes de WASM +
  5.777.746 do modelo = **17,3 MB** no primeiro acesso, sem gzip em produção. O `.wasm`
  comprime para **3,2 MB** (o `.task`, 5,5 → 4,7 MB) — o comentário do `web-nginx.conf` que diz
  que os dois já são comprimidos é falso para o `.wasm`. O gzip ficou fora desta task a pedido
  do Daniel (ele aplica no nginx); anotado no BACKLOG com os números.
- **Honestidade sobre uma medição minha**: tentei cronometrar a criação do landmarker pelo
  browser e vi passar de 40s. Era artefato da ferramenta de automação, não do app — o console
  mostrou o grafo subindo e fechando normalmente. O diagnóstico se sustenta pelos bytes medidos
  e pela ordem no código, não por aquele número.
- Gates: `tsc -b`, `eslint`, `vitest` 314/314 (12 novos: `pipelineGate`, `deadline`).
- Pendências geradas: pré-carregar WASM/modelo antes de a câmera abrir (o portão tirou a falha,
  não a espera) e o gzip do `.wasm`.

## 2026-07-30 (3) · T-067/T-068 — Fronteira SITE|APP, tab bar nova e o rodapé do treino (de verdade)

Segundo teste do Daniel em aparelho real. O relato: "na parte de baixo onde tem o botão ainda
está ficando algo por cima". A queixa de detecção do mesmo relato era conexão de internet —
confirmado por ele, nada a corrigir no pipeline.

- **O rodapé tinha DUAS causas, e a primeira revisão só pegou uma.**
  1. *Posição*: os avisos da CameraView (`.stage__banner`, `bottom: 46px`) e o chip de
     diagnóstico (`bottom: 12px`) moram no palco da câmera — que no treino é a tela inteira.
     "Conectando ao servidor…" pousava exatamente sobre o botão de play. O CSS culpado não
     está na tela de treino, e foi por isso que sobreviveu ao conserto anterior.
  2. *Ordem de pintura*: `.live__fade-bottom` — o gradiente de legibilidade, quase opaco —
     tinha `z-index: 2` dentro de `.live__chrome` e pintava **por cima** do player e da barra.
     É a explicação do "parece ter se misturado com outro componente": o botão estava lá,
     coberto por preto a 96%. Corrigido tirando o `z-index` (os gradientes são os primeiros no
     DOM, logo ficam atrás por ordem natural).
- **Rodapé virou uma pilha única, medida no browser** com todos os elementos presentes ao
  mesmo tempo e no pior caso de texto (aviso de duas linhas + dica de três): barra+FAB (0) ·
  pill (100px) · toast (176px) · avisos (260px) · chip de dev (348px), folgas de 12 a 17px.
  Verificado também que o toque no centro do FAB chega ao botão (`elementFromPoint`).
- **T-068 — tab bar nova**: Início · Progresso · Analytics · Perfil, com "Início" = a
  pré-configuração. No treino a MESMA barra ganha o play/stop no meio (FAB), e o player
  flutuante de 4 botões saiu: ⏮/⏭/música eram placeholders desabilitados, e era o
  posicionamento absoluto deles que gerava a colisão. Progresso e Analytics ganharam tela em
  vez de toast "em breve" — Progresso mostra o último treino persistido (validado no browser
  com o relatório real da sessão anterior: 26 reps, 52 rep/min, 30s), Analytics reabre a
  análise da sessão (`reopenReport`) e declara o que falta.
- **T-067 — SITE e APP são dois bundles** (ADR-010): `web/index.html` (landing + Sobre) e
  `web/app/index.html` (funil de treino), um build só. Medido: site 8,8 kB × app 239 kB — quem
  abre a landing parou de baixar MediaPipe e a máquina de sessão para ler um texto.
- Decisões da fronteira:
  - **`localStorage` é por origem, e isso manda no desenho.** Conta, preferência de exercício
    e `guide_seen` pertencem ao APP. Então o site não decide nada: aponta a intenção por duas
    pontes — `#/ex/:slug` (o app aplica a regra da SPEC-015 e escolhe Guia ou Pré-config) e
    `#/entrar` (o app abre a AccountSheet) — e as duas trocam a rota com `replace`, para o
    histórico não guardar um passo que só sabe redirecionar. "Entrar" no site é um link para o
    app, não um formulário: login no host errado não valeria no outro.
  - **Links que atravessam a fronteira são `<a href>`**, montados por `shell/origins.ts` a
    partir de `VITE_SITE_URL`/`VITE_APP_URL` (default `/` e `/app/`). São `VITE_*` porque a
    decisão é de build: o bundle do site não tem como descobrir em runtime onde o app foi
    servido.
  - **Deploy pronto para subdomínio sem exigi-lo hoje**: `SITE_DOMAIN`/`APP_DOMAIN` no
    `.env.prod` ligam o modo `site.dominio` | `app.dominio` — o `prod.sh` grava as origens no
    bundle, põe os dois hosts no `ALLOWED_HOSTS`/CORS (senão a API recusa o `Host` e o celular
    só mostra "sem conexão") e imprime os server blocks. No nginx só a **raiz** do host do app
    é reescrita para `/app/index.html`: mapear o host inteiro faria o navegador pedir
    `/app/assets/…` e tomar 404, porque o HTML referencia `/assets/…` absoluto.
  - Roteadores separados de propósito (`shell/nav.ts` × `site/nav.ts`): compartilhar o union
    de rotas obrigaria cada bundle a conhecer as telas do outro, e a fronteira vazaria pelo tipo.
- Verificado no browser: pilha do rodapé medida, funil site→app ponta a ponta
  (card do site → `#/ex/squat` → preferência gravada → `#/preparar`, e o back volta ao site em
  um passo), `#/entrar` abrindo a folha de conta, e as quatro telas do app.
- Gates: `tsc -b`, `eslint`, `vitest` 302/302 (14 novos: `shell/nav`, `shell/origins`,
  `site/nav`), `npm run build` com os dois entry points.
- Pendências geradas (no BACKLOG): a capa da câmera desligada repete ExercisePicker/
  CountdownSetting dentro do `#/treino` (ruído herdado da SPEC-013), e o chip de dev pode
  encostar nos cards do meio em telas mais baixas que ~740px.

## 2026-07-30 · SPEC-014…017 + T-056…T-062 — Plano de evolução e UI v2 completa

- **Planejamento documentado primeiro** (pedido do Daniel): SPEC-014 (Interface v2 —
  vinculante, réplica do protótipo Claude Design "Evolução UI v2" + `app-completo-mobile.png`
  + `index.png`), SPEC-015 (Primeiro Acesso Guiado: Index → Escolha → Guia → Treino),
  SPEC-016 (Free × Assinatura — *futura*), SPEC-017 (Perfil físico & progresso realista —
  *futura*). Plano-mestre em `docs/PLANO-UI-V2.md`; Fase 4 no BACKLOG (T-056…T-066).
- **Imagens geradas no Kairogen** (seedream-v4, 8 créditos; ~35 restantes): hero do index e
  passos do guia (polichinelo ×2, agachamento ×2), personagem consistente via reference
  image, comprimidas para ~80KB em `web/public/img/`.
- **UI v2 implementada** (T-056…T-062): tokens novos (Manrope/Space Grotesk, #05070d,
  azul/roxo/ciano, animações `df*`), roteador por hash (`shell/nav.ts`, sem dependência),
  tab bar flutuante de 4 itens (sem FAB), Index responsivo (mobile = tela 1; ≥900px =
  `index.png` com mini-HUD estático e footer), Escolha (cards com demo/badge/dot), Guia
  (SPEC-015, "visto" por exercício no localStorage), Pré-configuração (steppers funcionais de
  série/reps persistidos; duração TRAVADA nos 30s — autoridade do servidor; espelhar; grade +
  scan + silhueta ciano sobre a câmera ao vivo), Treino ao Vivo (HUD flutuante com anel de
  reps real, ângulo T-044, TimerRing, pill do exercício, player) e Sobre.
- Decisões:
  - **Pré-config e treino são UM componente** (`SessionScreen`) com a CameraView num slot
    estável (`.sess__cam`) e cromo absoluto por cima — trocar de tela não pode desmontar a
    câmera. A sessão só abre no `#/treino` (`useSession(camera && rota)`); a pré-config é
    espelho puro.
  - **Honestidade > fidelidade** (tabela de desvios na SPEC-014): FC e kcal mostram `--`
    (sem sensor/sem MET), player mostra **stop** e não pause (sessão de 30s é atômica),
    música desabilitada. Série/reps são metas cosméticas do HUD até a T-045.
  - Design system "Nocturne" do Claude Design **não** adotado (estética diverge do
    protótipo); os tokens vêm do próprio protótipo v2.
  - Google Fonts no `index.html`: offline degrada para system-ui — anotado na spec.
- Bug pego na verificação em browser: dois toques rápidos no stepper perdiam um incremento
  (closure velha) — corrigido com updater funcional + persistência em `useEffect`.
- Removidos os rascunhos `Index.tsx`, `ExecuteExercicies.tsx` e `hud/CardSelector.tsx`
  (substituídos pelas telas de `screens/`).
- Gates: `tsc` limpo, `eslint` limpo, `vitest` 288/288. Funil inteiro verificado no browser
  (mobile 375px e desktop 1280px), inclusive back do navegador e persistência do guia.
- Pendências: T-063…T-066 (Free/Assinatura, perfil físico, GIFs) ficam como specs futuras;
  duração configurável depende da SPEC-009 evolução; testar blur do HUD em aparelho real
  (degradar para fundo sólido se houver jank — SPEC-014 §Materiais).

**Mesma data, segunda rodada — ajustes do teste em aparelho real (SPEC-014 §Revisão):**

- Demo dos cards de exercício inteira (`contain` sobre `--bg`), sem corte.
- FC removida das duas telas (sem sensor = ruído); anel de reps maior (76px) e TEMPO
  RESTANTE promovido ao topo-direito — reps e tempo legíveis a ~2 metros.
- Card SÉRIE flutuante removido (info já está no subtítulo; colidia com o pill) e rodapé
  reespaçado com `env(safe-area-inset-bottom)` — o player ficava sob a barra do navegador.
- **Relatório sobrevive ao F5**: `report/lastReport.ts` persiste o último relatório
  (`digitalfit.last_report`); o store rehidrata no boot e reabre a folha se estava aberta;
  "Fechar" persiste fechado sem apagar os dados. Verificado no browser: reload com folha
  aberta reabre com os mesmos números; reload após fechar não reabre e mantém o dado.
- Gates: `tsc` + `eslint` limpos, `vitest` 288/288.

---

## 2026-07-29 · T-032 — Exercício 2: o agachamento

- Entregue: `exercises/squat.py` + 33 testes, `Code.SQUAT_TOO_SHALLOW` no contrato, mensagem
  no catálogo de feedback, entrada no catálogo do cliente (e portanto **selecionável** — o
  seletor da T-051 passou a desenhar de verdade).
- **A decisão que define o módulo: a feature não é o ângulo do joelho, e a SPEC-007 estava
  errada ao sugerir que fosse** ("agachamento: ângulo do joelho + profundidade do quadril").
  O joelho viaja para a frente e a câmera frontal — o enquadramento que a SPEC-003 pede em
  todo o produto — quase não vê esse eixo: 80° reais leem 133° no plano da imagem. Um limiar
  de `knee_angle < 90°` **nunca dispararia**. A spec foi corrigida.
  - O que se usa é a **altura do quadril** (quadril→tornozelo em torsos): 1,02 em pé → 0,64
    no fundo, monotônica, e sobrevive à normalização — a origem no quadril médio apaga a
    descida absoluta, mas não a perna encolhendo em relação ao próprio torso.
  - Divisor por frame, não da calibração. A lição da T-019 aplicada de novo.
  - `knee_angle_view` existe como feature, com `view` no nome de propósito: serve ao relatório
    e à bancada, e o nome grita que não é o ângulo do corpo. Tem teste travando que ele **não**
    serve de critério — para um "conserto" bem-intencionado falhar alto em vez de silenciar a
    contagem.
- Achado durante os testes: **o One Euro corta o fundo do agachamento acima de ~90 rpm**.
  Exato até 90, zero em 120 — e não é a FSM: o filtro entrega 0,727 contra o limiar de 0,72 e
  todo agachamento vira "raso". A 30 fps o mesmo ritmo volta a contar, o que fecha o
  diagnóstico. Os parâmetros do filtro foram medidos para o polichinelo, cujo pulso anda ~3
  torsos/s; o quadril anda bem menos. Não mexi no limiar de profundidade, que tem
  justificativa anatômica (coxa paralela ao chão) — o caminho certo é parâmetro por exercício
  na SPEC-006, e está nas Descobertas.
- No cliente, `main_angle: 'none'` para o agachamento e a célula "Ângulo" passa a mostrar
  `--`. Exibir o ângulo do braço durante um agachamento seria um número parado em ~12° o
  treino inteiro — e número imóvel enquanto a pessoa se esforça lê como "não está me vendo",
  que é a ansiedade que o esqueleto sobre a imagem existe para evitar (SPEC-013).
- **Limitação declarada, não escondida**: os limiares saem da geometria do gerador, não de
  vídeo de gente agachando (o corpus só tem polichinelo). São conservadores — o gerador não
  inclina o tronco e vídeo real inclina, o que aumenta o sinal. Virou **T-053**.
- Gates: `ruff` limpo, `pytest` **569**; web `lint`/`typecheck`/`test` (288) limpos; **e2e
  5/5**. Verificado ao vivo: `POST /api/sessions` com `"exercise":"squat"` devolve ticket, e
  slug inválido responde `disponiveis: jumping_jack, squat`.
- Pendências geradas: T-053 (corpus de agachamento) e T-054 (`KNEES_INWARD` — o valgo é a
  falha que a câmera frontal vê melhor que qualquer outra, e precisa de parâmetro novo no
  gerador de poses).

---

## 2026-07-29 · T-052 — O gerador de fixtures aprende a dobrar o joelho

- Por quê antes da T-032: todos os critérios de aceite da SPEC-007 são baseados em fixture.
  Sem gerador, a FSM 2 não teria como ser aceita — e essa metade do trabalho estava invisível
  no título da T-032.
- Feito: `Pose` ganhou `knee_angle`, `stick_figure` passou a montar a perna como cadeia de
  dois segmentos, e nasceram `squat_poses()`/`standing_pose()`, espelhando a forma do gerador
  do polichinelo.
- Decisões:
  - **Default `KNEE_STRAIGHT` = perna reta = a geometria que já existia.** A suíte inteira
    (535 testes) passa sem um número se mexer, e há teste explícito para isso. Um deslocamento
    de milésimos aqui reescreveria em silêncio o significado de todos os limiares medidos até
    hoje — inclusive os do corpus.
  - **Ao agachar, quem desce é o quadril; o chão fica.** Ancorar no quadril e deixar o
    tornozelo subir daria a mesma geometria relativa, mas a altura do corpo no quadro não
    mudaria — e a validação de cena veria um agachamento como alguém parado, enquanto em vídeo
    o corpo encolhe visivelmente.
- **A medição que muda a T-032**: de frente, 80° reais de joelho leem **133°**. O joelho viaja
  para a frente e a câmera frontal não vê esse eixo. Uma FSM com limiar de 90° lido do plano
  da imagem **nunca dispararia** no enquadramento que o produto pede. O que se vê bem é a
  altura ombro→tornozelo (0,607 → 0,468). O gerador reproduz essa perda de propósito: uma
  fixture que entregasse o ângulo verdadeiro de frente produziria uma FSM aprovada em teste e
  reprovada em vídeo — o pior resultado possível para uma bancada. Tabela nas Descobertas.
- Um teste meu falhou e o certo era corrigir o teste: eu tinha afirmado encolhimento de 25%
  sem medir; o real é 19%. Trocado pelo número medido, com o porquê de ele ser conservador
  (o gerador não inclina o tronco, e vídeo real inclina).
- Gates: `ruff` limpo, `pytest` **535** (era 521, +14).

---

## 2026-07-29 · T-051 — O cliente passa a escolher o exercício

- O buraco: `useSession.ts` mandava `DEFAULT_EXERCISE` fixo. Um exercício podia estar pronto,
  testado e medido no worker e ainda assim ser inalcançável pelo produto — só por `curl`. A
  SPEC-007 diz "usuário **seleciona** o exercício" desde o dia 1 e isso nunca foi construído.
- Decisões:
  - **O seletor não desenha nada enquanto houver um exercício só.** Um controle de uma opção
    não é escolha, é ruído em cima da câmera. O que a task entrega é o caminho da escolha até
    o `POST /sessions`; a superfície aparece sozinha quando o catálogo crescer. Virou regra
    nomeada (`offersChoice()`) com teste que se inverte sozinho no dia da T-032, em vez de um
    `&&` solto dentro do componente.
  - Mora na capa da câmera, ao lado da preparação, pelo mesmo motivo dela: é o instante em
    que a escolha importa, e é antes de a sessão abrir. A aba Exercícios (T-046) será a
    superfície de navegar; esta é a escolha rápida de quem já sabe o que veio fazer.
  - Persistida em `localStorage` como o countdown — treinar não exige conta (SPEC-011).
  - **Validada na leitura, não só na escrita.** Um slug guardado hoje pode sumir do catálogo
    amanhã; um aparelho parado há meses voltaria pedindo um exercício que não existe e levaria
    recusa do servidor a cada tentativa, sem caminho de volta pela interface.
  - Chips e não `<select>`: são nomes, e a roleta nativa abriria por cima da câmera.
- **Um defeito real, achado por um teste que eu escrevi esperando ver passar**: `'toString' in
  EXERCISE_CATALOG` é `true`. `in` percorre o protótipo, então `toString` passava por
  exercício válido, ia para o `POST /sessions`, e `getExercise` devolvia uma função no lugar
  do card — `.display_name` viraria `undefined` no meio da tela. `Object.hasOwn` nos dois
  pontos. Registrado como regra geral do web nas Descobertas.
- Gates: `lint`/`typecheck` limpos, vitest **287** (era 278); **e2e 5/5** com a stack subida.
- Pendências geradas: divergência possível entre o catálogo do web e o registro do worker —
  hoje falha alto na admissão, então não bloqueia; o fim da classe seria o servidor publicar
  o catálogo. Decidir junto com a T-046, que é quem precisa da lista completa.

---

## 2026-07-29 · T-050 — `Phase` vira par neutro (`rest`/`peak`)

- Por quê agora: mudança de contrato, e o AGENTS.md manda contrato primeiro. Escrever a FSM 2
  antes disso significaria escrevê-la duas vezes.
- Raio de alcance **medido antes de mexer**, não estimado: `phase` não vai para o Parquet nem
  para o Postgres, e nenhum componente do web a renderiza. Só existe em `events.py`,
  `jumping_jack.py`, `lib/events.ts` e testes. Por isso a troca foi limpa, sem camada de
  compatibilidade — que teria sido pura dívida para zero dado antigo.
- Decisões:
  - **`REST`/`PEAK`, não `UP`/`DOWN`.** Toda contagem por repetição tem os mesmos dois
    extremos: a posição de partida e o extremo da amplitude. Somar um par por exercício
    (`closed/open`, `up/down`, …) obrigaria HUD, relatório e dataset a virarem um `switch`
    sobre `exercise` para saber o que a palavra quer dizer — o oposto de um contrato.
  - **Nada de rótulo de exibição ainda.** A task previa isso, e eu tirei: nenhuma tela desenha
    a fase hoje. Construir o catálogo de tradução agora seria inventar requisito. A SPEC-007
    registra onde ele nasce quando nascer (catálogo do cliente).
  - `closed`/`open` passam a ser **rejeitados alto** na desserialização, com teste próprio. O
    risco real não é dado velho em disco — é um worker desatualizado publicando no stream; um
    `closed` aceito em silêncio viraria fase errada no HUD sem ninguém perceber.
  - No `jumping_jack.py` o texto continua dizendo FECHADO ⇄ ABERTO, porque é o nome do
    movimento. `REST`/`PEAK` é o nome do dado. Os dois convivem, e o docstring diz isso.
- Gates: `ruff` limpo, `pytest` **521**; web `lint`/`typecheck`/`test` (278) limpos; **e2e com
  a stack de verdade subida: 5/5** — que é o teste que importa aqui, já que a mudança cruza a
  rede entre o enum Python e o TS.
- Docs: SPEC-002 (tabela de eventos), SPEC-007 (fases + de quem é a palavra de tela),
  ARCHITECTURE §7.3.

---

## 2026-07-29 · T-047 — A FSM lê a fase inicial em vez de assumi-la

- Contexto: o Daniel perguntou se dá para começar o exercício 2. Auditei o código e a resposta
  foi "a espinha aguenta, mas não comece pela T-032". A T-047 entrou primeiro porque o bug não
  é do polichinelo — é do **padrão** que a segunda FSM vai copiar.
- Feito: `initial_phase(feats) -> Phase` entrou no **contrato** (`exercises/base.py`), não
  escondido dentro do polichinelo. `step()` chama no primeiro frame utilizável; se a leitura
  der `OPEN`, a FSM nasce aberta, anuncia `exercise.phase` (o HUD desenha a fase — adotar em
  silêncio o deixaria mentindo) e marca o início da rep.
- Decisões:
  - **A fase adotada exige os DOIS limiares de abertura**, não um. É o que separa "está no
    topo de um polichinelo" de "está parado com os braços erguidos": de pé com os pés juntos,
    `ankle_spread` reprova e baixar os braços não vira repetição. Pagar uma rep inventada para
    recuperar uma rep perdida seria um péssimo negócio — e a rep fantasma é a mais visível das
    duas para quem está treinando.
  - Frame intermediário ou `degraded` ⇒ `CLOSED`. Sem afirmação, vale o repouso.
  - O método foi para o Protocol de propósito: todo exercício novo é **obrigado** a responder
    onde começa. Era exatamente a pergunta que ninguém tinha feito.
- Medições (antes → depois):
  - `polichinelo-02.mp4 --no-calibrate`: **14/15 → 15/15**. É a rep diagnosticada na T-038.
  - `evalctl run eval/corpus/` (com calibração): **20/13/19 nos dois casos — não mudou**.
    Rodei o corpus com o código antigo via `git stash` para ter certeza em vez de supor. O
    motivo é a guarda dos dois limiares: no frame em que a contagem começa, depois da
    calibração, a pessoa está em posição intermediária. O "não mudou" é a prova de que a
    guarda existe de verdade, e não só no comentário.
  - `test_rep_feita_durante_a_preparacao_NAO_conta`: `rodar(3)` foi de 2 para 3. Não é
    regressão — é o conserto aparecendo no cenário do produto (quem exercita durante a
    preparação está em movimento quando o "VAI!" chega). Atualizei o número e o porquê.
  - Sobra no `02`: −2, e agora está inteiramente explicado — é a janela de calibração caindo
    em cima de exercício de verdade num vídeo a 73 rpm. Não é contagem. O produto não paga
    esse preço porque tem o countdown (T-049). Manifest atualizado.
- Auditoria da regra "um exercício novo não muda nada fora de `exercises/`" (nota técnica da
  SPEC-007): **falsa como está escrita**, e a spec foi corrigida para dizer isso. Agnósticos de
  fato: registro por slug, validação no `POST /sessions`, roteamento, relatório, Parquet e o
  catálogo de feedback. Ainda exigem mudança fora: `Phase` (T-050), seleção de exercício no
  cliente (T-051) e o gerador de fixtures (T-052).
- Gates: `ruff check` limpo; `pytest` **520** (era 514, +6).
- Pendências geradas: T-050, T-051, T-052 no backlog, nesta ordem, antes da T-032.

---

## 2026-07-29 · T-049 — Preparação "3, 2, 1" configurável antes de a contagem valer

- Pedido do Daniel: um timer de 3 s depois da preparação e antes de contar, extensível ou
  desligável, com UX que ajude sem virar atrito.
- **A SPEC-004 já pedia isso e a implementação tinha colapsado o passo.** A Fase Inicial diz
  "countdown fixo 3-2-1", mas desde a T-019 o `session.calibrated` era emitido e a contagem
  começava no MESMO frame: media o corpo e já valia, sem aviso para quem estava do outro lado.
  O que a task acrescenta de novo é a configuração.
- **A decisão que define a entrega: quem segura a contagem é o servidor.** Se fosse animação
  no cliente, o polichinelo feito durante o "3, 2, 1" entraria no total — e o recurso estaria
  enganando quem confia nele. Entrou uma fase no analysis-worker em que os frames continuam
  sendo normalizados (o One Euro precisa chegar quente ao primeiro movimento que vale) e a
  cena continua avisando (é quando "entre no quadro" mais ajuda), mas a FSM não os vê.
- Contrato primeiro, como manda o AGENTS.md: `SessionStarted.countdown_s` e
  `SessionCalibrated.countdown_ms`. O evento de calibração **mudou de significado** — era
  "contagem começou", agora é "corpo medido".
- Decisões:
  - **Os 30 s começam no "JÁ", não na medição.** `exercise_started_wall_ms` passa a ser um
    instante no futuro; `expiry_reason` já comparava contra ele e não precisou mudar. Cobrar a
    preparação do treino encurtaria a sessão de quem escolheu 10 s.
  - **Sem um `session.counting`.** Foi considerado e descartado: o cliente já ancorava o anel
    no relógio dele ao receber o `session.calibrated`, então o evento novo custaria uma ida ao
    servidor sem comprar autoridade. A autoridade está em o worker não alimentar a FSM.
  - **`clamp` em vez de recusa** no `countdown_s` (0–10 s): é conforto, não parâmetro de
    medição. Derrubar a sessão porque veio `-1` trocaria um treino por uma mensagem de erro. O
    teto de 10 s não é técnico — é para o campo não virar forma de segurar vaga sem treinar.
  - **A preferência mora no aparelho, não na conta.** A SPEC-011 é explícita em que treinar não
    exige conta; uma preferência que só funciona depois de cadastrar seria uma punição por não
    se cadastrar, no produto que se define por não precisar disso.
  - **UX em três níveis, do mais rápido de ler para o mais lento** (revisto depois de o Daniel
    pedir mais clareza): o anel que se esvazia dá o "está acabando" no periférico, sem leitura
    nenhuma; o número gigante dá o quanto falta; e a linha de apoio — "Fique parado. Comece o
    polichinelo quando aparecer **VAI!**" — resolve a única dúvida que custa caro, "já é pra
    começar?". A linha some no VAI!, porque aí a resposta é óbvia e texto sobrando durante o
    exercício é ruído. O anel reusa o gradiente e a técnica do `TimerRing` dos 30 s: é a mesma
    ideia visual (um tempo que corre), e duas linguagens para dois relógios no mesmo produto
    seria custo sem retorno. Fundo escurece só o bastante para destacar sem esconder a pessoa
    que está se posicionando, e há `prefers-reduced-motion`.
  - **A primeira versão dizia só "preparando…"**, e era insuficiente pelo motivo certo: quem vê
    a tela pela primeira vez não pode ficar em dúvida se já devia estar pulando — errar isso
    custa as primeiras repetições, que é exatamente o que a task existe para proteger.
  - **O controle fica na capa da câmera**, não em tela de ajustes: ela não existe (Perfil é
    conta e histórico), e este é o único instante em que a escolha importa. Ciclo por toque
    (3 → 5 → 10 → desligado) em vez de `<select>`, que abriria roleta nativa sobre a câmera.
- Erro que peguei na revisão: o `.stage` inteiro é espelhado (`scaleX(-1)`, visão de espelho) e
  o "3" sairia invertido. As outras camadas já desfaziam o espelho; a nova não. Corrigido.
- **Sete testes quebraram ao mudar o default, e isso foi informação.** Cada um era um teste de
  CONTAGEM herdando em silêncio uma decisão de produto. Agora declaram `countdown_s=0` no
  próprio corpo — quando o default mudar de novo, eles não se mexem.
- Gates: `pytest` 514 verde (era 507), `ruff` limpo, `npm run typecheck`/`eslint` limpos,
  vitest 278 (era 254). E-2-e 5/5 contra a stack real, com um caso novo que prova a corrente
  inteira: a preferência sai do cliente, atravessa a admissão, vira `session.started` no
  barramento e chega ao worker — que emite `countdown_ms: 10000` e **não conta** nenhuma das 5
  repetições feitas durante a preparação.
- Pendências geradas (4 em "Descobertas"): a mudança de significado do `session.calibrated`, a
  ausência deliberada do `session.counting`, o default 0 no caminho sem admissão, e a lição
  dos testes que herdavam o default.

---

## 2026-07-29 · T-040 — Fonte de vídeo no navegador e a terceira perna da paridade

- Entregue: `web/src/dev/videoSource.ts` (dirige o `<video>` a partir de um arquivo),
  `startFile` no `useCamera`, `VideoSourceControl` no painel de dev, `parityExport.ts` (o JSON
  no formato do `VideoResult`), e `evalctl parity --browser <json>` como terceira perna.
- **A task foi pequena porque o desenho já estava certo.** `useEdgePipeline` nunca soube de
  onde vinha a imagem — ele lê do elemento `<video>`. Trocar `srcObject` (MediaStream) por
  `src` (blob) não mudou uma linha dele. É o dividendo do "keypoint-first": a origem é
  detalhe.
- **O achado que quase estragou a medição: o capability probe come o começo do vídeo.** Ele
  roda 2 s de detecção antes de o loop começar. Com câmera é inofensivo; com arquivo são 2 s
  de conteúdo — e logo os primeiros, que a SPEC-004 usa para medir o corpo parado. Se eu
  tivesse dado `play()` ao carregar, o navegador leria um trecho diferente do que o harness lê,
  e a diferença apareceria como "divergência JS × Python" quando seria erro meu de montagem.
  Resolvido carregando **pausado no frame 0** e rebobinando depois do probe. Tem teste cujo
  único propósito é falhar se alguém puser um `play()` no carregamento.
- Decisões:
  - **O JSON do navegador sai no formato `VideoResult.to_dict()`**, que já existe e já é lido.
    Inventar um segundo formato só criaria tradução na fronteira — mesma razão do contrato de
    eventos.
  - **`load_browser_result` recusa arquivo sem `source: "browser-edge"`.** Passar um relatório
    do próprio harness por engano faria a comparação medir Python contra Python e responder
    "paridade perfeita" — o resultado mais tranquilizador e mais inútil possível.
  - **A perna do navegador entra no veredito com a mesma tolerância.** Se ela existe é porque
    alguém quis medi-la; reportar OK ignorando-a seria pior do que não ter a perna.
  - **O `delegate` (`gpu`/`cpu`) viaja no JSON.** Os dois dão resultados diferentes, e
    relatório que não diz qual rodou não é reproduzível.
  - Fim do arquivo encerra a captura pelo mesmo caminho de sempre (sem frames → `no_data`,
    T-011). Nada de rota nova para o modo dev.
- Gates: `pytest` 507 verde (era 500), `ruff` limpo, `npm run typecheck` limpo, `eslint` limpo,
  vitest 254 (era 238). CLI verificada contra o corpus real:
  `edge=20 cloud=20 browser=20 (delta +0, browser +0, tolerancia 1)`, com os dois caminhos de
  recusa saindo com código 2 **antes** de gastar a passada do MediaPipe.
- **O que NÃO está verificado, e é o principal:** o número do navegador naquela linha veio de
  um JSON que eu escrevi à mão para exercitar o encanamento. A medição de verdade — abrir o
  `polichinelo-01.mp4` no painel e ver quanto o MediaPipe WASM conta — depende de alguém
  clicar. É a passada que fecha a task, e é justamente a que ninguém pode fazer por automação
  barata (ver Descobertas).
- Pendências geradas (3 em "Descobertas"): o probe consumindo tempo do arquivo, a perna do
  navegador ser manual, e vídeo > 30 s ser cortado pelo timer autoritativo.

---

## 2026-07-29 · T-048 — Gate das ferramentas de dev (e dois gates que não existiam)

- Nasceu de uma pergunta do Daniel sobre a T-040: "quando você diz *eu*? porque um usuário
  comum não deveria estar upando vídeos". Eu tinha descrito a fonte de vídeo da bancada como
  se fosse fluxo de produto. Fui verificar como as superfícies de dev eram separadas hoje e a
  resposta era: **não eram**.
- **O chip de dev estava em produção desde a T-007.** `CameraView.tsx` renderizava o chip de
  diagnóstico e o `FixtureControls` atrás de `{isReady && ...}` — nenhuma flag. Quem abrisse o
  domínio público e ligasse a câmera via `pose gpu`, `seq 412 · 14.9fps` e botões de gravar
  fixture. O `FixtureControls.tsx` até declara no topo "não faz parte da UI de produto"; o
  código nunca fez valer. **Comentário não é gate.**
- Entregue: `web/src/dev/gate.ts` como único lugar que decide, `User.is_admin` (+ migration
  0003) exposto no `GET /api/me`, e `manage.py admin_tools` como única porta de concessão.
- Decisões:
  - **Duas fontes de direito: build de dev, ou conta com `is_admin`.** A segunda é o que o
    Daniel pediu — inspecionar o servidor de produção com o que está de pé lá, sem precisar
    de um build especial. Local continua sem login, porque exigir "crie conta e se promova"
    seria atrito diário para resolver um problema que só existe em produção.
  - **O `?dev=` modifica, nunca concede.** `?dev=0` desliga (o admin vê a tela como o usuário
    comum a vê, sem deslogar); `?dev=1` sozinho não faz nada para quem não é admin. Se
    concedesse, o gate seria decoração — tem teste para os dois lados.
  - **`is_admin` não entra por nenhuma rota.** Só pelo comando, que exige shell na máquina.
    Tem teste que manda `is_admin: true` no corpo do cadastro e exige `False` na resposta.
  - **A flag é lida do banco a cada `/api/me`, não posta no JWT.** Revogar tem efeito
    imediato, verificado ao vivo: promovi e revoguei com o MESMO access token na mão.
  - **`is_admin` e não `is_staff`**: `is_staff` é o campo que o admin do Django consulta, e
    não há admin aqui — reusar o nome prometeria semântica que o projeto não tem.
  - Aproveitei para tirar `docker compose up` da mensagem de erro que o usuário final vê
    quando o gateway cai. Instrução de subir a stack é diagnóstico, não produto.
- **Achado grave no caminho: o `tsc --noEmit` não checava um único arquivo.** O `tsconfig.json`
  da raiz tem `"files": []` + project references, e nessa forma o `tsc` sem `-b` sai 0 sem
  verificar nada. Eu rodei esse comando como gate várias vezes, inclusive fechando a T-022.
  Com `tsc -b --force` apareceram 10 erros reais — dois meus da T-022 (`accountSummary.ts`,
  `noUncheckedIndexedAccess` em `split()[0]`) e dois de `reportSummary.test.ts` que vinham da
  T-020. Ou seja, `npm run build` estava quebrado havia dias. Corrigidos todos e criado
  `npm run typecheck`, que agora é o gate de verdade.
- **Segundo erro meu, e o pior:** rodei `npx prettier --write` para formatar. O projeto **não
  tem Prettier** — o npx baixou a versão 3.9.6 na hora e reformatou seis arquivos para o
  estilo padrão dele (ponto-e-vírgula, aspas duplas), contra a convenção do repositório. O
  `eslint` passou nos dois estados, porque não checa estilo. Revertido pelo git nos arquivos
  versionados e reescrito à mão nos novos. Virou descoberta: enquanto não houver formatador
  configurado, não rodar formatador no `web/`.
- Gates: `pytest` 500 verde (era 492), `ruff` limpo, `npm run typecheck` limpo **de verdade**,
  `npm run build` voltou a funcionar, `eslint` limpo, vitest 238 (era 229). Ciclo verificado
  contra a stack real: cadastro tentando se promover pelo corpo → `is_admin: False`; comando
  `--on` → `/api/me` responde `True` com o mesmo token; `--list`; `--off`.
- Pendências geradas (3 em "Descobertas"): a superfície de dev exposta desde a T-007, o
  typecheck vazio (a T-027 tem de incluir `npm run typecheck`), e a falta de formatador no
  `web/`.

---

## 2026-07-29 · T-022 — Auth JWT + trial anônimo + histórico do usuário

- Entregue (servidor): `server/api/auth.py` (register/login/refresh/me com rate limit por IP),
  `server/api/trial.py` (quota de 3 sessões/dia por aparelho, em Redis), modelos `User` e
  `SessionClaim` + migration `0002`, `GET /api/sessions?mine` como histórico, e a admissão
  passando a gravar a dona da sessão. `tests/test_auth.py` (26 testes) organizado pelos três
  critérios da SPEC-011.
- Entregue (cliente): `web/src/auth/` (`storage.ts`, `api.ts`, `accountSummary.ts`,
  `AccountSheet.tsx`), `web/src/store/account.ts`, aba Perfil funcional, e a identidade
  passando a acompanhar admissão e busca de relatório. 5 arquivos de teste novos; a suíte web
  foi de 172 para 229.
- **O treino continua funcionando sem conta, e isso é a arquitetura, não uma gentileza.** O
  WebSocket da sessão autentica pelo token HMAC de 45 s do ticket (SPEC-009), não pelo JWT.
  Consequência direta: renovar o access no meio de um treino não derruba nada, porque o treino
  nunca dependeu dele — o critério 3 da spec sai de graça. Tem teste cujo único propósito é
  falhar se alguém acoplar o WS ao JWT no futuro.
- **A admissão NÃO passa pelo `authedFetch`.** Se o access venceu, `POST /api/sessions` cai no
  trial anônimo em vez de falhar. Negar o treino de quem tem conta por causa de um token velho
  seria pior do que contar a sessão como visitante.
- Decisões:
  - **`SessionClaim` em vez de `user_id` no `SessionResult`.** A spec pede `user_id` na
    sessão, mas o `SessionResult` é gravado pelo report-builder e a SPEC-010 promete que ele é
    derivável 100% por replay dos eventos. Dono é fato da admissão, não do treino: ficou em
    tabela própria, escrita pela API, e o histórico é a junção pelo `session_id`. O corpus da
    T-021 segue sem qualquer dado de pessoa.
  - **`X-Device-Id` em header, não cookie httpOnly.** Cookie cross-origin exigiria
    `SameSite=None; Secure`, que o navegador descarta em http — ou seja, todo o ambiente de
    dev. E httpOnly protegeria de XSS um dado que a própria spec assume ser burlável.
  - **Rate limit só nas rotas de auth** (`AUTH_THROTTLE_RATE`, 10/min por IP). Limitar
    `POST /sessions` seria mexer na quota do trial, que é decisão de produto e vive em
    `trial.py`. O contador vai no cache Redis para valer no serviço inteiro: com locmem, 3
    workers gunicorn dariam 3× o limite.
  - **Senha errada e e-mail inexistente devolvem a mesma mensagem**, para o login não virar
    oráculo de quem tem conta.
  - **`JWT_SIGNING_KEY` separado do `DJANGO_SECRET_KEY`**, para girar um não deslogar o mundo
    pelo outro. O `prod.sh secrets` agora gera a chave e a acrescenta em `.env.prod` quando ela
    não existe — quem já tem o arquivo de antes não precisa editar nada à mão.
- Gates: `pytest` 492 verde (era 466), `ruff check`/`format` limpos, `tsc --noEmit` e
  `eslint` limpos, vitest 229 verde. `npm run e2e` 4/4 contra o stack real, incluindo um caso
  novo que faz a jornada inteira — cadastro, sessão com conta, relatório, histórico — e prova
  que `session_claim` e `session_result`, duas tabelas sem chave estrangeira entre elas, se
  encontram no `GET /api/sessions?mine`.
- Pendências geradas (5 em "Descobertas"): device em header em vez de cookie; o dia do trial
  virando às 21 h no Brasil; ausência de logout no servidor (sem blacklist de refresh); as
  tabelas mortas que o `contrib.auth` trouxe; e o motivo do `SessionClaim`.

---

## 2026-07-28 · T-021 — dataset-writer (Parquet por sessão + schema documentado)

- Entregue: `workers/dataset_writer/` (`collector.py` puro, `parquet.py` com o schema,
  `main.py` com o loop); extra `dataset` (pyarrow) e imagem própria
  (`docker/dataset-writer.Dockerfile`); serviço no compose de dev e de prod;
  `docs/DATASET.md` (o "schema documentado" do critério 3); `tests/test_dataset_writer.py`
  (21 testes).
- **Lê dois streams, e não dá para escolher um.** Os frames vivem em `pose.frames`, mas o
  `session.completed` autoritativo é emitido pelo analysis-worker em `events.analysis` — ler
  só o primeiro perderia toda sessão encerrada pelo timer dos 30 s, que é o caso normal. Como
  os dois são independentes, o encerramento pode ultrapassar os últimos frames: daí a
  **carência de 1,5 s** antes de fechar o arquivo. Sem ela a cauda de cada série sumiria em
  silêncio, e um corpus com o fim de todo exercício faltando é pior que um corpus menor.
- **Ack imediato, ao contrário do report-builder.** Lá as mensagens ficam pendentes até o
  relatório estar no banco. Aqui isso seria teatro: `pose.frames` é aparado por `MAXLEN ~5000`
  (~11 sessões) e entrada aparada some do stream mesmo continuando no PEL — o restart
  reencontraria pendências vazias e acharia que se protegeu. O dataset é best-effort por
  construção, e a spec pede dele só que o arquivo seja legível.
- Decisões:
  - **O dataset guarda o dado de entrada, não keypoints canônicos.** A spec diz "sequências
    normalizadas" e era tentador aplicar a SPEC-006 aqui. Mas assar a canonicalização de hoje
    no arquivo congelaria `mincutoff`/`beta` dentro do corpus: mexer nos filtros amanhã
    invalidaria tudo que já foi gravado. Landmarks 0–1 no frame são reversíveis; normalização
    é reproduzível a partir deles, e continua sendo decisão revisável.
  - **Formato longo, 138 colunas** (`nose_x`… `right_foot_index_v`), `float32`, zstd, uma
    linha por frame. `df[COORD_COLUMNS].to_numpy()` já é a matriz `(n_frames, 132)` que um
    modelo temporal consome; uma coluna de listas custaria um `explode` em todo notebook.
  - **`session_id` entra como coluna**, além do nome do arquivo — não está na lista da spec e
    entra de propósito: um treino concatena centenas de arquivos e sem isso não há como dizer
    onde uma sequência termina.
  - **Sessão abandonada é gravada, não descartada** — o oposto do report-builder. Um relatório
    de sessão que não terminou seria errado; keypoints continuam sendo keypoints. Pelo mesmo
    motivo o SIGTERM faz `drain()`: deploy no meio da captura não pode virar sessão perdida.
  - **Escrita atômica** (`.tmp` + `os.replace`): crash no meio da escrita deixa o arquivo
    anterior intacto em vez de um Parquet truncado que só explodiria meses depois, dentro de
    um treino.
  - `RedisBus.consume` ganhou `block_ms=0` = **não bloquear** (no Redis, `BLOCK 0` bloqueia
    para sempre). É o que permite ler dois streams na mesma volta sem dobrar a latência
    ociosa. Tem teste com fakeredis: se a tradução se perder, o teste trava — melhor que o
    processo travar em produção.
- Gates: ruff + format limpos, pytest **466** verde (+21), `npm run e2e` 3/3 contra a stack
  real. No disco, sessões de verdade: 320 frames × 138 colunas lidas com `pandas.read_parquet`,
  `seq` contíguo de 0 a 141 nas três sessões do E2E (nenhum frame perdido), metadados
  `schema_version=1` no arquivo, ~725 B/frame.
- Pendências geradas: 3 itens em "Descobertas" (`degraded` sempre `false` porque nenhum
  produtor o preenche; duas réplicas partiriam a sessão ao meio; o corpus não carrega o
  desfecho da sessão, que vive no Postgres).

---

## 2026-07-28 · T-020 — relatório da sessão (consolidação + Postgres + tela)

- Entregue: `session.report.ready` no contrato; `workers/report_builder/builder.py` (puro);
  `SessionResult` + migration inicial; comando `manage.py report_builder`;
  `GET /api/sessions/{id}/report`; tela de relatório no cliente (`web/src/report/`); serviço
  `report-builder` no compose de dev e de prod; `tests/test_report_builder.py` (17 testes) e
  dois arquivos de teste no cliente.
- **O payload de `session.report.ready` é vazio de propósito.** A tentação era mandar reps e
  cadência junto, já que o builder acabou de calculá-los — e aí existiriam dois lugares
  dizendo quantas repetições a sessão teve, o evento e o `GET .../report`. Quando divergissem
  (replay, reprocessamento, mudança de fórmula), ninguém saberia qual está certo. O evento é
  um sino: diz "agora existe", e o conteúdo tem uma fonte só.
- **Ack só depois de gravar.** A SPEC-010 promete que um crash não deixa sessão sem relatório.
  Isso não sai de graça do loop: o builder acumula eventos e só confirma as mensagens da
  sessão quando o relatório está no banco. Se o processo morre no meio, nada foi confirmado e
  tudo é reentregue — o `RedisBus` ganhou `consume_pending()` (XREADGROUP id `0`) e o
  `InMemoryBus` ganhou o PEL correspondente, sem o qual todo teste de reinício passaria por
  não haver o que reentregar. Requisito colado nisso: **nome de consumidor estável**, porque o
  PEL é indexado por nome — um nome com PID dentro tornaria o critério falso na prática, sem
  erro nenhum aparecendo.
- **Um erro meu que o teste pegou**: a evacuação de sessões abandonadas comparava o `ts` do
  evento (relógio do **cliente**) com o agora do servidor. Isso descartaria na hora qualquer
  sessão de celular com a hora torta e todo replay da bancada. Separei `last_seen_ms`
  (servidor) de `last_ts` (cliente) — a mesma lição da T-016 no descarte por idade.
- Decisões:
  - **`session.started` passou a ser publicado nos dois streams** (`pose.frames` para a
    análise, `events.analysis` para o relatório). Sem isso o relatório não saberia o exercício
    e teria de consultar o Redis, quebrando a propriedade da spec — relatório derivável 100%
    por replay dos eventos. O contrato já previa publicar para outra audiência.
  - **ADR-008**: o report-builder roda dentro do Django, não em `workers/`. É o único
    consumidor que escreve no Postgres; um worker separado teria de importar `server/`,
    invertendo a única direção de dependência do repositório. A consolidação em si continua
    pura, sem Django, e é onde estão os testes de cadência.
  - **O total de reps vem do `session.completed`**, não da contagem de `rep.detected` vistos.
    Um builder que subiu no meio da sessão reporta o número certo; só o gráfico sai
    incompleto — e isso é visível, ao contrário de um total silenciosamente menor.
  - A tela mostra `repCount` ao vivo enquanto o relatório não chega: a pessoa acabou de treinar
    e não pode olhar para uma tela vazia por causa de um detalhe de consolidação.
- Gates: ruff + format limpos, pytest 445 verde, tsc e eslint limpos, vitest 165 verde. E2E
  contra a stack real com **3 testes** (um novo, cobrindo a cadeia inteira: worker →
  report-builder → Postgres → API → cliente). No banco, uma sessão real do E2E: 8 reps em
  8 377 ms, cadência 57,3 rpm, janelas `[4, 4]`, calibração com 16 amostras.
- Pendências geradas: 3 itens em "Descobertas" (publicação dupla de `session.started`; o
  report-builder não escala sem trocar a recuperação para `XAUTOCLAIM`; testes de banco em
  SQLite não cobrem nada específico de Postgres).

---

## 2026-07-28 · Produção na VPS — dois bugs que só existem fora da máquina de dev

Reportados pelo Daniel a partir do `docker ps` da VPS: `pose-worker` em `Restarting (1)` e
`api` em `Up (unhealthy)`. Causas distintas, ambas invisíveis em dev.

- **`pose-worker` em crash loop: o modelo não existe na VPS.** `eval/models/*.task` é
  gitignorado (5,5 MB de binário) e o compose de prod monta `./eval/models` por bind mount —
  num clone novo o Docker cria o diretório vazio e `resolve_model_path` estoura.
  - O sintoma engana: o `up` termina verde, api/gateway/web sobem, o modo **edge funciona
    inteiro**. Só o celular que cai em cloud fica sem contagem, e a causa está num container
    que reinicia calado, fora do caminho de quem está testando.
  - Corrigido em `scripts/prod.sh`: `garante_modelo()` roda como preflight do `up` (junto de
    `verifica_portas`) e baixa o `.task` quando falta ou está truncado. Reusa o
    `download_model` do contrato de propósito — a URL do modelo tem UMA fonte de verdade, e
    edge/cloud/bancada dependem de ser o mesmo arquivo. Só stdlib lá dentro, então o
    `python3` do sistema basta: sem `uv`, sem venv na VPS.
  - Novo comando `./scripts/prod.sh modelo`: baixa e religa só o `pose-worker`, para
    consertar uma stack já no ar sem rebuild de tudo.
  - Verificado no caminho real: modelo removido → baixado, `cmp` byte a byte igual ao da
    bancada; modelo truncado → detectado e rebaixado.
- **`api` unhealthy com a api perfeitamente viva: o healthcheck não mandava `Host`.** Em prod
  `ALLOWED_HOSTS` é só o `DOMAIN`; o healthcheck fazia `GET http://127.0.0.1:8000/healthz`,
  que chega com `Host: 127.0.0.1` e leva 400 (DisallowedHost).
  - Medido antes de mexer: `127.0.0.1 -> 400`, `fit.exemplo.com -> 200`.
  - Escolhi mandar o `Host` certo em vez de afrouxar `ALLOWED_HOSTS`. Acrescentar `127.0.0.1`
    resolveria o sintoma e desfaria a propriedade que a T-023 verificou de propósito (Host
    estranho recusado) — barato de fazer, caro de perceber depois.
  - Verificado no container real (projeto `digital-fit-hc`, porta alternativa): `healthy`,
    `exit=0`; e o comando antigo, rodado dentro do mesmo container, continua dando
    `HTTP Error 400`.
- Pendência gerada: 1 item em "Descobertas" (nenhum outro bind mount de prod depende de
  arquivo gitignorado — `./eval/models` era o único).

---

## 2026-07-28 · T-019 — calibração no countdown (e um critério de spec derrubado por medição)

- Entregue: `workers/analysis_worker/calibration.py`, `session.calibrated` no contrato,
  `Baseline` com `shoulder_span`/`wrist_rest_y`, `Normalizer.set_baseline()`, orquestração no
  router, calibração também na bancada, `tests/test_calibration.py` (12 testes),
  `session_poses()` nas fixtures.
- **O critério 3 da SPEC-004 estava errado, e o corpus provou.** A spec pedia `ankle_spread`
  relativo à largura de ombros medida na calibração. Implementei e a acurácia PIOROU: MAE de
  0,67 para 2,00, com o vídeo frontal caindo de 20/20 para 18/20.
  - Diagnóstico: a escala de `ankle_spread` subiu ~1,37× (p50 de 1,60 para 2,19) e a fração de
    frames abaixo do limiar de fechar caiu de 36% para 24% — as reps deixavam de FECHAR.
  - Tentei reexpressar os limiares por esse fator. A varredura mostrou que **não existe fator
    global**: o que levava o vídeo frontal a 20/20 derrubava o oblíquo de 19/21 para 3/21.
  - A razão é conceitual, e é o que fecha o caso: o divisor por frame **se autocorrige**. Com
    a pessoa em ângulo, abertura dos pés e largura de ombros encurtam JUNTAS em perspectiva, e
    a razão se mantém. Fixar o divisor numa medida única destrói exatamente essa invariância —
    e o vídeo oblíquo é quem paga.
  - Revertido; SPEC-004 corrigida com a medição registrada. A baseline segue valendo para a
    escala da normalização e para o relatório/T-030.
- Decisões:
  - **Os 30 s correm do fim da calibração**, não do primeiro frame: o countdown é preparação.
    Efeito colateral bom — o motivo `timeout`, que era inalcançável, virou o teto de vida da
    sessão e cobre a calibração que nunca fecha (com frames chegando, `no_data` não salvaria).
  - **Nada de contagem antes da medida** (SPEC-004, critério 2). Um "1" no placar durante o
    countdown seria uma repetição que a pessoa não fez.
  - **Frame degradado é recusado pela calibração**: landmark adivinhado pelo modelo viraria
    proporção inventada. Mediana, nunca média, pelo mesmo motivo.
  - **A bancada calibra também.** Se `evalctl` pulasse a calibração, mediria um pipeline que
    não existe — e diria uma acurácia que nenhum usuário experimenta.
- Consequência no corpus: MAE 1,333. O vídeo `01` (2 s parados no início) volta a **20/20**;
  `02` e `03` perdem 2 cada porque **não têm countdown** e a medição come exercício real. O
  guia de gravação passou a exigir 2–3 s parado, e `--no-calibrate` existe para comparação.
- **Cliente (mesma task)**: `sessionStatus` ganhou `calibrating`, o anel do HUD passou a
  ancorar em `session.calibrated` (e não no primeiro frame — senão o HUD mostraria menos
  tempo do que o servidor concede), e a tela ganhou a instrução "Fique em pé, parado" no
  centro do palco, onde é vista antes de a pessoa começar a pular.
- **O E2E ao vivo ficou mais rígido, e isso revelou um erro real**: a fixture sintética não
  tinha countdown, então a calibração comia a primeira repetição — 7 de 8 — e a asserção de
  `±1` engolia isso em silêncio. Com o countdown na fixture, a contagem é **exata** (8/8
  confirmado no log do worker) e a tolerância virou igualdade. O teste também passou a exigir
  que `session.calibrated` tenha chegado: sem ele, o servidor teria contado durante a
  preparação.
- Gates: ruff + format limpos, pytest 425 verde, tsc limpo, eslint limpo, vitest 144 verde,
  `npm run e2e` verde contra a stack real.
- Pendências geradas (3 em "Descobertas").

---

## 2026-07-28 · Corpus com 3 vídeos: paridade confirmada, dois erros de contagem diagnosticados

- Daniel gravou mais dois vídeos, ambos em retrato 576×1024 (o primeiro era paisagem):
  `02` com 15 reps começando imediatamente, cadência rápida (~73 rpm); `03` com 21 reps em
  ângulo oblíquo de 20–30°.
- **Paridade edge × cloud: perfeita nos três** — 20/20, 14/14, 20/20, delta 0 em todos. Isso é
  o resultado mais importante da rodada: os dois erros de contagem são **idênticos nos dois
  caminhos**, logo não vêm da degradação cloud (320px, JPEG, 10fps, IMAGE), e sim do pipeline.
  A T-018 sai mais forte do que entrou.
- Bancada no corpus: MAE 0,667, 33% exatos, 54 de 56 reps. Os dois erros são de −1.
- **Erro do vídeo 02, diagnosticado**: no `ts=0` a pessoa **já está aberta** (arm 143°, spread
  3.19). A FSM nasce em `Phase.CLOSED` e o debounce de 250 ms exige estabilidade antes de
  aceitar a abertura; aos 167 ms ela já está fechando. A primeira rep é estruturalmente
  impossível de contar. Virou a **T-047**.
  - Antes disso levantei a hipótese "erra quando não há tempo parado no início" e a **refutei
    por experimento**: cortando 0,5 / 1 / 1,5 / 2 / 2,5 / 3 s do começo do vídeo 01, a
    contagem continua 20/20 em todos os cortes. Não é o tempo parado, é a **fase** em que a
    captura começa. Registrar a hipótese errada importa: ela era plausível e teria virado
    "conhecimento" se eu tivesse parado na correlação.
- **Erro do vídeo 03, diagnosticado**: detecção perfeita nos primeiros 20 s e **zero pose** do
  segundo 21 ao 25 (mapa por segundo). A pessoa sai do quadro e a 21ª rep acontece onde o
  modelo não a vê. O ângulo oblíquo, que era a suspeita natural, **não atrapalhou**.
  - Descoberta de produto que veio junto: falha TOTAL de detecção é **silenciosa**. A validação
    de cena (SPEC-003) opera sobre landmarks; sem landmarks não há evento e não há
    `OUT_OF_FRAME`. Quem treina fica sem "volte para o quadro" justamente quando mais precisa,
    até o `no_data` de 10 s.
- Banda cloud medida nos três: 3,1 / 7,9 / 3,9 KB por frame (31–79 KB/s por sessão).
- Manifest atualizado com as condições de cada vídeo e com o que já se sabe que cada um
  expõe — `conhecido:` deixa explícito que aqueles −1 têm causa conhecida, para não serem
  lidos como ruído em toda rodada futura.

---

## 2026-07-28 · T-018 fechada com vídeo real + início do corpus (T-038)

- Daniel forneceu o primeiro vídeo rotulado: 20 polichinelos, 854×480 @30fps, 28,9s, com ~2s
  parados no início.
- **Paridade edge × cloud: `edge=20  cloud=20`, delta 0.** E as duas contagens batem com o
  rótulo humano — ou seja, o resultado valida três coisas de uma vez: o caminho cloud não
  perde repetição, a FSM acerta em vídeo real, e a bancada mede o que diz medir.
  - frames: edge 374 (15fps), cloud 248 (10fps); sem pose: 59 e 41
  - cadência 55,1 e 55,6 rpm; duração mediana da rep 1001 ms nos dois
  - zero sinais de qualidade, zero frames degradados
  - a rep mais longa (3,8 s) é a primeira, porque engloba os 2 s parados do começo
- **Banda cloud medida em vídeo real: 3,1 KB/frame (~31 KB/s por sessão)** — três vezes menor
  que a medição anterior sobre a referência de UI (9,8 KB), que era uma imagem renderizada
  cheia de detalhe. Três sessões simultâneas ≈ 0,75 Mbit/s. Folgado no orçamento da VPS.
- `evalctl run eval/corpus/`: MAE 0.000, 100% exatos. Baseline gravado em
  `eval/out/baseline.json` para o `evalctl compare` ter contra o que comparar.
- **T-038 começou**: `eval/corpus/manifest.yaml` com o primeiro vídeo rotulado e
  `eval/corpus/README.md` com o guia de gravação — o que variar entre vídeos (distância, luz,
  ângulo, execução preguiçosa) e por que execuções imperfeitas são as mais valiosas (são elas
  que testam o feedback engine, não só a contagem). Vídeos não são versionados; o manifest e o
  guia sim.
- Gates: ruff + format limpos, pytest 413 verde.

---

## 2026-07-28 · T-018 (parcial) — arruamento da paridade edge × cloud

- Entregue: `eval/parity.py` (`CloudPathExtractor`, `compare_paths`, tolerância),
  `evalctl parity <video>`, `tests/test_parity.py` (17 testes).
- O que a comparação isola: as quatro degradações reais do caminho cloud — 320px, JPEG q60,
  10fps em vez de 15, e `RunningMode.IMAGE` em vez de `VIDEO`. Nada além disso muda: mesmo
  arquivo de modelo, mesma FSM depois da extração.
- Decisões:
  - **Compara contagem de reps, não keypoints.** Landmarks idênticos são impossíveis por
    construção (JPEG e modo IMAGE mudam os números) e não é o que o produto entrega.
  - **A tolerância sai da contagem do caminho de referência (edge), não da média.** Com a
    média, um cloud muito errado aumentaria a própria margem — o critério afrouxaria
    justamente no caso em que precisa ser rígido. Há teste para isso.
  - **O `CloudPathExtractor` usa o extractor de produção**, não uma cópia: os bytes que passam
    pelo MediaPipe no teste são os mesmos que passariam vindos de um celular.
  - **Cadência diferente por caminho faz parte da comparação** (15 vs 10fps): menos frames é
    menos chance de a FSM ver o pico do movimento, e isso é uma degradação legítima do cloud.
- Verificação do encanamento com MediaPipe real, sobre um vídeo gerado da referência de UI:
  edge leu 45 frames (3s × 15fps), cloud leu 30 (× 10fps), **os dois detectaram a pessoa em
  100% dos frames** — o JPEG de 320px não perde a pessoa —, e 0 reps dos dois lados, correto
  para imagem estática. Banda medida: 9,8 KB/frame, ~98 KB/s por sessão cloud.
- **Não fecha a task**: falta rodar em vídeo com polichinelo de verdade, e isso é a T-038, que
  depende de gravação. O comando está pronto: `evalctl parity video.mp4 --expected-reps 20`.
- Gates: ruff + format limpos, pytest 413 verde.
- Pendências geradas (2 em "Descobertas"): a paridade é Python×Python, não navegador×servidor;
  e o número de banda medido, a conferir contra o orçamento na T-028.

---

## 2026-07-28 · T-017 — semáforo de slots cloud (o modo cloud passa a existir de verdade)

- Entregue: `workers/shared/slots.py` (`CloudSlots`), admissão consultando o semáforo,
  `analysis-worker` devolvendo a vaga em todos os finais, `tests/test_slots.py` (10 testes) e
  testes de liberação no `test_analysis_worker.py`. `fakeredis[lua]` nas dev deps.
- Decisões:
  - **ZSET com expiração por membro, não `INCR`/`DECR`.** A nota técnica da SPEC-009 sugeria
    contador. Contador atende ao critério 1 (negar a 4ª sessão) mas não ao 2, que exige
    liberar a vaga inclusive em crash de worker: quem crasha não decrementa, e depois de três
    crashes o modo cloud estaria esgotado para sempre, sem nada em log dizendo por quê. Com
    score = expiração e varredura a cada operação, a vaga do morto volta sozinha.
  - **Lua porque varrer-conferir-inserir é um passo só.** Entre o `ZCARD` e o `ZADD` de dois
    processos cabem duas admissões para a mesma vaga.
  - **Idempotente por `session_id`**: retry de rede não pode virar vazamento de vaga.
  - **Quem libera é o analysis-worker**, não a API: é ele que sabe quando a sessão acabou de
    verdade, inclusive por timer e por `no_data` — caminhos que nunca passam pela API.
  - **Libera sem perguntar o modo.** Remover membro ausente é no-op, então o worker chama
    `release` para toda sessão. A alternativa — guardar o modo e checá-lo aqui — é o tipo de
    detalhe que se esquece num caminho de erro e vaza vaga para sempre.
  - **A vaga é tomada antes de a sessão existir.** Registrar primeiro deixaria uma janela com
    token válido para uma sessão que nunca foi admitida.
  - **Falha ao liberar não impede o encerramento**: o score recolhe a vaga depois, e travar o
    fim da sessão deixaria o usuário sem o resultado do treino.
- Um teste antigo caiu com razão: `test_pedido_de_cloud_e_negado_na_fase_0` afirmava que cloud
  é sempre recusado. Virou três testes — cloud com vaga é admitido, sem vaga é negado, e edge
  nunca consulta o semáforo (o modo padrão do produto não pode depender da capacidade cloud).
- Verificação ao vivo contra a stack: quatro `POST /api/sessions` seguidos com
  `requested_mode: cloud` → `cloud, cloud, cloud, denied_cloud`, com `ZCARD slots:cloud == 3`.
  Passados 10s as três fecharam por `no_data` (o caminho do **timer do servidor**, que não
  passa por `session.completed` externo), o ZSET voltou a 0 e uma nova sessão cloud entrou.
- Gates: ruff + format limpos, pytest 396 verde.
- Pendências geradas (2 em "Descobertas"): a nota técnica da SPEC-009 sobre `INCR`/`DECR` ficou
  desatualizada e vale corrigir na próxima passada; e o registro de por que a liberação mora no
  worker.

---

## 2026-07-28 · T-016 — pose-worker: `frames.raw` → MediaPipe CPU → `pose.frame`

- Entregue: `workers/pose_worker/` (extractor + router + main), `workers/shared/pose_model.py`,
  `docker/pose-worker.Dockerfile`, serviço `pose-worker` nos dois compose, extra `pose` no
  pyproject, `tests/test_pose_worker.py` (14 testes), ADR-007.
- Decisões:
  - **ADR-007: `RunningMode.IMAGE`, sem estado entre frames.** A bancada usa `VIDEO`, que
    pressupõe uma sequência contínua com timestamps crescentes por instância. O worker lê de
    consumer group: dois frames seguidos da mesma sessão podem cair em réplicas diferentes,
    então essa premissa não vale. Manter rastreamento exigiria prender sessão a réplica
    (perdendo a tolerância a falha que o grupo dá de graça) ou misturar o rastreamento de
    sessões distintas — pior, porque o estado de uma pessoa influenciaria os landmarks de
    outra. Em troca, o mesmo JPEG dá sempre o mesmo resultado, e é isso que dá sentido à
    T-018.
  - **Modelo resolvido em `workers/shared/pose_model.py`**, reusado pela bancada (direção
    eval → workers, nunca o contrário). Três pontas carregam o mesmo `.task`; se cada uma
    resolvesse à sua maneira, o sintoma de divergência seria "a contagem mudou", sem nada
    apontando para o modelo.
  - **Mesmo decoder JPEG da bancada (cv2).** Com PIL de um lado e OpenCV do outro, a T-018
    mediria a diferença dos decodificadores, não a do pipeline.
  - **`ts` e `seq` do frame original são preservados** no `pose.frame`. Carimbar a hora do
    processamento faria a cadência vista pela FSM virar a do servidor sob carga, e os
    limiares de duração de repetição passariam a medir a fila, não o exercício.
  - **Imagem própria** (MediaPipe + OpenCV ≈ 250 MB): api, gateway e analysis-worker seguem
    enxutos. Modelo entra por volume, não assado na imagem.
  - **Lote de 5, não 50.** Cada frame custa uma detecção completa; puxar 50 encheria a
    memória com trabalho que vence por idade antes de ser feito.
  - **Sem pessoa no quadro não vira evento.** Um `pose.frame` com landmarks inventados faria
    a validação de cena (SPEC-003) dizer que está tudo bem.
- Verificação ponta a ponta contra a stack real, com JPEG de verdade (a referência de UI
  reduzida a 320px, 11 KB — dentro da faixa de 10–25 KB prevista no contrato): três
  `frame.raw` pelo WebSocket saíram como três `pose.frame` com `source=cloud`, 33 landmarks,
  todos visíveis, nariz em (0.518, 0.258). Os três resultados **idênticos** entre si —
  confirmando na prática o determinismo que motivou o ADR-007. No mesmo stream, lado a lado
  com `pose.frame` `source=edge` de sessões anteriores: é o critério 4 da SPEC-005 (downstream
  sem branch por origem) verificado com os olhos.
- Gates: ruff + format limpos, pytest 374 verde, compose de dev e de produção válidos.
- Pendências geradas (3 em "Descobertas"): descarte por idade usa relógio do cliente (risco de
  skew, contraria a nota da spec corrigir — precisa de decisão); IMAGE×VIDEO significa que a
  paridade da T-018 é de contagem, não de keypoints; modelo por volume exige `fetch-model` na
  VPS antes do primeiro deploy cloud.

---

## 2026-07-28 · T-015 — envio de `frame.raw` no modo cloud (início da Fase 1)

- Contrato primeiro (`AGENTS.md`): `EventType.FRAME_RAW`, dataclass `FrameRaw` e rota
  `frame.raw → frames.raw` em `workers/shared/events.py`. Depois gateway, depois cliente.
- Entregue: `FrameRaw` com validação (assinatura JPEG, teto de 256 KB, maior lado ≤ 320px);
  `_stream_de_entrada()` no gateway; `web/src/capture/jpegEncoder.ts` (redução + JPEG q60) e
  `web/src/capture/cloudFrames.ts` (loop de 10fps com trava de envio).
- Decisões:
  - **`frame.raw` é o único tipo cuja rota padrão não é `pose.frames`.** Imagem não entra no
    fluxo da análise; quem a consome é o pose-worker (T-016). Teste trava isso: se a rota
    voltar para `pose.frames`, o analysis-worker receberia JPEG onde espera 33 landmarks.
  - **Trava de "um por vez" no envio cloud.** A codificação é assíncrona e pode passar dos
    100ms do alvo de 10fps; sem a trava os frames se empilhariam enquanto a pessoa treina.
    Frame que chega com codificação em andamento é descartado — mesma regra do backpressure
    do gateway. A trava vem **antes** do relógio: consumir o tick e depois descartar
    derrubaria o fps efetivo abaixo do alvo (há teste para os dois lados).
  - **Validação de tamanho é do servidor, redução é do cliente.** Aceitar frame maior
    empurraria o resize para o pose-worker, que roda com 1 vCPU e é o gargalo do modo cloud
    (SPEC-005, critério 2).
  - **`source: cloud` em `frame.raw`**, embora o produtor seja o navegador — o campo descreve
    o caminho de extração, não a máquina.
  - **`InMemoryBus` passou a registrar o stream de destino** (`routed`, `published_in()`).
    Antes ele fazia `del stream`, então nenhum teste de roteamento podia falhar.
- Um teste antigo caiu, e com razão: `CLIENT_INGEST_TYPES <= ANALYSIS_INPUT_TYPES` deixou de
  valer, porque `frame.raw` entra pelo cliente e **não** vai para a análise. Reescrito para o
  invariante que continua verdadeiro e é o que importa: todo tipo que o cliente pode publicar
  tem consumidor declarado.
- Verificação: `frame.raw` publicado à mão contra a stack real cai em `frames.raw` (não em
  `pose.frames`), com o JPEG intacto como `bin` do MessagePack.
- Gates: ruff + format limpos, pytest 360 verde, tsc limpo, eslint limpo, vitest 144 verde.
- Pendências geradas (3 em "Descobertas"): o caminho cloud não é exercitável até T-016+T-017;
  convenção do `source`; gateway em dev não recarrega código (`uvicorn` sem `--reload`).

---

## 2026-07-28 · T-023 — ambiente de produção (VPS + domínio) separado do de dev

- **Motivo, e ele não é infraestrutural**: `getUserMedia` só existe em contexto seguro, então
  a câmera não abre por IP de rede local. Sem HTTPS de verdade, a T-014 (30s de polichinelo
  no celular) não tem como acontecer. Produção nasceu como pré-requisito de teste, não como
  entrega de produto.
- Entregue: `docker-compose.prod.yml` (autônomo), `docker/web.Dockerfile` (build multi-stage
  do Vite → nginx), `docker/web-nginx.conf`, `scripts/prod.sh`, `.env.prod.example`,
  `docs/DEPLOY.md`. `gunicorn` entrou no extra `server`.
- Decisões:
  - **Arquivo autônomo, não override.** Um `-f base -f prod` herdaria bind mounts e
    `runserver` em silêncio; o dia em que isso for percebido já é tarde. Custa duplicação
    entre os dois compose e vale a pena.
  - **Um domínio, três portas.** `/` → web, `/api/` → api, `/ws/` → gateway. Same-origin
    zera CORS e mantém `wss://` no mesmo host do `https://` — os dois pontos onde deploy
    assim quebra. Portas em `127.0.0.1`; quem expõe é o nginx do Daniel.
  - **`DOMAIN` como fonte única.** O script deriva `VITE_API_URL`, `GATEWAY_WS_URL`,
    `DJANGO_ALLOWED_HOSTS` e `CORS_ALLOWED_ORIGINS`. Mantidas à mão, essas quatro divergem
    calado, e cliente falando com um host enquanto o WS fala com outro só aparece no celular.
  - **`replicas: 1` fixo no `analysis-worker`.** A FSM tem estado em memória por sessão e o
    consumer group dividiria frames da mesma sessão entre réplicas — quebraria só sob carga.
  - **`gunicorn` para o `api`, `uvicorn` para o `gateway`**: a divisão WSGI/ASGI da
    ARCHITECTURE vale em produção também. `GATEWAY_RELAY=0` no `api` para o relay não
    empurrar cada evento duas vezes.
  - **Segredos: gerar, nunca sobrescrever.** `prod.sh secrets` só preenche campo vazio —
    rotacionar `SESSION_TOKEN_SECRET` sem querer derrubaria toda sessão em voo.
  - **`down`/`ps`/`logs` toleram `.env.prod` quebrado.** A hora em que mais se precisa
    derrubar uma stack é justamente quando a configuração está errada.
- Bugs encontrados e corrigidos **antes** da VPS:
  - `docker compose wait` bloqueia até o container **parar**, não até ficar saudável — a
    linha teria travado o primeiro deploy para sempre. Removida: `compose run` já respeita
    `depends_on: service_healthy`.
  - `.env.prod` não estava no `.gitignore` — segredos a um `git add -A` do repositório.
  - `.dockerignore` excluía `web/` inteiro, o que impedia a imagem do cliente de existir.
    Trocado por exclusões específicas (`web/node_modules`, `web/dist`, `public/wasm`…).
  - `application/wasm` explícito no nginx do container: com o MIME errado o navegador recusa
    o módulo, a câmera abre e a pose nunca carrega.
- Verificação (stack de produção subida localmente em portas alternativas, `Host` do domínio):
  `/healthz` e `/readyz` ok; `POST /api/sessions` devolvendo `ws_url` já como
  `wss://<domínio>/ws/session/…`; wasm servido como `application/wasm`; `redis` e `postgres`
  sem porta no host; `Host` estranho recusado com 400; worker abrindo e fechando a sessão
  criada por curl.
- Gates: ruff limpo, pytest 353 verde, tsc limpo, eslint limpo, vitest 132 verde.
- Pendências geradas (3 em "Descobertas"): Caddy→nginx manual; `VITE_API_URL` é build time
  (rebuild obrigatório ao trocar de domínio); produção sem backup/quota/auth (T-022/025/026)
  e sem snapshot de estado (T-031).
- **Não fecha a T-014**: falta o deploy real e os 30s de polichinelo no celular.

---

## 2026-07-28 · [A+B] Cliente ligado à API real + CORS + E2E headless

> **Para o Daniel**: falta só você na frente da câmera. `docker compose up`, abrir
> `http://localhost:5173` (ou o IP da máquina no celular), permitir a câmera e fazer 30 s de
> polichinelo. Tudo antes disso está verificado por máquina.

- `web/src/session/admission.ts`: o cliente **pede a sessão** (`POST /api/sessions`) e abre o
  WS no `ws_url` do ticket. Antes ele inventava `session_id` e token — resto de quando a T-011
  não existia; era uma sessão que o servidor não conhecia. `VITE_WS_URL` continua como escape
  para o mock local.
- `server/core/cors.py`: **sem CORS o app nunca teria funcionado no navegador**, e nenhum
  `curl` mostraria isso — quem aplica a regra é o navegador, não o servidor. Em `DEBUG` libera
  qualquer origem (o celular entra pelo IP da LAN, que ninguém lista antes); fora de `DEBUG`,
  só `CORS_ALLOWED_ORIGINS`, que nasce vazia.
- Serviço `web` no compose — a pendência que ficou **sem dono** entre os dois agentes (o A
  atribuiu ao B, o B disse que compose é território do A). O `setup-mediapipe` agora copia o
  modelo de `eval/models/` antes de sair para a rede, então a primeira subida do container não
  depende de internet.
- `web/src/session/live.e2e.test.ts` (`npm run e2e`, fora da suíte padrão): E2E do cliente
  contra o stack real. Prova o que nada provava — que o **espelho TS do contrato**
  (`lib/events.ts`) fala com o gateway Python. O mock do Agente B foi validado contra o
  `events.py`, mas mock e servidor podem concordar entre si e estarem os dois errados.
- Decisões:
  - **`probe_result` no formato do evento** (`probe_fps`, não `fps`): o cliente manda o payload
    de `session.capability` inteiro e o servidor monta o evento a partir dele. `fps` segue
    aceito para não quebrar ticket antigo.
  - **Middleware de CORS próprio** em vez de `django-cors-headers`: são 30 linhas e a Fase 0
    tem uma regra só. Com domínio de produção e cookies, trocar é uma linha no `MIDDLEWARE`.
  - E2E em config separada (`vitest.e2e.config.ts`), serial: cada teste abre a própria sessão
    e em paralelo disputariam o mesmo worker e o mesmo relógio.
- Bug de teste encontrado de raspão: `test_endpoint_cria_sessao` só passava quando a `views.py`
  ainda não tinha sido importada no momento do monkeypatch — a view faz
  `from api.sessions import create_session`, então patchar o módulo de origem não alcança a
  referência dela. Meus testes de CORS mudaram a ordem dos arquivos e a fragilidade apareceu.
  Agora o patch é em `api.views.create_session`, onde a view de fato lê.
- Gates: `ruff` limpo, **352 testes** Python, `tsc`/`eslint` limpos, **127 testes** web, build
  OK. E2E contra o stack de pé: 8 frames-rep enviados ⇒ **8 reps contadas** pelo servidor,
  `exercise.phase` chegando, nenhum `pose.frame`/`quality.signal` vazando para o cliente; parar
  de enviar ⇒ servidor fecha sozinho com `no_data`.
- Pendências: T-014 só com a validação humana (câmera real); T-038 (corpus) depende de gravar
  os vídeos.

---

## 2026-07-28 · [A+B] Junção das duas linhas de trabalho

- Os dois agentes trabalharam em **repositórios separados** que nunca se falaram: o Agente A em
  `Digital Fit/` (branch `master`) e o Agente B em `df-agent-b/` (branch `agent-b`). A base
  comum é o commit de bootstrap — cada um implementou a **própria T-001**, o que fez toda a
  infra (compose, pyproject, `server/`, README, CI) colidir como `add/add` no merge.
- Resolução: a infra ficou com a linha do Agente A, que evoluiu com gateway, worker e sessões e
  está verificada rodando; `web/` inteiro veio do Agente B; `DEVLOG`/`BACKLOG` foram unidos
  (as duas listas de "Descobertas" valem, e a tabela de tasks agora reflete os dois lados).
- O `web/` que eu tinha começado a montar nesta sessão foi **descartado**: era duplicata de
  trabalho já commitado e mais completo do Agente B (97 testes, mock-gateway validado contra o
  `events.py`, cliente WS com backpressure).
- Estado real da Fase 0 depois da junção: só a **T-014** (E2E com câmera real) e a **T-038**
  (corpus de vídeos) continuam abertas.

---

## 2026-07-28 · [A] T-010 — Feedback engine (núcleo)

> **Agente B**: o HUD agora tem um evento só para mostrar: `feedback.issued`
> `{code, severity, message, hint}`. A `message` e o `hint` já vêm em pt-BR, prontos para a
> tela — **não** monte texto a partir do `code`. O motor garante **no máximo um feedback por
> vez** e no máximo 1 do mesmo código a cada 4 s, então o card do treinador (SPEC-013) pode
> simplesmente substituir o conteúdo quando chega um novo, sem fila própria. `quality.signal`
> não vai mais para o cliente: é insumo do motor.

- `workers/analysis_worker/feedback/`: catálogo em `catalog.pt-BR.yaml` (código → mensagem,
  dica, severidade, prioridade) + `FeedbackEngine` (prioridade, throttle, supressão por cena).
- Ligado no `AnalysisRouter` como último passo do frame: cena e FSM produzem sinais, o motor
  decide o que o HUD vê.
- `SessionState.summary()` passa a devolver `feedback_issued` ao lado de `quality_signals` —
  o relatório (T-020) precisa da diferença entre "detectei 12" e "avisei 3".
- Decisões:
  - **Texto fora do código**: um YAML por idioma (`catalog.<locale>.yaml`); ajustar palavra não
    é deploy. Código desconhecido ou entrada sem `message` é erro na carga — typo não vira
    feedback mudo.
  - **Prioridade no catálogo, não no código** (`priority`, menor vence): cena 10–11, execução
    20–21. Ordenar é dado, não `if`.
  - **Supressão por cena com janela de 3 s** (`SCENE_SUPPRESS_MS`), não flag booleana: o
    validador repete o aviso a cada 2 s, então a janela se renova sozinha enquanto o problema
    existe e expira sozinha quando ele some — sem evento de "cena resolvida", que não existe.
  - **Throttle por código, não global**: braço e perna são problemas diferentes; calar um
    porque o outro falou esconderia metade da correção. Quando um código está em throttle, o
    próximo da fila passa.
  - **`rep.detected` é ignorado** pelo motor: feedback positivo é Fase Evolução.
  - Um motor por sessão — throttle e supressão são estado de sessão.
- Gates: `ruff` limpo, **346 testes** verdes (27 novos). Critérios da SPEC-008 verificados no
  stack real (API → WS → worker → HUD, Redis e gateway de verdade): 12 reps preguiçosas em 12 s
  ⇒ **3 feedbacks** de `ARMS_TOO_LOW` com gaps de 4,1 s (nunca 12); corpo fora de quadro ⇒ só
  `OUT_OF_FRAME`, **zero** crítica de execução; amplitude cheia ⇒ 12 reps e **nenhum** feedback
  falso; latência sinal→HUD **≤ 39 ms** (orçamento: 150 ms).
- Pendências: o card "Dica do Treinador" é T-012 (Agente B); agregação por padrão, TTS e
  feedback positivo ficam na Fase Evolução da SPEC-008.

---

## 2026-07-27 · [A] T-013 — Validação de cena mínima

> **Agente B**: `scene.warning` já chega pelo WS com `{code, severity, hint}` — códigos
> `OUT_OF_FRAME`, `TOO_FAR`, `TOO_CLOSE`. O `hint` vem em pt-BR e pode ir direto para a tela
> enquanto o catálogo do feedback engine não estiver na frente dele.

- `workers/analysis_worker/scene.py`: `SceneValidator` (um por sessão) com as duas travas da
  SPEC-003 Fase Inicial — enquadramento pelas 4 âncoras (ombros e tornozelos, `visibility ≥ 0.5`)
  e distância pela altura do corpo entre 40% e 95% do frame — e o debounce de 1 s para ligar /
  2 s para repetir.
- Ligado no `AnalysisRouter`: a cena é checada **antes** da FSM, então um frame ruim ainda avisa
  o usuário mesmo com a FSM congelada. É exatamente quando o aviso importa.
- Decisões:
  - **Altura do corpo sai dos pontos normalizados × escala**: `(tornozelo_y − nariz_y)` em torsos
    × `torso` (unidades de frame) = fração da altura do frame. Sem isso, o validador precisaria
    dos landmarks crus e teria uma segunda porta de entrada.
  - **`OUT_OF_FRAME` tem prioridade e interrompe a checagem de distância**: sem âncoras
    visíveis, a altura viria de landmarks adivinhados pelo modelo — mediria ruído.
  - O validador **conta** os avisos (`counts`) porque a SPEC-003 manda anexá-los ao relatório
    (T-020).
  - Rosto/mãos invisíveis não são problema de enquadramento — só as 4 âncoras contam.
- Gates: `ruff` limpo, **319 testes** verdes (22 novos). Critérios da SPEC-003: 2 s fora do quadro
  ⇒ **exatamente 1 aviso** (6 s ⇒ 3 avisos, pelo intervalo de 2 s); **zero falso positivo** em
  cena padrão, inclusive durante 20 polichinelos (o movimento muda a altura aparente e não
  dispara distância); 0,5 s de falha ⇒ nenhum aviso.

---

## 2026-07-27 · [A] T-011 — Ciclo de sessão (`POST /api/sessions` + timer autoritativo)

> **Agente B**: o fluxo de abertura está pronto. `POST /api/sessions`
> `{exercise, requested_mode, probe_result}` → `{session_id, token, ws_url, mode, exercise,
> duration_s, expires_at}`. Use o `ws_url` como veio (já traz o token). Pedido de `cloud`
> responde `mode: "denied_cloud"` — Fase 0 é edge only. O **fim da sessão vem do servidor**
> (`session.completed` pelo WS); o timer do HUD é cosmético.

- `server/api/sessions.py`: `SessionRequest.parse` (validação), `create_session` (registro em
  Redis com TTL, publicação de `session.started` e, quando houver probe, `session.capability`).
- `server/api/views.py`: `POST /api/sessions` → 201 com o ticket, 400 para pedido inválido,
  503 quando o Redis está fora.
- `workers/analysis_worker/router.py`: `SessionState.expiry_reason` + `AnalysisRouter.tick()`,
  chamado a cada volta do loop do worker (roda mesmo sem evento chegando).
- Decisões:
  - **Timer no relógio do servidor, não no `ts` do cliente**: celular com relógio torto não pode
    encurtar nem esticar a sessão. Há teste com `ts` no futuro provando isso.
  - **Duas regras de fim**: 30 s desde o primeiro frame ⇒ `completed`; 10 s sem frame ⇒
    `no_data` (critério 4 da SPEC-009). A regra de TTL virou código morto e foi removida — uma
    das duas sempre vence antes dos 45 s; `timeout` fica no vocabulário para o caminho de
    semáforo/quotas (T-017/T-025).
  - **Sessão negada não nasce**: pedido de cloud não gera registro, evento nem slot.
  - Estado da sessão em Redis (hash com TTL), não em Postgres: Fase 0 é anônima e a sessão é
    efêmera. Persistir resultado é a SPEC-010 (T-020).
- Bug encontrado por teste: sessão fechada por `no_data` **sem nenhum frame** montava envelope
  com `ts=0`, que o contrato recusa. Agora o `ts` cai para o relógio do servidor.
- Bug encontrado só na verificação real (e é o mais importante do dia): com `redis-py` 8, o
  `channels_redis` estoura `TimeoutError` na leitura do channel layer e **mata o consumer do
  WebSocket** — o cliente recebia as reps e depois nada. `redis>=5.2,<6` resolveu. Nenhum teste
  pegaria isso: eles usam channel layer em memória.
- Verificado ponta a ponta com os 5 serviços no ar (curl + cliente WebSocket real):
  - `POST /api/sessions` devolve ticket com token válido para aquela sessão; `requested_mode:
    cloud` ⇒ `denied_cloud`; exercício inexistente ⇒ 400;
  - abrir o WS com o `ws_url` do ticket, mandar 3 polichinelos e **parar de enviar** ⇒ o servidor
    encerrou sozinho 11 s depois (`no_data`, 3 reps) e o cliente recebeu o fim;
  - mandando frames sem parar ⇒ o servidor encerrou em **30,0 s** com `completed` e 29 reps.
- Gates: `ruff` limpo, **297 testes** verdes (26 novos), compose com 5 serviços de pé.

---

## 2026-07-27 · [A] T-005 — Gateway Channels (WS ↔ streams)

> **Agente B**: o WebSocket está no ar. `ws://localhost:8001/ws/session/{session_id}?token=…`,
> binário/MessagePack nos dois sentidos. O gateway aceita do cliente **só**
> `pose.frame`, `session.capability` e `session.completed` (abort) — publicar `rep.detected`
> pelo cliente é recusado de propósito. De volta chegam fase, rep, cena, feedback e fim.
> Token inválido/expirado fecha com **4401**; envelope de outra sessão fecha com **4400**.

- `server/api/tokens.py`: token de sessão HMAC-SHA256 truncado (`{expira_em}.{assinatura}`),
  TTL de 45 s, comparação em tempo constante. Emitido pela API na T-011, verificado aqui.
- `server/gateway/consumers.py`: `SessionConsumer` — valida token, entra no grupo da sessão,
  valida envelope, confere que a sessão do envelope é a da URL e enfileira para publicação.
- `server/gateway/relay.py`: um consumidor por processo lê `events.analysis` (grupo `gateway`)
  e faz `group_send` ao grupo da sessão; quem tem a conexão empurra pelo WS.
- `core/asgi.py` virou `ProtocolTypeRouter` (HTTP + WS) e sobe o relay; serviço `gateway`
  (uvicorn, porta 8001) no compose.
- Decisões:
  - **`group_send` via channel layer** em vez de o relay falar direto com a conexão: com 2
    processos de gateway (ADR-002), o evento lido por um processo precisa alcançar a conexão que
    está no outro. Sem isso, metade dos feedbacks se perderia ao escalar.
  - **Publicação em tarefa separada com fila de 3** (`INGEST_BUFFER`): `receive` nunca bloqueia,
    e frame novo desbanca frame velho — é o backpressure da SPEC-002 aplicado onde o servidor
    pode aplicá-lo.
  - **`CLIENT_INGEST_TYPES`**: o cliente só publica frames, capability e encerramento. Sem essa
    lista, um navegador poderia injetar `rep.detected` e a contagem não valeria nada.
  - **Sem `daphne` em produção**: o gateway sobe com uvicorn; daphne ficou só no grupo `dev`
    porque `channels.testing` o importa.
  - Texto no WS é ignorado (o transporte é MessagePack) e envelope corrompido é logado sem
    derrubar a conexão — critério 3 da SPEC-002.
- Verificado com o compose no ar (gateway + worker + redis), cliente WebSocket real:
  - 62 `pose.frame` de 4 polichinelos ⇒ **4 `rep.detected` + 8 `exercise.phase` chegaram ao
    cliente**, e o `session.completed` voltou com `rep_count=4` (critério 1 do fluxo);
  - **latência frame → evento no cliente: mediana 18 ms, p95 28 ms, máx 31 ms** (orçamento da
    SPEC-002 é < 150 ms) — medido com envio em tempo real a 15 fps;
  - **matar o `analysis-worker` no meio da sessão não derrubou o WS** (critério 2): o cliente
    seguiu conectado, e ao religar o worker as repetições voltaram a chegar. Ressalva honesta:
    sem snapshot, a FSM recomeça e o `rep_count` reinicia — previsto para a Fase 0 (T-031);
  - token `lixo` não conecta (o servidor recusa o upgrade).
- Gates: `ruff` limpo, **271 testes** verdes (32 novos), compose com 5 serviços (o `api` não
  subiu por porta 8000 ocupada no host — registrado em Descobertas).

---

## 2026-07-27 · [A] T-009 — analysis-worker (consumer de `pose.frames`)

> **Pegadinha do contrato, importante para a T-011 e para o gateway**: quem quer que o
> analysis-worker **veja** um evento publica em `pose.frames` explicitamente — inclusive o
> `session.completed` de encerramento. A rota padrão de `session.completed` é `events.analysis`
> (é a saída do worker), então publicar na rota padrão faz a sessão nunca fechar. Agora está
> codificado em `ANALYSIS_INPUT_TYPES` (events.py) e coberto por teste.

- `workers/shared/bus.py`: barramento sobre Redis Streams (`RedisBus`) + `InMemoryBus` para
  teste, atrás do protocolo `EventBus`. O gateway da T-005 usa o mesmo.
- `workers/analysis_worker/router.py`: `AnalysisRouter` — envelope entra, envelopes saem, **sem
  I/O**. Uma sessão = um `Normalizer` + um `ExerciseAnalyzer` + contador de `seq` de saída.
- `workers/analysis_worker/main.py`: loop (consume → handle → publish → ack), parada limpa em
  SIGTERM/SIGINT, `max_batches` para teste. Serviço `analysis-worker` no compose.
- Decisões:
  - **`seq` de saída é do worker**, contado por sessão: o `seq` do cliente numera frames de
    entrada e não serve para numerar eventos de análise.
  - **Ack sempre**, mesmo quando o processamento falha: evento problemático não pode ser
    reprocessado em loop nem matar o worker (há teste com roteador que explode de propósito).
  - **`pose.frame` sem `session.started` abre a sessão** com o padrão de 30 s em vez de
    descartar: perder repetições por corrida de eventos seria pior que assumir o default.
  - Frame que chega **depois** do fim abre sessão nova do zero — não soma em sessão encerrada.
  - Estado em memória, como o ARCHITECTURE §6 previu. **Snapshot em Redis não foi feito**: sem
    consumidor (retomada é T-031), seria peso morto.
  - O **timer autoritativo de 30 s ficou para a T-011**, junto do resto do ciclo de vida da
    sessão; aqui o worker fecha quando recebe o pedido de encerramento.
- Verificado com Redis e worker de verdade no compose (não só com o barramento falso):
  `session.started` + 92 `pose.frame` (6 polichinelos) + encerramento ⇒ **12 `exercise.phase`,
  6 `rep.detected`, 1 `session.completed` com `rep_count=6`**, ida e volta pelo Redis em
  **99 ms**. O log do worker mostra abertura e fechamento da sessão.
  A primeira tentativa deu 1 rep de 6 — e o culpado era o **script de verificação**, que
  publicou o encerramento na rota padrão; foi o que motivou o `ANALYSIS_INPUT_TYPES`.
- Gates: `ruff` limpo, **239 testes** verdes (29 novos), `docker compose up` com os 4 serviços.

---

## 2026-07-27 · [A] T-039 — Métricas, `evalctl compare` e fixtures de keypoints

> **Agente B (T-007, gravador de fixtures)**: o formato de fixture agora existe e é
> compartilhado — `workers/shared/keypoints.py`, `schema: 1`. Grave exatamente isso no
> navegador e o `pytest` e o `evalctl` consomem sem conversão.

- `workers/shared/keypoints.py`: formato de fixture de keypoints (`schema`, `label`,
  `exercise`, `expected_reps`, `source`, `fps`, `notes`, `conditions`, `frames[{ts,seq,
  landmarks}]`) + `save_fixture`/`load_fixture`. Ficou em `shared` de propósito: é fronteira
  entre bancada, testes, worker (replay da T-041) e cliente (T-007).
- `eval/metrics.py`: `aggregate()` (MAE de reps, % de vídeos exatos, taxa de falso positivo nos
  negativos e quebra por condição de gravação) e `compare()` (por vídeo + agregado, com
  regressão explícita). `evalctl compare a.json b.json` sai com **código 1 em regressão** — é o
  gate que a T-042 vai usar em CI.
- `evalctl run --save-keypoints DIR` exporta a fixture de cada vídeo (SPEC-012, critério 3).
- Decisões:
  - **Fixture guarda landmarks crus, não normalizados**: normalização é código que muda, e a
    fixture existe justamente para medir mudança de código. 5 decimais por coordenada — muito
    acima do ruído do modelo, e diff estável no git.
  - **Taxa de falso positivo é métrica de primeira classe**: negativo é vídeo rotulado com 0
    reps; sem essa métrica, "melhorar a contagem" pode virar inflar contagem.
  - **Vídeo com erro de leitura sai da conta de acurácia** (mas é contado em `errors`): uma
    falha de I/O não deve mascarar nem piorar a medida do algoritmo.
  - **Vídeo sem rótulo nunca gera veredito** no `compare` — aparece como "mudou (sem rotulo)".
    Regressão só se afirma contra rótulo.
- Verificado no CLI real: corpus com manifest (1 vídeo + 1 arquivo faltando) ⇒ tabela por vídeo,
  agregado e quebra por `light`/`distance`/`angle`, com o vídeo ausente isolado como erro;
  `compare` de um relatório contra uma versão degradada ⇒ "pior", `MAE 0.000 -> 3.000`,
  `REGRESSAO em: ...`, código de saída 1.
- Gates: `ruff` limpo, **210 testes** verdes (27 novos).

---

## 2026-07-27 · [A] T-037 — `evalctl run` (bancada de avaliação)

- `eval/`: `sources.py` (decode de vídeo + extração de pose), `pipeline.py` (frames →
  normalização → FSM → `VideoResult`), `evalctl.py` (CLI `run` e `fetch-model`), rodável com
  `uv run python -m eval.evalctl run video.mp4 --expected-reps 20 --report eval/out/eval.json`.
- Decisões:
  - **Extração de pose por interface** (`PoseExtractor`): a implementação real é MediaPipe, e os
    testes injetam um dublê alimentado por keypoints sintéticos. Resultado: 26 testes da bancada
    rodam em ~1 s, sem MediaPipe, sem OpenCV e sem vídeo.
  - **Imports pesados são tardios** e há teste que prova isso (subprocesso verifica que
    `import eval.pipeline` não carrega `mediapipe` nem `cv2`).
  - **`source: "file"` entrou no contrato** (`Source.FILE`), como a SPEC-012 previa: resultado de
    bancada nunca se disfarça de sessão real no dataset. Mudança de contrato registrada aqui
    para o Agente B — é adição de valor no enum, não quebra nada existente.
  - **MediaPipe Tasks, não `mp.solutions`**: a API legada não existe mais no MediaPipe 1.0, e a
    Tasks é justamente a que a SPEC-005 manda usar no cliente. Modelo `pose_landmarker_lite.task`
    fica fora do git; `evalctl fetch-model` baixa uma vez (5,5 MB). Resolução do caminho:
    argumento `--model` > `DIGITALFIT_POSE_MODEL` > `eval/models/`.
  - **Decimação por tempo** (não por contagem) no leitor de vídeo, igual ao frame clock do
    cliente (SPEC-001) — a bancada vê a mesma cadência que o navegador enviaria.
  - **Um vídeo ruim não derruba o corpus**: falha vira campo `error` no resultado daquele vídeo.
    Erro de leitura sai com código 1; contagem errada **não** é erro de execução (isso é métrica,
    T-039).
  - `manifest.yaml` traz `expected_reps` e `conditions`; pasta sem manifest processa os vídeos
    sem rótulo.
- Verificado de ponta a ponta com MediaPipe de verdade (não só com o dublê):
  - vídeo sintético sem pessoa ⇒ 30 frames sem pose, 0 reps, `eval.json` com commit e versão do
    modelo — encanamento decode → Tasks → normalização → FSM → JSON;
  - foto real de polichinelo aberto (a referência do Daniel) ⇒ pose detectada e features
    coerentes: `arm_angle=148°`, `ankle_spread=2.44`, pulsos acima dos ombros, frame não
    degradado. As features leem a imagem como "aberto", que é o que a FSM precisa.
- Gates: `ruff` limpo, **183 testes** verdes (26 novos). Critérios da SPEC-012 atendidos: roda só
  com Python (1), bancada e worker importam o mesmo módulo — há teste que verifica o
  `__module__` (2), vídeo negativo de pessoa parada dá 0 reps (4). `--save-keypoints` é T-039 (3).

---

## 2026-07-27 · [A] T-008 — `ExerciseAnalyzer` + FSM do polichinelo

- `workers/analysis_worker/exercises/base.py`: interface `ExerciseAnalyzer` (Protocol) com
  `features`/`step`/`ready_pose`/`scene_hints`/`summary`, os tipos `Features` e
  `AnalysisEvent`, o helper `feed(analyzer, frame)` e o registro `EXERCISES` +
  `get_analyzer(slug)` (o usuário escolhe o exercício; nada de detecção automática).
- `workers/analysis_worker/exercises/jumping_jack.py`: features (`arm_angle`,
  `wrist_above_shoulder`, `ankle_spread`, `cadence_10s`, `degraded`) + FSM fechado ⇄ aberto
  com histerese e debounce de 250 ms, e sinais de rep parcial.
- Decisões:
  - **A FSM emite payloads do contrato** (`ExercisePhase`, `RepDetected`, `QualitySignal`), não
    envelopes: `session_id`/`seq` são do worker. Analisador puro, sem I/O.
  - **`degraded` entra no dicionário de features** — a assinatura `step(feats, ts)` é fixada
    pela SPEC-007, e a qualidade do frame é informação que a FSM precisa para congelar.
  - **`ankle_spread` divide pela largura de ombros já normalizada** (em torsos), não pela de
    `NormFrame.shoulder_width` (unidades de frame) — misturar as duas escalas seria erro
    dimensional. A versão com baseline é a T-019.
  - **Sinal de rep parcial nasce ao voltar à posição fechada**, um por tentativa: reclamar a
    cada frame seria spam, e o throttle da SPEC-008 não deve existir para corrigir excesso da
    FSM.
  - `JumpingJackThresholds` é dataclass frozen e parametrizável porque a bancada da SPEC-012
    vai varrer esses limiares contra o corpus.
- **Para o Agente B (T-044, ângulo ao vivo no HUD)**: a fórmula a espelhar é
  `arm_angle = média dos dois braços de degrees(atan2(|dx|, dy))`, com `dx`/`dy` de
  ombro→pulso **nos pontos normalizados** (y cresce para baixo): 0° = braços ao lado do corpo,
  180° = acima da cabeça. Mesmo cálculo em TS dá paridade bem abaixo dos 5° exigidos.
- Dois bugs encontrados pelos próprios testes (e corrigidos):
  1. `EXERCISES[JumpingJackAnalyzer.slug]` registrava o *descritor do slot* como chave — em
     dataclass com `slots=True` o atributo de classe não é o default. Agora é literal.
  2. O gerador de fixtures terminava a sequência no instante exato do fechamento, então a
     última repetição ficava "em andamento" e a contagem dava 19/20 em alguns fps. As
     sequências agora terminam em pé, como uma gravação real.
- Gates: `ruff` limpo, **157 testes** verdes (48 novos). Critérios da SPEC-007:
  1. 20 polichinelos limpos ⇒ **exatamente 20** (também 1, 5, 20; a 10/15/30 fps; a 0,15/0,30/
     0,45 de torso, isto é, ~4 m a ~1,5 m da câmera);
  2. reps preguiçosas (amplitude 0,6 ⇒ pico ~105° e ~1,27) ⇒ **0 reps** + `ARMS_TOO_LOW` e
     `LEGS_TOO_CLOSED`, um sinal por tentativa;
  3. tremor parado (σ = 0,006, 300 frames) ⇒ **0 reps**; oscilar em cima do limiar ⇒ 0 reps;
  4. `step()` em **0,0009 ms** (exigido < 1 ms); com `features()`, o pipeline de análise custa
     0,008% de 1 vCPU por sessão a 15 fps.
- Medido de lado: o debounce de 250 ms conta corretamente até **~2 rep/s** (120 rpm) e descarta
  3+ rep/s como ruído. Cadência humana de polichinelo é 40–80 rpm, então há folga — mas é o
  teto da regra da spec, registrado aqui para não virar surpresa.

---

## 2026-07-27 · [Arquiteto] SPEC-013 — Interface Mobile a partir da referência do Daniel

- Referência visual aprovada movida para `referencias/ui-sessao-mobile-v1.png` e formalizada
  na SPEC-013 (vinculante para toda UI, mobile-first): barra de métricas (série/reps/ângulo/
  kcal), esqueleto sobre câmera, card do exercício + anel de countdown, card "Dica do
  Treinador" (superfície do feedback engine), bottom nav + FAB. Design tokens extraídos.
- A referência introduz features novas, faseadas: ângulo ao vivo (Fase 0, client-side, T-044);
  meta de reps e séries (evolução, T-045); kcal por MET + telas de catálogo/progresso/perfil
  (evolução, T-046). Nenhum evento novo no contrato v1 — ângulo é cosmético no edge;
  `metrics.update` só quando o modo cloud precisar.
- Propagado: T-012 redefinida (segue SPEC-013), T-043/T-044 na Fase 0; SPEC-008 aponta o card
  do treinador como sua superfície; SPEC-009 ganha meta/séries na evolução; prompt do Agente B
  atualizado (SPEC-013 + imagem viraram leitura obrigatória, ordem de tasks ajustada).

---

## 2026-07-27 · [A] T-006 — Normalização & One Euro Filter

- `workers/shared/filters.py`: One Euro Filter próprio, vetorizado em numpy — um filtro
  mantém estado por canal, então os 33×3 coordenadas passam numa chamada. `visibility` nunca
  é filtrada.
- `workers/shared/normalize.py`: `normalize(frames) -> frames` (função pura da SPEC-006) e
  `Normalizer` (mesma lógica com estado explícito, para o worker frame a frame). Saída
  `NormFrame` em torsos, com `to_data()` para o campo `data.norm` do mesmo `pose.frame`.
- `tests/synthetic_keypoints.py`: gerador determinístico de bonecos de 33 landmarks
  (abdução dos braços × afastamento dos tornozelos), com distância da câmera, posição no
  quadro, fps, visibilidade e jitter parametrizáveis. Serve também para a FSM da T-008.
- Decisões:
  - **Filtra em torsos, não em pixels**: normaliza primeiro, filtra depois. Assim `mincutoff`
    e `beta` significam a mesma coisa para quem está a 2 m e a 4 m — sem isso os parâmetros
    teriam de mudar com a distância.
  - **A escala também é suavizada** (filtro próprio, `scale_mincutoff=0.4`): o torso medido
    frame a frame tem ruído, e dividir por escala ruidosa injetaria jitter em tudo.
  - **Frame `degraded` não entra no filtro** e a escala anterior é mantida: landmarks
    "adivinhados" pelo modelo poluiriam o estado e sujariam os frames bons seguintes.
  - **`degraded` = média de visibilidade das 6 âncoras** (ombros, quadris, tornozelos) < 0.5 —
    os landmarks de que normalização e features dependem. Rosto/mãos invisíveis não invalidam
    o frame.
  - `Baseline` (torso/largura de ombros) já é parâmetro opcional; **medir** a baseline é a
    T-019 — aqui só se usa quando existe, senão vale o valor instantâneo.
  - Defaults `mincutoff=0.4, beta=1.5` escolhidos por **grade medida** (6×5 combinações) em
    10/15/30 fps contra os dois critérios da spec, não por chute.
- Gates: `ruff` limpo, **109 testes** verdes (29 novos de normalização, 12 do filtro).
  Critérios da SPEC-006 verificados um a um:
  1. 2 m vs 4 m ⇒ features idênticas (bem dentro dos 5%; a sequência inteira bate a 1e-6);
  2. jitter de pessoa parada **−70,1%** (exigido ≥ 60%) com **0 frames** de atraso no
     movimento rápido e 93% da amplitude preservada;
  3. `normalize()` pura — mesma entrada dá mesma saída, não muta a entrada, e o `Normalizer`
     incremental produz exatamente o mesmo resultado.
- Medido de lado: 0,056 ms/frame ⇒ ~0,08% de 1 vCPU por sessão a 15 fps (o orçamento do
  ARCHITECTURE §8 para o analysis-worker é 1–2%, então a FSM da T-008 tem folga).

---

## 2026-07-27 · [A] T-002 — **Contrato v1 publicado** (`workers/shared/events.py`)

> **Agente B: este é o contrato.** Envelope `{v, type, session_id, ts, seq, source, data}`,
> MessagePack no WebSocket. Tabela dos 9 eventos da Fase 0 na SPEC-002 (seção "Contrato v1
> publicado"); a fonte da verdade é `workers/shared/events.py`.

- Eventos v1 (Fase 0): `session.capability`, `session.started`, `pose.frame`,
  `exercise.phase`, `rep.detected`, `quality.signal`, `scene.warning`, `feedback.issued`,
  `session.completed`. Uma dataclass por payload, com `to_data()`/`from_data()`.
- Vocabulário fechado em enums: `Source` (edge/cloud/system), `Mode`, `Phase` (closed/open),
  `Severity` (info/warning), `Code` (ARMS_TOO_LOW, LEGS_TOO_CLOSED, OUT_OF_FRAME, TOO_FAR,
  TOO_CLOSE), `SessionEndReason` (completed/timeout/aborted/no_data), `Landmark` (33 índices
  do MediaPipe) e `Stream`.
- Decisões (importam para o cliente):
  - **`pose.frames` = entrada da análise** (frames + metadados da sessão); **`events.analysis`
    = saída** (o que HUD, relatório e dataset consomem). `STREAM_FOR_TYPE` é a rota padrão.
  - **`CLIENT_PUSH_TYPES`**: o gateway devolve ao cliente só fase, rep, cena, feedback e fim.
    `pose.frame` nunca volta; `quality.signal` é insumo interno do feedback engine — o HUD vê
    `feedback.issued`.
  - **Um campo por entrada de stream** (`e` = envelope MessagePack): WS e Redis usam
    exatamente a mesma serialização, sem conversão campo-a-campo no hot path.
  - Normalização (SPEC-006) enriquece o **mesmo** `pose.frame` em `data.norm` — sem tipo novo.
  - Validação leve: envelope valida no `__post_init__` (tipo/fonte/ts/seq/versão); a contagem
    de 33 landmarks só é checada quando o payload é decodificado, para não pesar no gateway.
  - `MAXLEN ~5000` e `CONSUMER_GROUPS` declarados aqui, mas aplicá-los é do produtor/consumidor.
- Gates: `ruff check` + `ruff format --check` limpos; **66 testes** verdes (round-trip
  MessagePack e stream de todos os payloads, 11 formas de envelope inválido, bytes corrompidos,
  payload sem campo, código desconhecido, tabelas de roteamento e landmarks).
  Medido em processo real: `pose.frame` = **1339 bytes** ⇒ ~19,6 KB/s a 15 fps (orçamento do
  ARCHITECTURE §4 é 20–30 KB/s). Nenhum import de Django no caminho dos workers.
- `pyproject.toml`: `ignore = ["RUF002", "RUF003"]` — docstrings/comentários em pt-BR usam
  travessão e meia-risca; RUF001 (strings de código) segue ativo.

---

## 2026-07-27 · [B] Ponta cliente do WebSocket (envio + backpressure)

- Fecha a última task da minha fila. O cliente agora **envia** `pose.frame` a 15fps, além de
  receber os `CLIENT_PUSH_TYPES`.
- **Backpressure da SPEC-002**: fila de no máximo 3 frames; encheu, descarta o **mais antigo**.
  Frame novo vale mais que frame velho — entregar frame atrasado é pior que não entregar.
  O cliente também para de empurrar quando `bufferedAmount` passa de 64 KB.
- **Decisão sobre o `seq`** (pendência que eu tinha registrado na T-004): o contrato diz
  "monotônico por **sessão**", sem ressalva por tipo, então criei `clientSequencer.ts` — um
  contador único por sessão que todos os eventos do cliente consomem. O frame clock continua
  dono do `ts` e da decimação, mas o `seq` do envelope sai do sequenciador.
  **Consequência que o Agente A precisa saber**: o `seq` dos `pose.frame` que chegam ao
  gateway **não é contíguo**, porque a `session.capability` consome o 0. Atualizei a
  descoberta no BACKLOG com isso.
- `session.capability` é enviada no momento em que o socket abre (o probe já terminou, porque
  a sessão só conecta com a câmera de pé).
- Estados de conexão viraram faixa na tela: conectando, e um aviso laranja explícito quando
  cai — dizendo que a contagem não vai avançar e como subir o mock. Silêncio aqui seria pior:
  o usuário veria o esqueleto funcionando e o contador parado, sem explicação.
- `sessionId`/token: na Fase 0 o cliente inventa o id (`POST /sessions` é a T-011). Dá para
  forçar por `?session=` e `?token=` para teste manual. Quando a T-011 existir, id e token
  passam a vir **só** de lá.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` **118/118**,
  `npm run build` OK.
- **Não verificado**: o envio de ponta a ponta. O mock conta os frames que recebe, mas sem
  webcam não há frame para enviar — o caminho `câmera → pose → WS → mock` só fecha com o
  Daniel na frente da câmera.

---

## 2026-07-27 · [B] T-044 — Ângulo articular ao vivo (+ correção do formato da T-007)

### Correção da T-007: eu tinha inventado um formato

Ao procurar a fórmula da FSM, encontrei `workers/shared/keypoints.py`, onde o Agente A já
tinha definido o `schema: 1` de fixture e escrito, no docstring, que é "o mesmo formato que o
gravador do cliente (T-007, Agente B) escreve". O meu gravava outra coisa (lista de envelopes
`pose.frame`). **Reescrevi o gravador para o schema dele** — o formato de interoperação é
dele, não meu. `load_fixture()` agora lê a saída do gravador sem conversão nenhuma, incluindo
`expected_reps` (que passei a perguntar ao parar a gravação: sem o rótulo, a fixture tem os
keypoints mas não a resposta certa). O contexto do device foi para `conditions`, campo livre
do schema. **Lição**: varrer `workers/shared/` inteiro antes de definir formato, não só
`events.py`.

### T-044

- `armAngle` espelha `_abduction` da FSM: `atan2(|dx|, dy)` em graus, média dos dois braços.
- **A paridade falhou de primeira e o motivo foi instrutivo.** Meu ângulo cru errava até 22°
  contra o worker — mais de 4× a tolerância. O erro era idêntico nos três casos de teste
  (2m, 4m, deslocado no quadro), o que provou que a fórmula estava certa e o problema era
  outro: o worker calcula sobre coordenadas **suavizadas** pelo One Euro, e eu comparava com
  o valor cru. Era lag de filtro, não erro de geometria.
- Para fechar o critério 4 tive de espelhar também `filters.py` e a ordem de
  `Normalizer.push` (`torso → escala suavizada → recentragem → One Euro → ângulo`), com os
  mesmos `NormParams`. Filtro só as 12 coordenadas que a fórmula usa — o One Euro tem estado
  independente por canal, então dá exatamente o mesmo que filtrar as 99 e descartar o resto.
- **Fixture de paridade gerada pelo código real do Agente A**: rodei o `JumpingJackAnalyzer`
  sobre sequências sintéticas normalizadas e gravei `landmarks crus + expected_arm_angle` em
  `web/src/pose/__fixtures__/`. 4 casos (2m, 4m, deslocado, com jitter), 128 amostras
  cobrindo 12°–161°. O número esperado é a saída dele, não um valor que eu escolhi.
- Um dos testes é deliberadamente ao contrário: afirma que **sem** o filtro o erro estoura a
  tolerância. Se alguém "simplificar" o tracker tirando o filtro, esse teste explica o porquê.
- Publicação a ≤10Hz (a spec não quer número piscando), mas o filtro é alimentado a cada
  frame — pular amostra corromperia a estimativa de velocidade dele.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` **112/112**.
- Pendência gerada: **duplicação cross-território do One Euro**. Se o Agente A mexer em
  `NormParams`, o teste de paridade quebra sem ninguém tocar no `web/`. Registrei as três
  saídas possíveis em "Descobertas" — decisão é do Daniel.

---

## 2026-07-27 · [B] T-012 — Tela de Sessão (SPEC-013) contra o mock de gateway

- **Mock do gateway** (`web/dev/mock-gateway.mjs`, fora do bundle): servidor node que fala o
  contrato v1 em MessagePack. Emite `session.started`, fases, reps, dois feedbacks, um
  warning de cena e `session.completed` aos 30s. **Validado contra o `events.py` do Agente A**:
  43 envelopes capturados passaram por `Envelope.from_dict` + `payload()`, `seq` monotônico
  0..42 sem repetição, nenhum tipo fora de `CLIENT_PUSH_TYPES` + `session.started`.
- **Cliente WS** (`src/lib/gateway.ts`) é o MESMO para mock e real — muda só `VITE_WS_URL`.
  Envelope inválido é descartado com log e não derruba a conexão (mesma regra da SPEC-002).
- Tela ligada aos eventos: contador vem de `rep.detected.rep_count` (**não é somado no
  cliente** — a autoridade é o worker), anel de 30s é cosmético a partir de `session.started`,
  card do treinador consome `feedback.issued`/`scene.warning`.
- **Prioridade do card** (`resolveCoachCard`, função pura): cena > feedback > `default_tip`.
  O card nunca fica vazio. Catálogo de exercícios do cliente ganhou os campos que a SPEC-013
  pede (`display_name`, `category`, `muscle_group`, `default_tip`, `main_angle`).
- Fase Inicial conforme a spec: SÉRIE fixo em `1`, REPETIÇÕES sem meta, ÂNGULO `--` (é a
  T-044) e KCAL `--` (MET é evolução). `placeholders.ts` da T-043 foi **deletado** — não
  sobrou número inventado na tela.
- Bug pego pelo lint e que valeu a pena: eu lia `Date.now()` no render do card. Além de
  impuro, era silencioso — o TTL só reavaliaria quando outra coisa causasse re-render, e o
  card ficaria preso no aviso vencido. Virou `useNow`, que só tiquetaqueia com aviso ativo.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` **97/97**,
  `npm run build` OK, screenshot 430×932 conferido.
- **Não verificado**: critério 1 (celular real) e o card trocando com sessão ao vivo —
  dependem de webcam. O caminho mock → tela só roda de ponta a ponta com câmera.
- Pendências geradas (2 em "Descobertas"): `scene.warning` **não tem campo `message`** (o
  cliente ficou com um mapa código → pt-BR que duplica o catálogo da T-010); e **não existe
  evento de "aviso resolvido"**, contornado com TTL de 6s no cliente.

---

## 2026-07-27 · [B] T-043 (2ª passada) — Alinhamento à SPEC-013

- Descobri no DEVLOG que o Arquiteto formalizou a referência na **SPEC-013** e atualizou meu
  prompt (SPEC-013 virou leitura obrigatória; ordem de tasks mudou: T-007 → T-043 → T-012 →
  T-044 → WS). A primeira passada da T-043 saiu só da imagem; esta refaz contra os tokens.
- Tokens agora são os da spec, não os que eu tinha estimado da imagem: `--bg #0B0B10`
  (era preto puro), `--accent #7C5CFF` (era `#a855f7`), `--accent-2 #A78BFA`, `--hot #FF8A3D`,
  `--text-dim rgba(255,255,255,.6)`, `--radius 18px`, `--skeleton #EAF2FF`.
- Glass real nas 3 superfícies permitidas (barra de métricas + 2 cards) com
  `backdrop-filter: blur(16px)`; **bottom nav ficou sólida de propósito** — a nota técnica da
  spec limita a 3 blurs simultâneos por custo em mobile.
- `font-variant-numeric: tabular-nums` nos números de métrica e no relógio do anel (critério
  de aceite 2: sem layout shift quando o contador muda).
- Esqueleto passou a usar o token `--skeleton`. Como o canvas está em pixels de **vídeo**
  (640) e não de CSS (~430 no celular), mantive `lineWidth: 3`, que dá os "~2px" que a spec
  pede na tela.
- Bottom nav: Exercícios/Progresso/Perfil agora são placeholders **declarados** — ficam
  esmaecidos, marcados `aria-disabled` e respondem "em breve" ao toque, em vez de fingirem
  navegação. O FAB central liga/desliga a sessão via `cameraControls` no store, para a nav
  não precisar conhecer o pipeline.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` 78/78,
  screenshot 430×932 conferido.
- Pendência gerada: **anel de countdown** — a spec diz gradiente roxo, a imagem mostra ciano
  → roxo. Segui a spec e registrei em "Descobertas" para o Arquiteto decidir.

---

## 2026-07-27 · [B] T-007 — Gravador de fixtures

- Botão de dev que acumula os keypoints da sessão e baixa um JSON para os testes do núcleo.
- **Formato**: `events` é uma lista de envelopes `pose.frame` do contrato, sem nenhum campo
  inventado. Rótulo, `capability`, resolução e `target_fps` ficam **em volta** dessa lista,
  não dentro dos envelopes — embalagem de fixture não é protocolo.
- **Interop verificada de verdade**, não só por teste unitário: gerei uma fixture pelo
  gravador e carreguei no lado Python do Agente A — 20 envelopes passaram por
  `Envelope.from_dict` + `payload()`, viraram `RawFrame` e rodaram em `normalize()` da
  SPEC-006 sem nenhum ajuste. É a primeira prova de que os dois territórios se encaixam.
- Decisões:
  - Gravador é **instância única fora do React**: o loop escreve nele a 15Hz e não pode
    provocar render. O store só guarda `recording`/`recordedFrames` para a UI.
  - Cada gravação abre uma sessão nova (`seq` recomeça do zero), igual ao contrato.
  - Frame sem pose detectada é descartado: viraria `landmarks: []`, que o contrato rejeita
    por exigir exatamente 33.
  - `window.prompt` para o rótulo — é ferramenta de dev; um modal próprio seria escopo que
    a task não pede.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` **78/78**.
- Pendências geradas (2 em "Descobertas"): **escopo do `seq`** (por sessão ou por tipo?) —
  bloqueia a ponta cliente do WS e precisa de decisão do Agente A; e o invólucro da fixture,
  que é trocável se o A preferir outro.

---

## 2026-07-27 · [B] T-004 — Capability probe + frame clock + `?mode=`

- **Contrato v1 consumido.** O `workers/shared/events.py` do Agente A já existia, então
  criei o espelho TypeScript em `src/lib/events.ts` — tipos, enums, códigos, envelope e
  `CLIENT_PUSH_TYPES`, tudo copiado do contrato, nada inventado. Chaves ficaram em
  **snake_case** de propósito: é o formato do fio, e traduzir na fronteira só criaria
  mais uma chance de drift. `src/lib/events.test.ts` trava o espelho contra o contrato
  (ordem dos 33 landmarks, tipos empurrados ao cliente, invariantes do envelope).
- **Frame clock** (`src/capture/frameClock.ts`): decimação **por tempo**, não por contagem,
  como pede a nota da SPEC-001. Testado com fonte de 24, 30 e 60fps — todos convergem para
  15 ± 1fps. A folga de `interval/3` existe porque, sem ela, uma câmera de 30fps perderia o
  alvo de 66,7ms por 0,1ms e o fps efetivo cairia pela metade.
- **Probe** (`src/probe/`): `decideMode` é função pura e testável sem GPU; a medição roda 2s
  no MESMO landmarker da sessão (nota da spec: config diferente faz o probe mentir) e conta
  só frames de vídeo distintos. `detectWasmSimd` valida um módulo WASM mínimo com `v128`.
- **`?mode=edge|cloud`** força o modo, mas a medição roda mesmo assim — o fps medido continua
  visível no chip de dev, e o modo forçado aparece marcado com `*`.
- Decisões:
  - `usePoseOverlay` virou `useEdgePipeline`: carregar modelo → probar → só então abrir o
    loop de frames. Era o jeito honesto de garantir "o probe usa o MESMO modelo".
  - Loop passou a usar `requestVideoFrameCallback` com fallback para `requestAnimationFrame`.
  - **Modo cloud não faz nada de útil na Fase 0** — `frame.raw` é a T-015. Em vez de fingir,
    o cliente mostra um aviso explícito de que não há esqueleto local nesse modo.
  - Pausa longa (aba escondida) reancora o relógio em vez de disparar rajada de frames
    atrasados, que estouraria a fila do gateway na volta.
- Critérios de aceite da SPEC-001: (1) probe dura 2s + carga do modelo, dentro dos 3s;
  (2) sem WebGL → cloud, coberto por teste; (3) `seq` sem repetição/retrocesso e Δ`ts` de
  66–100ms, coberto por teste com fonte de 30fps; (4) `?mode=cloud` força cloud, coberto por
  teste. **(1) e (2) em hardware real ainda dependem de webcam** — ver pendência abaixo.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` **65/65**,
  `npm run build` OK.
- **Não verificado nesta sessão**: probe e frame clock rodando com câmera real. O headless
  do Firefox não tem webcam e não montei automação de clique — tentei o dispositivo falso,
  mas exigiria adicionar um flag de autostart ao app só para o meu teste, e preferi não
  poluir o código. Validação fica com o Daniel: `?mode=edge` e `?mode=cloud`, conferindo o
  chip de dev (modo, probe fps, seq crescente, fps efetivo ~15).

---

## 2026-07-27 · [B] T-043 — Casca visual mobile (layout de referência)

- Task **criada nesta sessão** a pedido do Daniel, fora da ordem da fila: ele passou uma
  imagem de referência do app em celular e quis o design pronto antes da T-004, para o
  projeto já ter aspecto seguível. Registrada como T-043 para não furar a convenção de
  "toda implementação nasce de uma task".
- Escopo deliberadamente **só visual**: `src/hud/` (StatsBar, ExerciseCard, TimerRing,
  CoachTip), `src/shell/TabBar`, `src/ui/icons` (SVG inline, sem pacote de ícones nem CDN)
  e reescrita do `styles.css` como layout mobile-first (`100dvh`, `max-width: 430px`).
- **Nenhuma lógica de HUD foi implementada.** Todo número vive em `src/hud/placeholders.ts`,
  um arquivo único que documenta de qual evento cada valor virá (`rep.detected`, timer da
  T-011, ângulo da T-006) e que some quando a T-012 chegar. Contador, timer e kcal são
  estáticos de propósito — a T-012 continua inteira na fila.
- Ajuste no esqueleto para bater com a referência: `BODY_CONNECTIONS`/`BODY_JOINTS`
  (tronco e membros, sem rosto/mãos/pés) viraram o **padrão de desenho**, com linhas brancas
  e halo azul nas articulações. É escolha visual, **não** mudança de contrato: `POSE_CONNECTIONS`
  e os 33 landmarks continuam intactos, e `drawSkeleton` aceita outro conjunto por parâmetro.
- Câmera continua funcional: o botão "Ligar câmera" virou uma capa sobre o stage (some quando
  a câmera abre) e as infos de dev (delegate, nº de landmarks, resolução) viraram um chip
  discreto no canto — o HUD real não tem nenhum dos dois.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` 19/19,
  `npm run build` OK. Layout conferido em screenshot headless (Firefox, 430×932) contra a
  imagem de referência.
- Pendências geradas (2 em "Descobertas"): **"Série" e "Kcal" não existem em nenhuma spec**
  (a de série contradiz a sessão de 30s da SPEC-009; kcal exigiria peso do usuário + MET);
  telas de Exercícios/Progresso/Perfil aparecem no tab bar sem spec nem rota.

---

## 2026-07-27 · [B] T-003 — Webcam + MediaPipe + esqueleto

- Sessão do **Agente B** (território `web/`), rodando no worktree `../df-agent-b`
  (branch `agent-b`) para não competir com o Agente A no BACKLOG/DEVLOG.
- Criado o app Vite + React 19 + TypeScript do zero em `web/`: `src/capture/`
  (câmera + overlay), `src/pose/` (MediaPipe + geometria do esqueleto), `src/store/`
  (zustand), testes com vitest, lint com ESLint flat config.
- Entregue: `getUserMedia` 640×480 @30fps com fallback, estados de câmera na UI
  (desligada / pedindo permissão / pronta / negada / erro), MediaPipe Pose Landmarker
  (modelo `lite`, WASM) desenhando os 33 landmarks e 35 conexões sobre o vídeo.
- Decisões:
  - **Assets do MediaPipe servidos localmente**, não por CDN: `npm run setup`
    (`scripts/setup-mediapipe.mjs`) copia o WASM do `node_modules` e baixa o `.task`
    para `public/`. Roda automático no `predev`/`prebuild`. Motivo: o app precisa
    funcionar dentro do compose sem depender de CDN externo em runtime.
  - **Delegate GPU com fallback para CPU** em caso de exceção — a mesma config será
    usada pelo capability probe da T-004 (senão o probe mente, nota da SPEC-001).
  - **Espelhamento por CSS no container** de vídeo+canvas juntos, então o desenho usa
    as coordenadas normalizadas cruas do MediaPipe (sem matemática de espelho).
  - **Geometria do esqueleto como função pura** (`src/pose/skeleton.ts`:
    `isVisible`/`toCanvasPoint`/`visibleSegments`/`visiblePoints`), testável sem câmera;
    só `drawSkeleton` toca o canvas. Limiar de visibilidade 0.5 (convenções).
  - **Loop de render é `requestAnimationFrame` cru de propósito**: o frame clock real
    (`requestVideoFrameCallback`, decimação por tempo para 15fps, `ts`/`seq`) é a T-004
    e substitui esse loop — não antecipei.
- Fora de escopo, não implementado: capability probe e `?mode=` (T-004), WebSocket e
  espelho TS do contrato (o `events.py` do Agente A ainda não existe), HUD (T-012).
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` 13/13
  verde, `npm run build` OK. Dev server verificado servindo `/`, `/wasm/*.wasm` (11 MB)
  e `/models/pose_landmarker_lite.task` (5,5 MB) com 200.
- **Validação visual com webcam real ainda pendente** — feita pelo Daniel (`npm run dev`
  em `web/`, precisa de `localhost` ou HTTPS para o `getUserMedia` liberar).
- Pendências geradas (2 em "Descobertas"): serviço `web` no compose ficou **sem dono**
  (o Agente A atribuiu ao B, mas o arquivo é território do A); assets do MediaPipe não
  versionados exigem `npm run setup` em clone novo.

---

## 2026-07-27 · [A] T-001 — Monorepo + docker-compose

- Trabalho em paralelo: **Agente A** (núcleo Python: server/, workers/, eval/, tests/, infra)
  e **Agente B** (web/). Interface única entre os dois: o contrato de eventos
  (`workers/shared/events.py`). Entradas do Agente A no DEVLOG usam prefixo `[A]`.
- Repositório git inicializado (não existia). Primeiro commit = docs de bootstrap já
  existentes; segundo = T-001.
- Criado: `pyproject.toml` (ruff + pytest + deps), `uv.lock`, `.gitignore`, `.dockerignore`,
  `.env.example`, `README.md`, `docker/server.Dockerfile`, `docker-compose.yml`,
  `.github/workflows/ci.yml`, esqueleto Django (`server/core` + `server/api` com
  `/healthz` e `/readyz`), `workers/shared/` (vazio, aguardando T-002), `tests/test_smoke.py`,
  `web/README.md` (contrato + território do Agente B).
- Decisões:
  - **Um só ambiente Python** para api, gateway e workers (mesma imagem, muda o `command`);
    deps do Django ficam no extra `server`, e o teste de fumaça garante que
    `workers.shared` importa sem Django carregado.
  - **`uv` como gerenciador** (lock versionado, Python 3.12 gerenciado); a imagem usa
    `uv sync --frozen`.
  - **Compose sem `.env` obrigatório**: defaults inline (`${VAR:-default}`) para "1 comando".
  - Healthcheck de liveness (`/healthz`, não toca dependências) separado de readiness
    (`/readyz`, checa Postgres + Redis) — o compose usa o de liveness.
  - `core/asgi.py` já isolado para o Channels entrar por cima na T-005 sem mexer no HTTP.
  - Redis em dev sem persistência, `maxmemory 256mb` + `noeviction` (streams são efêmeros;
    o `MAXLEN ~5000` da SPEC-002 é responsabilidade do produtor, não do servidor).
  - `INSTALLED_APPS` mínimo e `migrate --noinput` no start do `api`, para "1 comando" não
    deixar warning de migration pendente.
  - CI minimalista de propósito (só ruff + pytest): build de imagens e lint do web são T-027,
    eval em CI é T-042.
- Gates: `ruff check` + `ruff format --check` limpos; `pytest` 4/4 verde;
  `docker compose up` sobe os 3 serviços `healthy`, `/healthz` e `/readyz` respondendo 200.
- Pendências geradas (3 itens em "Descobertas" do BACKLOG): serviço `web` no compose fica
  para o Agente B (T-003); `contrib.auth` só na T-022; usar sempre `uv run` localmente.

---

## 2026-07-27 · Bootstrap do projeto

- Definida arquitetura (ARCHITECTURE.md): keypoint-first, event-driven, dois modos de extração (edge default / cloud controlado), sessões de 30s como unidade de carga.
- Criada estrutura spec-driven: `context/` (memória), `specs/` (11 entidades, cada uma com Fase Inicial + Fase Evolução), `AGENTS.md`, `BACKLOG.md`, `prompts/`.
- Decisões: nome do produto = Digital Fit (nome da pasta); Redis Streams como broker (ADR-001); FSM baseada em regras antes de ML (ADR-004).
- Pendências: revisão das specs uma a uma pelo Daniel (todas em `draft`).
- Adição posterior na mesma data: SPEC-012 (Fontes de Entrada & Bancada de Avaliação) — harness `evalctl` para testar o pipeline com corpus de vídeos rotulados (luz/distância/ângulo variados) em vez de só câmera ao vivo; tasks T-037 a T-042 no backlog.
