# SPEC-025 — Internacionalização (pt-BR + en)
Status: approved | Camada: transversal | Depende de: SPEC-008, SPEC-011, SPEC-013, SPEC-018 | Referência: `docs/PLANO-I18N.md` (2026-08-18)

## Entidade e responsabilidade

A entidade é o **idioma de quem usa o app** — `pt-BR` e `en`, na Fase Inicial. Hoje o produto
nasce brasileiro: todo texto que o cliente lê está em português. Esta spec não cria uma feature
de produto; ela cria a garantia de que **todo texto novo que o cliente lê nasce nas duas
línguas por construção** — por gate que já é obrigatório, não por disciplina de quem lembra.

O texto não mora num lugar só. Mora em **cinco**, cada um com dono, ciclo de vida e caminho de
entrega diferentes — tratá-los como se fossem um é o erro que deixaria metade do app em inglês
e a outra metade em português sem ninguém perceber (plano §1):

| # | Fonte | Onde | Como chega ao cliente | Quem edita |
|---|---|---|---|---|
| 1 | Bundle do cliente | `web/src/**/*.tsx,ts` (~280 frases + ~30 rótulos de acessibilidade: `aria-label`, `alt`, `title`, `placeholder`) | compilado no JS | dev, com deploy |
| 2 | Catálogo de feedback | `workers/analysis_worker/feedback/catalog.pt-BR.yaml` (15 códigos × `message` + `hint`) | `feedback.issued` no WebSocket **e** `GET /api/config` | dev, sem deploy de código |
| 3 | Banco (painel) | `Exercise` (`display_name`, `muscle_group`, `default_tip`, `scene_tip`), `ExerciseGuideStep.texto`, `Plan` (`nome`, `quota_message`) | `GET /api/config` | Daniel, no painel |
| 4 | Código do servidor | `ACHIEVEMENTS` (`server/api/engagement.py`, 7 × nome+descrição); `detail` de erro em `auth.py`/`sessions.py` (~20) | `GET /api/engagement` e corpos de erro 4xx | dev, com deploy |
| 5 | HTML de shell | `web/index.html`, `web/app/index.html` (`<title>`, `<meta description>`, `lang`) | o próprio HTML — e o Google lê | dev, com deploy |

Duas coisas ficam de fora por definição, não por esquecimento:

- **O painel admin continua em pt-BR.** É ferramenta de operação do Daniel, não superfície do
  cliente; `USE_I18N = False` no Django fica como está.
- **O que já é código não vira texto.** Slug de categoria, `Code` do feedback,
  `SessionEndReason`, slug de conquista continuam em inglês no fio — é *vocabulário de
  contrato*, a mesma separação que já existe no projeto (`Category` guarda `forca`, não
  `"Força"`), e é ela que torna a tradução possível: **o código é a chave, a frase é o valor.**

## Fase Inicial

### Escopo / Comportamento

- **`pt-BR` (fonte) e `en`.** Duas línguas agora; a terceira não muda a arquitetura — é um
  diretório e um YAML a mais. É o teste de que o desenho está certo.

- **Negociação de locale em três pontas — cliente, API, HTML** (plano §3.3, §3.4):
  - **Cliente** (`resolveLocale()`): `localStorage['digitalfit.locale']` (escolha explícita,
    vence sempre) → `navigator.languages` (primeiro que casar por prefixo: `pt*` → `pt-BR`,
    `en*` → `en`) → `'en'` (fallback global). Mesma casa e mesmo motivo das outras preferências
    do aparelho (`digitalfit.countdown_s`, `digitalfit.exercise`): fica no aparelho, não exige
    conta — treinar sem conta é garantia da SPEC-011. O fallback é `en`, não `pt-BR`, de
    propósito: navegador brasileiro já cai na primeira regra; `en` é a resposta certa para "não
    sei quem é você". **Rejeitado**: GeoIP para decidir idioma — o navegador entrega idioma, não
    país, e é o idioma que decide a língua (quem mora fora e fala português deve receber
    português). Região é assunto de moeda e de fuso, não desta spec (ver Fora de escopo).
  - **API** (`server/api/i18n.py`, `resolve_locale(request)`): `?locale=` (override explícito) >
    header `Accept-Language` > `en`. O cliente manda `Accept-Language` com o locale **já
    resolvido** (não o do navegador) em todo `fetch` — é header safelisted de CORS, não gera
    preflight, mas `core/cors.py` precisa aceitá-lo na lista de permitidos. Resolve de uma vez
    `GET /api/config`, `GET /api/engagement` e os `detail` de erro 4xx, sem rota nova e sem
    parâmetro por chamada.
  - **HTML**: `<html lang>` escrito em runtime no app (segue a preferência); estático por entry
    point no site (item seguinte).

- **Site por URL, app por preferência** (plano §3.5):

  | | URL | `lang` | Como escolhe | Indexado |
  |---|---|---|---|---|
  | site | `/` = pt-BR · `/en/` = en | estático no HTML | a URL | sim, com `hreflang` recíproco |
  | app | `/app/` único | escrito em runtime | preferência → navegador | não (`noindex`) |

  Divergência de propósito, escrita para não parecer inconsistência: redirecionar `/` por
  `navigator.language` seria bom para a pessoa e péssimo para o Google, que rastreia dos EUA e
  só veria a versão inglesa. **Rejeitado**: unificar as duas regras — o site precisa de URL
  própria por idioma para SEO; o app precisa de preferência porque não é indexado e reload por
  navegação penalizaria quem já treina. As duas URLs existem, se apontam por `hreflang`, e um
  aviso discreto sugere a outra. O Vite já tem dois entry points (`index.html`, `app/index.html`);
  um terceiro (`en/index.html`) é uma linha em `rollupOptions.input`.

- **Dicionário tipado no cliente, sem biblioteca** (plano §3.1, §3.2). **Rejeitado**: `i18next` +
  `react-i18next` — custam ~50 KB minificados; o projeto tem quatro dependências de runtime e
  mede gzip de `.wasm` no nginx, e a conta não fecha por um `t()` e uma interpolação.
  `web/src/i18n/` (~2 KB): `index.ts` (`t()`, `useT()`, locale ativo, interpolação, plural),
  `locale.ts` (detecção/normalização/persistência), `format.ts` (data/hora/número via `Intl`, no
  locale ativo), `store.ts` (zustand, no padrão de `store/config.ts`), e `dict/{pt-BR,en}/` com
  **um arquivo por namespace** (nove: `shell`, `site`, `funnel`, `session`, `report`, `progress`,
  `account`, `catalog`, `errors`) — não é estética, é o que permite a Onda 2 do backlog rodar em
  paralelo sem colidir num `pt-BR.json` único. O tipo do dicionário sai do **pt-BR** (a fonte); o
  `en` é tipado por ele — chave faltando, sobrando ou renomeada de um lado só é **erro de
  compilação** (`tsc -b`, já gate do AGENTS.md, cobrado de graça pelo portão que já existe).
  `t('namespace:chave')` com namespace explícito; interpolação `{n}`; plural por sufixo
  `.one`/`.other` resolvido com `Intl.PluralRules`.

- **Tabela de tradução no banco** (plano §3.6). As colunas que já existem em `Exercise`, `Plan`
  e `ExerciseGuideStep` **são** o pt-BR — nada de migrar dado existente. Uma tabela (ou três
  pequenas e explícitas — decisão fina de implementação; a regra é a mesma nos dois casos) guarda
  só os **outros** idiomas, por `locale` + FK exclusiva + campo. Faltou tradução → cai na coluna
  base; nunca em branco, nunca em chave crua. **Rejeitado**: `JSONField` `{"pt-BR": ...,
  "en": ...}` numa coluna só — o próprio docstring de `Plan` já registrou a posição do projeto
  ("colunas tipadas e não chave-valor... este projeto está do lado da validação"), e um `JSONField`
  contradiria isso e ainda mataria a validação do formulário do painel. É estado novo persistido,
  e a justificativa é a exigida pela casa: texto traduzido é fato **não-derivável** — alguém
  precisa escrevê-lo, não há como computá-lo a partir do que já existe. No painel:
  `TabularInline` ao lado do `ExerciseGuideStep`, uma linha por idioma. `manage.py i18n_status`
  lista exercício habilitado sem tradução — mesma doutrina do `exercise_health`: buraco de
  conteúdo é visível, nunca silencioso.

- **YAML por idioma no servidor e no worker** (plano §3.7). O padrão já existe e já está certo
  (`catalog.pt-BR.yaml`, cabeçalho "um arquivo por idioma") — só estende:
  `workers/analysis_worker/feedback/catalog.en.yaml` (novo, ao lado do que existe);
  `server/api/i18n/messages.{pt-BR,en}.yaml` (novo — conquistas + `detail` de erro).
  `ACHIEVEMENTS` fica só com slug e predicado; nome e descrição saem para o YAML, resolvidos na
  serialização. `pytest` cobra paridade de chaves entre idiomas e cobertura total do enum `Code`
  (`FeedbackCatalog.missing()` já faz metade disso; falta rodar por idioma).

### Fora de escopo (vai para Evolução)

- **Painel admin continua em pt-BR.** Ferramenta de operação do Daniel, não superfície do
  cliente — traduzir `verbose_name` de model seria trabalho grande a serviço de ninguém.
- **Fuso horário.** `FUSO_DO_FOGO` fixo em São Paulo decide a virada do dia do streak, da meta
  diária e do TTL do cache — quem treina às 22h em Lisboa cai no dia errado. Não é idioma: é o
  mesmo objetivo ("não se restringir a um país") por outro eixo, e sai como task própria
  (T-156), fora desta frente, para não a inchar (plano §2.5).
- **Moeda / pagamento.** Região importa para moeda (PIX é só Brasil) e para fuso — não para
  idioma. GeoIP acertaria o país e erraria a pessoa (e erraria de novo com VPN); quem decide a
  língua é o idioma do navegador, não a localização (plano §3.3).
- **Terceiro idioma.** A arquitetura já suporta — é a garantia da spec, não a entrega dela.
  Entra quando houver motivo de produto para entrar.

### Critérios de aceite

1. Navegador em `en-US` abre `/app/` e **nada** aparece em português — incluindo o card do
   treinador durante uma sessão de verdade, o relatório do fim e as conquistas.
2. Trocar o idioma nas configurações muda a tela **e** o que vem do servidor na mesma ação, sem
   recarregar e sem esperar cache expirar.
3. `/` e `/en/` existem, se apontam por `hreflang`, e cada uma tem `title`/`description` na
   própria língua.
4. Um exercício novo cadastrado no painel sem tradução aparece em português para o inglês
   (fallback honesto) **e** sai listado no `i18n_status`.
5. Um `git commit` que acrescenta uma frase em português e esquece o inglês **não passa nos
   gates que já existem** — sem ninguém precisar lembrar de conferir.

Os quatro primeiros valem uma vez; o quinto é o produto real deste plano — ele vale para sempre.

## Fase Evolução

- `code` estável nos corpos de erro 4xx, para o cliente localizar a mensagem sozinho pelo
  próprio catálogo, em vez de depender do `detail` já traduzido pelo servidor (T-145). Mesmo
  princípio do §Eventos desta spec aplicado a mais uma superfície: o código é o contrato, quem
  resolve o texto é quem lê.
- Terceiro idioma — arquitetura já pronta (§Escopo); falta o motivo de produto.
- Tradução de conteúdo assistida no painel: sugestão automática ao cadastrar/editar
  `Exercise`/`Plan`/`GuideStep`, com revisão humana antes de publicar. Extensão natural da
  tabela de tradução da Fase Inicial (§3.6 do plano) — não é gate, é atalho para Daniel
  preencher menos campo à mão.

## Eventos (consome / produz)

**Nenhum evento novo.** Uma mudança de **contrato de leitura**, decidida aqui (plano §2.4):

`feedback.issued` carrega hoje um `message` já resolvido pelo catálogo do worker, e
`coachCard.textOf()` no cliente é `entry.message ?? textForCode(entry.code)` — a frase do fio
vence. **Rejeitado**: levar o idioma até o worker (cliente → `POST /sessions` → estado da sessão
no Redis → worker) — três camadas de encanamento para um problema que o cliente já resolve
sozinho, porque ele recebe o dicionário completo no `GET /api/config`, na sua língua, e o `code`
já é o contrato.

**Decisão**: a prioridade se inverte. O catálogo local do cliente (resolvido pelo `code`) passa
a valer sobre o `message` do evento; o `message` passa a ser diagnóstico/legado. O campo
**continua existindo** no evento — não é removido, não é renomeado — e por isso a mudança é
**aditiva-compatível**: nenhum produtor ou consumidor existente quebra, e `PROTOCOL_VERSION`
**não sobe**.

`feedback.issued.message` deixa de ser autoridade de texto. O `code` é que é.

A nota correspondente no docstring de `FeedbackIssued` (`workers/shared/events.py`) — mudança de
contrato de leitura documentada no código, regra do AGENTS.md — é responsabilidade da T-144, que
implementa a inversão; esta spec registra a decisão, não o código.

## Notas técnicas

Três armadilhas achadas no mapeamento (plano §2.1–§2.3). Nenhuma delas aparece como erro — todas
aparecem como "às vezes o app está na língua errada". Viram critério de aceite da T-143:

- **O ETag do `GET /api/config` não conhece idioma.** `config_etag()` hoje é `(config_version,
  plan_slug, is_admin)`, e a view manda `Vary: Authorization`. O payload passa a variar por
  idioma e o ETag não saberia: o navegador revalidaria com `If-None-Match`, receberia `304`, e
  continuaria mostrando o catálogo em português depois de trocar para inglês — o mesmo bug que o
  próprio `config_etag` já documenta para planos, agora numa dimensão nova. Precisa de locale
  **dentro** do ETag **e** `Accept-Language` **dentro** do `Vary`; uma sem a outra não resolve.
- **`_mensagens_de_feedback()` é `@lru_cache(maxsize=1)`.** Cache de tamanho 1, global de
  processo — o primeiro cliente a pedir define a língua de todo mundo até o processo reiniciar.
  Precisa virar cache **por locale**.
- **O cache de engajamento é por `(usuário, dia)`.** `engagement_cache.chave_de_cache(user_pk,
  dia_sp(...))` guarda o payload **já renderizado**, com nome e descrição de conquista dentro.
  Trocar de idioma não invalidaria nada — a pessoa veria as conquistas na língua da primeira
  visita do dia. O locale entra na chave.
