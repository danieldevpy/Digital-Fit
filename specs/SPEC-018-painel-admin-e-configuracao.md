# SPEC-018 — Painel de Administração & Plano de Configuração
Status: draft | Camada: api (Django) + client | Depende de: SPEC-009, SPEC-011, SPEC-016 | Habilita: SPEC-016 (T-063/T-064), SPEC-017

## Entidade e responsabilidade

Define **o que o sistema permite mudar sem deploy, quem muda, e por onde o valor chega em cada consumidor**.

Até aqui todo parâmetro do produto era constante em código (`TRIAL_LIMIT`, `DEFAULT_DURATION_S`, o catálogo de exercícios do cliente) ou variável de ambiente (banco, Redis, segredos). Isso estava certo enquanto os parâmetros eram de engenharia: número calibrado contra corpus muda por experimento e commit, não por formulário. A SPEC-016 introduz a primeira categoria diferente — **capacidade de plano** é decisão comercial, muda por teste de mercado, e não pode custar um rebuild de container.

Esta spec é a fronteira entre as três naturezas:

| Natureza | Onde vive | Quem muda | Exemplo |
|---|---|---|---|
| Negócio / conteúdo | Postgres, editável no admin | operador | sessões/dia do Free, nome do exercício, texto do feedback |
| Infra | variável de ambiente | deploy | `REDIS_URL`, `DJANGO_SECRET_KEY`, `GATEWAY_WS_URL` |
| Medição | constante em código | commit + bancada (SPEC-012) | `open_arm_angle`, `MIN_BODY_HEIGHT`, One Euro |

Nada atravessa essa fronteira sem ADR.

## Princípios (valem para toda configuração desta spec)

**P1 — A configuração é resolvida na fronteira da API e viaja carimbada no evento.**
Os workers (`workers/`) não têm ORM e não vão ganhar: a dependência do repositório corre em uma direção só (server → workers, ADR-008). Mais forte que isso, a SPEC-010 promete que o relatório é 100% derivável por replay do stream — se o `analysis-worker` consultasse o banco, o mesmo replay em dois momentos daria relatórios diferentes, e daria em silêncio. Então quem lê configuração é a API, no `POST /api/sessions`, e o valor resolvido vai dentro do `session.started` (que já carrega `duration_s` e `countdown_s` — `server/api/sessions.py:197`).

**P2 — Todo valor tem default no código; o banco apenas sobrepõe.**
Nenhuma leitura de configuração pode falhar uma sessão. Postgres lento, Redis fora, tabela vazia, deploy novo antes da migration: o caminho degradado é usar a constante que já existe hoje. Configuração indisponível é um treino a menos de personalização, nunca um erro na cara de quem ia treinar.

**P3 — O que a bancada calibra não é configuração.**
Limiar de FSM e de cena é medido contra o corpus da SPEC-012, e a bancada varre os defaults do código. Um valor mudado por formulário não tem fixture, não tem teste de regressão, muda a contagem de repetição sem aviso e contamina o Parquet da SPEC-010 — keypoints gravados sob limiares que ninguém registrou. Se um dia isso precisar ser ajustável, o formato não é campo no admin: é **perfil versionado carimbado na sessão**, para o relatório poder dizer sob qual perfil aquela contagem nasceu (ver Fase Evolução).

## Superfícies de configuração

### A. Planos e quotas — o motivo desta spec existir

| Capacidade | Hoje | Origem |
|---|---|---|
| Limite diário de sessões | `TRIAL_LIMIT = 3` | `server/api/trial.py:39` |
| Mensagem da recusa por quota | constante | `server/api/trial.py:45` |
| TTL do contador diário (48 h) | constante | `server/api/trial.py:52` |
| Duração da sessão (30 s) | `DEFAULT_DURATION_S` | `server/api/sessions.py:45` |
| Faixa de duração permitida | não existe (30 s fixo) | SPEC-016 |
| Modo cloud liberado? | livre para todos | SPEC-011 Evolução |
| Profundidade do histórico (50) | `HISTORY_LIMIT` | `server/api/views.py:24` |
| Acúmulo de kcal (dia/semana) | não existe | SPEC-016 |
| Modo Efeito (cosmético premium) | não existe | SPEC-016 |
| Gráficos de progresso | não existe | SPEC-016/017 |
| Exercícios liberados | todos | — |
| Countdown default (3 s) e teto (10 s) | `DEFAULT_COUNTDOWN_S` / `MAX_COUNTDOWN_S` | `workers/shared/events.py:376,380` |
| Faixas dos steppers (série 1–9, reps 5–30) | constantes no cliente | `web/src/session/configPrefs.ts` |

**O anônimo passa a ser um plano.** Hoje o trial é um caminho de código próprio (`api/trial.py`) porque era o único limite existente. Com `Plan`, `anon` é só o plano de entrada do funil: mesmo campo de limite, mesmo campo de mensagem, um resolvedor só. O que continua diferente é a chave do contador (`trial:{device}:{dia}` para anônimo, `df:quota:{user}:{dia}` para logado) — a identidade do contado muda, a regra não.

### B. Catálogo de exercícios — e a divergência que ele fecha

O catálogo está partido em dois hoje: o registro autoritativo (`EXERCISES`, mapeia slug → classe da FSM, `workers/analysis_worker/exercises/base.py:97`) e a apresentação (`web/src/session/catalog.ts`). O BACKLOG já registra o efeito em `[A/T-051]`: *"o catálogo do cliente e o registro do servidor podem divergir sem ninguém ver"*.

A FSM continua em código — é lógica, tem teste e fixture. A apresentação vira dado:

`display_name`, `category`, `muscle_group`, `default_tip`, `main_angle`, `demo_img`, `dot_color`, ordem de exibição, `enabled`, plano mínimo, e os passos do Guia da SPEC-015 (`img` + texto, ordenados).

Ganhos diretos: desligar um exercício quebrado sem deploy; publicar exercício exclusivo de assinante sem tocar em código; e o cliente deixa de ser fonte da verdade sobre o que existe.

**Trava obrigatória**: `Exercise.slug` só salva se existir em `EXERCISES`. Sem isso o admin passa a poder cadastrar um exercício que a admissão rejeita (`server/api/sessions.py:82`) — um botão na tela que não funciona, criado por quem achava que estava cadastrando um exercício.

### C. Textos do produto

- **Catálogo de feedback** (`workers/analysis_worker/feedback/catalog.pt-BR.yaml`): mensagem, dica, severidade, prioridade por código. São as frases que a pessoa lê suando; você vai querer reescrevê-las sem deploy. O conjunto de **códigos** continua em código (`Code`, no contrato) — o admin edita o texto de um código existente, nunca inventa código.
- Mensagem de quota esgotada, texto do sheet "Você treinou muito hoje 🎉" (SPEC-016), CTA de assinatura / lista de espera.

### D. Operação e capacidade

| Parâmetro | Hoje | Origem |
|---|---|---|
| Vagas cloud simultâneas (3) | `DEFAULT_CLOUD_SLOTS` | `workers/shared/slots.py:38` |
| Carência de liberação de vaga (15 s) | `GRACE_MS` | `workers/shared/slots.py:43` |
| TTL do ticket de sessão (45 s) | `DEFAULT_TTL_S` | `server/api/tokens.py:26` |
| Rate limit das rotas de auth | env `AUTH_THROTTLE_RATE` | `server/core/settings.py:138` |
| Throttle do feedback (4 s) e supressão por cena (3 s) | constantes | `workers/analysis_worker/feedback/__init__.py` |

As duas últimas linhas são lidas **dentro do worker** — chegam pelo plano de snapshot (§"Como cada consumidor lê"), não pelo evento, e ficam para a Evolução. As três primeiras são lidas pela API na admissão e entram já na Fase Inicial.

### E. Contas e suporte (CRUD, não configuração)

O painel também é a ferramenta de suporte que hoje não existe — tudo passa por shell na VPS:

- `User`: ver, buscar por e-mail, atribuir plano e validade, desativar (`is_active`), resetar senha.
- `is_admin` (superfície de diagnóstico do cliente, T-048): hoje só por `manage.py admin_tools`. Passa a ser marcável no painel, mantendo o comando como porta de emergência.
- `SessionClaim` e `SessionResult`: leitura para suporte ("meu treino não apareceu"). **Somente leitura** — `SessionResult` é escrito pelo report-builder a partir de eventos, e editar à mão criaria uma linha que nenhum replay reproduz, quebrando a SPEC-010.
- Auditoria: quem mudou o quê e quando (`LogEntry` do admin, de graça).

### F. O que **não** entra no painel — e por quê

- **Limiares de FSM** (`JumpingJackThresholds`, `server/../exercises/jumping_jack.py:47`; equivalentes no `squat.py`) e **de cena** (`MIN_BODY_HEIGHT`, `MAX_BODY_HEIGHT`, `TRIGGER_AFTER_MS`, `workers/analysis_worker/scene.py:44-52`) — princípio P3.
- **Normalização e filtros** (`workers/shared/normalize.py`, `filters.py`) — idem.
- **Contrato de eventos**: `PROTOCOL_VERSION`, `STREAM_MAXLEN`, `LANDMARK_COUNT`, `FRAME_RAW_MAX_SIDE/BYTES`. Mudar contrato é mudar código nos dois lados.
- **Infra e segredos**: `SECRET_KEY`, credenciais, `ALLOWED_HOSTS`, `DEBUG`, `GATEWAY_WS_URL`, tempos de vida do JWT. Configuração que derruba o serviço, ou que enfraquece autenticação, não pertence a um formulário web — e um painel comprometido não deve ser capaz de emitir tokens eternos.

## Modelo de dados

```
Plan(slug único, nome, is_default, ordem)
  ├─ daily_sessions            int      # 0 = ilimitado
  ├─ session_min_s/max_s       int      # clamp da duração pedida
  ├─ countdown_max_s           int
  ├─ allow_cloud               bool
  ├─ history_limit             int
  ├─ kcal_accumulation         bool
  ├─ effects_enabled           bool
  ├─ quota_message             text     # mensagem da recusa deste plano
  └─ flags                     JSON     # cosméticos voláteis

User.plan        FK(Plan, null=True → plano default)
User.plan_until  DateTime(null)         # assinatura expira sozinha; nulo = sem prazo
User.is_staff    bool                   # acesso ao painel (ver Notas técnicas)

Exercise(slug único, display_name, category, muscle_group, default_tip,
         main_angle, demo_img, dot_color, ordem, enabled, min_plan FK(null))
  └─ ExerciseGuideStep(exercise FK, ordem, img, texto)    # inline no admin

FeedbackMessage(code único, message, hint, severity, priority, active)

SiteConfig(singleton)
  ├─ cloud_slots, cloud_grace_ms, ticket_ttl_s
  ├─ default_duration_s, default_countdown_s
  ├─ series_min/max, reps_min/max, reps_default
  └─ version   int    # incrementa a cada save de QUALQUER modelo desta spec
```

**Colunas tipadas, não chave-valor.** EAV (`Config(key, value)`) dispensa migration, mas abre mão de validação, de tipo e de legibilidade — e este projeto está do lado da validação em todas as decisões anteriores. O preço é uma migration por capacidade nova, que é exatamente o momento em que alguém deveria pensar no que está criando. O `flags` JSON existe para o booleano cosmético que nasce e morre em duas semanas.

## Como cada consumidor lê

Três planos, e nenhum deles é "o worker consulta o banco".

**1. API (Django, tem ORM).** `capabilities_for(user | device)` resolve o plano e devolve um dataclass congelado. Leitura passa pelo cache (Redis, já configurado em `settings.py:176`): snapshot serializado sob `df:config:snapshot`, reconstruído do Postgres quando ausente e invalidado por `post_save`/`post_delete` dos modelos desta spec. Custo por admissão: um `GET` no Redis. Falhou tudo? P2 — defaults do código.

**2. Workers (sem ORM).** Dois caminhos, nesta ordem de preferência:
- *Por evento* (Fase Inicial): valor resolvido pela API entra no `session.started`. É como `duration_s` e `countdown_s` já funcionam, preserva replay e não acrescenta mecanismo.
- *Por snapshot no Redis* (Fase Evolução): para o que não é por sessão — textos do catálogo de feedback. O Django escreve `df:config:feedback` com a versão; o worker lê na abertura da sessão e cai no YAML se a chave não existir. O YAML permanece no repositório como semente e fallback de boot.

**3. Cliente.** `GET /api/config` devolve, num payload só: catálogo de exercícios habilitados, capacidades do plano de quem chamou (anônimo incluso), limites e mensagens, faixas dos steppers, e `config_version`. Com `ETag`/`If-None-Match` para o revalidar custar 304. O cliente mantém os defaults atuais em código para o primeiro paint e para o caso offline (`web/src/session/catalog.ts`, `configPrefs.ts`) — o valor do servidor vence quando chega, e a tela não espera por ele para desenhar.

## Fase Inicial

### Escopo / Comportamento

- Admin do Django ligado no processo `api` apenas, atrás de `DJANGO_ENABLE_ADMIN`, em caminho não-óbvio, com estáticos servidos.
- `User.is_staff` novo, marcável só por `manage.py` (não pela API, não pelo cadastro).
- Modelos `Plan`, `Exercise` (+ passos do guia), `SiteConfig` e as telas de admin correspondentes; `User` editável; `SessionClaim`/`SessionResult` em leitura.
- Migration de dados que cria os planos `anon`, `free` e `subscriber` e os dois exercícios existentes **com exatamente os valores de hoje** — ligar a spec não muda comportamento nenhum.
- `capabilities_for()` + cache com invalidação, e o `POST /api/sessions` passando a resolver duração, countdown, cloud e quota por ele (com os defaults do código como piso).
- `GET /api/config` e o cliente consumindo catálogo e capacidades.
- `session.started` ganha `config_version` (campo opcional, default `0` — aditivo, nenhum consumidor atual quebra); o relatório da SPEC-010 passa a registrar sob qual versão a sessão rodou.

### Fora de escopo (vai para Evolução)

Checkout e webhook de pagamento (o plano é atribuído à mão no painel); snapshot de config para workers (feedback continua em YAML); perfis de limiar; rollout gradual/A-B; i18n; painel multi-tenant.

### Critérios de aceite

1. Mudar `daily_sessions` do plano no painel muda a recusa do `POST /api/sessions` **sem restart** de nenhum serviço.
2. Com Postgres e Redis inacessíveis para leitura de config, a sessão ainda nasce, com os valores de hoje (teste que derruba a leitura de propósito).
3. `Exercise` com `enabled=false` some do `GET /api/config` e o `POST /api/sessions` com aquele slug recusa com mensagem clara.
4. Salvar `Exercise` com slug fora de `EXERCISES` falha com `ValidationError` no próprio formulário.
5. O admin **não** responde no processo do gateway, nem com `DJANGO_ENABLE_ADMIN=1`.
6. Conta comum autenticada não entra no painel; `is_admin` (diagnóstico) não concede painel; só `is_staff` concede.
7. Toda alteração fica registrada com autor e data, e é consultável no próprio painel.
8. Um relatório permite dizer sob qual `config_version` a sessão foi produzida.
9. A suíte inteira (`pytest`, `npm run test`) passa com o banco de configuração vazio — ou seja, nenhum teste passou a depender de linha em tabela.

## Fase Evolução

- **Snapshot de config para workers**: catálogo de feedback e throttles editáveis, via `df:config:*` com versão e fallback em YAML.
- **Perfis de limiar versionados**: se um dia limiar de FSM precisar variar (por exercício, por população), ele entra como `ThresholdProfile` versionado, carimbado no `session.started` e gravado no `SessionResult` — e a bancada da SPEC-012 passa a avaliar por perfil. Nunca como campo solto no painel.
- **Rollout gradual e A/B**: capacidade liberada para X% dos usuários, ou por coorte; exige `config_version` já estar no evento (é por isso que ele entra na Fase Inicial).
- **Pagamento**: webhook do Stripe/Mercado Pago escreve `User.plan`/`plan_until`; o painel vira leitura para esses campos e a fonte passa a ser o provedor.
- **Agendamento e preview**: "este limite passa a valer domingo"; diff entre versões de configuração.
- **i18n**: catálogos com idioma (`FeedbackMessage.lang`, `Exercise` traduzível).
- **Painel professor/academia** (SPEC-011 Evolução): deixa de ser admin do Django e vira produto, com tenancy. O admin continua sendo a ferramenta do operador da plataforma, não do cliente da plataforma.

## Eventos (consome / produz)

Não participa do hot path e **não publica eventos ao editar configuração** — mudança de config não é fato do domínio de treino, e um `config.changed` no `events.analysis` faria os consumidores lidarem com algo que não é sessão.

Produz (alteração aditiva no contrato): `session.started` ganha `config_version: int = 0`. Mexer em `workers/shared/events.py` primeiro, como manda o AGENTS.md.

## Notas técnicas

**O que ligar o admin custa** (nada disso existe hoje — ver ADR-011):

- `INSTALLED_APPS`: `django.contrib.admin`, `django.contrib.sessions`, `django.contrib.messages`. `staticfiles` já está.
- `MIDDLEWARE`: `SessionMiddleware`, `AuthenticationMiddleware`, `MessageMiddleware`, `CsrfViewMiddleware`.
- `TEMPLATES.OPTIONS.context_processors` está **vazio** (`settings.py:70`) e o admin exige `auth` e `messages` ali — sem eles o check `admin.E402/E403` recusa subir.
- `User` (`AbstractBaseUser` sem `PermissionsMixin`, por decisão em `models.py:64`): adicionar campo `is_staff` e métodos `has_perm`/`has_module_perms` retornando `is_staff`. Assim o `ModelBackend` nunca é consultado e as tabelas de permissão continuam mortas — sem `PermissionsMixin`, sem grupos. Trocar por `PermissionsMixin` só no dia em que mais de uma pessoa operar o painel com níveis diferentes.
- **`is_staff` novo em vez de reusar `is_admin`**: o docstring de `is_admin` promete, em produção, que a flag "não dá acesso a dado de ninguém" (`models.py:78`). Contas que já a têm foram concedidas sob essa promessa; transformá-la em acesso ao painel a quebraria retroativamente, sem ninguém revisar quem tem.
- **Estáticos**: sem whitenoise e sem nginx servindo `STATIC_ROOT`, o painel sobe sem CSS em produção. Ou entra `collectstatic` + rota no nginx, ou entra whitenoise no serviço `api`.
- **`ROOT_URLCONF` é compartilhado** entre `api` (WSGI) e `gateway` (ASGI, `core/asgi.py`): sem gate por variável de ambiente, o painel fica exposto também no processo de WebSocket. Critério de aceite 5.
- **Cookies**: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE="Lax"` e `CSRF_TRUSTED_ORIGINS` para o domínio do painel — o login do admin é o primeiro cookie de sessão do projeto, que até aqui era JWT e só JWT (`settings.py:127`).
- **Exposição**: caminho diferente de `/admin`, HTTPS obrigatório e, de preferência, restrição por IP ou basic-auth no nginx. É a URL que todo scanner tenta primeiro.

**Sobre o limite do admin.** Ele não sabe que uma edição tem consequência: nada nele impede salvar `daily_sessions = 0` às 3 h da manhã e desligar o produto para todo mundo. Isso se compra com `clean()` nos modelos (faixas plausíveis, plano default sempre existente, pelo menos um exercício habilitado) e com o princípio P2. Validação de consequência é parte do escopo desta spec, não polimento posterior.
