# SPEC-026 — Descoberta & Idioma de Acesso
Status: draft | Camada: site + build + entrega | Depende de: SPEC-014, SPEC-020, SPEC-025 | Referência: `docs/PLANO-SEO.md` (2026-08-18)

## Entidade e responsabilidade

A entidade é **a descoberta**: o caminho de quem ainda não conhece o produto até uma tela que
consegue ler. A SPEC-025 garantiu que o texto existe nas duas línguas; esta spec garante que
alguém **chega** até ele.

São três perguntas encadeadas, e hoje as três respondem "não":

| # | Pergunta | Hoje | Por quê |
|---|---|---|---|
| 1 | O robô consegue **ler** a página? | não | o `<body>` do site é `<div id="root"></div>`; o texto só existe depois do JS |
| 2 | Ele sabe **qual versão** mostrar para quem? | não | `hreflang` com `href` relativo é ignorado em silêncio; não há `x-default` |
| 3 | A pessoa que chega **consegue ler**? | depende | `/app/` acerta desde a T-142; `/` entrega português a qualquer um |

A responsabilidade é declarar as regras que fazem as três virarem "sim" — e, principalmente,
**a regra que não pode ser quebrada**: nenhuma delas se resolve redirecionando ninguém.

Superfícies e o que cada uma promete:

| Superfície | URLs | Idioma decidido por | Indexado |
|---|---|---|---|
| **site** | `/`, `/sobre/`, `/exercicios/<slug>/` e os espelhos sob `/en/` | a **URL** | sim |
| **app** | `/app/` | a **preferência** do aparelho (SPEC-025) | não (`noindex`) |

A divergência é a mesma da SPEC-025 e continua sendo de propósito: o site é rastreado por URL,
o app não é rastreado por ninguém.

**De onde vem o texto novo desta spec** (SPEC-025 §Entidade, as cinco fontes):

- `<title>` e `<meta description>` de cada rota → **fonte 1 (bundle do cliente, dicionário)**,
  não fonte 5. É uma mudança de endereço deliberada, e está no §Escopo abaixo.
- O texto das páginas por exercício → **fonte 3 (banco/painel)**, via o modelo `Translation`
  que a T-146 já criou.
- Nenhuma frase nova nasce em HTML solto. É o que mantém o portão do `tsc` valendo.

## Fase Inicial

### Escopo / Comportamento

- **A tabela de rotas é a fonte única.** `web/src/site/routes.ts` declara, tipada, cada rota do
  site: caminho por locale, chave de `title`, chave de `description`, e se é estática ou vem do
  banco. Dela saem — geradas, nunca escritas à mão — **quatro** coisas: o roteador, o
  pré-render, o `sitemap.xml` e os `hreflang` de cada página.

  **Rejeitado**: manter as quatro por conta própria, como está hoje. Foi exatamente essa
  independência que produziu o `hreflang` inerte do §Notas técnicas — quatro lugares que
  precisam concordar e nenhum mecanismo que os obrigue a isso. Com uma fonte só, "rota nova sem
  sitemap" deixa de ser possível em vez de deixar de ser esquecido.

- **Metadados de rota moram no dicionário, não no HTML.** `title` e `description` de cada rota
  são chaves do namespace `site` (SPEC-025 §Escopo), resolvidas no pré-render. Consequência
  direta e é ela que justifica a escolha: **`tsc -b` passa a reprovar rota nova sem título em
  inglês**, pelo portão que a T-142 já construiu, sem regra nova e sem ninguém lembrar de
  conferir.

  **Rejeitado**: `<title>` escrito em cada `index.html`, que é como está hoje. Funciona para
  duas páginas e não sobrevive a dez — e deixaria o único texto do produto sem gate de paridade,
  justamente no lugar que o Google lê.

- **Pré-render em tempo de build.** Um passo do build percorre `rotas × locales`, renderiza com
  `renderToString` (o `react-dom` já é dependência) e injeta no `<body>` de cada entry o HTML
  pronto, mais `<title>`, `<meta description>`, `canonical` e `hreflang` daquela rota. O React
  hidrata normalmente depois. Nenhuma dependência de runtime nova.

  **Rejeitado — SSR com processo Node em produção**: a VPS tem 4 vCPU/6 GB e já roda dois
  pose-workers; um processo a mais para servir uma landing não se paga. E não é preciso: o
  conteúdo do site muda por deploy, não por requisição.

  **Rejeitado — migrar para Next**: a superfície que precisa de SEO é 466 linhas de 22.516
  (2% do frontend), e os outros 98% são câmera, MediaPipe WASM e máquina de sessão por frame —
  que no App Router viram uma ilha `'use client'` onde tudo que o Next tem de valioso fica
  inerte. Some-se que a fonte de conteúdo é o **Postgres**, não o sistema de arquivos, o que
  anula o trunfo de roteamento por arquivo. Registrado como **ADR-012**, porque é a decisão que
  alguém questiona de novo daqui a seis meses.

- **Rotas por caminho, não por fragmento.** `#/sobre` vira `/sobre/`, com espelho em
  `/en/about/`. Fragmento não viaja no pedido HTTP: o servidor nunca o vê e o buscador trata
  `/#/sobre` e `/` como a mesma página.

  **Rejeitado**: manter o hash e só pré-renderizar. Não resolveria nada — sem URL não há o que
  indexar, e o pré-render entregaria a mesma página para todos os fragmentos.

- **Idioma de acesso em três camadas, e nenhuma é redirecionamento.** É a invariante da spec:

  | Camada | Atende | Mecanismo |
  |---|---|---|
  | **Achar** | o robô | `hreflang` recíproco **absoluto** + `x-default` → `/en/` |
  | **Chegar certo** | quem não veio da busca | aviso client-side, dispensável |
  | **Traduzir** | quem não fala nenhuma das duas | o navegador, em ~130 línguas |

  **Rejeitado — redirecionar `/` por GeoIP ou por `Accept-Language`**: o Googlebot rastreia dos
  Estados Unidos. Redirecionar por geografia faria o robô ver só a versão inglesa, e a
  portuguesa sairia do índice. A SPEC-025 §Escopo já havia rejeitado GeoIP pelo argumento da
  pessoa (quem mora fora e fala português deve receber português); este é um segundo argumento,
  independente e mais duro, e vale para `Accept-Language` também.

  O `x-default` aponta para `/en/` pelo mesmo motivo que `DEFAULT_LOCALE` é `'en'` em
  `web/src/i18n/locale.ts`: é a resposta certa para *"não sei quem é você"*. As duas pontas
  passam a dizer a mesma coisa, e é assim que devem ser lidas.

  **O aviso vai na língua de destino, não na da página.** Um francês em `/` não lê *"esta página
  também está disponível em inglês"* escrito em português — para ele o aviso é `View in
  English →` e mais nada. Ele é renderizado **depois da hidratação**, fora do HTML
  pré-renderizado: robô e pessoa recebem o mesmo documento, e não há sombra de cloaking.

- **Idioma curado × idioma traduzido.** Promessa de produto, escrita para poder ser cobrada:
  - **Curado** (`pt-BR`, `en`): tom de treinador, revisado, layout conferido em aparelho real.
    Mora no dicionário, com paridade cobrada pelo `tsc`.
  - **Traduzido** (qualquer outra língua): tradução automática **do navegador**. O produto não
    promete qualidade nela, e quem a ligou sabe disso.

  **Rejeitado**: traduzir os dicionários por máquina para N idiomas. A string passaria a morar
  no bundle, com a marca do produto em cima, e o projeto assumiria uma qualidade que não revisou
  — além de multiplicar a revisão de layout e tom (T-155) por N a cada release. Deixar o
  navegador traduzir é a opção honesta: a expectativa fica calibrada por quem ligou a tradução.

- **A tradução do navegador não pode derrubar o app.** O Google Translate embrulha cada nó de
  texto num `<font>`; o React continua achando que o nó é filho direto do elemento original e
  quebra com `removeChild` ao redesenhar. As regiões voláteis do `/app/` — contador de
  repetições, ângulo, card do treinador, cronômetro, números do relatório — recebem
  `translate="no"`.

  Não é só defesa: é a decisão certa de produto pelos dois lados. Número e vocabulário de
  contrato não deveriam ser traduzidos por máquina de qualquer forma.

- **Páginas públicas por exercício.** `/exercicios/<slug>/` e `/en/exercises/<slug>/`, montadas
  no pré-render a partir de `Exercise` + `ExerciseGuideStep` + `Translation` (SPEC-020,
  SPEC-025 §3.6). Cada uma linka o app com o exercício já escolhido. Exercício despublicado sai
  do sitemap junto.

  É a única parte desta spec que gera tráfego de verdade: ninguém procura "Digital Fit". O
  insumo já está escrito e já é multilíngue — hoje só é visível depois de a câmera abrir.

- **O `/app/` continua `noindex`, e nada aqui o toca** além do `translate="no"`. Quem chega pela
  busca deve cair no site, que explica o produto antes de pedir a câmera.

- **URL inexistente devolve 404.** O `try_files ... /index.html` de hoje devolve **200** com a
  home em português para qualquer caminho errado — *soft 404*, que o Google trata como sinal de
  site de baixa qualidade. Passa a existir um `404.html` de verdade, nas duas línguas.

### Fora de escopo (vai para Evolução)

- **Terceiro idioma curado.** A arquitetura já suporta (SPEC-025) e esta spec não muda isso —
  `LOCALES` é a lista. Entra quando houver mercado, não por vaidade.
- **Conteúdo editorial (blog, guias longos).** As páginas por exercício são o primeiro degrau
  porque o insumo já existe no banco; conteúdo escrito do zero é operação, não engenharia, e
  precisa de dono antes de precisar de código.
- **Moeda, unidade de medida e GeoIP.** Região decide moeda (PIX é só Brasil) e unidade (kg × lb,
  cm × ft — um americano e um britânico falam a mesma língua e discordam). Nenhum dos dois é
  idioma, e o fuso já foi resolvido pela T-156. GeoIP entra ali, como sugestão de default, e
  **nunca** como redirecionamento.
- **Pré-render do `/app/`.** É `noindex` por decisão de produto; renderizar no build uma tela
  que existe para abrir a câmera não serviria a ninguém.
- **CDN, AMP e imagem OG gerada por rota.** Infra e refinamento; nenhum se paga antes de haver
  tráfego para medir.

### Critérios de aceite

1. `curl` de `/`, `/en/` e `/sobre/`, **com JavaScript fora da conta**, devolve o `<h1>` e o
   corpo da página — não um `<div>` vazio.
2. Navegador em francês abre `/`, vê um aviso **escrito em inglês** apontando para `/en/`, e
   **não é redirecionado**. Ignorando o aviso, o Chrome oferece traduzir a página, e a tradução
   funciona.
3. Navegador em francês abre `/app/` e recebe inglês — sem aviso, sem escolha, sem erro.
   *(Já é verdade desde a T-142; entra na lista para não regredir.)*
4. Traduzir o `/app/` pelo navegador e fazer 30 s de treino de verdade **não derruba a tela**: o
   contador sobe, o card do treinador troca de frase, e nada dá `removeChild`.
5. Colar o link no WhatsApp mostra título, descrição e imagem — na língua da URL colada.
6. `sitemap.xml` lista todas as rotas de todos os idiomas, cada URL declarando suas
   alternativas; uma URL inexistente devolve **404**, não 200.
7. Um commit que acrescenta uma rota e esquece o `title` em inglês, ou esquece o sitemap, **não
   passa nos gates**.

Os seis primeiros valem uma vez. O sétimo é o produto real desta spec — ele vale para sempre, e
é o mesmo papel que o critério 5 tem na SPEC-025.

## Fase Evolução

- **Terceiro idioma curado** (`es` é o candidato: dobra o alcance na América Latina e é onde a
  mesma busca tem volume com pouca concorrência de app com visão computacional). Arquitetura
  pronta; falta mercado.
- **Conteúdo editorial próprio** — guias, comparativos, dúvidas de execução. É o degrau seguinte
  às páginas por exercício, e o primeiro que exige alguém dedicado a escrever.
- **Tradução on-device no app** (`Translator API` do Chrome), para oferecer o app em uma língua
  não curada sem depender da tradução de página. Fica para quando houver medição de que alguém
  quer — e continua sujeito à promessa do §Escopo: seria idioma *traduzido*, não curado.
- **Imagem OG gerada por rota** (nome do exercício sobre a arte), no lugar de uma imagem por
  idioma.
- **Dados estruturados de exercício** (`HowTo`/`ExerciseAction`) nas páginas do §Escopo, quando
  houver tráfego que justifique medir o ganho.

## Eventos (consome / produz)

**Nenhum evento novo, e nenhuma mudança de contrato.**

A descoberta acontece inteiramente **antes** de existir sessão: quem lê a landing ainda não
abriu a câmera, não tem ticket e não produziu keypoint nenhum. Nada aqui é fato do domínio de
treino, então nada aqui pertence ao fio de eventos — `PROTOCOL_VERSION` não se move.

A única leitura de dado do domínio é o pré-render das páginas por exercício, e ela é feita
**no build**, contra o ORM, pelo mesmo caminho que o painel já usa. Nenhum worker é envolvido, e
a regra da SPEC-018 continua intacta: workers não leem banco.

## Notas técnicas

Cinco armadilhas achadas no mapeamento (plano §2). Nenhuma aparece como erro — todas aparecem
como "o site simplesmente não aparece" ou "às vezes a tela quebra". Viram critério de aceite das
tasks correspondentes:

- **O `hreflang` da T-147 está inerte.** `web/index.html` e `web/en/index.html` declaram
  `href="/"` e `href="/en/"`; a especificação exige URL absoluta com esquema e host, e relativa é
  ignorada sem aviso. O par pt/en que a T-147 entregou não existe para o Google hoje. O host não
  está no código de propósito (ADR-010: `VITE_SITE_URL` é decidida no build), então a correção é
  injetá-lo no build — que é o que o pré-render já faz. **(T-160)**

- **O pré-render é o que liga a tradução automática do navegador.** O Chrome decide se oferece
  "Traduzir esta página" analisando o texto do HTML da **resposta**. Com `<div id="root"></div>`
  não há texto para detectar idioma, e a oferta não aparece de forma confiável. A correção de
  SEO e a entrega da camada "Traduzir" do §Escopo são **a mesma tarefa**. **(T-159)**

- **`<font>` do Google Translate × React.** Detalhado no §Escopo. O risco concentra-se em
  `hud/StatsBar.tsx` (redesenha `repCount` a cada repetição, alterna `angulo` entre `'--'` e
  `'12°'`) e `hud/CoachTip.tsx` (troca a frase a cada `feedback.issued`). O site é imune por ser
  estático — o que reforça a divisão: o site traduz à vontade, o app se protege. **(T-162)**

- **`SiteApp.tsx:22` decide o idioma por igualdade, não por normalização.**
  `document.documentElement.lang === 'en' ? 'en' : 'pt-BR'` — com um terceiro idioma, `/es/`
  cairia silenciosamente em português. `matchLocale()` já existe e já faz isso certo. **(T-162)**

- **`/en/index.html` não tem regra de cache.** O nginx tem `location = /index.html` e
  `location = /app/index.html` com `no-cache`, e nada para o terceiro entry. O HTML inglês fica
  sujeito a cache heurístico do navegador — e é justamente o arquivo que aponta para os assets
  com hash novo. Irmão exato do bug que as outras duas linhas existem para evitar. **(T-158)**
