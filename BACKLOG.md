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
| T-038 | Corpus inicial: 12–15 vídeos rotulados (manifest.yaml) + guia de gravação | 012 | doing — manifest + guia de gravação prontos, 1 de 12–15 vídeos (falta gravar) |
| T-039 | Métricas agregadas + `evalctl compare` (regressão entre versões) + `--save-keypoints` | 012 | done |

## Fase 1 — Modo cloud + persistência

| ID | Task | Spec | Status |
|---|---|---|---|
| T-015 | Envio de `frame.raw` JPEG 320px @10fps quando modo cloud | 001/005 | done |
| T-016 | pose-worker: consumer `frames.raw` → MediaPipe CPU → `pose.frame` (cgroup 1 vCPU) | 005 | done |
| T-017 | Semáforo `slots:cloud=3` (Lua atômico) + liberação em todos os finais | 009 | done |
| T-018 | Teste de paridade edge×cloud: mesmo vídeo, reps idênticas (±1/20) | 005 | done |
| T-019 | Baseline/calibração no countdown (mediana 1s); FSM NÃO usa baseline no divisor — ver Descobertas | 004 | done |
| T-020 | report-builder: consolidação + `SessionResult` no Postgres + tela de relatório | 010 | done |
| T-021 | dataset-writer: Parquet por sessão + schema documentado | 010 | done |
| T-022 | Auth JWT + trial anônimo (3/dia por device) + histórico do usuário | 011 | done |
| T-048 | Gate das ferramentas de dev: separadas da UI de produto, liberadas por conta (`is_admin`) para inspecionar produção | 012/011 | done |
| T-040 | Fonte de vídeo na UI web (upload → `<video>` → caminho edge) + paridade edge×cloud×harness — dentro do gate da T-048, nunca na UI de produto | 012 | done — falta 1 passada manual (abrir um vídeo do corpus no navegador e exportar o JSON) |
| T-041 | `evalctl replay --ws`: injetar keypoints gravados via gateway (integração + carga sintética) | 012 | todo |
| T-049 | Preparação "3, 2, 1" configurável entre o corpo medido e a contagem valer (3s padrão, 5/10s ou desligado) | 004/013 | done |
| T-047 | FSM inicia a fase pelo que observa, não assumindo `CLOSED` (perde a 1ª rep quando a captura começa com a pessoa aberta — ver Descobertas) | 007/004 | done |

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
| T-050 | `Phase` deixa de ser vocabulário de polichinelo: par neutro (`rest`/`peak`) no contrato | 007/002 | done |
| T-051 | Seleção de exercício no cliente (hoje `useSession.ts` fixa `DEFAULT_EXERCISE`) — sem isto o exercício 2 é inalcançável pelo produto | 013/007 | done |
| T-052 | Gerador sintético de poses além do polichinelo (`Pose` só tem `arm_angle`/`ankle_spread`) — sem isto a FSM 2 não tem fixture nem critério de aceite | 007/012 | done |
| T-032 | Exercício 2: agachamento (novo módulo `exercises/squat.py`) | 007 | done — limiares calibrados no gerador; falta corpus de vídeo (T-053) |
| T-053 | Corpus de agachamento + varredura dos limiares contra ele (hoje calibrados só no gerador sintético) | 012/007 | todo |
| T-054 | `KNEES_INWARD` (valgo dinâmico) — a falha de agachamento que a câmera FRONTAL vê melhor que qualquer outra; exige parâmetro novo no gerador de poses | 007/012 | todo |
| T-055 | Relatório e histórico mostram QUAL exercício foi feito (o dado já viaja ponta a ponta; nenhuma tela o desenha) | 013/010 | todo |
| T-033 | Form score por rep (amplitude, simetria, estabilidade) | 007 | todo |
| T-034 | Ferramenta de rotulagem do dataset + primeiro treino do classificador temporal | 010/007 | todo |
| T-035 | Coach por voz (TTS dos feedbacks) | 008 | todo |
| T-036 | Planos pagos + Stripe/Mercado Pago + LGPD (export/exclusão) | 011 | todo |
| T-045 | Meta de reps (`target_reps`, fim por `target_reached`) + séries/circuitos com descanso | 013/009 | todo |
| T-046 | KCAL estimada (MET × peso do perfil) + acumulado do dia + telas Exercícios/Progresso/Perfil | 013/010/011 | todo |

## Fase 4 — UI v2 (Evolução da interface — SPEC-014/015; plano em `docs/PLANO-UI-V2.md`)

Réplica fiel do protótipo Claude Design "Evolução UI v2" + `referencias/app-completo-mobile.png` + `referencias/index.png`. Só o Index é responsivo pc/mobile; o app de exercício mantém aspecto mobile.

| ID | Task | Spec | Status |
|---|---|---|---|
| T-056 | Tokens v2 (Manrope/Space Grotesk, paleta azul/roxo/ciano, animações df*) + roteador por hash + shell/tab bar nova | 014 | done |
| T-057 | Index responsivo (landing mobile + desktop com mini-HUD decorativo e footer) com hero Kairogen | 014 | done |
| T-058 | Tela Escolha de exercício (cards com demo, badge 30s, dot de grupo) + campos novos no catálogo | 014 | done |
| T-059 | Tela Guia passo a passo (primeiro acesso por exercício, imagens Kairogen, "visto" no localStorage) | 015 | done |
| T-060 | Pré-configuração funcional: steppers série/reps/duração, espelhar, câmera com grade+scan+silhueta, FC/kcal `--` | 014 | done |
| T-061 | Treino ao Vivo imersivo: HUD flutuante (anéis reais de reps/tempo, ângulo), player (stop honesto), toasts de cena/coach | 014 | done |
| T-062 | Tela Sobre / footer mobile | 014 | done |
| T-067 | Fronteira SITE \| APP: dois entry points do Vite, links cruzados por `VITE_SITE_URL`/`VITE_APP_URL`, pontes `#/ex/:slug` e `#/entrar`, nginx e `prod.sh` prontos para subdomínio (ADR-010) | 014 | done |
| T-068 | Tab bar Início · Progresso · Analytics · Perfil, play/stop como FAB no treino, telas Progresso e Analytics, rodapé do treino reempilhado e medido | 014 | done |
| T-069 | Portão de partida: sessão só é pedida quando o pipeline pode emitir frame; prazo de 12s no landmarker com queda GPU→CPU; estado de aquecimento visível na tela | 001/009 | done |
| T-070 | Assets de pose baixados UMA vez (fim do download duplicado que o prazo da T-069 causava), fileset reaproveitado entre tentativas, progresso do download na tela; gzip do `.wasm` no nginx (incluindo `gzip_http_version 1.0`, sem o qual nada comprime atrás do proxy) | 001 | done |
| T-071 | Porcentagem do download sobrevive ao gzip (manifesto de tamanhos no build) + HUD do treino sem colisão: cards em px, instrução de medição manda na tela, aviso de cloud curto | 001/014 | done |

### Futuras (specs prontas, implementar depois)

| ID | Task | Spec | Status |
|---|---|---|---|
| T-072 | Admin do Django ligado no processo `api`: apps + middlewares + context processors, `is_staff` novo (separado do `is_admin` de diagnóstico), estáticos servidos, gate por `DJANGO_ENABLE_ADMIN` e ausência no gateway; `User` editável, `SessionClaim`/`SessionResult` em leitura | 018 | done |
| T-073 | `Plan` + `User.plan`/`plan_until` + `SiteConfig` + `capabilities_for()` com cache invalidado por `post_save` e defaults do código como piso; `POST /api/sessions` passa a resolver quota, duração, countdown e cloud por ele — sem mudar comportamento nenhum (migration de dados com os valores de hoje) | 018/016 | todo |
| T-074 | `Exercise` (+ passos do guia) no admin com trava de slug contra `EXERCISES`, e `GET /api/config` servindo catálogo e capacidades ao cliente — fecha a divergência do `[A/T-051]` | 018/015 | todo |
| T-075 | `config_version` no `session.started` (aditivo, default 0) e no `SessionResult`: o relatório diz sob qual versão de configuração a sessão foi produzida | 018/010/002 | todo |
| T-063 | Modo Free: quota diária no servidor (`quota_exceeded`), sheet de limite, kcal só ao vivo — **lê do `Plan` da T-073**, não de constante nova | 016/018 | todo |
| T-064 | Modo Assinatura: duração configurável, modos de exercício, acúmulo de kcal, Modo Efeito — capacidades vêm do `Plan` da T-073 (a flag de plano deixa de ser desta task) | 016/018 | todo |
| T-065 | Perfil físico (peso/altura), kcal MET real, IMC, série temporal de peso, Progresso realista | 017 | todo |
| T-066 | GIF/vídeo de demonstração por exercício (Escolha + Guia) | 015 | todo |
| T-076 | A suíte roda no Postgres do compose, não em SQLite: as variáveis da `conftest.py` não alcançam mais o settings (ver Descobertas `[A/T-072]`) — mover para `pytest-env` ou `core/settings_test.py`, e conferir o job Python da CI | — | todo |

## Descobertas (entram aqui, nunca no escopo da task atual)

- **[A/T-072] A suíte NÃO roda em SQLite em memória — roda no Postgres do compose.** A
  `tests/conftest.py` promete, no próprio docstring, ser "carregada antes de o pytest-django
  chamar `django.setup()`". Não é mais: o `pytest_load_initial_conftests` do pytest-django 4.12
  força a leitura do settings (`dj_settings.DATABASES`) **antes** dos conftests, então
  `DJANGO_DB_SQLITE`, `DJANGO_CACHE_LOCMEM` e qualquer variável posta ali não têm efeito nenhum.
  Medido: dentro de um teste, `settings.DATABASES["default"]["ENGINE"]` é `postgresql`, e com
  `POSTGRES_PORT=59999` a suíte inteira que toca banco quebra. Passou despercebido porque a
  máquina de desenvolvimento tem o `docker compose up` de pé, e o teste conecta no container.
  Duas consequências: (a) **o job Python da CI, que não sobe Postgres, não pode estar passando**
  — vale abrir o Actions antes de mais nada; (b) o cache do rate limit também não é LocMem, ou
  seja, os testes de auth compartilham contador com o Redis real. A correção não cabia na T-072
  (que precisa da suíte como está para não confundir causa e efeito): ou as variáveis migram
  para o `[tool.pytest.ini_options]` via `pytest-env`, ou nasce um `core/settings_test.py`
  apontado por `DJANGO_SETTINGS_MODULE` no `pyproject.toml`. **Proposta: T-076.**
- **[A/T-072] Teste de formulário não cobre tela de admin.** O `ContaCreateForm` instanciado à
  mão validava e salvava perfeitamente enquanto `GET /painel/api/user/add/` respondia **500**:
  os `add_fieldsets` pedem `usable_password`, campo que só existe em `AdminUserCreationForm`
  (Django 5.1+), e não em `UserCreationForm`. O erro só aparece quando o `modelform_factory`
  monta o formulário a partir dos fieldsets — ou seja, na requisição. Regra que fica: **toda
  tela do painel precisa de um teste que a peça por HTTP**, não do teste da classe que ela usa.
  Descoberto abrindo o painel de verdade no compose, não pela suíte.
- **[A/T-072] `django.contrib.auth` registra "Grupos" no painel sozinho.** Sem
  `PermissionsMixin` no `User`, grupo aqui não muda permissão de ninguém — seria um controle
  que não controla, na primeira tela que o operador vê. Desregistrado em `api/admin.py`. Quando
  a T-073 trouxer mais modelos, vale reler o índice do painel com o mesmo olho: o que aparece
  ali é o que alguém vai clicar.
- **[T-069] Pré-carregar WASM e modelo antes da câmera**: o portão de partida tirou o `no_data`
  do caminho, mas a espera continua — no primeiro acesso são **8,7 MB na rede** (3,2 de wasm
  gzipado + 5,5 do modelo, que fica sem comprimir) baixados só DEPOIS de a câmera abrir, porque o
  probe precisa de frames reais. Dá para começar o download na Escolha ou na Pré-configuração
  (`link rel=prefetch` ou fetch em idle) e ter tudo em cache quando a câmera abrir. Não entrou na
  T-069 porque muda o carregamento de outras telas, não a partida da sessão. É a maior melhoria
  de percepção que sobrou no funil.
- **[T-070] Gerar os `.gz` no build para o `gzip_static` pagar**: o `web-nginx.conf` já tem
  `gzip_static on` (serve `arquivo.gz` pronto, zero CPU) com `gzip on` como rede de segurança.
  Hoje só o segundo caminho atua: comprime 11 MB a cada requisição numa VPS de 4 vCPU que também
  roda dois pose-workers. Um `gzip -9 -k` no `scripts/setup-mediapipe.mjs` resolve, sem tocar no
  nginx de novo.
- **[T-071] Caminho do WASM sem versão impede cache `immutable`**: `/wasm/` e `/models/` levam
  `max-age=3600` porque os nomes de arquivo não têm hash de conteúdo — marcar `immutable` por um
  ano deixaria aparelhos presos a um binário velho por um ano depois de atualizar o
  `@mediapipe/tasks-vision`, sem forma de invalidar. Versionar o caminho (`/wasm/0.10.14/`, vindo
  do `package.json` no `setup-mediapipe.mjs` + `WASM_BASE_PATH`) permitiria `immutable` e mataria
  a revalidação horária. Ganho pequeno (uma requisição de 0 bytes por hora), custo pequeno.
- **[T-071] `pose-assets.json` sem política de cache explícita**: o manifesto de tamanhos (180
  bytes) cai no `location /` sem `expires`, então vale a heurística do navegador. Num deploy que
  mude os tamanhos, um manifesto velho faria a barra de progresso mostrar porcentagem levemente
  errada — cosmético, e um `no-cache` resolve em uma linha.
- **[T-068] Capa da câmera desligada repete escolhas na tela de treino**: com a câmera
  fechada, `.stage__cover` mostra "Ligar câmera" + ExercisePicker + CountdownSetting também
  em `#/treino`, onde essas escolhas já foram feitas na pré-configuração. Não é o bug do
  rodapé (aquele saiu) — é ruído herdado da SPEC-013. Provável correção: passar
  `compactCover` também no treino, ou uma capa própria com "voltar à pré-configuração".
- ~~**[T-068] Chip de diagnóstico pode encostar nos cards de ângulo/calorias**~~ — resolvido na
  T-071: os cards do meio saíram de `top: 46%` e foram para px fixos, então a distância entre o
  grupo de cima e a pilha do rodapé não depende mais da altura do aparelho.

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
- **[A/T-020] `session.started` passou a ser publicado nos DOIS streams**: a rota padrão
  (`pose.frames`) é a entrada da análise, e o report-builder lê só `events.analysis` — sem a
  segunda publicação o relatório não saberia o exercício da sessão e teria de perguntar ao
  Redis, quebrando a propriedade da SPEC-010 (relatório derivável 100% por replay dos
  eventos). Quem for mexer no roteamento precisa saber que este evento é publicado duas vezes,
  de propósito.
- **[A/T-020] O nome do consumidor do report-builder é estável e o serviço não escala**: o PEL
  do Redis é indexado por nome de consumidor, e é por ele que as pendências voltam depois de
  um restart (SPEC-010, critério 2). Duas réplicas com o mesmo nome disputariam as MESMAS
  entregas pendentes. Escalar exige antes trocar a recuperação para `XAUTOCLAIM` — que rouba
  pendências de qualquer consumidor do grupo, e aí nomes por réplica voltam a ser seguros.
- **[A/T-020] Testes com banco rodam em SQLite (`DJANGO_DB_SQLITE=1`, ligado no conftest)**: a
  CI não sobe Postgres. O schema vem das mesmas migrations, mas nada específico de Postgres
  (JSONB, índices GIN, constraints de exclusão) seria pego pela suíte — quando a persistência
  crescer, a CI precisa de um Postgres de verdade.
- **[A/T-023] Artefato gitignorado + bind mount = falha só em produção**: o `pose-worker` de
  prod monta `./eval/models`, e o `.task` não está no git — num clone novo da VPS o serviço
  entra em crash loop enquanto o resto da stack sobe verde (edge funciona; só o cloud morre).
  Resolvido com o preflight `garante_modelo()` no `scripts/prod.sh`. Hoje `./eval/models` é o
  **único** bind mount de prod; qualquer novo que dependa de arquivo fora do git precisa do
  mesmo tratamento — ou a falha volta a aparecer só na VPS, calada.
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
- **[A/T-019] A baseline NÃO serve como divisor de `ankle_spread` — medido, não suposto.** O
  critério 3 da SPEC-004 pedia isso; implementei, o corpus reprovou, e a spec foi corrigida.
  O divisor por frame **se autocorrige**: com a pessoa em ângulo, abertura dos pés e largura
  de ombros encurtam juntas em perspectiva, e a razão se mantém. Fixá-lo destrói a
  invariância. Números: o vídeo frontal caiu de 20/20 para 18/20, e a varredura de limiares
  que consertava o frontal derrubava o oblíquo de 19/21 para **3/21** — não existe fator
  global que sirva aos dois. A baseline segue valendo para a escala da normalização
  (SPEC-006) e vai no `session.calibrated` para o relatório e para a T-030.
- **[A/T-019] Os 30 s passaram a correr do fim da calibração, não do primeiro frame.** O
  countdown é preparação; descontá-lo do treino encurtaria a sessão de quem demora a se
  posicionar — justamente quem mais precisa dos 30 s. Efeito colateral bom: o motivo de fim
  `timeout`, que era inalcançável, virou o teto de vida da sessão e agora cobre o caso de uma
  calibração que nunca fecha (frames continuam chegando, então `no_data` não salvaria).
- **[A/T-019] A bancada passou a calibrar também** (`analyze_frames(calibrate=True)`), senão
  `evalctl` mediria um pipeline que não existe mais. Consequência: vídeo de corpus sem
  countdown perde as reps que acontecem durante a medição. Os vídeos `02` e `03` são assim e
  caem 2 reps cada por isso — o `01`, que tem 2 s parados, segue 20/20. O guia de gravação
  passou a exigir 2–3 s parado no início, e `--no-calibrate` existe para comparar com o
  comportamento anterior.
- **[A/T-038] A FSM perde a primeira rep quando a gravação começa com a pessoa já ABERTA.**
  Diagnosticado no `polichinelo-02.mp4` (14 de 15): no `ts=0` os features já são
  `arm_angle=143°, ankle_spread=3.19` — posição aberta. A FSM nasce em `Phase.CLOSED` e o
  debounce de 250 ms (SPEC-007) exige estabilidade antes de aceitar a abertura; aos 167 ms a
  pessoa já está fechando, então a transição para `OPEN` nunca acontece e o ciclo se perde.
  Uma hipótese anterior ("erra quando não há tempo parado no início") foi **refutada** por
  experimento: cortar até 3 s do início do `polichinelo-01.mp4` continua dando 20/20 — o que
  importa não é o tempo parado, é a **fase** em que o vídeo começa. No produto o countdown
  (SPEC-004 / T-019) faz a pessoa começar parada e fechada, então o caso é raro ao vivo; para
  a bancada é real. Proposta: **T-047** — ~~aberta~~ **RESOLVIDA**: `--no-calibrate` no `02`
  passou de 14 para 15/15. O que sobra naquele vídeo é a calibração comendo exercício, não a
  contagem.
- **[A/T-032] O relatório e o histórico NÃO dizem QUAL exercício foi feito.** O dado existe
  em toda a cadeia (`SessionResult.exercise` no Postgres, coluna `exercise` no Parquet,
  `sessionReport.ts` no cliente), mas nenhum `.tsx` o renderiza: `ReportSheet` e
  `AccountSheet` não têm uma única menção. Com um exercício só isso era invisível; com dois, o
  histórico vira uma lista de "12 repetições" sem dizer de quê, e duas sessões diferentes
  ficam indistinguíveis na tela. É conserto pequeno (o `display_name` já está no catálogo do
  cliente) e puramente de apresentação — proposta **T-055**.
- **[A/T-032] Escolher o exercício errado dá ZERO repetições, em silêncio.** Medido: 10
  polichinelos com o agachamento selecionado = 0 reps, nenhum sinal de qualidade, nenhum
  aviso; e o inverso também. Não é contagem errada, é contagem nenhuma — o que é o
  comportamento seguro, mas a pessoa fica se mexendo na frente da câmera sem entender por que
  o contador não anda. O sistema **não sabe** o que está sendo feito: ele é informado pela
  seleção (SPEC-007: "usuário seleciona; nada de detecção automática ainda"). Duas saídas
  possíveis, e vale escolher antes de o terceiro exercício entrar: (a) `ready_pose()` já
  existe no contrato e ninguém chama — dava para avisar "você não está na posição inicial do
  agachamento" (é a T-030); (b) detecção automática pelo classificador temporal (T-034).
  A (a) é barata e cobre o caso comum.
- **[A/T-032] O One Euro corta o fundo do agachamento acima de ~90 rpm.** Medido: a contagem é
  exata até 90 rpm (1,5 agachamentos/s, já mais rápido do que se faz) e vai a zero em 120 rpm
  — e o motivo **não é a FSM**: o filtro entrega fundo de 0,727 torsos contra o limiar de
  0,72, e o agachamento inteiro vira "raso". A 30 fps o mesmo ritmo volta a contar 5 de 8,
  o que confirma o diagnóstico (mais amostras, menos corte). Os parâmetros do One Euro foram
  medidos para o polichinelo (SPEC-006: "o pulso percorre ~3 torsos/s"); o quadril de um
  agachamento anda bem menos e o filtro trata mais do movimento como ruído. Se algum
  exercício futuro precisar de mais banda, o caminho é **parâmetro por exercício na SPEC-006**
  — não afrouxar o limiar de profundidade, que tem justificativa anatômica.
- **[A/T-032] Os limiares do agachamento NÃO foram medidos em vídeo de gente agachando.** O
  corpus (T-038) só tem polichinelo. Eles saem da geometria do gerador sintético, e são
  conservadores porque o gerador não inclina o tronco à frente — vídeo real inclina, o que
  aumenta o sinal. É honesto, mas não é medição: proposta **T-053**.
- **[A/T-052] De frente, o ângulo do joelho MENTE — e por muito. Medido no gerador:**

  | joelho real | visto de frente | altura ombro→tornozelo |
  |---|---|---|
  | 172° (em pé) | 177° | 0,607 |
  | 140° | 165° | 0,588 |
  | 110° | 152° | 0,549 |
  | 80° (agachado) | **133°** | 0,491 |
  | 70° | 124° | 0,468 |

  O joelho de um agachamento viaja para a **frente**, e uma câmera frontal quase não vê esse
  eixo. Uma FSM que decidisse "agachou" por `knee_angle < 90°` lido do plano da imagem **nunca
  dispararia** em vídeo frontal — que é o enquadramento que o produto pede em toda a SPEC-003.
  O que a câmera enxerga bem é a **altura ombro→tornozelo**, que cai de forma monotônica
  (0,607 → 0,468, ~19%) e é candidata a feature principal do agachamento. **Consequência
  direta para a T-032**: as features do agachamento não podem espelhar as do polichinelo (lá o
  ângulo do braço é lido no plano da imagem e funciona, porque a abdução acontece nesse
  plano). Decidir isso antes de escrever a FSM, não depois de ela reprovar no corpus.
- **[A/T-052] O gerador é conservador quanto ao encolhimento, de propósito**: um agachamento
  real também **inclina o tronco à frente**, e de frente isso encurta ainda mais a projeção. O
  boneco mantém o tronco vertical, então mostra MENOS sinal do que o vídeo terá. Errar para
  menos é o lado seguro (a FSM não fica dependente de um sinal que talvez não venha); errar
  para mais aprovaria limiares que reprovam em produção. Se a T-032 quiser o tronco inclinado,
  é um parâmetro novo em `Pose` — não foi adicionado por não ter consumidor ainda.
- **[A/T-051] O catálogo do cliente e o registro do servidor podem divergir sem ninguém ver.**
  `EXERCISE_CATALOG` (web) é conteúdo de apresentação; `EXERCISES` (worker) é quem existe de
  verdade, e o `POST /sessions` recusa slug desconhecido dizendo quais aceita. Se alguém
  adicionar exercício só no web, o usuário escolhe e leva uma recusa de admissão. É alto e
  explicado, não silencioso — por isso não bloqueia a T-032. O jeito de acabar com a classe
  toda seria o servidor **publicar** o catálogo (ex.: `GET /api/exercises`) e o cliente
  desenhar o que veio, em vez de manter uma segunda lista. Vale decidir junto com a aba
  Exercícios (T-046), que é quem realmente precisa da lista completa.
- **[A/T-051] `'toString' in EXERCISE_CATALOG` é `true`** — pego por teste que escrevi
  esperando ver passar. `in` percorre o protótipo, então um `toString` guardado no aparelho
  passava por exercício válido, ia parar no `POST /sessions` e fazia `getExercise` devolver
  uma função no lugar do card (`.display_name` = `undefined` no meio da tela). Trocado por
  `Object.hasOwn` nos dois pontos. Vale como regra geral do web: **catálogo indexado por
  string vinda de fora usa `Object.hasOwn`, nunca `in`.**
- **[A/T-047] O ganho da fase lida não aparece no corpus calibrado — e isso é a guarda
  funcionando.** Medido antes e depois: `evalctl run eval/corpus/` devolve exatamente
  `20/13/19` nos dois casos. Só o caminho `--no-calibrate` melhorou. O motivo é que
  `initial_phase` exige os **dois** limiares de abertura, e no frame em que a contagem começa
  (depois da calibração) a pessoa está em posição intermediária — nada é afirmado, adota-se
  `CLOSED`. Foi uma escolha deliberada: aceitar só o braço levantado recuperaria mais reps na
  bancada e criaria repetição fantasma para quem calibra com o braço erguido. **Lição: medir
  antes e depois vale mesmo quando o número não muda** — foi o "não mudou" que provou que a
  guarda existe de verdade, e não só no comentário.
- **[A/T-038] Falha TOTAL de detecção é silenciosa — nem sequer vira `OUT_OF_FRAME`.**
  No `polichinelo-03.mp4` (20 de 21) a detecção é perfeita nos primeiros 20 s e **zero** pose
  do segundo 21 ao 25: a pessoa sai do quadro e a 21ª rep acontece onde o modelo não a vê. O
  problema é que a validação de cena (SPEC-003) opera sobre landmarks — sem landmarks não há
  evento, logo não há aviso. O sistema fica mudo até o `no_data` de 10 s. Quem está treinando
  não recebe "volte para o quadro" justamente quando mais precisa. Cobrir isso é da SPEC-003
  Fase Evolução (T-029), mas vale decidir antes se um `pose.frame` "vazio" deve existir só
  para a cena poder reclamar.
- **[A/T-018] A paridade compara Python×Python, não navegador×servidor**: o lado "edge" do
  `evalctl parity` é o MediaPipe do **Python** em modo VIDEO e resolução cheia, não o do
  navegador. Uma divergência entre a implementação JS e a Python passaria despercebida. O que
  o teste isola são as quatro degradações reais do caminho cloud (320px, JPEG q60, 10fps em
  vez de 15, IMAGE em vez de VIDEO) — que é o risco de fato. Cobrir o navegador exigiria
  dirigir um browser; fica para quando houver motivo.
- **[A/T-018] Banda do modo cloud medida: ~98 KB/s por sessão** (9,8 KB por JPEG a 10fps, em
  vídeo 270×480). Três sessões simultâneas ≈ 2,4 Mbit/s de entrada na VPS. Número medido, não
  estimado — vale conferir contra o orçamento da ARCHITECTURE quando a T-028 (carga) rodar.
- **[A/T-017] Semáforo é ZSET com expiração por membro, não `INCR`/`DECR`**: a nota técnica da
  SPEC-009 sugeria contador em Lua. Um contador atende ao critério 1 (negar a 4ª) mas **não**
  ao 2, que exige liberar a vaga inclusive em crash de worker — quem crasha não decrementa, e
  depois de três crashes o modo cloud estaria esgotado para sempre sem nada em log. Cada
  sessão virou membro de um ZSET com score = expiração, e toda operação varre os vencidos. A
  nota da spec ficou desatualizada; **vale atualizar a SPEC-009** na próxima passada por ela.
- **[A/T-017] Quem devolve a vaga é o analysis-worker, não a API**: é ele que sabe quando a
  sessão realmente acabou, inclusive por timer e por `no_data` — caminhos que nunca passam
  pela API. E ele libera sem perguntar o modo da sessão (liberar vaga inexistente é no-op),
  porque "lembrar de checar o modo" é o tipo de detalhe que se esquece num caminho de erro.
- **[A/T-016] ~~Descarte por idade usava o relógio do CLIENTE~~ — RESOLVIDO, com correção da
  SPEC-005.** A nota técnica mandava medir a idade pelo `ts` do envelope, carimbado pelo
  navegador: um celular com relógio atrasado faria todo frame parecer velho e o worker
  descartaria a sessão inteira em silêncio. A própria spec se contradizia — o texto do
  comportamento diz "frame que esperar > 500ms **na fila**", e espera na fila é relógio de
  servidor. A nota foi corrigida e o worker passou a medir pela hora de entrada no stream
  (ID do Redis, `<ms-do-servidor>-<n>`). O `ts` do cliente segue no `pose.frame` emitido, que
  é o certo: para a FSM o tempo é o da captura. Teste de regressão com celular 1h atrasado.
- **[A/T-016] `pose-worker` roda em `RunningMode.IMAGE`, a bancada em `VIDEO`**: registrado
  como ADR-007. A bancada é uma sequência contínua num processo só (pode rastrear); o worker
  lê de consumer group, onde frames da mesma sessão caem em réplicas diferentes. Consequência
  prática a lembrar na T-018: os dois lados NÃO produzem landmarks idênticos frame a frame —
  a paridade que a spec pede é de contagem de reps (±1 em 20), não de keypoints.
- **[A/T-016] Modelo `.task` fica fora da imagem, vem por volume**: `DIGITALFIT_POSE_MODEL`
  aponta para `/models`, montado de `./eval/models`. Assar o modelo na imagem faria cliente,
  bancada e worker divergirem sem ninguém perceber. O custo é que a VPS precisa do arquivo
  antes do primeiro deploy do modo cloud (`python -m eval.evalctl fetch-model`).
- **[A/T-015] O caminho cloud existe mas ainda não pode ser exercitado**: o cliente já envia
  `frame.raw`, o gateway já aceita e roteia para `frames.raw` — mas ninguém consome (T-016) e
  a admissão continua recusando cloud com `denied_cloud` (T-017). Para ver o fluxo inteiro é
  preciso as três. Foi verificado à mão publicando `frame.raw` numa sessão edge contra a
  stack real: o evento cai em `frames.raw`, com o JPEG intacto.
- **[A/T-015] `source` de `frame.raw` é `cloud`, não `edge`**: quem produz o evento é o
  navegador, mas o campo descreve o **caminho de extração**, não a máquina — mesma convenção
  que `pose.frame` já usa. Documentado na docstring do contrato porque a leitura errada é
  natural e levaria o pose-worker a filtrar pelo valor errado.
- **[A/T-015] Gateway em dev não recarrega código**: o `uvicorn` do compose sobe sem
  `--reload`, então mudança em `workers/shared/events.py` só vale depois de
  `docker compose restart gateway`. Custou uma verificação que falhou com `type invalido:
  'frame.raw'` parecendo bug de contrato. O `api` não tem o problema (roda `runserver`).
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
- **[A/T-021] A coluna `degraded` do dataset é sempre `false`.** O contrato do `pose.frame`
  tem o campo, mas nenhum produtor o preenche: quem calcula degradação é o `Normalizer`
  dentro do analysis-worker (SPEC-006, item 4), e esse resultado não volta para o evento. O
  cliente edge (`useEdgePipeline.ts`) e o pose-worker mandam só `landmarks`. Consequência: o
  corpus não carrega a máscara de qualidade, e quem treinar precisa derivá-la das colunas
  `_v`. Opções: (a) o produtor calcula visibilidade das âncoras antes de enviar — barato, é
  uma média de 6 números; (b) a análise reemite o frame marcado, o que dobra o tráfego do
  stream; (c) aceitar e documentar (feito em `docs/DATASET.md`). Proposta: **(a)**, como task
  nova, porque `degraded` também é o que faz a FSM congelar e hoje ela nunca congela por essa
  via.
- **[A/T-021] Duas réplicas de dataset-writer partiriam a sessão ao meio.** O consumer group
  distribui frames entre consumidores, e cada um bufferiza por conta própria: a mesma sessão
  sairia como dois arquivos parciais com o mesmo nome (o segundo sobrescrevendo o primeiro).
  Fixado em `replicas: 1` no compose de produção, com o motivo escrito lá. Escalar de verdade
  exige particionar por sessão (ex.: um stream por hash de `session_id`) ou consolidar os
  arquivos depois — nenhum dos dois é problema enquanto uma réplica der conta de 15 fps.
- **[A/T-021] O corpus não sabe se a sessão foi boa.** O Parquet guarda keypoints e o rótulo
  do exercício, mas não o desfecho (reps contadas, motivo do fim, warnings de cena) — isso
  vive no `SessionResult`, no Postgres, ligado pelo `session_id`. Para treinar classificador
  basta o que está no arquivo; para *filtrar* o conjunto de treino ("só sessões com scene
  score ≥ X") vai ser preciso juntar as duas fontes. A SPEC-010 já prevê isso na Fase
  Evolução ("Filtro de qualidade do dataset"); registrado aqui só para que a junção não seja
  descoberta na hora do treino.
- **[A/T-022] O device do trial vai em header, não em cookie httpOnly.** A SPEC-011 pede
  cookie httpOnly para o id do aparelho; a entrega usa `X-Device-Id` guardado no
  `localStorage`. Motivo: o cliente e a API vivem em origens diferentes (`web` no 5173, `api`
  no 8000), e cookie cross-origin exige `SameSite=None; Secure` — que o navegador descarta em
  http, ou seja, o dev inteiro. O header funciona igual nos dois ambientes e não muda a
  garantia: a spec já assume que o funil é burlável (limpar o armazenamento zera a quota), e
  httpOnly protegeria contra XSS um dado que não é segredo. Reverter para cookie é possível
  sem tocar no cliente — `trial.device_id_from` lê o header, bastaria ler o cookie antes.
- **[A/T-022] O dia do trial vira às 21h no Brasil.** A quota usa a data UTC na chave do
  cache (`trial:<device>:<AAAA-MM-DD>`), então quem treinou às 20h50 ganha 3 sessões novas dez
  minutos depois. Consciente: o servidor não sabe o fuso de quem está do outro lado, e
  adivinhar por IP erraria mais do que acerta. Corrigir de verdade é mandar o offset do
  cliente (`Intl.DateTimeFormat().resolvedOptions().timeZone`) no mesmo header da admissão —
  mas aí o próprio cliente escolhe quando o dia vira, o que só faz sentido depois que houver
  uma razão melhor que "3 grátis" para criar conta.
- **[A/T-022] Não existe logout do lado do servidor.** `ROTATE_REFRESH_TOKENS: False` e sem a
  blacklist do simplejwt: sair apaga os tokens do `localStorage` e nada mais. Um refresh
  copiado antes disso continua valendo até os 14 dias vencerem. Aceitável enquanto a conta só
  guarda histórico de treino; vira problema no dia em que houver pagamento ou dado sensível —
  aí entram `rest_framework_simplejwt.token_blacklist` (uma migration, uma tabela) e rotação.
- **[A/T-022] `django.contrib.auth` trouxe tabelas que ninguém usa.** Entrou por causa de
  `AbstractBaseUser`/`make_password`, e junto vieram `auth_permission`, `auth_group` e
  `django_content_type` — 12 migrations aplicadas para nada, já que não há admin nem
  permissões. Custo real é zero (linhas paradas no Postgres) e o benefício é não reescrever o
  hashing de senha. Registrado para quem estranhar as tabelas no banco.
- **[A/T-022] `SessionClaim` é uma tabela nova em vez de `user_id` no `SessionResult`.** A
  SPEC-011 diz que "`Session` ganha `user_id` opcional", mas o `SessionResult` é gravado pelo
  report-builder a partir dos eventos, e a SPEC-010 promete que ele é 100% derivável por
  replay do stream. Um `user_id` lá dentro quebraria isso — o dono é fato da admissão, não do
  treino. A dona ficou em `session_claim`, escrita pela API no `POST /api/sessions`, e o
  histórico é a junção das duas pelo `session_id`. Efeito colateral bom: apagar a conta não
  toca no corpus da T-021.
- **[A/T-048] A superfície de dev estava no ar em produção desde a T-007.** O chip de
  diagnóstico e o gravador de fixtures ficavam atrás de `{isReady && ...}` no `CameraView` —
  só isso. Qualquer pessoa que abrisse o domínio público e ligasse a câmera via `pose gpu`,
  `seq 412 · 14.9fps` e os botões de gravar fixture. O comentário no topo do
  `FixtureControls.tsx` já dizia "não faz parte da UI de produto"; o código nunca fez valer.
  Corrigido pelo gate (`web/src/dev/gate.ts`). A lição que fica: **comentário não é gate** —
  quando um arquivo declara que não pertence à UI de produto, quem garante isso tem de ser
  uma condição, e ela precisa de teste.
- **[A/T-048] O `tsc --noEmit` não checava um único arquivo.** O `tsconfig.json` da raiz tem
  `"files": []` + project references, e nessa configuração o `tsc` sem `-b` sai com 0 sem
  verificar nada. Rodei esse comando como "gate" várias vezes, inclusive na T-022. Com o
  `tsc -b --force` de verdade apareceram 10 erros, dois deles meus na T-022
  (`accountSummary.ts`, `noUncheckedIndexedAccess` em `split()[0]`) e dois anteriores em
  `reportSummary.test.ts`, da T-020 — ou seja, o `npm run build` estava quebrado havia tempo e
  ninguém percebeu, porque o build de produção roda por Docker e a imagem `web` de dev usa o
  Vite direto. Virou `npm run typecheck`, que a T-027 (CI) tem de incluir junto do lint.
- **[A/T-048] Não há formatador configurado no `web/`.** O gate é só `eslint .`, que não
  reformata; o estilo do projeto (sem ponto-e-vírgula, aspas simples) existe por convenção e
  não por ferramenta. Rodar `npx prettier --write` num arquivo o converte para o estilo padrão
  do Prettier e passa no lint do mesmo jeito — descobri isso do jeito ruim, reformatando seis
  arquivos sem querer. Ou entra um `prettier.config` com as opções do projeto (e um
  `format:check` no CI), ou o eslint ganha as regras de estilo. Enquanto não houver, **não
  rodar formatador no `web/`**.
- **[A/T-040] O capability probe come o começo do vídeo — e comeria a calibração.** O probe
  roda 2 s de detecção no `<video>` antes de o loop começar. Com a câmera isso é inofensivo
  (o tempo passa e a pessoa ainda está lá); com um ARQUIVO, esses 2 s são 2 s de conteúdo, e
  logo os primeiros — que a SPEC-004 usa para medir o corpo parado. Sem tratar, a contagem do
  navegador divergiria da do harness por montagem, e a "divergência JS × Python" que a task
  existe para medir seria um artefato meu. Resolvido carregando o vídeo **pausado** no frame 0
  e rebobinando depois do probe (`rewindAndPlay`). Fica o alerta para quem mexer no probe: se
  ele passar a consumir tempo em outro ponto, a fonte de arquivo quebra em silêncio — o
  sintoma é contagem sempre alguns abaixo, nunca acima.
- **[A/T-040] A perna do navegador é manual e não dá para automatizar barato.** O JSON sai de
  alguém abrir o painel, escolher o vídeo e clicar em baixar. Automatizar exigiria dirigir um
  browser de verdade (Playwright + WASM do MediaPipe + um servidor de pé), que é ordem de
  grandeza acima do resto da bancada e não cabe na T-042 (eval em CI) como está escrita.
  Enquanto for manual, vale a regra: rodar a passada do navegador **antes de mexer em
  normalização, filtro ou FSM**, porque é a única medida do que o usuário realmente executa.
- **[A/T-040] Vídeo maior que 30 s é cortado pelo servidor, não pelo cliente.** A sessão tem
  duração fixa (SPEC-009) e o timer é autoritativo: um arquivo de 45 s vira uma sessão de 30 s
  e o resto do arquivo não é contado. Para o corpus atual (28–29 s) não muda nada, mas quem
  gravar vídeo longo vai comparar 30 s de navegador contra 45 s de harness e achar que
  encontrou divergência. Ou o corpus se mantém abaixo de 30 s, ou a paridade passa a recortar
  o vídeo antes de entregar ao harness.
- **[A/T-049] `session.calibrated` mudou de significado.** Antes queria dizer "a contagem
  começou"; agora quer dizer "o corpo foi medido", e quem lê precisa somar `countdown_ms` para
  saber quando o relógio dos 30 s anda. Nenhum consumidor atual quebrou (o cliente foi
  atualizado; o report-builder só usa `samples`), mas qualquer consumidor novo que trate o
  evento como marco de início vai errar em 3 s por padrão — e errar em silêncio, que é pior.
- **[A/T-049] Não há segundo evento para o "JÁ".** Foi considerado um `session.counting` e
  descartado: o cliente já ancorava o anel no relógio DELE ao receber o `session.calibrated`,
  então um evento novo custaria uma ida ao servidor sem comprar autoridade nenhuma. A
  autoridade que importa está no worker, que não alimenta a FSM antes do prazo. Se algum dia o
  anel precisar bater com o servidor ao milissegundo, aí o evento passa a valer a pena.
- **[A/T-049] A preparação não vale para sessão aberta sem `session.started`.** O
  `SessionState` do worker tem `countdown_s = 0` como default, e não os 3 s do produto: esse
  caminho é o fallback em que um `pose.frame` abre a sessão sem admissão, onde não há cliente
  coordenando nada. Engolir 3 s de frames ali seria perder dado para preparar uma pessoa que
  não existe.
- **[A/T-049] Toda suíte que conta reps precisou declarar `countdown_s=0`.** Sete testes
  quebraram ao mudar o default, em `test_analysis_worker`, `test_calibration`, `test_sessions`,
  `test_feedback` e no e2e do cliente. Não é ruído: cada um deles é um teste de CONTAGEM que
  estava herdando em silêncio uma decisão de produto. Agora dizem no próprio corpo que não
  querem preparação — e o dia em que o default mudar de novo, eles não se mexem.
