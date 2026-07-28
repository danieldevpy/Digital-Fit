# DEVLOG — Digital Fit

> Registro de sessões de trabalho. Entradas mais recentes no topo.
> Formato: data · task(s) · o que foi feito · decisões · pendências geradas.

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

## 2026-07-28 · [A] T-001 — Monorepo + docker-compose

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
