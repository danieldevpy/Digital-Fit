# DEVLOG — Digital Fit

> Registro de sessões de trabalho. Entradas mais recentes no topo.
> Formato: data · task(s) · o que foi feito · decisões · pendências geradas.

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
