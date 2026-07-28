# Digital Fit

App web que analisa exercícios físicos por visão computacional em sessões de 30 segundos:
conta repetições, corrige a execução e classifica o exercício. MVP: polichinelo.

Princípio central: **keypoint-first, event-driven** — o dado do sistema são keypoints
(33 landmarks), nunca vídeo; tudo flui como eventos por Redis Streams.
Ver [ARCHITECTURE.md](ARCHITECTURE.md) e [context/project.md](context/project.md).

## Subir o ambiente local

```bash
docker compose up --build
```

Sobe `redis` (barramento), `postgres` (dados) e `api` (Django/DRF). Sem `.env`
necessário — os defaults de desenvolvimento estão no próprio compose
(`.env.example` mostra o que é sobrescrevível).

Verificar:

```bash
curl localhost:8000/healthz   # liveness  -> {"status":"ok","service":"api"}
curl localhost:8000/readyz    # postgres + redis respondendo
```

## Desenvolvimento Python (fora do Docker)

```bash
uv sync --extra server   # cria .venv com Python 3.12 (api + workers + testes)
uv run ruff check .
uv run pytest
```

## Bancada de avaliação (`evalctl`)

Mede a precisão do pipeline contra vídeos rotulados, sem sistema no ar (SPEC-012). As
dependências são pesadas (MediaPipe + OpenCV) e ficam num extra separado:

```bash
uv sync --extra server --extra eval
uv run python -m eval.evalctl run video.mp4 --exercise jumping_jack --expected-reps 20
uv run python -m eval.evalctl run eval/corpus/ --report eval/out/eval.json
```

Nada em `server/` ou `workers/` importa `eval/` — a bancada usa os módulos deles, nunca o
contrário.

## Estrutura

```
docker-compose.yml     # dev local: um comando
docker/                # Dockerfiles
server/                # Django: core (settings), api (DRF), gateway (Channels, T-005)
workers/               # Python puro, sem Django
  shared/events.py     #   contrato de eventos — única fonte da verdade
eval/                  # evalctl: bancada de avaliação (SPEC-012)
tests/                 # testes e fixtures de keypoints
web/                   # cliente React + Vite
```

## Como o trabalho acontece

Projeto spec-driven: comportamento nasce de uma spec em [`specs/`](specs/), implementação
nasce de uma task `T-XXX` no [`BACKLOG.md`](BACKLOG.md), sessões ficam registradas no
[`DEVLOG.md`](DEVLOG.md). Regras em [`AGENTS.md`](AGENTS.md), convenções em
[`context/conventions.md`](context/conventions.md).
