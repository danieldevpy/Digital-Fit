# DEVLOG — Digital Fit

> Registro de sessões de trabalho. Entradas mais recentes no topo.
> Formato: data · task(s) · o que foi feito · decisões · pendências geradas.

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
