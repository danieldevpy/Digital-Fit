# DEVLOG — Digital Fit

> Registro de sessões de trabalho. Entradas mais recentes no topo.
> Formato: data · task(s) · o que foi feito · decisões · pendências geradas.

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
