# BACKLOG — Digital Fit

> Tasks nascem das specs. Status: `todo` | `doing` | `done` | `blocked`.
> Regra: task de Fase Inicial nunca inclui itens de Fase Evolução da spec.

## Fase 0 — Prova local (edge only, sem auth)

| ID | Task | Spec | Status |
|---|---|---|---|
| T-001 | Monorepo + docker-compose (redis, postgres, django vazio, web vite) sobe com 1 comando | — | done |
| T-002 | `workers/shared/events.py`: envelope + eventos da fase 0 + testes de serialização | 002 | done |
| T-003 | Webcam + MediaPipe no browser desenhando esqueleto (validação visual) | 001/005 | todo |
| T-004 | Capability probe + frame clock (ts/seq) + modo forçável por query param | 001 | todo |
| T-005 | Gateway Channels: WS autenticado por token, publica `pose.frame` no stream | 002 | done |
| T-006 | Normalização + One Euro Filter como função pura + fixtures de teste | 006 | done |
| T-007 | Gravador de fixtures: salvar sequência de keypoints do browser em JSON p/ testes | 006/007 | todo |
| T-008 | Interface `ExerciseAnalyzer` + FSM do polichinelo + testes (20 limpos, preguiçosos, jitter) | 007 | done |
| T-009 | analysis-worker: consumer de `pose.frames`, roda FSM, publica `events.analysis` | 007 | done |
| T-010 | Feedback engine (catálogo YAML, throttle, prioridade) + faixa de feedback no HUD | 008 | todo |
| T-011 | Ciclo de sessão mínimo: `POST /sessions`, token HMAC, TTL 45s, timer autoritativo | 009 | done |
| T-012 | Tela de Sessão conforme referência (SPEC-013): barra de métricas, esqueleto sobre câmera, card exercício + anel 30s, card do treinador, warnings — mobile-first | 013/008/003 | todo |
| T-043 | App shell mobile-first: design tokens (SPEC-013), bottom nav (placeholders) + FAB de iniciar sessão | 013 | todo |
| T-044 | Ângulo articular ao vivo no HUD (client-side edge, fórmula espelhada da FSM, ≤10Hz, teste de paridade <5°) | 013 | todo |
| T-013 | Validação de cena mínima: OUT_OF_FRAME + TOO_FAR/TOO_CLOSE com debounce | 003 | done |
| T-014 | E2E local: 30s de polichinelo real → contagem correta na tela (demo gravável) | todas | todo |
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
| T-023 | compose.prod + Caddy TLS + deploy na VPS Debian + healthchecks | — | todo |
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

