# BACKLOG — Digital Fit

> Tasks nascem das specs. Status: `todo` | `doing` | `done` | `blocked`.
> Regra: task de Fase Inicial nunca inclui itens de Fase Evolução da spec.

## Fase 0 — Prova local (edge only, sem auth)

| ID | Task | Spec | Status |
|---|---|---|---|
| T-001 | Monorepo + docker-compose (redis, postgres, django vazio, web vite) sobe com 1 comando | — | done |
| T-002 | `workers/shared/events.py`: envelope + eventos da fase 0 + testes de serialização | 002 | todo |
| T-003 | Webcam + MediaPipe no browser desenhando esqueleto (validação visual) | 001/005 | done |
| T-004 | Capability probe + frame clock (ts/seq) + modo forçável por query param | 001 | todo |
| T-005 | Gateway Channels: WS autenticado por token, publica `pose.frame` no stream | 002 | todo |
| T-006 | Normalização + One Euro Filter como função pura + fixtures de teste | 006 | todo |
| T-007 | Gravador de fixtures: salvar sequência de keypoints do browser em JSON p/ testes | 006/007 | todo |
| T-008 | Interface `ExerciseAnalyzer` + FSM do polichinelo + testes (20 limpos, preguiçosos, jitter) | 007 | todo |
| T-009 | analysis-worker: consumer de `pose.frames`, roda FSM, publica `events.analysis` | 007 | todo |
| T-010 | Feedback engine (catálogo YAML, throttle, prioridade) + faixa de feedback no HUD | 008 | todo |
| T-011 | Ciclo de sessão mínimo: `POST /sessions`, token HMAC, TTL 45s, timer autoritativo | 009 | todo |
| T-012 | HUD completo: contador, timer 30s, fase aberto/fechado, warnings de enquadramento | 008/003 | todo |
| T-013 | Validação de cena mínima: OUT_OF_FRAME + TOO_FAR/TOO_CLOSE com debounce | 003 | todo |
| T-014 | E2E local: 30s de polichinelo real → contagem correta na tela (demo gravável) | todas | todo |
| T-037 | CLI `evalctl run`: vídeo mp4 → MediaPipe → normalização → FSM → resultado JSON (reusa módulos dos workers) | 012 | todo |
| T-038 | Corpus inicial: 12–15 vídeos rotulados (manifest.yaml) + guia de gravação | 012 | todo |
| T-039 | Métricas agregadas + `evalctl compare` (regressão entre versões) + `--save-keypoints` | 012 | todo |

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
- **[B/T-003] Serviço `web` no compose: conflito de território, NÃO feito.** A descoberta
  `[A/T-001]` acima atribui isso ao Agente B, mas `docker-compose.yml` é território do
  Agente A (`prompts/agente-b-web.md`: "PROIBIDO tocar em … docker-compose"). O Vite já
  existe e o serviço pode entrar: build a partir de `web/`, `npm run dev -- --host`, porta
  5173, `VITE_API_URL`/`VITE_WS_URL` apontando para `api`. **Atenção**: `npm run dev`
  dispara `predev` → `scripts/setup-mediapipe.mjs`, que baixa ~5.5 MB do modelo — no
  container isso exige rede na primeira subida ou um volume para `web/public/models/`.
  Decisão de quem faz fica para o Daniel / sessão conjunta.
- **[B/T-003] Assets do MediaPipe não versionados**: `web/public/wasm/` (~11 MB) e
  `web/public/models/pose_landmarker_lite.task` (~5,5 MB) são gerados por `npm run setup`
  e ignorados via `web/.gitignore`. Clone novo precisa de `npm install && npm run setup`
  (ou só `npm run dev`, que roda o setup sozinho) antes de abrir o app.
