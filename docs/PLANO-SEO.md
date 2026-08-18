# PLANO — Descoberta e idioma de acesso

Objetivo: o site deixa de ser invisível. Ele passa a ter conteúdo que um robô lê, URLs que um
buscador indexa, e uma resposta honesta para **qualquer** pessoa que chegue — fale ela uma das
duas línguas curadas ou nenhuma delas.

Duas metas, e é importante que sejam duas, porque têm custos e ritmos diferentes:

1. **Ser encontrável** — o Google, o Bing e os rastreadores de LLM precisam ver texto, achar URLs
   e saber qual versão mostrar para quem.
2. **Acertar o idioma de acesso** — qualquer estrangeiro usa `pt-BR` ou `en`, e traduz sozinho
   para a própria língua se quiser. É a prioridade declarada, e ela depende da meta 1 por um
   motivo que quase ninguém enxerga (§2.3).

Este plano é irmão do `PLANO-I18N.md` e **não o refaz**. A frente de i18n construiu a máquina de
conteúdo multilíngue (nove namespaces tipados, negociação por `Accept-Language`, o modelo
`Translation` no painel) e ela funciona. O que nunca existiu é a frente de descoberta.

---

## 1. O mapa — onde a descoberta acontece hoje

| Superfície | URLs indexáveis | HTML entregue | Indexado? |
|---|---|---|---|
| **site pt-BR** | `/` | `<div id="root"></div>` | tenta |
| **site en** | `/en/` | `<div id="root"></div>` | tenta |
| **site — Sobre** | *nenhuma* (`#/sobre` é fragmento) | — | não |
| **app** | `/app/` | `<div id="root"></div>` | não, e **está certo** |

O índice inteiro do produto são duas URLs, e as duas chegam vazias ao robô.

E a proporção que decide todas as escolhas abaixo: `web/src/` tem **203 arquivos e 22.516
linhas**; `site/` + `entries/` somam **466**. A superfície que precisa de SEO é **2%** do
frontend. Toda decisão deste plano é enviesada por esse número — nada aqui pode custar tocar nos
outros 98%.

---

## 2. As armadilhas — o que quebraria em silêncio

### 2.1 O `hreflang` que a T-147 escreveu está inerte

`web/index.html` e `web/en/index.html` declaram `href="/"` e `href="/en/"`. A especificação exige
URL **absoluta com esquema e host**; relativa é ignorada sem aviso. O par pt/en que a T-147
entregou, e que o `LocaleSwitch` do site respeita corretamente, **não existe para o Google hoje**.

O host não está no código de propósito (ADR-010: `VITE_SITE_URL` é decidida no build), então a
correção não é escrever o domínio no HTML — é injetá-lo no build, que é exatamente o que o
pré-render (§3.1) já vai fazer.

### 2.2 Não há `x-default`, e é ele que responde a pergunta deste plano

`x-default` é a anotação que diz ao buscador *"para quem não é nem pt nem en, mande para cá"*.
Sem ela, o Google decide sozinho — e a decisão dele para o domínio raiz costuma ser `/`, que é
português. **O francês que busca em francês cai na versão brasileira.**

O destino certo do `x-default` é `/en/`, pelo mesmo argumento que a T-142 já registrou em
`web/src/i18n/locale.ts` ao escolher `DEFAULT_LOCALE = 'en'`: *"`en` é a resposta certa para
'não sei quem é você'"*. As duas pontas passam a dizer a mesma coisa.

### 2.3 O pré-render é o que liga a tradução automática do navegador

Esta é a descoberta que reordena o plano.

O Chrome decide se oferece *"Traduzir esta página"* analisando o texto do HTML da **resposta**.
Hoje o `<body>` do site tem `<div id="root"></div>` e mais nada: não há texto para detectar
idioma, e a oferta não aparece de forma confiável.

Ou seja: o pré-render não é só a correção de SEO. **É a mesma correção que entrega a prioridade
declarada** — "traduzir automaticamente se ele quiser" é uma capacidade que o navegador já tem,
de graça, em ~130 línguas, e que o site atual desliga sem querer. Uma tarefa, dois problemas.

### 2.4 Tradução de navegador quebra React, e o HUD é onde dói

O Google Translate **embrulha cada nó de texto num `<font>`**. O React continua achando que
aquele nó é filho direto do elemento original, e na hora de remover ou trocar dá
`NotFoundError: Failed to execute 'removeChild' on 'Node'`. A tela morre.

No site é inofensivo — é estático e não re-renderiza. No `/app/` é onde mora o risco, porque o
HUD troca texto o tempo todo: `hud/StatsBar.tsx` redesenha `repCount` a cada repetição e alterna
`angulo` entre `'--'` e `'12°'`; `hud/CoachTip.tsx` troca a frase a cada `feedback.issued`.

Convidar a pessoa a traduzir sem tratar isto é convidá-la a travar a sessão no meio do treino.
A mitigação é `translate="no"` nas regiões voláteis — e ela cai bem: números e o card do
treinador são justamente onde tradução de máquina não deveria mexer.

### 2.5 O roteamento por hash não produz URL

`web/src/site/nav.ts` roteia por `#/sobre`. Fragmento não viaja no pedido HTTP — o servidor nunca
o vê, e o buscador trata `/#/sobre` e `/` como a mesma página. Enquanto o hash for o roteador, o
site tem no máximo uma URL por idioma, faça-se o que se fizer com metadados.

### 2.6 O `try_files` transforma erro em 200

`docker/web-nginx.conf` faz `try_files $uri $uri/ /index.html` — qualquer URL inexistente devolve
**200** com a home em português. É o *soft 404*, e o Google o trata como sinal de site de baixa
qualidade. Hoje quase não custa (não há URLs para errar); no dia em que existirem páginas por
exercício, custa muito.

### 2.7 `SiteApp` decide o idioma por igualdade, não por normalização

`web/src/site/SiteApp.tsx:22`: `document.documentElement.lang === 'en' ? 'en' : 'pt-BR'`. Com um
terceiro idioma curado, `/es/` cairia silenciosamente em português. `matchLocale()` já existe e já
faz isso certo. Uma linha hoje; um bug mudo depois.

### 2.8 `/en/index.html` não tem regra de cache

O nginx tem `location = /index.html` e `location = /app/index.html` com `no-cache`, e nada para
`/en/index.html`. O HTML inglês fica sujeito a cache heurístico do navegador — e é justamente o
arquivo que aponta para os assets com hash novo. Irmão exato do bug que as outras duas linhas
existem para evitar.

### 2.9 Não há `robots.txt`, `sitemap.xml`, `canonical` nem Open Graph

Sem sitemap, uma SPA quase sem links internos rastreáveis é descoberta a conta-gotas. Sem Open
Graph, compartilhar o link no WhatsApp — o canal real de crescimento no Brasil — mostra uma caixa
cinza sem título e sem imagem.

---

## 3. As decisões de arquitetura

### 3.1 Pré-render em tempo de build, no Vite — não SSR, não Next

O site precisa chegar com HTML pronto. Três caminhos, e dois se descartam com o número do §1.

**Por que não Next** (a pergunta que alguém refaz em seis meses):

- A superfície que precisa de SEO é 2% do frontend. Migrar a base de build dos 98% para atender
  os 2% é a troca errada por definição.
- Os 98% não querem Next: o `/app/` é câmera + MediaPipe WASM de 11 MB + WebSocket com msgpack +
  máquina de estados por frame. No App Router isso vira **uma ilha `'use client'` gigante**, e
  tudo o que o Next tem de valioso — Server Components, streaming, server actions — fica inerte
  dentro dela. Imposto de framework em 98% do código, colheita zero.
- O encanamento atual foi caro e é medido: `gzip_http_version 1.0` no `web-nginx.conf` transformou
  11.532.084 bytes em 3,2 MB no waterfall de um celular real; `gzip_static` com `.gz`
  pré-gerados; cache diferente por caminho; MIME de `application/wasm`; `setup-mediapipe.mjs`
  baixando o modelo de 5,5 MB no `prebuild`. Nada disso se transporta de graça — se transporta
  para ser medido de novo.
- **A fonte de conteúdo é o Postgres, não o sistema de arquivos.** As páginas por exercício saem
  de `Exercise` + `Translation`, editadas no painel. O maior trunfo do Next para site de conteúdo
  (roteamento por arquivo sobre MDX) não se aplica, e buscar do Django por requisição exigiria o
  processo Node em produção que a VPS de 4 vCPU — já rodando dois pose-workers — não tem folga
  para hospedar.
- Com `output: 'export'` o Next dá SSG estático e evita o Node, o que é legítimo. Mas aí a
  comparação real fica: nova toolchain + novo roteamento + reconfigurar WASM e assets + remedir a
  compressão + migrar 203 arquivos de teste do Vitest + refazer o i18n que acabou de nascer,
  **contra ~150 linhas de script de build**.
- Coerência: este projeto recusou 50 KB de `i18next` por um `t()` e uma interpolação, e a decisão
  se provou certa (o runtime tem ~2 KB e a paridade dos dicionários é cobrada de graça pelo `tsc`
  que já rodava). Trazer o Next depois disso seria abandonar a régua sem um argumento novo.

**O que entra no lugar:** um passo de build que percorre `rotas × locales`, renderiza com
`renderToString` (o `react-dom` já é dependência) e injeta o HTML no `<body>` de cada entry, junto
com `<title>`, `<meta description>`, `canonical` e `hreflang` daquela rota. O React hidrata
normalmente depois. A **mesma tabela de rotas** alimenta o `sitemap.xml`.

**A saída de emergência já está construída, e é o que torna esta decisão barata de errar.** A
ADR-010 separou SITE e APP em bundles, roteadores e origens distintos. Se um dia o site virar
operação de conteúdo com dono próprio, ele sai para o próprio artefato — Next, Astro, o que for —
num subdomínio, e o corte é limpo. Dizer "não" hoje não fecha essa porta. O que **nunca** deve
acontecer, em cenário nenhum, é fundir o `/app/` dentro desse framework.

### 3.2 Idioma de acesso: três camadas, e nenhuma é redirecionamento

A regra de ouro, e o motivo é o objetivo: **o Googlebot rastreia dos Estados Unidos.** Se `/`
redirecionar por IP ou por `Accept-Language`, o robô vê só a versão inglesa e a portuguesa
desaparece do índice. Redirecionar por geografia é o jeito mais eficiente conhecido de sumir do
Google. (O §3.3 do `PLANO-I18N.md` já havia rejeitado GeoIP pelo argumento da pessoa — quem mora
em Miami e fala português deve receber português; este é um segundo argumento, independente, e
mais duro.)

| Camada | Quem atende | Mecanismo |
|---|---|---|
| **Achar** | o robô | `hreflang` absoluto recíproco + `x-default` → `/en/` |
| **Chegar certo** | quem não veio da busca | aviso client-side, **nunca** redirect |
| **Traduzir** | quem não fala nenhuma das duas | o navegador, em ~130 línguas |

**Metade disto já está entregue.** Um francês abre `/app/` hoje e recebe inglês:
`resolveLocale(null, ['fr-FR','fr'])` → `matchLocale('fr')` devolve `null` → `DEFAULT_LOCALE`.
O app acerta desde a T-142. O furo é inteiramente do lado do site, e é a raiz dele.

**O aviso, com o detalhe que quase todo mundo erra:** ele vai **na língua de destino**, não na da
página. Um francês não lê *"esta página também está disponível em inglês"* escrito em português —
para ele o aviso é literalmente `View in English →`. E ele é renderizado **depois da hidratação**,
fora do HTML pré-renderizado: o robô e a pessoa recebem o mesmo conteúdo, e não há sombra de
cloaking.

### 3.3 Idioma curado × idioma traduzido

A distinção que permite ser global sem prometer quarenta idiomas:

- **Curado** (`pt-BR`, `en`): tom de treinador, revisado, layout conferido em aparelho real — é o
  que a T-155 existe para garantir. Mora no dicionário, com paridade cobrada pelo `tsc`.
- **Traduzido** (qualquer outra língua): tradução automática **do navegador**. O produto não
  promete qualidade nela, e quem ligou a tradução sabe disso e calibra a expectativa sozinho.

Por isso **não** se traduzem os dicionários por máquina para dez línguas: a string passaria a
morar no bundle, com a marca do produto em cima, e o projeto assumiria uma qualidade que não
revisou — além de multiplicar a T-155 por dez a cada release. Deixar o navegador traduzir é a
opção honesta.

Idioma curado novo entra quando houver mercado, não por vaidade. `LOCALES` em
`web/src/i18n/locale.ts` é literalmente a lista, e o plano de i18n provou que o custo é um
diretório de dicionário, um `catalog.<locale>.yaml`, um `messages.<locale>.yaml`, um entry HTML e
as traduções do painel. O custo **real** não é esse: é o conteúdo do §3.4 multiplicado por N.

### 3.4 Conteúdo: o insumo já está no banco

Ninguém procura "Digital Fit". Procuram *"como fazer agachamento correto"*, *"contador de
flexões"*, *"squat form check app"*. Um site de duas páginas não ranqueia para nada, e nenhuma
correção técnica muda isso.

O insumo já existe e já é multilíngue: oito exercícios com `default_tip`, `scene_tip`,
`ExerciseGuideStep`, mais o catálogo de feedback de erro de execução — tudo escrito, tudo no
painel, e hoje só visível depois de a câmera abrir. Uma página pública por exercício por idioma
(`/exercicios/agachamento/` · `/en/exercises/squat/`) sai do `Translation` que a T-146 criou.

**A frente de i18n construiu a infraestrutura de conteúdo multilíngue e ela ainda não foi
colhida.** É esta a virada de tráfego; o resto do plano é o que a torna possível.

### 3.5 O que continua como está

- **O `/app/` continua `noindex`.** É ferramenta, não conteúdo; quem chega pela busca deve cair no
  site, que explica o produto antes de pedir a câmera. Nada neste plano toca no app além do
  `translate="no"` do §2.4.
- **O cliente continua mandando o locale RESOLVIDO no `Accept-Language`.** O francês manda `en`,
  não `fr` — o servidor não tem catálogo em francês e cairia no fallback de qualquer forma.
  Vira comentário explícito, porque é o tipo de coisa que alguém "conserta" errado.
- **GeoIP fica fora do idioma.** Região serve para moeda e para unidade de medida (kg × lb,
  cm × ft — um americano e um britânico falam a mesma língua e discordam), e o fuso já foi
  resolvido pela T-156. Nenhum dos três é este plano.

---

## 4. Como uma página nova entra — os portões

Mesmo espírito do §4 do `PLANO-I18N.md`: processo escrito num documento é processo esquecido; o
que vale é o que trava num gate que já é obrigatório.

**A receita, para quem for criar a próxima página:**

1. A rota entra na **tabela de rotas** (uma só, tipada, em `web/src/site/routes.ts`).
2. Dessa tabela saem, sozinhos: o roteador, o pré-render, o `sitemap.xml` e os `hreflang`.
   Ninguém escreve nenhum dos quatro à mão.
3. `<title>` e `<meta description>` da rota são **chaves do dicionário** — então o `tsc` já cobra
   que existam nas duas línguas, pelo portão que a T-142 construiu.

| Portão | Onde | Pega | Já é gate? |
|---|---|---|---|
| Tipo derivado do pt-BR | `tsc -b` | rota nova sem `title`/`description` em algum idioma | **sim**, AGENTS §4 |
| Teste da tabela de rotas | `vitest` | rota no roteador e fora do sitemap (ou o inverso) | **sim**, AGENTS §4 |
| Teste de metadados do build | `vitest` | HTML gerado sem `canonical`, sem `hreflang` recíproco ou sem `x-default` | novo, entra na T-166 |
| `manage.py i18n_status` | operação | exercício publicado sem tradução → página órfã | já existe (T-146) |

O terceiro é o que fecha o buraco do §2.1: um `hreflang` relativo, ou um par que não aponta de
volta, passa a ser **erro de teste**, não descoberta de seis meses depois.

---

## 5. As tasks

Numeração a partir de **T-157** (T-156 é a última do backlog). Spec nova: **SPEC-026**.
ADR nova: **ADR-012** (pré-render no Vite, e o "por que não Next" do §3.1).

```
                      ┌──────────────────────────────────────────┐
 Onda 0               │  T-157  SPEC-026 — o contrato            │
                      └──────────────┬───────────────────────────┘
                                     │
 Onda 1               ┌──────────────┴──────────────┐
                 ┌────▼─────┐                  ┌────▼─────┐
                 │  T-158   │                  │  T-162   │  ← independente,
                 │  rotas   │                  │ tradução │    pode começar já
                 │  reais   │                  │ sem quebrar│
                 └────┬─────┘                  └──────────┘
              ┌───────┼────────┬─────────┐
 Onda 2  ┌────▼───┐ ┌─▼──────┐ ┌▼───────┐│
         │ T-159  │ │ T-160  │ │ T-161  ││
         │ pré-   │ │hreflang│ │ aviso  ││
         │ render │ │x-default│ │de idioma││
         └───┬────┘ └────────┘ └────────┘│
             │           ┌───────────────┘
        ┌────┴────┐ ┌────▼────┐
        │  T-164  │ │  T-163  │
        │ OG+JSON │ │robots+  │
        │  -LD    │ │sitemap  │
        └────┬────┘ └────┬────┘
             └──────┬────┘
 Onda 3         ┌───▼────┐   ┌────────┐
                │ T-165  │──►│ T-166  │
                │páginas │   │portões │
                │por exer│   └────────┘
                └────────┘

 Prioridade declarada (idioma de acesso):  T-160 · T-161 · T-162
```

### Onda 0 — o contrato (bloqueia tudo)

| ID | Task | Spec | Tam |
|---|---|---|---|
| T-157 | **SPEC-026 — Descoberta e idioma de acesso.** A tabela de rotas como fonte única (roteador, pré-render, sitemap, hreflang); a regra das três camadas do §3.2 com **"nunca redirecionar"** como invariante declarada; `x-default` → `/en/` amarrado ao `DEFAULT_LOCALE`; a distinção **curado × traduzido** (§3.3) como promessa de produto; o `/app/` permanecendo `noindex`; os portões do §4 como critério permanente. ADR-012 no `ARCHITECTURE.md` com o "por que não Next". Fora de escopo explícito: moeda, unidade de medida, GeoIP | 026 | M |

### Onda 1 — a base

| ID | Task | Dep | Tam |
|---|---|---|---|
| T-158 | **Rotas reais no lugar do hash.** `web/src/site/routes.ts` como tabela tipada (rota × locale × chave de `title`/`description`); `nav.ts` passa a ler `location.pathname`; `/sobre/` e `/en/about/` viram URLs de verdade; `origins.ts`/`siteLocaleHref` acompanham; nginx com `location` por prefixo de idioma, **`404.html` de verdade no lugar do soft-404** (§2.6) e a regra de `no-cache` faltante para `/en/index.html` (§2.8); 301 dos `#/sobre` antigos para não perder quem tem o link salvo | T-157 | G |
| T-162 | **Tradução do navegador sem quebrar o app.** `translate="no"` nas regiões voláteis do `/app/` (`hud/StatsBar`, `hud/CoachTip`, `hud/TimerRing`, e os números do `ReportSheet`), com o motivo do `<font>` (§2.4) escrito no código; `SiteApp.tsx:22` passa a usar `matchLocale()` (§2.7); comentário explícito no wrapper de `fetch` sobre mandar o locale **resolvido** (§3.5). Teste que simula o embrulho em `<font>` e prova que o HUD sobrevive a um redesenho. **Não depende de nenhuma outra** | T-157 | M |

### Onda 2 — descoberta e idioma de acesso

| ID | Task | Dep | Tam |
|---|---|---|---|
| T-159 | **Pré-render em tempo de build.** Passo de build que percorre `rotas × locales`, renderiza com `renderToString` e injeta HTML, `<title>`, `<meta description>` e `canonical` em cada entry; hidratação verificada nas duas línguas; sem dependência de runtime nova. Critério que não pode faltar: `curl` da URL, com JS desligado, devolve o `<h1>` e o texto da página | T-158 | G |
| T-160 | **`hreflang` absoluto + `x-default` + `canonical`.** Host vindo de `VITE_SITE_URL` no build (§2.1); recíproco entre `/` e `/en/` para cada rota; `x-default` → `/en/` (§2.2). Teste sobre o HTML **gerado**, não sobre o template | T-158 | M |
| T-161 | **Aviso de idioma no site.** Client-side, depois da hidratação, quando `matchLocale(navigator.languages)` discorda do `lang` da página; **na língua de destino** (§3.2); dispensável e lembrado (não reaparece depois de fechado); **nunca redireciona**. Reaproveita o `LocaleSwitch` que a T-153 já deixou pronto para as duas superfícies | T-158 | M |
| T-163 | **`robots.txt` + `sitemap.xml` + descoberta.** Ambos gerados da tabela de rotas no build; `sitemap` com `<xhtml:link>` de idioma alternativo por URL; `robots.txt` liberando o site, mantendo o `/app/` fora e apontando o sitemap. Decisão a registrar: política para rastreadores de LLM (GPTBot, ClaudeBot, PerplexityBot) — recomendação é **permitir**, porque hoje parte da descoberta de produto acontece dentro de um chat | T-158 | M |
| T-164 | **Open Graph + JSON-LD.** `og:*` e `twitter:card` por rota e por idioma, com imagem própria; JSON-LD `SoftwareApplication` + `Organization`. Critério de aceite verificado no validador do Facebook e num WhatsApp real — é o canal que motiva a task | T-159 | M |

### Onda 3 — conteúdo, e o fecho

| ID | Task | Dep | Tam |
|---|---|---|---|
| T-165 | **Páginas públicas por exercício.** `/exercicios/<slug>/` e `/en/exercises/<slug>/` a partir de `Exercise` + `Translation` + `ExerciseGuideStep` (§3.4), consumidos pelo pré-render em build; cada página linka o app com o exercício já escolhido; exercício despublicado sai do sitemap. É a task que transforma a tradução já paga em tráfego | T-159, T-163 | G |
| T-166 | **Os portões.** Teste do build que cobra, para cada rota gerada: `canonical` presente, `hreflang` recíproco e absoluto, `x-default` existente, `title`/`description` não vazios e diferentes entre idiomas; teste da tabela de rotas (roteador ↔ sitemap); a regra da rota nova no `AGENTS.md` e na skill `df-spec` | Onda 2 | P |

---

## 6. O caminho crítico

**T-157 → T-158 → T-159 → T-165 → T-166**: o contrato, as URLs, o HTML pronto, o conteúdo, o
fecho. Tudo o mais cabe na sombra disso:

- A **T-162 não depende de nada** além do contrato e entrega um terço da prioridade declarada.
  Pode ser a primeira a rodar.
- **T-160 e T-161 só dependem da T-158**, não do pré-render — as duas rodam enquanto a T-159 é
  escrita. Com elas, a prioridade declarada fecha antes da metade do plano.
- **T-163 e T-164** são folhas e podem esperar sem bloquear ninguém.

Ordem mínima segura, se for uma raia só: **T-157 · T-162 · T-158 · T-160 · T-161 · T-159 · T-163 ·
T-164 · T-165 · T-166**.

---

## 7. Como se sabe que acabou

1. `curl` de `/`, `/en/` e `/sobre/`, **com JavaScript fora da conta**, devolve o texto da página
   — título, `h1` e corpo.
2. Um navegador em francês abre `/`, vê um aviso escrito **em inglês** apontando para `/en/`, e
   **não é redirecionado**. Se ignorar o aviso, o Chrome oferece traduzir a página para francês, e
   a tradução funciona.
3. Um navegador em francês abre `/app/` e recebe inglês — sem aviso, sem escolha, sem erro.
   *(Já é verdade hoje; entra na lista para não regredir.)*
4. Traduzir o `/app/` pelo navegador e fazer trinta segundos de treino de verdade **não derruba a
   tela**: o contador sobe, o card do treinador troca de frase, e nada dá `removeChild`.
5. Colar o link no WhatsApp mostra título, descrição e imagem — na língua da URL colada.
6. `sitemap.xml` lista todas as rotas de todos os idiomas, e cada URL declara suas alternativas.
   Uma URL inexistente devolve **404**, não 200.
7. Um commit que acrescenta uma rota e esquece o `title` em inglês, ou esquece o sitemap, **não
   passa nos gates**.

O item 7 é o produto real deste plano, como foi no da i18n. Os outros seis são de uma vez; ele é
para sempre.
