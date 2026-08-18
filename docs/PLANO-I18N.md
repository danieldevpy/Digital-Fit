# PLANO — Internacionalização (pt-BR + en)

Objetivo: o app deixa de nascer brasileiro. Ele detecta o idioma de quem abre, aplica sozinho,
deixa trocar nas configurações — e, daí em diante, **todo texto novo que o cliente lê nasce nas
duas línguas por construção**, não por disciplina de quem lembra.

Duas línguas agora: `pt-BR` (fonte) e `en`. A terceira não muda nada da arquitetura abaixo —
é um diretório e um arquivo YAML a mais. É esse o teste do plano.

---

## 1. O mapa — onde o texto mora hoje

Não existe um lugar. Existem **cinco**, e cada um tem dono, ciclo de vida e caminho de entrega
diferentes. Tratar os cinco como se fossem um é o erro que faria metade do app virar inglês e a
outra metade continuar em português sem ninguém ver.

| # | Fonte | Onde | Volume | Como chega ao cliente | Quem edita |
|---|---|---|---|---|---|
| 1 | **Bundle do cliente** | `web/src/**/*.tsx,ts` — 53 arquivos | ~280 frases + 30 rótulos de acessibilidade (`aria-label`, `alt`, `title`, `placeholder`) | compilado no JS | dev, com deploy |
| 2 | **Catálogo de feedback** | `workers/analysis_worker/feedback/catalog.pt-BR.yaml` | 15 códigos × (`message` + `hint`) | `feedback.issued` no WebSocket **e** `GET /api/config` | dev, sem deploy de código |
| 3 | **Banco (painel)** | `Exercise` (`display_name`, `muscle_group`, `default_tip`, `scene_tip`), `ExerciseGuideStep.texto`, `Plan` (`nome`, `quota_message`) | ~8 exercícios × 4 campos + passos de guia + planos | `GET /api/config` | Daniel, no painel |
| 4 | **Código do servidor** | `ACHIEVEMENTS` em `server/api/engagement.py` (7 × nome+descrição); `detail` de erro em `auth.py` e `sessions.py` (~20) | ~35 frases | `GET /api/engagement` e corpos de erro 4xx | dev, com deploy |
| 5 | **HTML de shell** | `web/index.html`, `web/app/index.html` | `<title>`, `<meta description>`, `lang="pt-BR"` | o próprio HTML — **e o Google lê** | dev, com deploy |

Duas coisas que **não** entram e é importante dizer em voz alta:

- **O painel admin continua em pt-BR.** É ferramenta de operação do Daniel, não superfície do
  cliente. `USE_I18N = False` no Django fica como está. Traduzir `verbose_name` de modelo seria
  trabalho grande a serviço de ninguém.
- **O que já é código não vira texto.** Slug de categoria, `Code` do feedback, `SessionEndReason`,
  slug de conquista — tudo isso é *vocabulário de contrato* e continua em inglês no fio. É a
  separação que já existe no projeto (`Category` guarda `forca`, não `"Força"`), e é ela que faz
  a tradução ser possível: **o código é a chave, a frase é o valor.**

---

## 2. As armadilhas — o que quebraria em silêncio

Estas são as descobertas do mapeamento. Cada uma vira critério de aceite de alguma task abaixo,
porque nenhuma delas aparece como erro: todas aparecem como "às vezes o app está na língua errada".

### 2.1 O ETag do `/api/config` não conhece idioma

`config_etag()` hoje é `(config_version, plan_slug, is_admin)` e a view manda
`Vary: Authorization`. O payload passa a variar por idioma **e o ETag não saberia** — o navegador
revalidaria com `If-None-Match`, receberia `304`, e continuaria mostrando o catálogo em português
depois de trocar para inglês. Pior: o comentário no próprio `config_etag` já explica que um ETag
incompleto vaza resposta entre planos; é exatamente o mesmo bug, com outra dimensão.

**Consequência**: locale entra no ETag **e** `Accept-Language` entra no `Vary`. Sem as duas, não
adianta uma.

### 2.2 `_mensagens_de_feedback()` é `@lru_cache(maxsize=1)`

Cache de tamanho 1, global de processo. O primeiro cliente a pedir define a língua de todo mundo
até o processo reiniciar. Precisa virar cache **por locale**.

### 2.3 O cache de engajamento é por `(usuário, dia)`

`engagement_cache.chave_de_cache(user_pk, dia_sp(...))` guarda o payload **já renderizado**, com
nome e descrição de conquista dentro. Trocar de idioma não invalidaria nada: a pessoa veria as
conquistas na língua da primeira visita do dia. O locale entra na chave.

### 2.4 O worker manda a frase pronta pelo fio

`feedback.issued` carrega `message` já resolvido pelo catálogo do worker. Levar o idioma até lá
significaria: cliente → `POST /sessions` → estado da sessão no Redis → worker. Três camadas de
encanamento para um problema que **o cliente já resolve sozinho**.

O `coachCard.textOf()` hoje é `entry.message ?? textForCode(entry.code)` — a frase do evento
vence. **Inverter essa prioridade** resolve o idioma inteiro sem tocar em nenhuma camada: o
cliente já recebe o dicionário completo no `GET /api/config`, na sua língua, e o `code` já é o
contrato. O `message` do fio passa a ser diagnóstico/legado, e o campo continua no evento (mudança
aditiva-compatível, sem bump de `PROTOCOL_VERSION`).

É a decisão de maior alavanca do plano inteiro: **um `??` invertido paga por três camadas de
plumbing.** Por ser mudança de contrato de leitura, tem de estar escrita no docstring de
`workers/shared/events.py` — regra do AGENTS.md.

### 2.5 O fogo tem fuso fixo em São Paulo

`FUSO_DO_FOGO = ZoneInfo("America/Sao_Paulo")` decide a virada do dia para o streak, para a meta
diária e para o TTL do cache. Quem treinar às 22h em Lisboa tem a sessão contada no dia seguinte;
quem treinar às 21h em Nova York, no dia anterior. **Não é i18n** — é o mesmo objetivo ("não se
restringir a um país") por outro eixo, e sai como task própria (T-156) para não inchar esta frente.

### 2.6 Data e número já estão presos ao Brasil

`toLocaleDateString('pt-BR')` literal em `accountSummary.ts` (3×) e `ProgressScreen.tsx` (3×), e
`DIAS_DA_SEMANA = ['S','T','Q','Q','S','S','D']` montado à mão. Entram nas tasks de migração, via
formatadores que leem o locale ativo.

### 2.7 Plural feito na unha

`engagement/format.ts` decide `"1 dia seguido"` × `"N dias seguidos"` com `if`. Português e inglês
concordam nessa regra, mas a terceira língua não vai concordar. O runtime já nasce com
`Intl.PluralRules`, e a chave vira `{ one, other }`.

### 2.8 SEO: site e app não seguem a mesma regra

O app é `noindex` — a URL dele não importa, a preferência manda. O **site** é indexado, e um
buscador que rastreia dos EUA precisa achar a versão inglesa por URL própria, não por
`navigator.language`. Regras diferentes de propósito (§3.5).

---

## 3. As decisões de arquitetura

### 3.1 Cliente: dicionário próprio, sem biblioteca

`i18next` + `react-i18next` custa ~50 KB minificado. Este projeto tem **quatro** dependências de
runtime e mede gzip de `.wasm` no nginx — a conta não fecha por um `t()` e uma interpolação.

`web/src/i18n/` com ~2 KB:

```
web/src/i18n/
  index.ts          # t(), useT(), locale ativo, interpolação, plural
  locale.ts         # detecção, normalização, persistência (função pura + storage)
  format.ts         # data, hora, número, percentual — via Intl, no locale ativo
  store.ts          # zustand, no mesmo padrão de store/config.ts
  dict/
    pt-BR/{shell,site,funnel,session,report,progress,account,catalog,errors}.ts
    en/   {shell,site,funnel,session,report,progress,account,catalog,errors}.ts
```

**Dicionário em `.ts`, não em `.json`** — e é isto que faz o plano inteiro se sustentar:

```ts
// dict/pt-BR/session.ts
export const session = {
  'start.button': 'Iniciar Exercício',
  'start.opening': 'Abrindo câmera…',
  'stats.reps': 'Repetições',
  'report.reps.one': '{n} repetição',
  'report.reps.other': '{n} repetições',
} as const

// dict/en/session.ts
import type { Session } from '../pt-BR/session'
export const session: Session = { /* mesmas chaves, obrigatoriamente */ }
```

O tipo sai do **pt-BR** (a fonte) e o `en` é tipado por ele. Chave que falta no inglês, chave a
mais no inglês, chave renomeada de um lado só: **erro de compilação**. `npm run typecheck` já é
gate obrigatório do AGENTS.md — a paridade dos dicionários passa a ser cobrada de graça, pelo
portão que já existe, no dia em que o texto é escrito.

`t('session:start.button')` com namespace explícito; interpolação `{n}`; plural por sufixo
`.one`/`.other` resolvido com `Intl.PluralRules`.

### 3.2 Um arquivo por namespace, e o namespace espelha a tela

Nove namespaces: `shell`, `site`, `funnel`, `session`, `report`, `progress`, `account`, `catalog`,
`errors`.

Não é organização estética: é **o que permite a Onda 2 rodar em paralelo**. Seis tasks de migração
mexendo num `pt-BR.json` único colidiriam a cada commit. Com um arquivo por namespace, cada task
tem seu par de arquivos e seu conjunto de componentes — zero sobreposição.

### 3.3 Como o idioma é escolhido

```
resolveLocale():
  1. localStorage['digitalfit.locale']   → escolha explícita, vence sempre
  2. navigator.languages                 → primeiro que casar por prefixo (pt* → pt-BR, en* → en)
  3. 'en'                                → fallback global
```

Mesma casa e mesmo motivo das outras preferências (`digitalfit.countdown_s`,
`digitalfit.exercise`): fica no aparelho, não exige conta — a SPEC-011 garante treinar sem conta,
e uma preferência que só funciona depois de cadastrar seria uma punição por não se cadastrar.

**Sobre "identificador de região":** o navegador entrega *idioma*, não país, e é o idioma que
decide a língua — quem mora em Miami e fala português deve receber português. GeoIP acertaria o
país e erraria a pessoa (e erraria de novo com VPN). Região importa para **moeda** (Bloco D, PIX é
só Brasil) e **fuso** (§2.5); nenhum dos dois é este plano.

O fallback é `en` e não `pt-BR` de propósito: navegador brasileiro manda `pt-BR` e cai na primeira
regra. `en` é a resposta certa para *"não sei quem é você"*.

### 3.4 Servidor: negociação por `Accept-Language`

`server/api/i18n.py`: `resolve_locale(request)` = `?locale=` (override explícito) > header
`Accept-Language` > `en`. O cliente passa a mandar `Accept-Language` com o locale **resolvido**
(não o do navegador) em todo `fetch` — é header safelisted de CORS, não gera preflight, mas
`core/cors.py` precisa aceitá-lo na lista de permitidos.

Isso resolve, de uma vez, `GET /api/config`, `GET /api/engagement` e os `detail` de erro — sem
rota nova e sem parâmetro em cada chamada.

### 3.5 Site por URL, app por preferência

| | URL | `lang` | Como escolhe | Indexado |
|---|---|---|---|---|
| **site** | `/` = pt-BR · `/en/` = en | estático no HTML | a URL | sim, com `hreflang` recíproco |
| **app** | `/app/` único | escrito em runtime | preferência → navegador | não (`noindex`) |

O Vite já tem dois entry points; um terceiro (`en/index.html`) é uma linha no `rollupOptions.input`.
Redirecionar `/` por `navigator.language` seria bom para a pessoa e péssimo para o Google, que
rastreia dos EUA e veria só a versão inglesa: as duas URLs existem, se apontam por `hreflang`, e um
aviso discreto sugere a outra.

### 3.6 Banco: tabela de tradução, não coluna JSON

Três caminhos, e o projeto já rejeitou dois deles por escrito. O docstring de `Plan` diz: *"Colunas
tipadas e não chave-valor... este projeto está do lado da validação em todas as decisões
anteriores. O preço — uma migration por capacidade nova — é exatamente o momento em que alguém
deveria pensar no que está criando."* Uma coluna `JSONField` com `{"pt-BR": ..., "en": ...}`
contradiria isso e ainda mataria a validação do formulário do painel.

Então:

```python
class Translation(models.Model):
    """Tradução de conteúdo do painel. As colunas do modelo base SÃO o pt-BR."""
    locale  = models.CharField(max_length=8)          # 'en'
    # FK para exatamente um dos três, com constraint de exclusividade
    exercise / plan / guide_step
    campo   = models.CharField(...)                   # 'display_name', 'quota_message', ...
    texto   = models.TextField()
```

Ou três tabelas pequenas e explícitas (`ExerciseTranslation`, `PlanTranslation`,
`GuideStepTranslation`) — decisão fina para a spec resolver; a **regra** é a mesma nos dois casos:

- **As colunas que já existem são a tradução pt-BR.** Nada de migrar dado existente.
- A tabela guarda só os **outros** idiomas.
- Faltou tradução → cai na coluna base. Nunca cai em branco, nunca cai em chave crua.
- No painel: `TabularInline` ao lado do `ExerciseGuideStep`, uma linha por idioma.
- Comando `manage.py i18n_status` lista exercício habilitado sem tradução — mesma ideia do
  `exercise_health`: **buraco de conteúdo tem de ser visível, não silencioso.**

### 3.7 Texto do servidor sai do código e vai para YAML por idioma

O padrão já existe e já está certo: `catalog.<locale>.yaml`, e o cabeçalho do arquivo até diz
*"Um arquivo por idioma"*. Estender para o resto:

```
workers/analysis_worker/feedback/catalog.pt-BR.yaml   # existe
workers/analysis_worker/feedback/catalog.en.yaml      # novo
server/api/i18n/messages.pt-BR.yaml                   # conquistas + detail de erro
server/api/i18n/messages.en.yaml
```

`ACHIEVEMENTS` fica só com slug e predicado — nome e descrição saem para o YAML, resolvidos na
serialização. `pytest` cobra paridade de chaves entre idiomas e cobertura total do enum `Code`
(o `FeedbackCatalog.missing()` já faz metade disso; falta rodar por idioma).

---

## 4. Como um texto novo entra — o requisito "continuamente"

Este é o item que o plano existe para garantir. Não é processo escrito num documento que alguém
lê uma vez: são **quatro portões, todos pendurados em gates que já são obrigatórios**, mais duas
linhas de processo.

**A receita, para quem for escrever a próxima tela:**

1. Escreveu uma frase que o cliente lê → põe a chave no `dict/pt-BR/<namespace>.ts`.
2. `npm run typecheck` reprova até a mesma chave existir no `dict/en/<namespace>.ts`.
3. Usa `t('namespace:chave')` no componente. `npm run lint` reprova string literal em JSX.
4. Se o texto for de conteúdo (exercício, plano, conquista, feedback), ele **não** vai para o
   dicionário: vai para o painel ou para o YAML — e o `i18n_status` / `pytest` cobram o par.

**Os portões:**

| Portão | Onde | Pega | Já é gate? |
|---|---|---|---|
| Tipo derivado do pt-BR | `tsc -b` | chave faltando/sobrando entre os dois dicionários | **sim**, AGENTS §4 |
| `no-literal-strings` | `eslint` | string nova solta em JSX, `aria-label`, `alt`, `title`, `placeholder` | **sim**, AGENTS §4 |
| Paridade de YAML + cobertura do enum `Code` | `pytest` | idioma sem entrada, código sem mensagem | **sim**, AGENTS §4 e CI |
| `manage.py i18n_status` | operação | exercício/plano habilitado sem tradução | não (é conteúdo, não bloqueia deploy — mas aparece) |

**Sobre o ESLint, um detalhe que evita virar muro:** ligar `no-literal-strings` no repositório todo
de uma vez produziria ~280 erros e travaria toda a Onda 2. A regra entra **por diretório**, via
`files:` no `eslint.config.js`: cada task de migração liga a regra **para a pasta que ela acabou de
migrar**. O portão nunca é mentira e nunca é parede. A T-154 só remove os overrides e liga global.

**As duas linhas de processo** (T-154): uma regra nova no `AGENTS.md` §Fluxo, e um item na checklist
das skills `df-executor` e `df-spec` — *"texto que o cliente lê entra nas duas línguas na mesma
task; texto de conteúdo entra no painel/YAML"*.

---

## 5. As tasks

Numeração a partir de **T-141** (T-140 é a última do backlog). Spec nova: **SPEC-025**.

```
                      ┌──────────────────────────────────────────┐
 Onda 0               │  T-141  SPEC-025 — o contrato            │
                      └────┬────┬────┬────┬─────────────────────┘
                           │    │    │    │
              ┌────────────┘    │    │    └────────────┐
 Onda 1       │        ┌────────┘    └───────┐         │
         ┌────▼────┐ ┌─▼───────┐ ┌───────────▼─┐ ┌─────▼──────┐
         │  T-142  │ │  T-143  │ │    T-144    │ │   T-145    │   ┌──────────┐
         │ runtime │ │servidor │ │ feedback yml│ │ msgs yaml  │   │  T-146   │
         │ cliente │ │ locale  │ │  + inversão │ │ conquistas │   │  banco   │
         └────┬────┘ └────┬────┘ └─────────────┘ └────────────┘   └────┬─────┘
              │           │                                            │
 Onda 2  ┌────┴───┬───────┼────────┬─────────┬─────────┐               │
      ┌──▼──┐ ┌───▼─┐ ┌───▼──┐ ┌───▼──┐ ┌────▼──┐ ┌────▼───┐           │
      │T-147│ │T-148│ │T-149 │ │T-150 │ │ T-151 │ │ T-152  │           │
      │site │ │funil│ │sessão│ │report│ │ conta │ │catálogo│           │
      └──┬──┘ └──┬──┘ └───┬──┘ └───┬──┘ └────┬──┘ └────┬───┘           │
         └───────┴────────┴────────┴─────────┴─────────┴───────────────┘
                                     │
 Onda 3              ┌───────────────┼───────────────┐
                ┌────▼────┐    ┌─────▼────┐    ┌─────▼────┐
                │  T-153  │    │  T-154   │    │  T-155   │
                │ seletor │    │ portões  │    │ revisão  │
                └─────────┘    └──────────┘    └──────────┘

 Paralelo, independente:  T-156  fuso por usuário (descoberta §2.5)
```

### Onda 0 — o contrato (sequencial, bloqueia tudo)

| ID | Task | Spec | Tam |
|---|---|---|---|
| T-141 | **SPEC-025 — Internacionalização.** Vocabulário de locale (`pt-BR`, `en`, normalização, fallback); a regra de negociação nas três pontas (cliente, API, HTML); onde cada uma das cinco fontes de texto passa a morar; a inversão de prioridade do `coachCard` declarada como decisão de contrato, com a nota correspondente em `workers/shared/events.py`; a forma da tabela de tradução; a regra do texto novo (§4) como critério de aceite permanente. Fora de escopo explícito: painel admin, fuso, moeda | 025 | M |

### Onda 1 — fundações (4 raias em paralelo; só dependem da T-141)

| ID | Task | Spec | Tam |
|---|---|---|---|
| T-142 | **Runtime i18n do cliente.** `web/src/i18n/` completo: `t()` com namespace e interpolação, plural por `Intl.PluralRules`, formatadores de data/hora/número, detecção + persistência (`digitalfit.locale`), store, `<html lang>` escrito em runtime. Entrega migrando **um** namespace piloto (`shell`: TabBar, nav, AppShell) para provar o caminho ponta a ponta — e ligando o `no-literal-strings` só nessa pasta. **Não migra o resto.** Tipo do `en` derivado do `pt-BR` desde o primeiro commit | 025/013 | G |
| T-143 | **Negociação de locale no servidor.** `resolve_locale(request)`; `Accept-Language` no wrapper de `fetch` do cliente e na lista do `core/cors.py`; `Vary: Accept-Language` nas rotas afetadas; **locale dentro do `config_etag`** (§2.1); `_mensagens_de_feedback()` com cache por locale (§2.2); locale na chave do cache de engajamento (§2.3). Teste que prova os três caches: mesma conta, dois idiomas, duas respostas | 025/018/011 | M |
| T-144 | **Feedback por idioma.** `catalog.en.yaml`; `FeedbackCatalog.load(locale)`; teste de paridade de chaves entre idiomas + cobertura de todo o enum `Code`; **inversão da prioridade** em `coachCard.textOf()` (catálogo local vence o `message` do fio), com o embutido de `CODE_MESSAGES` nas duas línguas e a nota no docstring de `events.py` | 025/008/002 | M |
| T-145 | **Texto do servidor em arquivo.** `server/api/i18n/messages.{pt-BR,en}.yaml`; `ACHIEVEMENTS` fica só com slug + predicado, nome e descrição resolvidos na serialização de `GET /api/engagement`; `detail` de erro localizados em `auth.py` e `sessions.py` (só os voltados ao cliente — `"corpo deve ser objeto JSON"` é para dev e fica); teste de paridade | 025/019/011 | M |
| T-146 | **Tradução do conteúdo do banco.** Modelo(s) de tradução (§3.6); colunas atuais permanecem sendo o pt-BR; `exercises_for()`/`config_payload()` resolvem por locale com fallback para a base; inline no painel; `manage.py i18n_status`. Integra com a T-143, mas não depende dela para ser escrita | 025/018/020 | G |

### Onda 2 — migração das telas (6 raias em paralelo; dependem da T-142)

Conjuntos de arquivos **disjuntos** e um par de dicionário por task — é isso que as torna
paralelas de verdade. Cada uma liga o `no-literal-strings` para sua própria pasta ao terminar.

| ID | Namespace | Arquivos | Tam |
|---|---|---|---|
| T-147 | `site` | `site/IndexScreen`, `AboutScreen`, `SiteBar`, `SiteApp`, `nav` **+ `index.html` por idioma, `en/index.html` no Vite, `hreflang` recíproco, `<title>`/`<meta description>` traduzidos** (§3.5) | M |
| T-148 | `funnel` | `screens/ChooseScreen`, `GuideScreen`, `ExerciseCards`, `ExerciseRails`, `funnel`, `ui/ViewPicker`, `ExerciseDemo`, `hud/ViewConfirm`, `ExercisePicker`, `session/guideGate`, `viewGate` | M |
| T-149 | `session` | `screens/SessionScreen`, `capture/CameraView`, `useCamera`, `useEdgePipeline`, `hud/*` (CoachTip, StatsBar, GetReady, TimerRing, CountdownSetting, ZoomControl), `session/startGate`, `pipelineGate`, `admission`, `useSession`, `scene/sceneQuality`, `pose/assetWarmup`, `probe/runProbe` | G |
| T-150 | `report` + `progress` | `report/ReportSheet`, `reportSummary`, `sessionReport`, `screens/ProgressScreen`, `AnalyticsScreen`, `history/aggregates`, `session/kcal` **+ troca dos `toLocaleDateString('pt-BR')` pelos formatadores (§2.6) e do `DIAS_DA_SEMANA` montado à mão** | G |
| T-151 | `account` + `errors` | `auth/AccountSheet`, `accountSummary`, `auth/api` (mensagens de rede/falha), `engagement/EngagementSheet`, `EngagementSection`, `FireChip`, `XpLine`, `AchievementGallery`, `AchievementToast`, `format` **+ plural via `Intl.PluralRules` (§2.7)** | G |
| T-152 | `catalog` | `session/catalog.ts` (o catálogo embutido — o fallback offline precisa existir nas duas línguas), `exerciseViews.ts`, `ui/exerciseFigures`, `categoryLabel`. Par com a T-146: o servidor manda o traduzido, o embutido é o que aparece sem rede | M |

### Onda 3 — fechar

| ID | Task | Dep | Tam |
|---|---|---|---|
| T-153 | **Seletor de idioma nas configurações.** Entra no Perfil (`AccountSheet`); troca sem reload; persiste em `digitalfit.locale`; **força revalidação do `GET /api/config` e do `GET /api/engagement`** ao trocar (senão o ETag/cache devolve a língua velha — §2.1/§2.3); reescreve `<html lang>`. No site, o mesmo controle navega entre `/` e `/en/` | T-142, T-143 | M |
| T-154 | **Os portões + o processo.** Regra ESLint `no-literal-strings` global (removendo os overrides por pasta); parity de tipos já garantida desde a T-142; teste de paridade dos YAML no CI; `i18n_status` no checklist de release; **`AGENTS.md` e as skills `df-executor`/`df-spec` ganham a regra do texto novo** (§4) | Onda 2 | P |
| T-155 | **Revisão de tradução e de layout.** Passada ponta a ponta nas duas línguas, nos dois entry points, em aparelho real: qualidade do inglês (tom de treinador, não tradução literal), estouro de layout nos cards e chips (`"Repetições"` → `"Reps"` muda a métrica visual), e o caminho novo do primeiro acesso com o navegador em inglês | Ondas 1–2 | M |

### Fora da frente, mesmo objetivo

| ID | Task | Origem | Tam |
|---|---|---|---|
| T-156 | **Fuso do fogo por usuário.** `FUSO_DO_FOGO` deixa de ser constante de São Paulo: a virada do dia (streak, meta diária, TTL do cache) passa a ser resolvida pelo fuso de quem treina, com o do aparelho como default. Descoberta §2.5 — não é idioma, é o mesmo *"não se restringir a um país"* pelo eixo do tempo, e ninguém percebe que está errado até o streak quebrar sozinho | §2.5 | M |

---

## 6. O caminho crítico

O que dita o prazo é a raia **T-141 → T-142 → (T-149 ‖ T-150 ‖ T-151) → T-154**: a spec, o runtime,
as três telas grandes e o fecho. Tudo o mais cabe em paralelo dentro dessa sombra:

- A Onda 1 inteira roda enquanto a T-142 é escrita — nenhuma das quatro toca o `web/src/i18n/`.
- As seis tasks da Onda 2 são disjuntas em arquivo **e** em dicionário. Com quatro raias, a onda
  toda cabe no tempo da mais lenta.
- A T-146 (banco) e a T-156 (fuso) não bloqueiam ninguém e podem começar em qualquer momento
  depois da T-141.

Ordem mínima segura, se for uma raia só: **T-141 · T-142 · T-143 · T-144 · T-152 · T-149 · T-150 ·
T-151 · T-148 · T-147 · T-145 · T-146 · T-153 · T-154 · T-155**.

---

## 7. Como se sabe que acabou

1. Navegador em `en-US` abre `/app/` e **nada** aparece em português — incluindo o card do
   treinador durante uma sessão de verdade, o relatório do fim e as conquistas.
2. Trocar o idioma nas configurações muda a tela **e** o que vem do servidor na mesma ação, sem
   recarregar e sem esperar cache expirar.
3. `/` e `/en/` existem, se apontam por `hreflang`, e cada uma tem `title`/`description` na própria
   língua.
4. Um exercício novo cadastrado no painel sem tradução aparece em português para o inglês (fallback
   honesto) **e** sai listado no `i18n_status`.
5. Um `git commit` que acrescenta uma frase em português e esquece o inglês **não passa nos gates
   que já existem** — sem ninguém precisar lembrar de conferir.

O item 5 é o produto real deste plano. Os outros quatro são de uma vez; ele é para sempre.
