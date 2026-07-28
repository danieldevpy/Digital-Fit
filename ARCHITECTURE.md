# Arquitetura — Digital Fit (app de análise de exercícios)

> Documento vivo. Versão 0.2 — 2026-07-27
> Detalhamento por entidade (fase inicial + evolução): ver `specs/`. Tasks: `BACKLOG.md`.
> Stack alvo: React · Python · Django · Redis · Postgres · Docker
> Infra alvo: VPS Debian 4 vCPU / 6 GB RAM · Desenvolvimento local via docker-compose

---

## 1. Visão do produto

Aplicativo web que captura vídeo do usuário em **sessões de 30 segundos**, analisa a pose corporal em tempo real, **conta repetições, corrige a execução e classifica o exercício**. MVP: polichinelo (jumping jack). Evolução: SaaS multiusuário com histórico, planos e novos exercícios.

## 2. Princípio central: *keypoint-first, event-driven*

A decisão que destrava tudo: **vídeo nunca é o dado central do sistema — keypoints são.**

Não importa se a pose foi extraída no navegador (dispositivos potentes) ou no servidor (fallback): ambos os caminhos convergem para o **mesmo evento** `pose.frame` (33 landmarks + timestamp + session_id). Todo o resto do sistema — análise, feedback, relatórios, métricas, ML futuro — consome esse fluxo único de eventos e **não sabe nem se importa de onde a pose veio**.

Consequências:

- O pipeline pesado (visão computacional) fica isolado e opcional.
- Trocar MediaPipe por MoveNet/YOLO-pose amanhã não afeta nada downstream.
- Um "consumer" novo (gamificação, notificação, dataset p/ ML) é só mais um assinante do stream.
- Testes locais podem injetar keypoints gravados (fixtures) sem câmera nenhuma.

## 3. Diagrama geral

```
                         ┌────────────────────── NAVEGADOR (React) ──────────────────────┐
                         │  getUserMedia → <video>                                       │
                         │  Capability Probe (2s): mede fps do modelo local              │
                         │    ├─ MODO EDGE:  MediaPipe Pose (WASM/WebGPU) → keypoints    │
                         │    └─ MODO CLOUD: frames JPEG 320px @10fps                    │
                         │  HUD tempo real: contador, cadência, dicas (recebe eventos)   │
                         └──────────────┬───────────────────────────▲────────────────────┘
                                        │ WebSocket (binário)       │ WebSocket (feedback)
                                        ▼                           │
┌──────────────────────── GATEWAY (Django ASGI + Channels) ─────────┴──────────┐
│  Autentica sessão · valida quota · publica eventos · devolve feedback        │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ publica em
       ▼
┌─────────────────────────  REDIS STREAMS (barramento)  ───────────────────────┐
│  frames.raw ─────► [pose-worker]* ────► pose.frames                          │
│  pose.frames ────► [analysis-worker] ─► events.analysis (rep, feedback, fim) │
│  events.analysis ► [gateway → HUD]  e  [consumers…]                          │
│                        * só existe no modo cloud                             │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ consumer groups
       ▼
┌── CONSUMERS ────────────────────────────────┐   ┌── PERSISTÊNCIA ────────────┐
│ report-builder → relatório da sessão        │──►│ Postgres (usuários,        │
│ metrics → contadores/telemetria             │   │ sessões, resultados)       │
│ dataset-writer → keypoints p/ ML futuro     │   │ Arquivos .parquet (ML)     │
└─────────────────────────────────────────────┘   └────────────────────────────┘
```

## 4. Os dois modos de captura

### Modo EDGE (padrão — dispositivos capazes)

O navegador roda o **MediaPipe Pose Landmarker** (WASM + SIMD, ou WebGPU quando disponível) e envia apenas keypoints: ~1–2 KB/frame a 15 fps ≈ **20–30 KB/s por sessão**. O servidor só roteia eventos e roda a FSM de análise — custo de CPU quase nulo.

### Modo CLOUD (fallback)

O navegador envia frames JPEG reduzidos (320 px no maior lado, qualidade ~60, 10 fps ≈ 100–150 KB/s) via WebSocket binário. Um `pose-worker` em Python (MediaPipe) extrai os keypoints e publica o mesmo `pose.frame`.

### Capability Probe (decisão automática)

Ao abrir a sessão, o cliente roda o modelo local por ~2 s em frames reais:

- fps medido ≥ 12 → **EDGE**
- fps < 12, WebGL indisponível, ou erro → solicita slot **CLOUD** à API
- Usuário pode forçar o modo nas configurações (útil p/ debug)

## 5. Contrato de eventos (o coração do desacoplamento)

Envelope comum (MessagePack no transporte, JSON nos exemplos):

```json
{
  "v": 1,
  "type": "pose.frame",
  "session_id": "uuid",
  "ts": 1722100000123,
  "seq": 142,
  "source": "edge",
  "data": { }
}
```

| Evento | Produtor | Consumidores | data |
|---|---|---|---|
| `session.started` | API | analysis, consumers | user, exercise, mode, duração (30s) |
| `frame.raw` | cliente (cloud) | pose-worker | jpeg bytes |
| `pose.frame` | cliente (edge) ou pose-worker | analysis-worker | 33 landmarks `[x,y,z,visibility]` normalizados 0–1 |
| `rep.detected` | analysis-worker | gateway→HUD, report | rep_count, fase, duração da rep |
| `feedback.issued` | analysis-worker | gateway→HUD, report | code (`ARMS_TOO_LOW`…), severidade, mensagem |
| `session.completed` | analysis-worker/API | report-builder | motivo (timeout 30s, abort) |
| `session.report.ready` | report-builder | gateway→cliente, API | url/id do relatório |

**O feedback é parte do event loop** (sua escolha): `analysis-worker` emite `rep.detected` / `feedback.issued` no stream; o gateway está inscrito e empurra ao HUD pelo mesmo WebSocket. Latência alvo edge→feedback: **< 150 ms**. Qualquer consumer futuro (ex.: áudio de coach, gamificação) assina os mesmos eventos sem tocar no código existente.

**Por que Redis Streams e não Kafka/RabbitMQ:** consumer groups + ack + replay + persistência configurável, com ~100 MB de RAM. Kafka não cabe no orçamento da VPS; RabbitMQ não tem replay natural. Se um dia precisar, o contrato de eventos migra sem reescrever os workers. (ADR-001)

## 6. Serviços

| Serviço | Tech | Papel | Escala |
|---|---|---|---|
| `web` | React + Vite + MediaPipe Tasks | captura, probe, HUD, relatório | estático (CDN/Caddy) |
| `api` | Django + DRF | auth, contas, quotas, abrir/fechar sessão, histórico | 1 processo (gunicorn) |
| `gateway` | Django Channels (ASGI/uvicorn) | WebSocket ingest + push de feedback | 1–2 processos |
| `pose-worker` | Python + MediaPipe | frames.raw → pose.frames (só cloud) | 0–2 réplicas |
| `analysis-worker` | Python puro (numpy) | FSM, reps, feedback, fim de sessão | 1–2 réplicas |
| `report-builder` | Python | consolida sessão → Postgres + relatório | 1 réplica |
| infra | Redis, Postgres, Caddy | broker/estado, dados, TLS/proxy | 1 cada |

Notas de desacoplamento:

- `gateway` nasce **dentro** do projeto Django (Channels) para simplicidade na fase 0, mas conversa com o resto **somente via eventos** — extraí-lo para um serviço próprio (ou FastAPI) depois é mover pastas, não reescrever. (ADR-002)
- `analysis-worker` é Python puro sem Django: importável, testável com pytest injetando sequências de keypoints gravadas.
- Estado de sessão ativa (FSM, contadores) vive na memória do worker com snapshot em Redis hash — se o worker cair, outro retoma pelo snapshot + replay do stream.

## 7. Pipeline de análise — polichinelo como caso 1

### 7.1 Normalização (invariância a câmera/corpo)

1. Origem no ponto médio dos quadris.
2. Escala = distância ombro-médio → quadril-médio (torso). Tudo vira múltiplos de torso.
3. Suavização: **One Euro Filter** por landmark (mata jitter sem atrasar movimento rápido).
4. Descarte de frames com `visibility` média < 0.5 (usuário saiu do quadro → feedback `OUT_OF_FRAME`).

### 7.2 Features do polichinelo

- `arm_angle`: ângulo ombro→pulso vs. vertical (abdução), média dos dois braços
- `wrist_above_shoulder`: pulsos acima da linha dos ombros?
- `ankle_spread`: distância entre tornozelos ÷ largura dos ombros
- `cadence`: reps nos últimos 10 s

### 7.3 Máquina de estados (com histerese + debounce)

```
        arm_angle > 110° E ankle_spread > 1.4        arm_angle < 40° E ankle_spread < 0.9
FECHADO ────────────────────────────────► ABERTO ────────────────────────────────► FECHADO
                                                        = 1 repetição válida
```

- **Histerese**: limiares de entrada ≠ saída (ex.: abre em 1.4, só fecha abaixo de 0.9) — evita contagem dupla na fronteira.
- **Debounce**: fase mínima de 250 ms — evita falsos positivos por ruído.
- **Rep parcial** → feedback: passou de 70° mas não de 110° = `ARMS_TOO_LOW` ("estenda mais os braços"); tornozelos < 1.2 no pico = `LEGS_TOO_CLOSED`.

### 7.4 Classificação de exercício — evolução planejada

- **Fase 0–1**: usuário escolhe o exercício; a FSM correspondente valida a execução (na prática, classificar *qualidade*, não *identidade*).
- **Fase 3**: o `dataset-writer` já terá acumulado sequências reais de keypoints rotuladas por sessão → treinar um classificador temporal (janela de 2–3 s; 1D-CNN ou ST-GCN leve, rodando ONNX no `analysis-worker`) que **detecta qual** exercício está sendo feito. O app coleta seu próprio dataset desde o dia 1 — de graça.

Novos exercícios = novo módulo `exercises/squat.py` implementando a interface `ExerciseAnalyzer` (features + FSM + regras de feedback). Nada mais muda.

## 8. Sessões de 30 s = unidade de carga (admission control)

A sessão fixa de 30 s vira a moeda de capacidade:

1. Cliente pede `POST /sessions` informando resultado do probe.
2. API consulta semáforos em Redis: `slots:edge` (alto, ex. 40) e `slots:cloud` (baixo, ex. 3).
3. Com slot → sessão criada com TTL de 45 s (30 s + margem); sem slot cloud → fila de espera com posição visível ("~30 s").
4. `session.completed` (ou TTL) libera o slot.

Sobrecarga fica **impossível por construção** — a VPS nunca aceita mais do que aguenta.

### Orçamento da VPS (4 vCPU / 6 GB)

| Componente | RAM | CPU |
|---|---|---|
| Postgres | ~512 MB | baixo |
| Redis | ~256 MB | baixo |
| Django api + gateway | ~500 MB | baixo/médio |
| analysis-worker | ~150 MB | ~1–2% CPU por sessão (só aritmética em 33 pontos) |
| pose-worker ×2 | ~800 MB | **~0,5–0,7 vCPU por sessão cloud @10 fps** |
| Caddy + SO | ~400 MB | baixo |

→ Estimativa: **30–50 sessões EDGE simultâneas** e **~3 sessões CLOUD** simultâneas. Como edge é o padrão, a VPS atende bem um MVP SaaS real. Escalar depois = subir `pose-worker` em outra máquina apontando pro mesmo Redis (workers são stateless em relação à origem).

## 9. Fases de desenvolvimento

### Fase 0 — Prova local (1–2 semanas de trabalho)

Objetivo: **ver o contador de polichinelos funcionando na tela.**

- Monorepo + docker-compose (redis, postgres, api, web)
- React + MediaPipe no browser (modo edge apenas)
- Gateway Channels: recebe `pose.frame`, publica no stream
- `analysis-worker` com FSM do polichinelo + testes com keypoints gravados
- HUD: contador, timer 30 s, dicas
- Sem auth, sem quota — `SessionAnonymous`

### Fase 1 — Modo cloud + persistência

- `pose-worker` + envio de frames JPEG + capability probe/fallback
- `report-builder` → relatório pós-sessão (reps, cadência, erros, gráfico)
- Auth (Django allauth ou JWT simples), histórico de sessões
- `dataset-writer` gravando keypoints (parquet) — o futuro do ML começa aqui

### Fase 2 — SaaS-ready na VPS

- Admission control (semáforos/fila), quotas por plano
- Deploy: docker-compose + Caddy (TLS automático) na VPS Debian
- CI (GitHub Actions): testes + build de imagens
- Observabilidade mínima: logs estruturados (JSON) + healthchecks + página de status; Prometheus/Grafana só se sobrar RAM
- Backup do Postgres (pg_dump diário → object storage)

### Fase 3 — Inteligência e catálogo

- Classificador temporal de exercícios (dataset da fase 1)
- Novos exercícios: agachamento, flexão, prancha (esta é *hold time*, não reps — a interface `ExerciseAnalyzer` já prevê)
- Coach por voz (TTS dos eventos `feedback.issued`)
- Se precisar de vídeo de alta qualidade no cloud: avaliar WebRTC/SFU — **adiado deliberadamente** (ADR-003: WS binário resolve 320px@10fps com 1/10 da complexidade)

## 10. Estrutura de repositório sugerida

```
digital-fit/
├── docker-compose.yml            # dev local: tudo com 1 comando
├── docker-compose.prod.yml       # overrides p/ VPS
├── web/                          # React + Vite
│   └── src/{capture,probe,hud,report}/
├── server/                       # projeto Django
│   ├── api/                      # DRF: auth, sessions, results
│   ├── gateway/                  # Channels: WS ingest + feedback push
│   └── core/                     # models, settings
├── workers/
│   ├── shared/events.py          # contrato de eventos (única fonte da verdade)
│   ├── pose_worker/
│   ├── analysis_worker/
│   │   └── exercises/{base.py, jumping_jack.py}
│   └── report_builder/
├── tests/fixtures/keypoints/     # sessões gravadas p/ testar sem câmera
└── docs/adr/                     # decisões de arquitetura numeradas
```

## 11. Decisões registradas (ADRs)

| # | Decisão | Motivo | Revisitar quando |
|---|---|---|---|
| 001 | Redis Streams como broker | cabe na RAM, consumer groups, replay | > 1 VPS ou > 5k eventos/s |
| 002 | Gateway dentro do Django (Channels) | 1 deploy, menos partes na fase 0 | gateway virar gargalo de CPU |
| 003 | WebSocket binário, não WebRTC | simplicidade; 10fps JPEG pequeno basta | precisar de vídeo HD no cloud |
| 004 | FSM baseada em regras antes de ML | explicável, zero dado necessário, feedback específico | dataset ≥ ~500 sessões |
| 005 | Edge como modo padrão | VPS 4vCPU vira roteador de eventos, não fábrica de CV | nunca (é o superpoder do design) |
| 006 | Sessão fixa de 30 s + admission control | capacidade previsível por construção | planos premium com sessões maiores |
| 007 | `pose-worker` sem estado entre frames (MediaPipe `RunningMode.IMAGE`) | frames chegam por consumer group: dois frames seguidos da mesma sessão podem cair em réplicas diferentes, e o modo `VIDEO` pressupõe sequência contínua por instância. Sem estado, a réplica pode morrer no meio da sessão sem perda, e o mesmo JPEG dá sempre o mesmo resultado — que é o que dá sentido ao teste de paridade edge×cloud (T-018) | o custo da detecção completa por frame estourar o orçamento de 1 vCPU, ou sessão passar a ser fixada a uma réplica |
| 008 | `report-builder` roda **dentro do Django** (comando de manage), não em `workers/` | é o único consumidor que escreve no Postgres, e ORM, migrations e o `SessionResult` que a API lê vivem em `server/`. Um worker em `workers/` teria de importar `server/`, invertendo a dependência que o repositório mantém em uma direção só (server → workers) — e a inversão apareceria em toda a suíte, não só nele. Precedente: `gateway/relay.py` já é consumidor de stream dentro do Django. A consolidação continua pura e sem Django em `workers/report_builder/builder.py`: o que mora no Django é encanamento | o relatório precisar de escala horizontal (aí o gargalo justifica processo próprio + acesso ao banco por API interna), ou surgir um segundo worker que escreva no Postgres |

## 12. Primeiros passos concretos

1. `docker-compose.yml` com redis + postgres + django vazio
2. Página React com webcam + MediaPipe desenhando o esqueleto (validação visual)
3. `workers/shared/events.py` — escrever o contrato antes de qualquer serviço
4. FSM do polichinelo como função pura + pytest com fixture de keypoints
5. Ligar as pontas: browser → WS → stream → worker → WS → contador na tela

Quando quiser, começamos pela etapa 1.
