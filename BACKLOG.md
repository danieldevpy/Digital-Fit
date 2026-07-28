# BACKLOG — Digital Fit

> Tasks nascem das specs. Status: `todo` | `doing` | `done` | `blocked`.
> Regra: task de Fase Inicial nunca inclui itens de Fase Evolução da spec.

## Fase 0 — Prova local (edge only, sem auth)

| ID | Task | Spec | Status |
|---|---|---|---|
| T-001 | Monorepo + docker-compose (redis, postgres, django vazio, web vite) sobe com 1 comando | — | done |
| T-002 | `workers/shared/events.py`: envelope + eventos da fase 0 + testes de serialização | 002 | done |
| T-003 | Webcam + MediaPipe no browser desenhando esqueleto (validação visual) | 001/005 | done |
| T-004 | Capability probe + frame clock (ts/seq) + modo forçável por query param | 001 | done |
| T-005 | Gateway Channels: WS autenticado por token, publica `pose.frame` no stream | 002 | done |
| T-006 | Normalização + One Euro Filter como função pura + fixtures de teste | 006 | done |
| T-007 | Gravador de fixtures: salvar sequência de keypoints do browser em JSON p/ testes | 006/007 | done |
| T-008 | Interface `ExerciseAnalyzer` + FSM do polichinelo + testes (20 limpos, preguiçosos, jitter) | 007 | done |
| T-009 | analysis-worker: consumer de `pose.frames`, roda FSM, publica `events.analysis` | 007 | done |
| T-010 | Feedback engine — núcleo (catálogo YAML, throttle, prioridade); a superfície visual é o card do treinador da T-012 | 008 | done |
| T-011 | Ciclo de sessão mínimo: `POST /sessions`, token HMAC, TTL 45s, timer autoritativo | 009 | done |
| T-012 | Tela de Sessão conforme referência (SPEC-013): barra de métricas, esqueleto sobre câmera, card exercício + anel 30s, card do treinador, warnings — mobile-first | 013/008/003 | done |
| T-043 | App shell mobile-first: design tokens (SPEC-013), bottom nav (placeholders) + FAB de iniciar sessão | 013 | done |
| T-044 | Ângulo articular ao vivo no HUD (client-side edge, fórmula espelhada da FSM, ≤10Hz, teste de paridade <5°) | 013 | done |
| T-013 | Validação de cena mínima: OUT_OF_FRAME + TOO_FAR/TOO_CLOSE com debounce | 003 | done |
| T-014 | E2E local: 30s de polichinelo real → contagem correta na tela (demo gravável) | todas | doing — máquina verificada (`npm run e2e`), falta a passada com câmera + pessoa |
| T-037 | CLI `evalctl run`: vídeo mp4 → MediaPipe → normalização → FSM → resultado JSON (reusa módulos dos workers) | 012 | done |
| T-038 | Corpus inicial: 12–15 vídeos rotulados (manifest.yaml) + guia de gravação | 012 | todo |
| T-039 | Métricas agregadas + `evalctl compare` (regressão entre versões) + `--save-keypoints` | 012 | done |

## Fase 1 — Modo cloud + persistência

| ID | Task | Spec | Status |
|---|---|---|---|
| T-015 | Envio de `frame.raw` JPEG 320px @10fps quando modo cloud | 001/005 | todo |
| T-016 | pose-worker: consumer `frames.raw` → MediaPipe CPU → `pose.frame` (cgroup 1 vCPU) | 005 | todo |
| T-017 | Semáforo `slots:cloud=3` (Lua atômico) + liberação em todos os finais | 009 | todo |
| T-018 | Teste de paridade edge×cloud: mesmo vídeo, reps idênticas (±1/20) | 005 | todo |
| T-019 | Baseline/calibração no countdown (mediana 1s) + FSM usando baseline | 004 | todo |
| T-020 | report-builder: consolidação + `SessionResult` no Postgres + tela de relatório | 010 | todo |
| T-021 | dataset-writer: Parquet por sessão + schema documentado | 010 | todo |
| T-022 | Auth JWT + trial anônimo (3/dia por device) + histórico do usuário | 011 | todo |
| T-040 | Fonte de vídeo na UI web (upload → `<video>` → caminho edge) + paridade edge×cloud×harness | 012 | todo |
| T-041 | `evalctl replay --ws`: injetar keypoints gravados via gateway (integração + carga sintética) | 012 | todo |

## Fase 2 — SaaS na VPS

| ID | Task | Spec | Status |
|---|---|---|---|
| T-023 | compose.prod + deploy na VPS Debian + healthchecks (TLS/nginx são manuais, por decisão) | — | done |
| T-024 | Fila de espera cloud com posição visível + limite edge | 009 | todo |
| T-025 | Quotas por plano em Redis + enforcement no POST /sessions | 009/011 | todo |
| T-026 | Logs estruturados JSON + página de status + backup diário do Postgres | — | todo |
| T-027 | CI: ruff+pytest+lint web+build de imagens no push | — | todo |
| T-028 | Teste de carga: 30 sessões edge + 3 cloud simultâneas na VPS via `evalctl replay` (validar orçamento) | 009/012 | todo |
| T-042 | Eval em CI: subset rápido em todo push, corpus completo manual; PR que degrada acurácia falha | 012 | todo |

## Fase 3 — Evoluções (uma task por "Fase Evolução" priorizada)

| ID | Task | Spec | Status |
|---|---|---|---|
| T-029 | Validação de cena completa: luz, tilt de câmera, gate de início, scene score | 003 | todo |
| T-030 | Gate de prontidão por pose + silhueta-alvo no HUD | 004 | todo |
| T-031 | Reconexão com resume (WS) + retomada de sessão via snapshot | 002/009 | todo |
| T-032 | Exercício 2: agachamento (novo módulo `exercises/squat.py`) | 007 | todo |
| T-033 | Form score por rep (amplitude, simetria, estabilidade) | 007 | todo |
| T-034 | Ferramenta de rotulagem do dataset + primeiro treino do classificador temporal | 010/007 | todo |
| T-035 | Coach por voz (TTS dos feedbacks) | 008 | todo |
| T-036 | Planos pagos + Stripe/Mercado Pago + LGPD (export/exclusão) | 011 | todo |
| T-045 | Meta de reps (`target_reps`, fim por `target_reached`) + séries/circuitos com descanso | 013/009 | todo |
| T-046 | KCAL estimada (MET × peso do perfil) + acumulado do dia + telas Exercícios/Progresso/Perfil | 013/010/011 | todo |

## Descobertas (entram aqui, nunca no escopo da task atual)

- **[A/T-001] Serviço `web` fora do compose**: a T-001 entregou apenas `redis`, `postgres` e
  `api`; `web/` ficou como pasta com README (território do Agente B). Quem criar o Vite
  (T-003) adiciona o serviço `web` ao `docker-compose.yml` — só então "1 comando" cobre o
  cliente também.
- **[A/T-001] Django da Fase 0 sem `contrib.auth`/`sessions`/`admin`**: `INSTALLED_APPS`
  mínimo (contenttypes, staticfiles, rest_framework, api), coerente com "sem auth" da Fase 0.
  A T-022 (auth JWT) terá de adicionar esses apps + migrations.
- **[A/T-001] Toolchain Python**: a máquina tem Python 3.11 no sistema; o projeto exige 3.12+
  (convenções). Resolvido usando o Python gerenciado pelo `uv` (`uv sync` / `uv run`).
  Rodar `pytest` do sistema direto não funciona — sempre via `uv run`.
- **[A/T-037] MediaPipe 1.0 removeu a API `mp.solutions`**: o extractor usa a **Tasks API**
  (`vision.PoseLandmarker`), que é a mesma que a SPEC-005 manda usar no cliente web — bom para
  paridade edge×bancada, mas exige um arquivo de modelo `.task` (5,5 MB, fora do git). Baixar
  uma vez com `python -m eval.evalctl fetch-model`. Quando o `pose-worker` da T-016 nascer, tem
  de usar o MESMO modelo e o MESMO caminho de resolução (`DIGITALFIT_POSE_MODEL`).
- **[A/T-037] `uv sync` sem extras remove o Django**: o fluxo local é
  `uv sync --extra server` (e `--extra eval` para a bancada). README e CI atualizados; a CI
  não instala o extra `eval` de propósito (MediaPipe pesa ~200 MB).
- **[A/T-005] Porta 8000 do host ocupada**: durante o desenvolvimento havia um processo Python
  do usuário escutando em `0.0.0.0:8000`, o que impede o serviço `api` de subir
  (`address already in use`). O gateway (8001), o worker, o redis e o postgres subiram normais.
  Se acontecer, `API_PORT=8002 docker compose up` resolve sem tocar no processo alheio.
- **[A/T-005] Sem snapshot de estado, worker reiniciado recomeça a numeração**: matar e religar
  o analysis-worker **não** derrota o WS (critério 2 da SPEC-002 verificado), e as repetições
  seguintes continuam chegando — mas o `rep_count` reinicia, porque o estado da FSM é só de
  memória. É o comportamento previsto para a Fase 0; a retomada por snapshot é a T-031.
- **[A/T-011] `redis-py` fixado em 5.x**: com `redis-py` 8, o `channels_redis` 4.3 estoura
  `redis.exceptions.TimeoutError` na leitura bloqueante do channel layer e **mata o consumer do
  WebSocket** — o cliente parava de receber eventos depois de ~10 s de silêncio. Só apareceu em
  teste real (os testes usam camada em memória). Fixado `redis>=5.2,<6` no `pyproject.toml`;
  revisitar quando o `channels_redis` declarar suporte a 6+.
- **[A/T-011] `session.completed` com motivo `timeout` não é emitido na Fase 0**: o worker sempre
  fecha antes, por duração (30 s) ou por falta de dados (10 s). O motivo continua no vocabulário
  para o caminho do TTL em Redis, que só passa a valer com semáforo/quotas (T-017/T-025).

- **[B/T-003] ~~Serviço `web` no compose~~ — RESOLVIDO na sessão da junção.** Ficou sem dono
  porque cada agente achava que o arquivo era do outro; com as duas linhas juntas, entrou:
  `node:22-alpine`, `npm install && npm run dev`, porta 5173, `VITE_API_URL` apontando para o
  host (o WS abre no **navegador**, então as URLs são as do host, não os nomes de serviço do
  compose). O download de 5,5 MB do modelo deixou de ser risco: `setup-mediapipe.mjs` procura
  em `DIGITALFIT_POSE_MODEL`, `../eval/models/` e `/models/` (bind mount) antes da rede.
- **[A/T-001] `docker compose up` conflita com o `npm run dev` local na 5173**: quem já roda o
  Vite na mão vê o serviço `web` falhar com `address already in use`, e o resto da stack sobe
  normalmente — o erro parece grave e não é. Enquanto não há um perfil separado, o caminho é
  `docker compose up -d` para a infra e o Vite na mão, **ou** só o compose. Vale um
  `profiles: [web]` no serviço quando alguém encostar no arquivo.
- **[A/T-023] Caddy trocado por nginx manual**: a task previa Caddy pelo TLS automático, mas a
  VPS já tem nginx configurado à mão. O compose de produção passou a expor três portas em
  `127.0.0.1` (web 8080, api 8000, gateway 8001) e o proxy fica fora do projeto —
  `./scripts/prod.sh nginx` imprime o server block de referência. Um domínio só para os três,
  o que zera CORS (same-origin) e mantém `wss://` no mesmo host do `https://`.
- **[A/T-023] `VITE_API_URL` é build time, não runtime**: variável `VITE_*` é gravada no
  bundle pelo Vite, então trocar de domínio exige **rebuild** da imagem do web — não adianta
  mudar o environment do compose. Por isso o `prod.sh up` sempre reconstrói. Se um dia isso
  incomodar, a saída é o cliente ler a origem da própria página (same-origin) em vez de uma
  variável — hoje `apiBaseUrl()` cairia no default de `localhost:8000`.
- **[A/T-023] Conflito de porta na VPS estourava tarde demais**: o `docker compose up` só
  tenta ligar as portas no último passo, então uma `8000` já ocupada (comum numa VPS com
  outros apps) falhava **depois** do build e das migrations, deixando a stack pela metade.
  O `prod.sh up` passou a checar `WEB_PORT`/`API_PORT`/`GATEWAY_PORT` com `ss` antes de
  qualquer coisa, pulando serviço que já está rodando — senão atualizar a stack acusaria
  conflito com ela mesma.
- **[A/T-023] Produção não tem backup, quota nem auth**: o volume `postgres-data` é tudo
  (T-026), qualquer um que alcance a URL abre sessão (T-022/T-025), e reiniciar o
  `analysis-worker` derruba as sessões em voo (T-031). Aceitável para um domínio privado de
  teste; não para público. Listado em `docs/DEPLOY.md` para não virar surpresa.
- **[A/T-014] Stack parcialmente morta engana o diagnóstico**: com `redis`/`api` fora e o
  `gateway` de pé, o cliente mostra "API fora do ar" (correto) enquanto o `analysis-worker`
  entra em crash loop de DNS (`Temporary failure in name resolution`) — dois sintomas
  distantes da mesma causa. O worker não espera o redis voltar: morre e depende do restart
  do Docker, e o backoff dele pode disparar antes do redis ficar `healthy`, exigindo um
  `docker compose restart analysis-worker` a mais. Reconexão com espera é candidata a tarefa.
- **[B/T-012] `scene.warning` não tem campo `message`.** O contrato manda só `code`,
  `severity` e `hint?`, e a SPEC-013 exige que o card do treinador exiba o aviso de cena com
  prioridade máxima. Como não há texto para mostrar, o cliente ficou com um mapa
  código → pt-BR em `src/session/coachCard.ts` — que **duplica** o catálogo YAML do feedback
  engine (T-010). Decidir: ou o gateway/worker enriquece `scene.warning` com `message` (como
  já faz em `feedback.issued`), ou o mapa do cliente é oficialmente a fonte para cena.
- **[B/T-012] Não existe evento de "aviso resolvido".** Nada no contrato diz que um
  `scene.warning` ou `feedback.issued` deixou de valer, então o card ficaria preso no último
  aviso até o fim da sessão. Contornei com TTL de 6s no cliente (`COACH_ENTRY_TTL_MS`),
  puramente cosmético. Se a intenção da SPEC-008 é que o worker reemita enquanto o problema
  persistir, o TTL está certo; se não, falta um evento de limpeza no contrato.
- **[B/T-043] Anel de countdown: spec e imagem discordam.** A SPEC-013 diz duas vezes que o
  gradiente é roxo (`§3` "gradiente roxo" e `§Design tokens` "gradiente: accent → accent-2"),
  mas na imagem de referência o anel vai de **ciano** a roxo. Segui a spec (roxo → roxo
  claro), conforme o AGENTS.md ("conflito entre spec e código → a spec vence"). Se a intenção
  era o ciano da imagem, é 1 linha em `TimerRing.tsx` + um token novo — e a spec pede que
  divergências intencionais virem seção "Desvios da referência".
- **[B/T-004] Escopo do `seq` — resolvido lendo o contrato ao pé da letra, mas confirme.**
  O contrato diz "contador monotônico **por sessão** (nunca repete nem retrocede)", sem
  ressalva por tipo. Então `session.capability` e `pose.frame` **não** podem ter cada um o
  seu contador começando em 0. Implementei `src/lib/clientSequencer.ts`: um único contador
  por sessão que todos os eventos do cliente consomem. O frame clock continua dono do `ts` e
  da decimação, mas o `seq` do envelope sai do sequenciador. **Consequência para o Agente A**:
  o `seq` dos `pose.frame` que chegam ao gateway **não é contíguo** — a capability consome o
  0, e qualquer evento futuro do cliente consumirá outros. Se algum consumidor assumir
  contiguidade em `pose.frames`, quebra. Se a intenção era `seq` por tipo, é trocar uma
  linha aqui e o contrato precisa dizer isso explicitamente.
- **[B/T-007] ~~Formato da fixture divergiu~~ — RESOLVIDO na mesma sessão.** A primeira
  versão do gravador escrevia uma lista de envelopes `pose.frame`. Depois encontrei
  `workers/shared/keypoints.py`, onde o Agente A já tinha definido o `schema: 1` e escrito
  que é "o mesmo formato que o gravador do cliente (T-007) escreve". Os dois eram
  incompatíveis. **O gravador foi reescrito para o schema do Agente A** — ele é o dono desse
  formato, não eu. Verificado: `load_fixture()` lê o que o gravador produz sem conversão.
  Lição para as próximas: varrer `workers/shared/` inteiro antes de definir qualquer formato
  de interoperação, não só `events.py`.
- **[B/T-044] One Euro Filter duplicado no cliente.** Para o ângulo ao vivo ficar dentro dos
  5° do worker (critério 4 da SPEC-013), não bastou espelhar a fórmula: o worker calcula sobre
  coordenadas **suavizadas**, e só o lag do filtro dava até 22° de diferença no meio do
  polichinelo. Foi preciso espelhar também `filters.py` e a ordem de `Normalizer.push` em
  `web/src/pose/oneEuro.ts` + `armAngleTracker.ts`, incluindo os valores de `NormParams`
  (`mincutoff 0.4`, `beta 1.5`, `dcutoff 1.0`, escala `0.4/0.0`). **Isso é duplicação
  cross-território e vai driftar**: se o Agente A mexer em `NormParams` ou na ordem do
  pipeline, o teste de paridade quebra sem que ninguém tenha tocado no `web/`. Opções para o
  Daniel decidir: (a) aceitar e tratar a quebra do teste como o alarme; (b) o worker passa a
  mandar o ângulo num evento (a SPEC-013 já prevê `metrics.update` para o modo cloud);
  (c) afrouxar a tolerância para o ângulo cru caber.
- **[B/T-043] "Série" e "Kcal" não existem em nenhuma spec.** A referência de design pede
  quatro métricas no topo (série, repetições, ângulo, kcal), mas só *repetições* e *ângulo*
  saem do pipeline atual. **Série** pressupõe treino com múltiplas séries — a SPEC-009 define
  a sessão de 30s como unidade, sem agrupamento. **Kcal** exige estimativa de gasto calórico
  (peso do usuário + MET do exercício), que nenhuma spec cobre. Decidir: ou entram nas
  SPEC-009/010 antes da T-012, ou saem do HUD. Hoje são placeholder.
- **[B/T-043] Telas do tab bar não existem**: Exercícios, Progresso e Perfil aparecem na
  navegação mas não têm spec nem rota. Perfil/histórico só na T-022 (auth). O tab bar é
  decoração até lá.
- **[B/T-003] Assets do MediaPipe não versionados**: `web/public/wasm/` (~11 MB) e
  `web/public/models/pose_landmarker_lite.task` (~5,5 MB) são gerados por `npm run setup`
  e ignorados via `web/.gitignore`. Clone novo precisa de `npm install && npm run setup`
  (ou só `npm run dev`, que roda o setup sozinho) antes de abrir o app.
