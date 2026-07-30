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

## Subir em produção (VPS + domínio)

```bash
cp .env.prod.example .env.prod   # decidir o DOMAIN
./scripts/prod.sh secrets
./scripts/prod.sh up
./scripts/prod.sh nginx          # server block de referência para o seu nginx
```

Arquivo separado (`docker-compose.prod.yml`), projeto docker separado, sem bind mount e com
`gunicorn` no lugar do `runserver`. TLS e domínio ficam com o seu nginx — passo a passo e
limites conhecidos em [docs/DEPLOY.md](docs/DEPLOY.md).

Existe por um motivo concreto: `getUserMedia` exige contexto seguro, então **a câmera não
abre pelo IP da rede local** — testar no celular pede HTTPS de verdade.

## Contas e trial

Treinar não exige conta: quem chega tem **3 sessões por dia** por aparelho (SPEC-011). A
quarta responde `429` com `code: trial_exhausted`, e a tela convida a criar conta — de graça,
e-mail e senha, sem confirmação. A conta serve para guardar o histórico:

```
POST /api/auth/register    # 201 + {user, access, refresh}
POST /api/auth/login
POST /api/auth/refresh     # troca o refresh (14 dias) por um access novo (15 min)
GET  /api/me
GET  /api/sessions?mine    # histórico do usuário
```

O treino em si **não** usa JWT: o WebSocket autentica pelo token HMAC de 45 s do ticket
(SPEC-009), então renovar o access nunca derruba uma sessão em andamento. Em produção,
`JWT_SIGNING_KEY` é gerado pelo `./scripts/prod.sh secrets` — trocá-lo desloga todo mundo.

## Ferramentas de diagnóstico

A UI de produto não tem nada de dev. O chip de diagnóstico, o gravador de fixtures e a fonte
de vídeo da bancada aparecem só para quem tem direito, decidido em `web/src/dev/gate.ts`:

- **local** (`npm run dev`): sempre ligadas, sem login;
- **produção**: para contas com `is_admin`, que é como se inspeciona o servidor que está no ar.

Para criar uma conta já com as ferramentas ligadas:

```bash
docker compose exec api python manage.py createsuperuser    # dev
./scripts/prod.sh exec api python manage.py createsuperuser # producao
```

Apesar do nome, ela **não** é superusuário do Django: não há painel, grupos nem permissões, e
as rotas continuam filtrando por dono da sessão — ela não lê o histórico de mais ninguém. O que
ganha é a superfície de dev do cliente.

Para ligar/desligar numa conta que já existe (nenhuma rota da API aceita o campo):

```bash
./scripts/prod.sh exec api python manage.py admin_tools voce@exemplo.com --on
./scripts/prod.sh exec api python manage.py admin_tools --list      # quem tem hoje
./scripts/prod.sh exec api python manage.py admin_tools voce@exemplo.com --off
```

Ela vale no próximo carregamento da página (o cliente lê no `GET /api/me`) e revogar tem
efeito imediato — não está no JWT. Não dá acesso a dado de ninguém: histórico e relatório
continuam filtrados por dono da sessão. `?dev=0` na URL desliga as ferramentas sem deslogar,
para conferir a tela como o usuário comum a vê; `?dev=1` não promove ninguém.

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

### A perna do navegador (T-040)

O `edge` das duas colunas acima é o MediaPipe **do Python** — não é o que roda no celular do
usuário. Para medir o MediaPipe **do navegador** contra o mesmo vídeo:

1. abra o app com as ferramentas de dev ligadas e clique em **vídeo** no chip de diagnóstico;
2. escolha um arquivo do corpus — ele toca pelo caminho edge real e abre uma sessão de verdade;
3. no fim, clique em **baixar json**;
4. ponha o número ao lado dos outros dois:

```bash
uv run python -m eval.evalctl parity eval/corpus/polichinelo-01.mp4 \
  --expected-reps 20 --browser polichinelo-01.browser.json
# OK  …: edge=20 cloud=20 browser=20 (delta +0, browser +0, tolerancia 1)
```

O vídeo carrega **pausado**: o capability probe roda antes e consumiria os primeiros 2 s do
arquivo — que são o trecho parado da calibração. Vídeos acima de 30 s são cortados pelo timer
autoritativo da sessão, então mantenha o corpus abaixo disso.

## Estrutura

```
docker-compose.yml     # dev local: um comando
docker-compose.prod.yml # produção: autônomo, não é override do de cima
scripts/prod.sh        # deploy: build + migrate + start + nginx de referência
docker/                # Dockerfiles (server, web)
docs/DEPLOY.md         # como sobe na VPS e o que ainda não tem
docs/DATASET.md        # schema do Parquet de keypoints (SPEC-010)
server/                # Django: core (settings), api (DRF), gateway (Channels, T-005)
  api/auth.py          #   contas JWT; api/trial.py = quota do visitante (SPEC-011)
  api/management/      #   report-builder roda como comando do Django (ADR-008: é o único
                       #   consumidor que escreve no Postgres)
workers/               # Python puro, sem Django
  shared/events.py     #   contrato de eventos — única fonte da verdade
  report_builder/      #   consolidação da sessão (pura); o processo vive em server/
  dataset_writer/      #   corpus de keypoints: um Parquet por sessão
dataset/               # o corpus gravado (fora do git; sai da máquina por rsync)
eval/                  # evalctl: bancada de avaliação (SPEC-012)
tests/                 # testes e fixtures de keypoints
web/                   # cliente React + Vite — DOIS bundles (ADR-010)
  index.html           #   SITE: landing e Sobre, servido em /
  app/index.html       #   APP: funil de treino, servido em /app/ (ou app.dominio.com)
```

## Como o trabalho acontece

Projeto spec-driven: comportamento nasce de uma spec em [`specs/`](specs/), implementação
nasce de uma task `T-XXX` no [`BACKLOG.md`](BACKLOG.md), sessões ficam registradas no
[`DEVLOG.md`](DEVLOG.md). Regras em [`AGENTS.md`](AGENTS.md), convenções em
[`context/conventions.md`](context/conventions.md).
