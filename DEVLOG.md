# DEVLOG — Digital Fit

> Registro de sessões de trabalho. Entradas mais recentes no topo.
> Formato: data · task(s) · o que foi feito · decisões · pendências geradas.

---

## 2026-08-19 (89) · T-169 — SPEC-027: de que lado e de que jeito o celular olha

**O pedido.** Duas ferramentas, trazidas como independentes: trocar entre câmera frontal e
traseira ("um amigo pode querer gravar o outro") e não deixar a UI estranha com o celular
deitado. Viraram uma spec só porque são a mesma entidade — o **enquadramento físico**: quem
segura o aparelho, para onde ele aponta e em que posição. Cada uma isolada produziria uma
decisão pela metade: trocar de câmera sem decidir o espelho entrega vídeo invertido, e desenhar
paisagem sem decidir a orientação do quadro entrega exercício mal lido.

**O que já existia.** `capture/useCamera.ts` chama `getUserMedia` sem `facingMode` nenhum — pega
a câmera default e pronto. A seleção de câmera já estava escrita como Fase Evolução da SPEC-001
("Seleção de câmera + espelhamento correto; preferência lembrada"), sem task. De orientação não
existia **nada**: nenhum `matchMedia`, nenhum `@media (orientation: …)` nas ~4.800 linhas do
`styles.css`; quatro `height: 100dvh` e a coluna de `max-width: 430px` que a SPEC-014 manda valer
em qualquer tela.

### As três decisões que a spec tomou, e o que foi rejeitado

**1. Espelho é função da câmera, não preferência independente.** Frontal abre espelhado
(default de hoje), traseira abre sem espelho — quem filma outra pessoa não está se vendo. O
botão Espelhar continua existindo e continua vencendo até a câmera mudar. *Rejeitado:* amarrar o
espelho à câmera e remover o botão — a inferência acerta quase sempre, e é por isso que o caso
raro em que erra viraria um app possuído, sem nada na tela para desfazer. Também ficou decidido
**não persistir** o espelho (hoje ele nasce `true` no store a cada carga): persiste-se a câmera,
o espelho se deduz. Dois estados salvos são dois jeitos de a tela abrir errada.

**2. `facingMode`, nunca `deviceId`; `exact` na troca, `ideal` na abertura.** `deviceId` aponta
para uma lente específica e o mapeamento muda entre versões de SO. E `{ ideal: 'environment' }`
num aparelho sem traseira **não falha** — entrega a frontal em silêncio, e o botão passaria a
mentir. Daí `exact` na troca, com `OverconstrainedError` voltando para a câmera anterior. O
rótulo vem de `getSettings().facingMode`, o que o track entregou, não o que foi pedido.

**3. A divergência da SPEC-014, delimitada.** A trava de 430px cai **só em paisagem** e **só nas
duas telas de câmera**. Índice, Escolha, Guia, Progresso, Analytics e Perfil continuam na coluna
mobile em qualquer orientação: são telas de ler, onde uma linha de 850px é pior. Nas de câmera é
o contrário — o quadro largo é a ferramenta.

### A descoberta que mudou o desenho do botão manual

O pedido do Daniel incluía "um botão para virar, caso não seja detectado automático". Investigando
o caso que motiva esse botão — **celular com a rotação de tela travada** — apareceu o que ninguém
tinha escrito: nesse aparelho **o quadro da câmera também não gira**. O navegador entrega os
frames alinhados à orientação da tela, que está travada. O mundo chega deitado.

E aí para de ser estético:

- `TOO_FAR`/`TOO_CLOSE` (SPEC-003) medem altura do corpo como fração da **altura do frame** —
  com o mundo a 90° eles medem outra coisa;
- a linha ombro-ombro, que a Evolução da SPEC-003 compara com a horizontal, fica perpendicular;
- `arm_abduction` (T-044/T-052) continua **existindo** e passa a estar errado, que é pior que
  não existir.

Também ficou registrado o contraponto à leitura apressada da T-110: aquela medição provou que um
quadro **largo e em pé** normaliza igual a um quadro **estreito e em pé** — não que orientação
seja problema resolvido. Quadro com o mundo deitado é outro assunto.

Por isso o botão ganhou duas responsabilidades em vez de uma: alterna o layout **e**, quando
força paisagem numa viewport que continuou retrato, diz na mesma frase que destravar a rotação é
o caminho que preserva a leitura do exercício. A sessão sai marcada `landscape_forced`.

**Girar o frame antes da pose ficou fora da Fase Inicial, com o motivo escrito** para não ser
decidido às pressas dentro de uma task: é um canvas a mais no caminho quente a 15fps, e a
SPEC-001 decide `edge` × `cloud` por **latência por inferência** — um passo ali pode empurrar
aparelho honesto para cloud e gastar vaga do semáforo da SPEC-009.

### Onde cada coisa foi morar

- Recomendação de orientação por exercício → **campo no banco + painel** (SPEC-018, natureza
  "negócio/conteúdo"), espelhado no catálogo embutido. O catálogo já sabia disso em texto solto:
  o comentário do `scene_tip` diz que a flexão e o abdominal pedem o celular deitado.
- A **frase** que a pessoa lê → dicionário do cliente (`session:*`), nas duas línguas. Do banco
  vem o valor, não o texto.
- Limiar de cena por orientação → **código + bancada** (natureza "medição"), nunca painel.
- Rótulo do enquadramento → **`session.capability` aditivo** (`facing`, `orientation`), no padrão
  do `ua` que já tem default vazio. **Nenhum evento novo**: enquadramento é atributo de sessão,
  não fato do domínio de treino.

### Tasks

Fase 9, oito tasks. T-169 (esta) abre; depois **três raias paralelas de verdade**: A
(`capture/`, T-170), B (bancada/limiares, T-171 — não toca UI e por isso não é a última) e C
(layout, T-172 → T-173 → T-175, serial porque é o mesmo CSS). T-174 (catálogo) depende só da
T-172; T-176 fecha o contrato.

**Pendência declarada:** a spec está `draft`. Vira `approved` na revisão do Daniel — nenhuma task
da Fase 9 deve ser executada antes disso.

---

## 2026-08-19 (88) · T-140 — A série contada entra na conta, e a coluna que ela obrigou a existir

**O buraco.** Desde a T-136 uma sessão pode terminar em `target_reached` — a meta de repetições
foi atingida. O `exercise_health` conhecia quatro motivos e somava o quinto **em nenhum balde**:
entrava no `total` e sumia da taxa de zero-rep, das `abortadas`, das `sem dado` e da mediana de
cadência. Um modo inteiro do produto ficava fora do instrumento que decide promover e rebaixar
exercício — e não por decisão: o motivo nasceu na T-134 e ninguém voltou aqui.

**A decisão, que a task delegava à SPEC-020.** `target_reached` conta como sessão que chegou ao
fim. O bucket significa "a análise correu até o fim", e uma série que bateu a meta chegou lá de
forma mais categórica que os 30 s do modo livre: o fim é a N-ésima repetição **detectada**, não
o relógio. A cadência dela entra na mediana pelo mesmo motivo, com um argumento a mais — no modo
contado todas as séries têm a mesma meta, então reps/min mede ritmo e não quanto a pessoa
aguentou. É o dado mais comparável que o instrumento tem.

### A consequência que não era óbvia, e a coluna que ela obrigou

**`target_reached` quase nunca pode contar zero.** A sessão terminou porque a rep N foi vista,
então `rep_count >= 1` por construção. Ele engrossa o **denominador** da taxa e nunca o
numerador — ou seja, **puxa a taxa para baixo**.

Isso é honesto: cada uma dessas sessões é uma observação real de que a análise funcionou. E é
justamente por isso que é perigoso. Um produto que migre para o modo contado — que é exatamente
o que o Bloco C da Fase 6 está construindo — veria a taxa despencar e pararia de ouvir o alarme,
**sem nada ter melhorado**. O instrumento morreria em silêncio, que é o modo de morte mais caro
que existe neste projeto.

Daí a coluna `atingiu_meta`, ao lado de `completas` na tabela e no JSON. Medido com dados de
teste:

```
exercicio            maturidade   sessoes  completas   meta  zeradas    taxa   sem dado  veredito
Agachamento          validado          10         10      4        1   10.0%     0 (0%)  ok
```

Sem a coluna, essa linha é indistinguível de um exercício que melhorou. Com ela, quem lê vê que
4 das 10 vieram do modo contado e que a taxa diz menos do que parece. É a mesma doutrina do
`no_data` em coluna separada, aplicada ao problema **simétrico**: lá a soma inflava o número,
aqui ela o esvazia. A legenda do comando ganhou a frase em maiúscula, porque é a leitura errada
mais provável.

**O zero improvável continua sendo contado.** `rep_count = 0` num `target_reached` não deveria
existir; se existir, é sinal de que algo está errado na meta ou na contagem. Descartá-lo por um
`if` que assume o impossível transformaria uma anomalia em silêncio — o lugar dela é o alarme.
Tem caso de teste próprio.

### A spec foi corrigida antes do código

A SPEC-020 §Maturidade dizia *"a taxa é sobre as sessões `completed`, e essa palavra é o critério
inteiro"* e *"uma sessão morre por quatro motivos"* — escrita antes de o quinto existir. A linha
de `validado` passou a dizer "sessões que **chegaram ao fim**", com `target_reached` nomeado, a
consequência da diluição escrita por extenso e o "deixar de fora" registrado como alternativa
rejeitada. A própria task dizia que a decisão do balde era da spec; ela só não tinha sido tomada.

### As medições

- **Cinco mutações num golpe**: com `_CHEGOU_AO_FIM` de volta a `(_COMPLETED,)` — o estado de
  ontem — caem os cinco casos novos, incluindo o da cadência e o da diluição. O portão morde.
- **Saída do comando conferida com dados reais** (tabela acima), com a linha `sem sessao` e a
  `poucas (<5)` intactas.
- **Gates**: `ruff check` + `ruff format --check` limpos, `pytest` verde (18 casos em
  `test_exercise_health.py`, eram 13). O `web/` não foi tocado.

### Pendências

- **Nenhuma sessão `target_reached` existe em produção ainda** — o modo contado tem servidor
  (T-135/T-136) e não tem cliente (T-137). Ou seja: esta task foi feita **antes** de o dado
  aparecer, que é o único momento em que consertar um instrumento é barato. Quando a T-137
  subir, a coluna `meta` já vai estar contando desde a primeira série.
- A faixa do painel (T-130) não mostra `atingiu_meta` de propósito: ela só fala de exercício
  ACIMA do limite, e a diluição nunca é motivo de um alarme — só de um alarme que deixou de
  tocar. Está escrito no docstring.

---

## 2026-08-19 (87) · T-165 — As páginas por exercício, e o endereço que precisou virar coluna

**O que a task entrega.** `/exercicios/agachamento/` e `/en/exercises/squat/`, doze páginas no
lugar de quatro, montadas no build a partir do catálogo do Postgres. É a task que transforma a
tradução já paga (T-146/T-152) em tráfego: ninguém procura "Digital Fit" — procuram "como fazer
agachamento correto". O texto já estava escrito e só aparecia **depois de a câmera abrir**.

### A decisão que o Daniel tomou, e a spec que estava errada

A SPEC-026 §Eventos dizia que o pré-render leria o ORM "no build". **Não é executável**: o
`web.Dockerfile` constrói num `node:22-alpine` sem Django e sem Postgres, e o `prod.sh up` roda
build → migrate → start — na hora do build não há ORM nem API de pé. Três saídas foram
apresentadas; o Daniel escolheu o **snapshot exportado**, e pediu a correção da spec junto.

`manage.py export_site_catalog` escreve `web/src/site/exercicios.json` a partir de
`config.exercises_for(None)` — o mesmo resolvedor do `GET /api/config` e da admissão, com
solicitante **anônimo**, porque quem chega da busca é anônimo e a página existe para levá-lo a
um exercício que ele consegue abrir. Virou **ADR-013**, e o §Eventos da spec foi reescrito.

O que a exportação compra: build **hermético** (roda no CI e em clone novo, sem banco), conteúdo
publicado **no diff** (dá para saber o que estava no ar em cada deploy), e banco fora do ar
**congela** o conteúdo em vez de derrubar o build. O preço, declarado: exercício despublicado só
some do site no próximo build.

`scripts/prod.sh` mudou de ordem por causa disso: era build de tudo → migrate → up; agora é
`build api` → migrate → **exporta** → build → up. Buildar o web antes de migrar publicaria o
catálogo do deploy anterior, e um exercício novo ficaria sem página sem nada acusar.

### O endereço virou coluna, e é a metade da task que quase se perdeu

`/exercicios/squat/` desperdiça exatamente o sinal que motiva a página. Mas `Exercise.slug` é
contrato — chave do registro do servidor, lida pelo cliente, pela admissão e pelo worker — e não
pode servir aos dois papéis sem que mudar um quebre o outro. Entraram `Exercise.url_slug` e
`ExerciseTranslation.url_slug`, vazias caindo no slug técnico, e a `0024` semeia as portuguesas.

**Rejeitado: derivar o endereço do `display_name`.** Sairia de graça e trocaria a URL toda vez
que alguém corrigisse o nome no painel. URL trocada é página perdida, e o operador não teria como
saber que uma edição de texto custa o ranqueamento acumulado.

### Três erros meus, e o que cada um ensinou

**1. A migration violava uma invariante declarada da T-146.** A primeira versão criava linhas de
`ExerciseTranslation` para semear o endereço inglês (`push-up`, `sit-up`). Quatro testes de
`test_i18n_content.py` caíram, e um deles — `test_migration_nao_criou_traducao_nenhuma` — não é
um teste de implementação: é a decisão da SPEC-025 de que **tradução é conteúdo de operador**,
com teste em cima. A migration foi reescrita para tocar só a coluna base. O inglês continua
vindo do painel, e o que falta ficou **visível**: `url_slug` entrou em `CAMPOS_EXERCICIO`, então
`manage.py i18n_status` passou a listar quem está sem endereço em inglês.

**2. O endereço inglês caía no endereço PORTUGUÊS.** Ao pôr `url_slug` no overlay genérico de
tradução, o fallback dele virou o dos campos de texto — cai na coluna base. Para texto isso está
certo (mostrar português é melhor que mostrar vazio); para **endereço** produz
`/en/exercises/polichinelo/`, que é pior que o slug técnico, porque põe na URL inglesa a palavra
que ninguém digita em inglês. `url_slug` saiu do overlay e ganhou regra própria em
`site_catalog._endereco()`, escrita por extenso. Só apareceu porque eu conferi o JSON gerado com
os olhos — nenhum teste que eu tinha escrito até ali olhava para o valor inglês.

**3. `params` era um valor só, e punha "Agachamento" dentro da moldura inglesa.** Meia página em
cada língua, que é o modo de falha que a SPEC-025 existe para não repetir. Virou
`Record<Locale, params>`, e tem caso de teste próprio em `routes.test.ts`.

### Duas mudanças estruturais no roteador

**A identidade de uma rota deixou de ser uma tela.** Era `'index' | 'sobre'`; agora existe
`'exercicio/squat'`, com o slug **técnico** depois da barra. Técnico e não o endereço público
porque o endereço é traduzido: usá-lo como identidade daria duas identidades à mesma página, e o
`hreflang` não teria como parear as duas. Manter o id como **string** foi deliberado —
`metatags.ts`, `descoberta.ts`, `social.ts` e `shell/origins.ts` continuam recebendo uma rota e
devolvendo URL, sem saber que existem rotas dinâmicas.

**Página de exercício não tem entry próprio: clona.** Entry do Rollup precisa ser arquivo real em
disco, e N páginas exigiriam N `index.html` idênticos versionados e gerados por script — lixo que
envelhece. Cada rota declara um `molde` (`sobre`), e o pré-render copia o entry já construído do
mesmo idioma, que o Vite preencheu com os `<script>` dos assets com hash. O script passou a ler
**todos** os templates antes de escrever qualquer um: ler sob demanda faria a primeira página
clonada herdar um arquivo já processado, com o `<title>` e o `canonical` de outra página, e o
resultado continuaria sendo um HTML válido.

### Os portões da T-166 pegaram a mudança de invariante

Os dois testes que a T-166 escreveu ontem falharam na primeira execução desta task — pelo motivo
certo: `ROTAS_INDEXAVEIS` passou a ter rota sem entry no build, e as rotas de exercício
compartilham a mesma chave de dicionário de propósito. Nenhum dos dois foi afrouxado: o primeiro
virou "toda rota **com entry próprio** tem HTML" **mais** "toda rota clonada aponta para um molde
que tem entry"; o segundo virou "nenhuma rota **estática** reaproveita chave de outra" **mais**
"cada rota de exercício traz o nome no idioma certo" — que é o caso que pegou o erro 3 acima.

### As medições

- **Gates**: `ruff check` + `ruff format --check` limpos, `pytest` verde, `npm run lint` e
  `typecheck` sem saída, `npm run test` com **846 testes em 69 arquivos** (eram 836 em 68), e
  `npm run build:local` gerando **12 páginas** + `sitemap.xml` + `robots.txt`.
- **No navegador** (`vite preview` sobre o `dist/`): `/exercicios/agachamento/` renderiza nome,
  músculos, dica, os três passos, a instrução de cena e o CTA `/app/#/guia/squat` — o slug
  **técnico**, não o traduzido. Console limpo, sem erro de hidratação. O seletor de idioma leva a
  `/en/exercises/squat/`, e os links "Outros exercícios" ficam dentro do site.
- **Contra o nginx de produção** (imagem `nginx:1.27-alpine` com o `web-nginx.conf` real sobre o
  `dist/`), que é o que decide o 404:

  | URL | |
  |---|---|
  | `/exercicios/agachamento/` · `/en/exercises/squat/` | **200** |
  | `/exercicios/squat/` (endereço inglês na pasta portuguesa) | **404** |
  | `/en/exercises/agachamento/` | **404** |
  | `/exercicios/levitacao/` | **404** |

  Os dois 404 do meio são regra, não acaso: aceitar as duas grafias daria duas URLs ao mesmo
  conteúdo, que é o que o `canonical` da T-160 existe para evitar. **Nota**: sob `vite preview`
  esses mesmos caminhos devolvem **200 com a landing** — é o fallback de SPA do servidor de
  desenvolvimento, exatamente o *soft 404* que a T-158 tirou do nginx. Medir a 404 no preview
  daria o resultado errado.
- **O portão do arquivo versionado morde**: mudei um endereço na migration sem reexportar, e
  `pytest` acusou *"exercicios.json esta desatualizado em relacao ao banco"*.

### Pendências — e uma delas precisa de decisão antes do deploy

- **As páginas em inglês vão para o ar com o conteúdo em português.** Não há nenhuma
  `ExerciseTranslation` no banco semeado, então o fallback honesto da T-146 assume e o título sai
  *"How to do a Agachamento correctly"* — moldura inglesa, substantivo português, e concordância
  errada de quebra. Não inventei tradução: conteúdo é do painel, e `manage.py i18n_status` lista
  exatamente o que falta. **Mas publicar assim é pior que não publicar aquela metade**, e a saída
  (não gerar a rota num idioma sem tradução) é decisão de produto — está nas Descobertas.
- `flexao` e `jumping_jack` têm slug técnico português, então o endereço inglês deles cai em
  `/en/exercises/flexao/` até alguém preencher `push-up` e `jumping-jack` no painel.
- **T-164**: conferir o card num WhatsApp real depois do deploy.
- **T-155** (Fase 7) segue aberta, e agora tem doze páginas para revisar em vez de quatro.
- A SPEC-026 segue em **`draft`**, agora com o §Eventos corrigido e o §Escopo declarando a coluna
  de endereço. Com a T-166 e a T-165 fechadas, a Fase 8 está inteira — falta a revisão que a
  passa a `approved`.

---

## 2026-08-19 (86) · T-166 — Os portões: cinco mutações, cinco vermelhos

**O que a Onda 2 tinha, e o que ela não tinha.** Quatro tasks entregaram `canonical`,
`hreflang` absoluto, `x-default`, `sitemap.xml` e Open Graph, todas com teste. Todos os testes
verdadeiros, e nenhum deles respondia à pergunta que a Fase 8 existe para responder: **a página
que vai para o ar tem essas anotações?** Eles cobrem as funções que *decidem* o `<head>`. Entre
a função e o arquivo servido havia uma injeção por expressão regular que já comeu a abertura de
`<html>` uma vez (T-159) — e um `hreflang` impecável numa string que não chega ao arquivo custa
exatamente o mesmo que o `hreflang` relativo da T-147.

### A decisão que fez o resto ser possível

**A injeção saiu do `scripts/prerender.mjs` e virou função pura** (`src/site/paginaGerada.ts`).
Enquanto ela morava no script de build, o único jeito de conferir o resultado era rodar
`npm run build` e abrir o `dist/` com os olhos — que é precisamente o regime em que o
`hreflang` da T-147 sobreviveu meses. A fronteira desta casa é sempre a mesma (decisão no
código testável, leitura do mundo na borda), e aqui ela estava no lugar errado: `metatags.ts` e
`social.ts` já eram puros e testados, faltava a função que decide **como** eles entram no
arquivo. O script ficou com `readFile`, `writeFile` e a variável de ambiente, e mais nada.

**O refactor não podia mudar o artefato, e não mudou.** `diff -r` entre o `dist/` do `HEAD` e o
da task: nenhuma diferença em nenhum HTML, no `sitemap.xml`, no `robots.txt` nem nos assets.

### Os três portões

| Portão | Arquivo | Pega |
|---|---|---|
| Tabela ↔ entries do build | `site/routes.test.ts` *(já existia)* | rota na tabela sem HTML no `vite.config.ts` |
| Tabela ↔ `sitemap`, **nos dois sentidos** | `site/descoberta.test.ts` | o sentido novo: URL no mapa que o roteador não sabe abrir |
| **O HTML gerado** | `site/paginaGerada.test.ts` *(novo)* | `canonical` ausente/duplicado/relativo, `hreflang` não recíproco, `x-default` faltando, título igual nos dois idiomas |

O terceiro monta cada página com o **mesmo código do build**, sobre o template real em disco, e
cobra o resultado — sem `npm run build`, que leva minutos e não caberia numa suíte que roda a
cada salvamento.

**Duas coisas que ele faz e que nenhum teste anterior fazia:**

1. **Confere a reciprocidade contra as páginas que existem de verdade.** Em `metatags.test.ts`
   as duas pontas saem da mesma função, então a reciprocidade é tautológica. Aqui cada `href`
   é procurado no `canonical` de uma página **realmente gerada**, e a página encontrada precisa
   apontar de volta. Um `alternate` para uma URL que ninguém escreve — slug renomeado em um
   idioma só — cai aqui e em lugar nenhum mais.
2. **Cobra título e descrição diferentes entre os idiomas.** É o erro mais barato de cometer e
   o mais caro de descobrir: a chave nasce no `pt-BR`, o `tsc` cobra a existência dela no `en`,
   e **copiar o português para dentro do inglês satisfaz o tipo**. A página inglesa iria para o
   índice com título português sem nenhum portão dizer nada.

### O que o portão NÃO alcança, dito para não ser confundido com cobertura

O template lido no teste é o **fonte** (`web/index.html`); o build injeta nele os `<script>` e
`<link>` dos assets com hash antes do pré-render rodar. Se uma atualização do Vite mudasse a
forma dessa injeção e isso quebrasse uma âncora, o teste continuaria verde. Quem cobre esse
flanco é a conferência de moldura dentro do próprio `montarPagina()`, que roda no build de
verdade e o derruba. Os dois juntos são o portão; nenhum dos dois sozinho é. Registrado nas
Descobertas.

### As medições — cinco mutações, cinco vermelhos

Portão que nunca falhou não é portão, é decoração. Cada classe de erro que a task promete pegar
foi induzida no código e revertida:

| # | A mutação | O que ficou vermelho |
|---|---|---|
| 1 | `urlAbsoluta` volta a devolver caminho relativo (**o bug da T-147**) | `montarPagina` para o build: *"a injeção destruiu a estrutura — faltou `<link rel="canonical" href="https://…" />`"* |
| 2 | título inglês "traduzido" copiando o português | `'sobre' tem título e descrição próprios em cada idioma` |
| 3 | `about/` renomeado para `about-us/` em um idioma só | 7 casos, entre eles `rota gerada sem HTML de entrada no build` |
| 4 | roteador deixa de olhar o slug do idioma | `toda URL do mapa volta pelo ROTEADOR…` — *"`/en/about/` não é uma rota que o roteador conhece"* |
| 5 | **rota `/planos/` nova, título só em português** (critério 7 da spec, ponta a ponta) | `tsc`: *"missing the following properties: `meta.pricing.title`, `meta.pricing.description`"*. Acrescentado o inglês, caem `routes.test.ts` e `paginaGerada.test.ts` por falta de entry no build |

A quinta é o critério de aceite 7 da SPEC-026 executado como experimento: *"um commit que
acrescenta uma rota e esquece o `title` em inglês, ou esquece o sitemap, não passa nos gates"*.
Passou a ser verdade medida, não promessa.

### O processo

`AGENTS.md` ganhou o **§Fluxo 5 — "Rota nova do site nasce na tabela de rotas"**, e a skill
`df-spec` ganhou o par no desdobramento de spec (slug traduzido, chaves de `title`/`description`
no namespace `site`, e a invariante de que **nenhuma camada de idioma é redirecionamento**). A
inserção empurrou os gates para o §Fluxo 6 — a única referência cruzada que existia para o
número antigo, na Descoberta `[T-156]` do BACKLOG, foi corrigida junto.

### O aviso que apareceu no meio

Reexportar o **tipo** da página de `entries/prerender.tsx` produziu cinco avisos de
`react-refresh`: o plugin lê um nome capitalizado dentro de um `export { … }` como componente e
passa a cobrar do arquivo inteiro a regra de módulo de componente. O tipo não precisava estar
ali — quem o consome é o teste, que importa direto, e o `scripts/prerender.mjs` é JavaScript e
não vê tipo nenhum. A linha saiu, com o motivo escrito no arquivo.

**Gates.** `ruff check` e `ruff format --check` limpos, `pytest` verde, `npm run lint` e
`typecheck` sem saída, `npm run test` com **773 testes em 68 arquivos** (eram 726 em 65), e
`npm run build:local` gerando as 4 páginas + `sitemap.xml` + `robots.txt`.

### Pendências

- **A SPEC-026 segue em `draft`** — com a Onda 2 e os portões fechados, ela está pronta para a
  revisão que a passa a `approved`. Só falta a T-165 (páginas por exercício) do §Escopo.
- **T-164**: conferir o card num WhatsApp real depois do deploy (continua aberta).
- Os quatro commits da frente ainda não foram para o `origin`.

---

## 2026-08-19 (84) · T-168 — As duas colunas param de pesar diferente

**O pedido.** Daniel, depois de aprovar a T-167: *"só divida os botões card entre os lados da
tela, do lado esquerdo tem mais que o direito."*

**A medição, antes de mover qualquer coisa.** Alturas tiradas do CSS (`.prep-cell` = 22px de
moldura + conteúdo, `gap: 8px` entre cards):

| | câmera desligada | câmera ligada |
|---|---|---|
| esquerda | ~434px | ~434px |
| direita | ~296px | ~418px |

Com a câmera **ligada** as colunas já estavam quase iguais. O desequilíbrio é do estado de
chegada: o `ZoomControl` (~114px) só é montado com a câmera pronta, então a direita nasce curta
e engorda depois. Somado a isso, `.prep__side` alinhava pelo topo — então os 138px de diferença
apareciam todos embaixo, que é exatamente a forma como o olho lê "um lado tem mais que o outro".

**O que foi feito.**

1. **`Duração` desceu para a coluna direita, encostada na `Preparação`.** As duas são tempo —
   uma é quanto o treino dura, a outra é quanto se tem para chegar na posição — e a travada
   estava fazendo número ímpar no meio dos steppers editáveis. Continua travada nos 30s
   (SPEC-009).
2. **`Espelhar` subiu para o pé da coluna esquerda.** É o card mais baixo da tela (39px: um
   ícone e uma palavra) e sozinho no TOPO da direita deixava aquela coluna começando com um
   talo. No pé da esquerda ele fecha a pilha sem competir com o card do exercício.
3. **`justify-content: safe center` nas duas colunas.** Elas nunca vão ter a mesma altura — o
   `ZoomControl` depende da câmera e o `ViewPicker` depende do exercício ter variação, então
   qualquer divisão que feche a conta num estado abre no outro. Centralizadas, as duas dividem
   o mesmo eixo e a sobra se reparte metade em cima, metade embaixo. O `safe` é para conteúdo
   mais alto que a coluna não sair do alcance da rolagem; navegador que não conhece a palavra
   ignora o valor todo e cai no `flex-start` de antes.

**Depois:** esquerda ~381px; direita ~349px (câmera desligada) e ~471px (ligada). E, no que se
conta em vez de se medir, as colunas ficaram **5 e 5** — ou 4 e 4 quando os dois condicionais
somem juntos.

### A decisão que não é óbvia

**Isto piora o estado de câmera ligada, e mesmo assim é o certo.** Antes: 138px de diferença
desligada, 16px ligada. Depois: 32px e 90px. Trocar 16 por 90 num estado parece regressão — só
que com o alinhamento central o que se vê é metade disso em cada ponta, e o pior caso das duas
telas cai de 69px para 45px. A média também melhora. O ganho vem de a conta não depender mais
de um card que aparece e some.

**O que fecharia de vez, e ficou de fora.** Se o `ZoomControl` não sumisse — um card reduzido
com `--` e sem slider enquanto não há track para ajustar, que é exatamente o que `Ângulo` e
`Calorias` já fazem — as duas colunas ficariam a ~20px de diferença nos dois estados. Não fiz
porque reverte uma decisão explícita da T-120 ("antes disso a escolha ficaria vazia") e isso é
produto, não layout. Registrado nas Descobertas.

**Gates.** `npm run lint`, `typecheck`, `test` (65 arquivos, 726 testes) e `build` verdes.

**Não verificado por mim.** O equilíbrio é para ser visto, e as alturas acima são calculadas do
CSS, não medidas em aparelho — o navegador controlado segue fora do ar nesta sessão. Confirmação
é no celular.

---

## 2026-08-18 (85) · T-164 — O link do produto passa a ter cara de link

**O que foi feito.** `site/social.ts` (Open Graph, Twitter Card e JSON-LD, puros e testados),
injetados pelo pré-render em cada rota × idioma; `public/img/og.jpg` (1200×630, 48 kB), gerada
por `scripts/og-image.html`, que fica no repositório.

**O problema.** O `<title>` normal não alimenta preview de link — WhatsApp, Instagram, LinkedIn,
Telegram, Slack e Discord leem **Open Graph**, e o site não tinha nenhuma. O link do produto
aparecia como caixa cinza. É o canal que motiva a task: no Brasil, app de treino se espalha em
grupo de WhatsApp antes de se espalhar na busca.

**E nada disto funcionaria sem a T-159.** Nenhum desses robôs executa JavaScript; uma tag de OG
escrita em runtime pelo React seria invisível para todos. O pré-render é o que torna esta task
possível — a dependência declarada no BACKLOG não era formalidade.

### As decisões

**A regra que governa os dados estruturados: só o que é verdade verificável.** Nada de
`aggregateRating`, `offers`, contagem de download ou prêmio — são justamente os campos que mais
"rendem" no resultado de busca e os que o produto ainda não tem. É a doutrina do `--` da
SPEC-014 ("a célula existe no design, o dado ainda não"), aqui com um agravante que vale
registrar: dado estruturado inventado é **violação de política do Google** e derruba o rich
result inteiro, não só o campo mentiroso. Virou caso de teste, para o dia em que alguém quiser
"melhorar o resultado de busca".

**A imagem é neutra de idioma, e é decisão, não preguiça.** A arte traz a marca, uma figura de
keypoints em neon violeta (os tokens da SPEC-014) e a legenda bilíngue
*"computer vision · visão computacional"*. O título e a descrição do card já vêm por idioma, nas
tags; uma imagem com frase obrigaria duas artes e as duas a envelhecerem juntas. **Imagem por
rota — nome do exercício sobre a arte — é Fase Evolução da SPEC-026** e ficou de fora de
propósito.

**JPEG, não PNG.** 48 kB contra 494 kB do mesmo desenho. Card de compartilhamento é re-comprimido
pela plataforma de qualquer forma, e 494 kB atrasariam o preview em rede ruim, que é onde ele
mais importa.

**O gerador da imagem mora no repositório** (`scripts/og-image.html`, Canvas 2D). O PNG/JPEG é
artefato, não blob órfão: quem quiser trocar a arte edita o desenho e regenera. Não há
rasterizador nesta máquina (nem `rsvg-convert`, nem ImageMagick, nem `sharp`), então o desenho
roda no navegador — que ainda tem a vantagem de renderizar a fonte de verdade.

**`og:locale` é `pt_BR`, não `pt-BR`.** O formato quer `idioma_TERRITÓRIO`. Um `replace('-','_')`
acertaria o português e erraria o inglês, que não tem território na tag e precisa de `en_US` — o
mapa é explícito para a escolha aparecer quando o terceiro idioma entrar.

### As medições

- **Unitário** (`site/social.test.ts`, 9 casos): `og:locale` mapeado nos dois idiomas; o
  `alternate` lista a outra língua e não a si mesmo; `og:url` e `og:image` absolutos; card
  grande; aspas do título escapadas; o JSON-LD é JSON válido com `SoftwareApplication` +
  `Organization`; nenhum campo inventado; `<` escapado (um `</script>` no texto fecharia o bloco
  e o resto viraria HTML); `@id` da Organization estável entre páginas.
- **No `dist` gerado**: as 16 tags presentes em cada uma das quatro páginas, com título e
  descrição na língua da rota, e o JSON-LD reparseado com sucesso a partir do HTML.
- **Imagem**: JPEG 1200×630, 48.524 bytes, conferida visualmente.
- **Gates**: `ruff check` e `ruff format --check` limpos, `pytest` verde, `npm run lint` e
  `typecheck` sem saída, `npm run test` com **743 testes**.

### Pendências

- **O critério de aceite da task não foi verificado**: ele pede o card conferido num **WhatsApp
  real**, e isso exige o site no ar com a origem de produção. Fica declarado como pendência, do
  mesmo tipo do critério 4 da SPEC-026 (tradução do navegador). O validador do Facebook também
  só funciona com URL pública.
- A arte é substituível a qualquer momento sem tocar em código: trocar `public/img/og.jpg`
  basta, e o gerador está lá para quem quiser partir dele.
- A SPEC-026 segue em **`draft`**.

## 2026-08-18 (84) · T-163 — O mapa e a porta, e o `Disallow` que teria feito o contrário do pedido

**O que foi feito.** `site/descoberta.ts` (os dois arquivos, puros e testados), gerados no
pré-render a partir da tabela de rotas. É a **quarta e última saída** da fonte única prometida
pela SPEC-026 — roteador, pré-render, `hreflang` e agora `sitemap`/`robots` saem todos de
`src/site/routes.ts`.

### A decisão que contraria a redação da task

A linha do BACKLOG pedia *"`robots.txt` liberando o site, mantendo o `/app/` fora"*. A intenção
está certa e o meio estava errado, então implementei o oposto e corrigi a linha.

**`Disallow` impede o RASTREAMENTO, não a indexação.** Um robô que não rastreia `/app/` nunca lê
o `<meta name="robots" content="noindex">` que está lá desde a T-067 — e a URL pode acabar
listada assim mesmo, sem descrição, porque **o site linka para ela** ("Abrir o app" na barra).
Para uma página que não pode ser indexada, o par correto é o inverso do intuitivo: **permitir
rastrear + `noindex` na página**. Bloquear no `robots.txt` desligaria a única instrução que de
fato funciona.

Isso virou caso de teste, e o caso existe para impedir a "correção" bem-intencionada de amanhã —
alguém vai olhar o arquivo, achar que falta um `Disallow`, e o teste vai explicar por que não.

### As outras decisões

**Rastreador de LLM é permitido, e é decisão de produto, não omissão.** GPTBot, ClaudeBot,
PerplexityBot entram pelo `User-agent: *`. Parte da descoberta de produto hoje acontece dentro de
uma conversa, e nenhum deles executa o bundle — é exatamente o público que o pré-render da T-159
passou a atender. Bloqueá-los seria abrir mão do canal para proteger conteúdo institucional que é
público por definição. Está escrito como comentário **dentro do `robots.txt`**, não só aqui: quem
for editá-lo daqui a um ano vai estar olhando para o arquivo.

**Sem `lastmod`.** Carimbar a data do build faria toda página parecer atualizada a cada deploy,
inclusive as que não mudaram. O Google trata `lastmod` não confiável como ruído e passa a
ignorá-lo — data que mente é pior que data ausente. Tem caso de teste.

**`<xhtml:link>` em cada `<url>`, duplicando o `hreflang` do `<head>`.** A duplicação é exigida:
o Google pede que as duas fontes concordem e aceita qualquer uma isolada. Como as duas saem da
mesma `urlAbsoluta()` da T-160, não têm como divergir.

**Gerados, não postos em `public/`.** Um `sitemap.xml` escrito à mão seria a quinta lista que
precisa concordar com as outras quatro — que é a descrição exata do bug que abriu a Fase 8.

### Um teste meu estava grosseiro demais

O caso "não bloqueia o `/app/`" reprovou na primeira execução: eu procurava a palavra `Disallow`
no arquivo inteiro, e ela aparece no **comentário** que explica por que ela não está lá. Um teste
que não distingue diretiva de comentário proibiria justamente a documentação da decisão. Passou a
olhar só as linhas que não começam com `#`.

### As medições

- **Unitário** (`site/descoberta.test.ts`, 8 casos): uma entrada por rota indexável por idioma,
  sem duplicatas; as URLs são exatamente as que a tabela declara; a 404 fica de fora; cada `<url>`
  carrega as alternativas e o `x-default`; todo `loc` e todo `href` são absolutos; nenhum
  `lastmod`; o `robots.txt` libera, aponta o sitemap e não tem diretiva `Disallow`.
- **XML bem-formado**, validado por parser: 4 `<url>`, 3 alternativas em cada.
- **Servidos pelo nginx real**: `/robots.txt` → `200 text/plain`; `/sitemap.xml` → `200 text/xml`.
- **Gates**: `ruff check` e `ruff format --check` limpos, `pytest` verde, `npm run lint` e
  `typecheck` sem saída, `npm run test` com **734 testes**.

### Pendências

- A SPEC-026 segue em **`draft`**.
- O `sitemap.xml` cresce sozinho quando a T-165 acrescentar as páginas por exercício — é o teste
  "lista exatamente as URLs que a tabela declara" que garante isso.

## 2026-08-18 (83) · T-161 — O aviso que sugere sem empurrar

**O que foi feito.** `site/sugestaoDeIdioma.ts` (a decisão, pura e testada), `site/AvisoDeIdioma.tsx`
(a faixa), as chaves `site:hint.*` nas duas línguas e a pele em `styles.css`. Fecha a prioridade
declarada da frente: qualquer estrangeiro usa uma das duas línguas curadas, ou traduz pelo
navegador (T-162), e agora **chega na certa sem ser empurrado**.

**A camada que faltava.** A T-160 cuidou de quem vem da busca — `hreflang` e `x-default` mandam
o buscador para a URL certa. Sobrava quem NÃO veio da busca: quem digitou o domínio, quem clicou
num link compartilhado. Essa pessoa cai em `/`, que é português, seja ela quem for. E a saída
óbvia é proibida: redirecionar por `Accept-Language` ou por IP faria o Googlebot — que rastreia
dos EUA — ver só a versão inglesa, e a portuguesa sairia do índice. Sobra sugerir.

### As decisões

**O aviso é escrito na língua de DESTINO.** É o detalhe que quase todo mundo erra. Um francês em
`/` não lê *"esta página também está disponível em inglês"* escrito em português — para ele o
aviso é `This page is also available in English.` e mais nada. Daí o `translate(sugerido, ...)`
com locale explícito em vez do `useT()` da página, e o `lang={sugerido}` no bloco, que é o que
conta ao leitor de tela e ao tradutor do navegador que aquele trecho está em outra língua.

**Sugere-se o que o APP daria a essa pessoa** (`detectLocale()`), e isso traz de graça a
propriedade que mais importa: **quem já escolheu um idioma explicitamente no app não recebe
sugestão nenhuma**. A escolha explícita continua vencendo, como em toda a SPEC-025. E o francês
recebe inglês por construção — `matchLocale('fr')` é `null`, a cadeia cai em `DEFAULT_LOCALE`,
que é o mesmo destino do `x-default` da T-160. Nenhuma regra especial para francês em lugar
nenhum.

**Dispensou, acabou.** Sem isso o aviso vira faixa de cookie: aparece toda visita, ninguém lê, e
passa a ser custo puro.

**`useSyncExternalStore` no lugar de `useState` + `useEffect`.** A primeira versão usava efeito, e
o `react-hooks` reprovou: *"Calling setState synchronously within an effect can trigger cascading
renders"*. Estava certo — é um render a mais em toda visita para um valor que já se sabe ler de
saída. O `useSyncExternalStore` é a ferramenta certa e já é a da casa (`useLocale`, T-159): o
terceiro argumento é o snapshot de SERVIDOR, e devolver `null` ali **é** a regra "não existe no
HTML pré-renderizado", escrita uma vez e no lugar onde se lê. Isso importa duas vezes: a
hidratação tem de bater com a T-159, e conteúdo diferente para robô e pessoa é cloaking.

**As chaves resolvidas antes do JSX.** O `no-literal-string` roda em `jsx-only` e trata a chave
passada dentro de um atributo como frase solta; a lista de `callees` da regra conhece `t`, não
`translate`. Mexer no portão compartilhado para acomodar um componente seria caro pelo motivo
errado — três `const` acima do `return` resolvem e ainda leem melhor.

### As medições

- **Unitário** (7 casos): o francês em `/` recebe sugestão de **inglês** e o francês em `/en/`
  não recebe nada; o brasileiro que cai em `/en/` por link compartilhado recebe português; quem
  tem escolha explícita gravada não recebe sugestão; dispensado não sugere em nenhuma combinação.
- **No navegador, com o `dist` real servido pelo nginx real** (navegador reportando
  `["pt-BR","pt","pt","en"]`):
  - em `/` (pt-BR): **nenhum aviso** — a pessoa já está na língua dela;
  - em `/en/`: aviso presente com `lang="pt-BR"`, texto *"Esta página também está disponível em
    português."*, CTA *"Ver em português"* apontando para `/`. **A URL continuou `/en/` e o `h1`
    continuou em inglês** — o critério que mais importa: sugeriu, não redirecionou;
  - clicar no × faz o aviso sumir, grava `digitalfit.lang_hint`, e ele **não volta** ao
    recarregar;
  - console **sem nenhuma mensagem** — a hidratação da T-159 continua limpa com o aviso no ar.
- **O aviso não está no HTML pré-renderizado**: `grep -c langhint` devolve 0 nas quatro páginas.
- **Gates**: `ruff check` e `ruff format --check` limpos, `pytest` verde, `npm run lint` e
  `typecheck` sem saída, `npm run test` com **726 testes em 65 arquivos**.

### Pendências

- O critério 2 da SPEC-026 fala em navegador **em francês**. O caso francês está provado no
  unitário (via `resolveLocale`), e no navegador foi provado o espelho exato (pt-BR em `/en/`),
  porque o navegador da bancada reporta português. A conferência com um navegador realmente em
  francês fica junto da T-155.
- A SPEC-026 segue em **`draft`**.

## 2026-08-18 (82) · T-160 — O `hreflang` passa a existir, e o `x-default` responde a pergunta da frente

**O que foi feito.** `src/site/metatags.ts` (puro, testado), os `<link>` gerados e injetados pelo
pré-render, os `hreflang` relativos escritos à mão apagados dos quatro HTML, e a origem pública
do site virando requisito de build — com `VITE_SITE_ORIGIN` derivada no `prod.sh`, exigida no
`compose` e documentada no `DEPLOY.md`.

**O bug que fecha aqui.** A T-147 escreveu `hreflang` à mão, com `href="/"` e `href="/en/"`. A
especificação exige URL absoluta com esquema e host; relativa é ignorada — sem aviso, sem erro,
sem nada em log. O par pt/en que a Onda 2 da i18n entregou **nunca existiu para o Google**. É o
achado que abriu a Fase 8, e desta task em diante ele não pode voltar: os links são gerados da
tabela de rotas, e o teste reprova qualquer `href` que não comece com o esquema.

**E o `x-default` é a resposta para a pergunta que motivou a frente.** *"E quem não é nem pt nem
en?"* — o francês que busca em francês. Ele aponta para `/en/` pelo mesmo motivo que
`DEFAULT_LOCALE` é `'en'` em `i18n/locale.ts`: é a resposta certa para "não sei quem é você". As
duas pontas dizem a mesma coisa de propósito, e há um caso de teste que cai se alguém mudar uma
sem a outra.

### As decisões

**`VITE_SITE_ORIGIN`, e não `VITE_SITE_URL` — divergindo da redação da task, com a linha do
BACKLOG corrigida.** As duas parecem a mesma coisa e não são. `VITE_SITE_URL` responde *"qual a
base para um link de um bundle para o outro"* e é **vazia** no deploy de domínio único, porque
ali o site mora em `/` e o relativo basta (`scripts/prod.sh` só a preenche no modo subdomínio).
`canonical` e `hreflang` fazem outra pergunta — *"em que origem pública esta página vai ser
servida"* — e essa tem resposta nos dois modos. Reaproveitar a primeira deixaria o deploy de
domínio único, que é o de hoje, sem anotação nenhuma.

**Exigir em vez de deduzir.** A T-159 emitia `canonical` só quando conhecia a origem e o omitia
calado quando não. Omitir é melhor que escrever relativo, mas continua sendo página sem anotação
indo para produção sem ninguém ver — e silêncio é exatamente como o `hreflang` da T-147
sobreviveu meses. Agora o build **para**, com uma frase que diz o que fazer.

**`build` estrito e `build:local` separados.** O estrito é o do deploy (é o que o Dockerfile
roda) e falha sem a variável. O `build:local` existe para conferir o artefato na máquina sem
inventar uma origem de produção: ele usa `http://localhost:4173`, e a origem de mentira fica
visível no HTML gerado, deixando claro que aquele build não é para servir. A alternativa — um
default silencioso — traria de volta exatamente o modo de falha que a task inteira combate.

**Cada idioma aponta para si mesmo também.** Auto-referência é exigência do formato e o erro mais
comum de quem escreve `hreflang` à mão. Tem caso de teste próprio.

### O portão da T-154 pegou uma frase minha

`npm run test` reprovou com uma frase em português viva em `metatags.ts`. Ela estava dentro de um
`throw new Error(...)`, que é contexto isento — mas o portão olha os **120 caracteres anteriores**
ao literal, e a mensagem estava quebrada em três literais concatenados: o terceiro caía fora da
janela. O portão estava certo e a forma da mensagem é que estava errada; virou uma interpolação
só. Registro porque é a segunda vez que um portão desta casa se paga numa task que não é a dele.

### As medições

- **Unitário** (`site/metatags.test.ts`, 11 casos): todo `href` gerado começa com o esquema, em
  todas as rotas × idiomas; o par é recíproco e inclui a auto-referência; o `canonical` muda com
  o idioma da página; o `x-default` aponta para o inglês; `exigirOrigem` recusa `undefined`,
  `''`, `/`, host sem esquema e origem com caminho.
- **No artefato de deploy real** (`docker build` com
  `VITE_SITE_ORIGIN=https://pratice.magmacursosltda.com.br`): as quatro páginas com `canonical`
  próprio e os três `alternate` absolutos. `/sobre/` e `/en/about/` apontam uma para a outra, e o
  `x-default` de cada uma vai para a versão inglesa **daquela rota** — não para a home.
- **O caminho negativo**: `docker build` sem o `--build-arg` morre no pré-render com
  `VITE_SITE_ORIGIN inválida`.
- **Gates**: `ruff check` e `ruff format --check` limpos, `pytest` verde, `npm run lint` e
  `typecheck` sem saída, `npm run test` com **719 testes em 64 arquivos**.

### Pendências

- `robots.txt` e `sitemap.xml` (T-163) continuam sem existir — e o `sitemap` sairá da mesma
  tabela de rotas e da mesma `urlAbsoluta()` desta task.
- A SPEC-026 segue em **`draft`**.

## 2026-08-18 (81) · T-159 — O HTML passa a chegar pronto, e dois bugs mudos apareceram no caminho

**O que foi feito.** `src/entries/prerender.tsx` (a árvore montada em Node), `vite.ssr.config.ts`
(a segunda passada do build), `scripts/prerender.mjs` (a injeção), `SiteApp` sem nenhum acesso a
`window`/`document`, `hydrateRoot` no entry do navegador, e `title`/`description`/`canonical`
gerados a partir da tabela de rotas. O `<body>` do site deixou de ser `<div id="root"></div>`.

**Por que esta é a task que paga a frente.** Duas consequências do body vazio, e a segunda quase
ninguém enxerga: o robô não lê (o Google só na segunda onda; WhatsApp, LinkedIn e rastreadores
de LLM, nunca), e **o Chrome não oferece traduzir** — ele decide analisando o texto do HTML da
resposta, e sem texto não há idioma a detectar. A camada "Traduzir" da SPEC-026 estava desligada
sem ninguém ter decidido isso. Uma tarefa, os dois problemas.

### O bug que só aparece como "a página está na língua errada"

O primeiro pré-render saiu com o `<title>` em português e o `<h1>` em inglês **na mesma página**.

A causa é do tipo que esta fase existe para caçar: **o zustand v5 monta o `useSyncExternalStore`
com `selector(api.getInitialState())` como *server snapshot***, e o React usa esse terceiro
argumento em toda renderização de servidor. O estado inicial do store de idioma vem de
`detectLocale()`, que em Node não tem `window` e cai em `DEFAULT_LOCALE` — então todo componente
renderizava em inglês por baixo, enquanto o `<title>`, que sai de um `t()` direto sem hook, saía
certo. Nenhum erro, nenhum aviso.

A correção é `useLocale()` em `i18n/index.ts`: `useSyncExternalStore` com o estado **atual** como
snapshot de servidor, e todos os sete leitores de locale migrados para ela. Uma regra só ("leia o
locale por `useLocale()`") é mais barata de manter do que "use o store, exceto nos componentes
que um dia forem pré-renderizados".

### O segundo bug, e foi o navegador que o achou

Depois de corrigir o primeiro, `/sobre/` continuava saindo em inglês no cliente. O `curl` dizia
que o servidor mandava português; o DOM dizia outra coisa. A verificação no navegador mostrou
`document.documentElement.lang === ''`.

O comentário que eu mesmo escrevi no topo de `sobre/index.html` citava a palavra `<title>` — e o
regex de injeção era **não-guloso**: o casamento começou dentro do comentário, correu até o
`</title>` do `<head>` e levou junto a tag de abertura do documento e a do cabeçalho. Sem `lang`,
o cliente caía no `DEFAULT_LOCALE` e re-renderizava a landing inteira em inglês **por cima** do
HTML português, silenciosamente.

Corrigido em três frentes, porque uma só não bastava:

1. O regex passou a `[^<]*` — uma classe que não casa `<` não consegue atravessar uma tag.
2. O comentário do arquivo foi reescrito e ganhou a regra ("não escreva nome de tag entre sinais
   de menor/maior neste arquivo"), porque a defesa barata é não criar a armadilha.
3. **O script confere a moldura depois de injetar** e falha o build se `<html lang="`, `<head>`,
   `</head>` ou o título novo não estiverem lá. Injeção em HTML por expressão regular é frágil
   por natureza; o preço de usá-la é conferir. Um `<html>` comido não aparece como erro — aparece
   como a página na língua errada, semanas depois.

### As outras decisões

**Config de SSR em arquivo próprio.** O callback de `defineConfig` recebe `isSsrBuild`, mas ele
não chega populado quando a entrada vem pela linha de comando — o build falhava com *"input
should not be an html file when building for SSR"*. `vite.ssr.config.ts` torna a intenção
explícita e não depende de detecção de flag, que é o tipo de coisa que volta a quebrar numa
atualização.

**`SiteApp` ficou puro, e os entries viraram os únicos módulos que conhecem o navegador.** Ler a
URL e o `<html lang>` migrou para `entries/site.tsx`; quem monta a mesma árvore no build é
`entries/prerender.tsx`. Um componente que lê `document` no import não renderiza fora do
navegador — e manter as duas pontas simétricas é o que impede o pré-render de divergir da tela.

**`hydrateRoot` quando há conteúdo, `createRoot` quando não há.** As duas metades são de verdade:
as rotas indexáveis chegam prontas; a 404 chega vazia de propósito, porque não tem idioma para
ser renderizada em build (é a resposta a uma URL que não existe). Escolher pela presença do
conteúdo evita um terceiro lugar para desincronizar.

**`canonical` só com origem absoluta.** Deploy em subdomínio passa `VITE_SITE_URL`; o de domínio
único não passa nada, e o bundle não descobre o host sozinho. Omitir é melhor que escrever um
relativo que o buscador ignora em silêncio — que é exatamente o bug do `hreflang` da T-147. **A
T-160 fecha isto**: ela precisa de origem absoluta para o `hreflang` e o `x-default`, e quando a
tiver como requisito de build o `canonical` deixa de ser condicional.

### As medições

- **As quatro páginas, servidas pelo nginx real, lidas sem executar o bundle**: `/` (pt-BR,
  12.301 B no `#root`), `/en/` (en, 12.210 B), `/sobre/` (pt-BR, 4.540 B), `/en/about/` (en,
  4.508 B) — cada uma com `lang`, `<title>`, `<meta description>` e `<h1>` na própria língua.
- **Hidratação**: aba limpa, build corrigido, `/sobre/` e `/en/` sem **nenhuma** mensagem de
  console. `#root` marcado com `__reactContainer$`. O HTML do servidor e o DOM final do cliente
  comparados byte a byte: **idênticos**. (O React #418 visto antes era mensagem retida no buffer
  da aba do build quebrado — a aba nova não o reproduz.)
- **O invariante pega o que promete**: reintroduzida a armadilha no comentário E afrouxado o
  regex, o build morre com *"a injeção destruiu a estrutura — faltou `<html lang="`"*; com a
  armadilha e o regex estreito, passa.
- **Caminho de deploy**: `docker build -f docker/web.Dockerfile` com
  `VITE_SITE_URL=https://exemplo.com.br/` conclui, roda o pré-render dentro da imagem, e as
  quatro páginas saem com `canonical` absoluto correto. `dist-ssr/` **não** chega ao runtime.
- **Gates**: `ruff check` e `ruff format --check` limpos, `pytest` verde, `npm run lint` e
  `typecheck` sem saída, `npm run test` com **708 testes em 63 arquivos**.

### Pendências

- `canonical` condicional à origem (acima) — **T-160**.
- A 404 continua sem pré-render, por decisão registrada, não por esquecimento.
- A SPEC-026 segue em **`draft`**.

## 2026-08-18 (80) · T-158 — O site ganha URLs, e uma URL errada passa a doer

**O que foi feito.** `src/site/routes.ts` (a tabela de rotas), o roteador lendo
`location.pathname` no lugar de `window.location.hash`, `/sobre/` e `/en/about/` como
documentos de verdade no build, uma tela de 404, o `try_files` do site trocado por `=404` com
`error_page`, e a regra de `no-cache` que faltava para três dos cinco `index.html`.

**O problema, em uma frase.** O site tinha duas URLs indexáveis no mundo inteiro. `#/sobre` é
fragmento, e fragmento não viaja no pedido HTTP: o servidor nunca o vê e o buscador trata `/` e
`/#/sobre` como a mesma página. Nenhuma quantidade de metadado conserta isso — não havia o que
anotar.

### As decisões

**Uma tabela, quatro saídas.** Roteador, pré-render (T-159), `hreflang` (T-160) e `sitemap.xml`
(T-163) respondem à mesma pergunta — "quais páginas existem, em que idiomas, com que endereço" —
e até aqui cada um responderia por conta própria. Foi essa independência que produziu o bug que
abriu a Fase 8: a T-147 escreveu `hreflang` à mão, relativo, e ficou inerte por meses sem nada
acusar. `routes.ts` passa a ser a fonte, e o `routes.test.ts` confronta a tabela com a lista de
entries do `vite.config.ts` — as duas listas que precisam concordar agora se conhecem.

**Slug traduzido, decidido pelo Daniel.** `/sobre/` ↔ `/en/about/`, e não `/en/sobre/`. A
palavra na URL é sinal de busca, que é o objetivo declarado da frente; o custo é uma entrada a
mais por rota, no lugar onde ela deve doer.

**Navegação de documento, não SPA.** Sumiu o `useSyncExternalStore` de `hashchange`: com cada
tela num documento próprio, a rota não muda durante a vida da página e o `subscribe` estaria
assinando um evento que não acontece. O custo é uma ida à rede por clique, e é barato — o bundle
do site já está em cache e não há estado de sessão a preservar. Em troca, cada URL vira um
documento, que é a condição para o pré-render e para o sitemap existirem.

**Cada rota virou entry do Vite, e isso é o que torna o 404 possível.** Enquanto o site fosse
servido por fallback (`try_files ... /index.html`), qualquer caminho errado devolveria **200 com
a landing** — o *soft 404*. Com `sobre/index.html`, `en/about/index.html` e `404.html` no build,
o nginx pôde passar a `=404` de verdade. A ordem das duas coisas não é escolha: 404 exige
arquivo conhecido.

**A 404 é uma tela React, não um HTML com frases dentro.** Um `404.html` escrito à mão seria a
única superfície do produto fora do portão do texto nas duas línguas (AGENTS §Fluxo 4) — e
justamente a que ninguém abre para conferir. E o idioma dela segue a **preferência do aparelho**,
divergindo do resto do site de propósito: "site por URL" existe porque o buscador escolhe pela
URL, e aqui a URL não existe. Sem URL para perguntar, a pergunta certa é a do `/app/`.

**O `internal` no `location = /404.html`.** Sem ele a página de erro teria URL própria e
responderia 200 — o soft 404 voltando pela porta dos fundos, agora com endereço fixo.

**O "301" do `#/sobre` é do lado do cliente, e não podia ser diferente.** O fragmento não chega
ao servidor: ele recebe `GET /` e não tem como saber que havia um `#/sobre`. Roda antes do React
montar, com `location.replace` e não `history.replaceState` — a navegação de verdade traz o
documento certo (título, canonical, hreflang daquela rota), enquanto o `replaceState` mudaria a
barra de endereço e deixaria os metadados da página anterior. Meia-correção é o que esta frente
existe para não repetir.

**Título e descrição saíram do HTML e entraram no dicionário.** `site:meta.<rota>.*`. É a
consequência que paga a mudança: `tsc -b` passa a reprovar rota nova sem título em inglês, pelo
gate que a T-142 já construiu. Os `<title>` estáticos dos HTML ficaram como cópia temporária,
anotada em cada arquivo — a T-159 passa a gerá-los da tabela e a duplicação morre com ela.

### As medições

Com o `dist/` real servido pelo `docker/web-nginx.conf` real (`nginx:1.27-alpine`, porta 8099):

| URL | status |
|---|---|
| `/` · `/sobre/` · `/en/` · `/en/about/` · `/app/` | **200** |
| `/app/qualquer-coisa` | **200** (fallback do SPA preservado — o app é `noindex`) |
| `/nao-existe` | **404** |
| `/404.html` direto | **404** (o `internal` funcionando) |

- `Cache-Control: no-cache` presente nos **cinco** `index.html`. Antes eram dois; `/en/index.html`
  estava sem desde a T-147.
- Corpo servido em `/nao-existe`: a 404 de verdade, com `noindex` e
  `<title>Page not found — Digital Fit</title>`.
- Build: seis HTMLs (`index`, `en/index`, `sobre/index`, `en/about/index`, `404`, `app/index`).
- Gates: `ruff check` + `ruff format --check` limpos, `pytest` verde, `npm run lint` e
  `typecheck` sem saída, `npm run test` com **708 testes em 63 arquivos**.

### Pendências e descobertas

- **O bundle do site passou de 8,8 kB para 11,27 kB** (2,84 kB gzip). Vem da tela de 404 e da
  tabela de rotas. A ADR-010 cita o número antigo ao justificar a fronteira SITE|APP; a ordem de
  grandeza contra os 291 kB do app não mudou, então a ADR continua válida — mas o número dela
  está velho e fica registrado aqui.
- Os `<title>`/`<meta description>` estáticos dos seis HTML duplicam o dicionário até a T-159.
  É hand-off declarado, não dívida esquecida: está escrito em cada arquivo.
- A SPEC-026 segue em **`draft`**.

## 2026-08-18 (79) · T-162 — Deixar traduzir sem deixar quebrar

**O que foi feito.** `translate="no"` nas regiões que o React reescreve durante a sessão —
valores da `StatsBar`, relógio do `TimerRing`, corpo do `CoachTip`, números do `ReportSheet` —,
`SiteApp` decidindo idioma por `matchLocale()` em vez de `=== 'en'`, o motivo do locale
resolvido escrito no `i18n/http.ts`, e um portão novo (`i18n/traducao.test.ts`) que cobra a
marcação. Primeira task de código da Fase 8, e a única que não depende das URLs.

**A ideia por trás.** O produto tem duas línguas curadas e vai continuar tendo. A terceira,
quarta e quadragésima língua são a tradução do navegador — de graça, sem manutenção, e é a
camada "Traduzir" da SPEC-026. Aceitar isso tem um preço em duas moedas: número traduzido por
máquina é ruído com risco, e o Google Translate embrulha cada nó de texto num `<font>`, o que
põe uma tela que redesenha texto a cada repetição na rota de uma classe conhecida de falha do
React. As duas se pagam com o mesmo atributo.

### As decisões

**Marcação cirúrgica, não cortina.** `translate="no"` foi nos VALORES, nunca na barra inteira.
"Repetições"/"Reps", "restantes", "Detalhes" são exatamente o que alguém que ligou a tradução
quer ler na própria língua — e só mudam quando o locale muda, que é o caso em que o React
redesenha tudo de qualquer forma. Cobrir o container faria o app parar de quebrar e a camada
"Traduzir" morrer junto, em silêncio. Virou o terceiro caso de teste do portão, justamente para
impedir a "correção" preguiçosa de amanhã.

**O card do treinador foi protegido, e isso custa alguma coisa.** É o texto que mais muda na
sessão e a superfície mais exposta — mas também é a frase que um estrangeiro mais gostaria de
ler traduzida. Escolhido proteger, pelo argumento da SPEC-026 §Escopo: o app já existe em duas
línguas curadas, e perder a dica é melhor que perder a sessão no meio do treino. Registrado
aqui porque é troca, não ganho puro.

**Recusado o teste que a task pedia, e a linha do BACKLOG foi corrigida em vez de contornada.**
A redação original dizia "teste que simula o embrulho em `<font>` e prova que o HUD sobrevive a
um redesenho". Ele não foi escrito, por um motivo que não é de esforço: **quem honra
`translate="no"` é o tradutor do navegador** — não o React, não o DOM. Um teste desses provaria
que o *bug* existe, não que a *correção* existe, e ainda exigiria `jsdom` como dependência de
desenvolvimento (o repositório roda `environment: 'node'`), num projeto que recusou 50 KB de
`i18next` por um `t()`. O que regride de verdade é a marcação sumir sem ninguém notar, e é isso
que o portão cobra — mesma doutrina do `portoes.test.ts`: mirar o modo de falha real da equipe
(esquecer) em vez de perseguir prova exaustiva que ninguém mantém.

**`matchLocale()` no `SiteApp`, e o fallback mudou junto.** A comparação `=== 'en' ? 'en' :
'pt-BR'` respondia certo para exatamente dois valores; um `/es/` futuro cairia no PORTUGUÊS em
silêncio — página em espanhol, dicionário em português, nenhum erro em lugar nenhum. O fallback
passou de `'pt-BR'` para `DEFAULT_LOCALE` de propósito: é a mesma resposta que o `x-default` da
SPEC-026 dá ao robô, e as duas pontas passam a dizer a mesma coisa.

### As medições

- **O portão pega o que promete pegar**, provado por mutação no fonte real: removida a marcação
  do `ring__time`, o teste ficou vermelho apontando a tag inteira
  (`<p className="ring__time tabular">`); restaurada, verde. Não é um portão que só sabe dizer
  "está tudo bem".
- **React emite o atributo**: `renderToStaticMarkup` de um `<p translate="no">` contém
  `translate="no"` no HTML (medido com um teste temporário, removido em seguida).
- **Gates**: `ruff check` e `ruff format --check` limpos (176 arquivos), `pytest` verde,
  `npm run lint`/`typecheck` sem saída, `npm run test` com **698 testes em 62 arquivos**.

### Critérios de aceite da SPEC-026 conferidos

- **3** (navegador em francês abre `/app/` e recebe inglês) — já coberto por
  `i18n/locale.test.ts:56`, que prova `resolveLocale(null, ['fr-FR','de-DE'])` →
  `DEFAULT_LOCALE`. Entrou na conferência para não regredir, não como entrega desta task.
- **4** (traduzir o `/app/` e treinar 30 s sem derrubar a tela) — **pendência declarada**. Exige
  navegador real com tradução ligada e uma sessão de verdade; nada neste repositório simula o
  tradutor. É verificação de aparelho, e vai junto da T-155.

### Pendências

- Critério 4 da SPEC-026 aguarda verificação em aparelho real (acima).
- A SPEC-026 continua em **`draft`** — a T-157 a escreveu e a revisão do Daniel é o que a leva a
  `approved`. Esta task foi executada porque não toca nenhuma decisão em disputa da spec.
- **Sessão paralela no mesmo repositório.** No meio desta task apareceu na árvore uma alteração
  em `web/src/styles.css` que não era daqui (largura do hero, `min(76%, 210px)` →
  `min(82%, 210px)`); ficou de fora do stage, e pouco depois ela foi commitada pela própria
  sessão vizinha como **T-167**. Nenhuma colisão de numeração — a Fase 8 reservou T-157…T-166 —,
  mas fica o registro de que duas sessões escreveram no `master` no mesmo dia, e que o commit
  desta task nasce em cima daquele.

## 2026-08-18 (78) · T-167 — A pré-configuração para de esconder o quadro

**O pedido.** Daniel, usando o app: *"a janela onde mostra com nitidez a pessoa está muito
pequena e o borrado está muito forte; não dá pra perceber o espaço ao redor da pessoa com
facilidade, atrapalhando o posicionamento do celular."*

**O que foi feito.** Quatro mudanças na pré-configuração, todas na mesma direção — devolver a
leitura do quadro a quem está do outro lado do celular:

1. **Cortina → véu.** Os quatro painéis da T-080 iam de `blur(16px) brightness(.42) saturate(.85)`
   mais um preto chapado de 34% — o entorno ficava em ~28% da luz original. Agora é
   `blur(5px) brightness(.66) saturate(.92)` e o escurecimento virou GRADIENTE: denso na borda da
   tela, que é onde mora o texto sem card, quase transparente na borda da janela, que é onde mora
   o corpo. Os dois laterais são os mais leves dos quatro, porque 92 dos 106px da faixa esquerda
   já estão cobertos por cards — ali o wash não comprava legibilidade nenhuma, só tapava a única
   coisa que a pessoa precisava ver de lado.
2. **A janela cresceu, e nas quatro bordas.** Horizontal: as colunas encostaram na borda (8+92+6
   e 8+96+6, contra 12+92+8 e 12+96+8) — os cards **não** encolheram, porque o chip "ver exemplo"
   já ocupa a largura inteira deles; o que saiu foi margem morta. Vertical: as duas constantes
   viraram medição (ver abaixo). E saiu o `inset 0 0 50px rgba(5,7,13,.45)` da moldura, que numa
   janela de 174px de largura não era acabamento de borda — vinhetava a janela inteira.
3. **A silhueta-guia parou de ser cortada.** Ela era `170px` fixos dentro de uma janela que tinha
   **162px** num iPhone de 390: com `overflow: hidden`, pulsos e pernas saíam cortados. A guia
   ensinava um enquadramento que não cabia nela mesma. Virou `min(82%, 210px)` com
   `aspect-ratio: 2/3` (o do `viewBox`).
4. **Chip "quadro cheio".** Toque e o cromo inteiro sai — cabeçalho, colunas, rodapé, os quatro
   véus —, sobrando a imagem de borda a borda com a guia. Toque em qualquer lugar volta.

### As decisões

**A janela deixou de ter constante vertical, e isso é conserto de bug, não refinamento.**
`--prep-win-bottom: 150px` foi medido num rodapé sem `env(safe-area-inset-bottom)`. Em iPhone com
entalhe o rodapé real é ~34px mais alto, então a borda de baixo da janela caía **dentro da tab
bar** — e a faixa que ela prometia mostrar e não mostrava é onde ficam os PÉS de quem se
enquadra. Constante nova só adiaria o problema para o próximo aparelho. Agora o `usePrepWindow`
mede cabeçalho e rodapé com `ResizeObserver` e a conta pura mora em `session/prepWindow.ts`, com
tabela de testes — mesma doutrina do `startGate`. Vem de graça: título que quebra em duas linhas
noutro idioma (SPEC-025) e o CTA trocando de altura entre os dois degraus da T-120 deixam de
desalinhar a janela.

**O achado que explica o relato inteiro: a janela nítida nunca foi o recorte que a análise usa.**
A pose sai do `<video>` inteiro (`detectPose(landmarker, video)` em `useEdgePipeline`). O quadro
de verdade é a TELA — tudo que a cortina escondia estava sendo analisado. A moldura comunicava
"seu quadro é isto" sobre uma coisa que não era o quadro, e quem se posicionava pela janela se
posicionava por uma borda que o modelo não conhece. É por isso que o chip de quadro cheio não é
enfeite: é a única superfície da tela que mostra o que a análise realmente vê. A pergunta de
produto que sobra — a guia deveria pedir o corpo dentro da janela ou dentro da tela? — ficou
registrada nas Descobertas, porque responder "da tela" é revisão de spec, não ajuste de CSS.

**Estado derivado e não efeito.** A primeira versão do quadro cheio corrigia o estado num
`useEffect` quando a câmera caía ou a tela trocava; o `react-hooks/set-state-in-effect` reprovou,
e com razão — seria um render a mais com a tela errada no meio. O estado guarda só a intenção
(`pediuQuadroCheio`) e o valor que vale é uma conta de render.

**O véu clareou porque o card passou a se sustentar sozinho.** `.prep-cell` foi de
`--surface` (0.8) para `rgba(10,14,26,.9)`, e título/subtítulo — o único texto da tela sem fundo
próprio — ganharam `text-shadow`. O contraste do cromo vinha metade dele mesmo e metade da
cortina; sem trocar essa dependência, clarear o fundo teria custado legibilidade.

**Gates.** `npm run lint`, `npm run typecheck` e `npm run test` (61 arquivos, 690 testes) verdes;
`ruff check` + `ruff format --check` + `pytest` verdes (nada de Python foi tocado).

**Pendências geradas.** Duas Descobertas no BACKLOG: a pergunta da guia (janela × tela), e os
vizinhos do rodapé (`.sess__cam--prep .stage__banner`/`.stage__dev` e o pill de saída) que
continuam se posicionando por soma de constantes — o mesmo tipo de conta que pôs a janela dentro
da tab bar.

**Não verificado por mim.** Câmera e área segura precisam de aparelho real com HTTPS; o Daniel
testa no celular. O que rodou aqui foi a tabela de geometria e os gates.

---
## 2026-08-18 (77) · T-157 — SPEC-026: o site existe e ninguém consegue achar

**O que foi feito.** `docs/PLANO-SEO.md` (o mapeamento e o sequenciamento em ondas),
`specs/SPEC-026-descoberta-e-idioma-de-acesso.md` (o contrato, em `draft`), a **ADR-012** no
`ARCHITECTURE.md` e o bloco **Fase 8** no `BACKLOG.md` com dez tasks (T-157…T-166). Nenhuma
linha de código: esta é a task que decide o que as outras nove vão fazer.

**A pergunta que abriu a frente.** Depois da Fase 7, o produto fala duas línguas — e continua
invisível. A conversa começou em "o site não vai ter SEO né?", e o mapeamento respondeu pior do
que a suspeita: não é que falte SEO, é que **as anotações que existem estão inertes**. A T-147
escreveu `hreflang` com `href="/"` e `href="/en/"`, e a especificação exige URL absoluta com
esquema e host — relativa é ignorada em silêncio. O par pt/en que a Onda 2 da i18n entregou, e
que o `LocaleSwitch` respeita corretamente, **não existe para o Google**. Somado a isso: o site
tem duas URLs indexáveis no mundo inteiro (o `#/sobre` é fragmento, não URL) e as duas chegam ao
robô como `<div id="root"></div>`.

### As decisões

**A descoberta que reordenou o plano inteiro: o pré-render é o que liga a tradução do
navegador.** O Chrome decide se oferece "Traduzir esta página" analisando o texto do HTML da
*resposta* — com o `<body>` vazio, não há idioma para detectar e a oferta não aparece de forma
confiável. A prioridade declarada pelo Daniel ("qualquer estrangeiro usa uma das duas ou traduz
automaticamente se quiser") e a correção de SEO são, portanto, **a mesma tarefa**. Isso pôs a
T-159 no caminho crítico e deixou T-160/T-161 dependendo só das URLs, não do pré-render — a
prioridade fecha antes da metade do plano.

**Metade da prioridade já estava entregue e ninguém tinha percebido.** Um francês abre `/app/`
hoje e recebe inglês: `resolveLocale(null, ['fr-FR','fr'])` → `matchLocale('fr')` devolve `null`
→ `DEFAULT_LOCALE`. O `en` como fallback (e não `pt-BR`) foi escolhido na T-142 exatamente com o
argumento "`en` é a resposta certa para não sei quem é você". O `x-default` da SPEC-026 aponta
para `/en/` pelo mesmo motivo — as duas pontas passam a dizer a mesma coisa, e é assim que devem
ser lidas. O furo era inteiramente a raiz do site.

**Rejeitado: migrar para Next — e virou ADR-012, porque é a pergunta que volta.** A proporção
decide: `site/` + `entries/` somam 466 linhas de 22.516 em `web/src/`; a superfície que precisa
de SEO é 2% do frontend, e os 98% restantes (câmera, MediaPipe WASM, máquina de sessão por
frame) virariam uma ilha `'use client'` onde tudo que o Next tem de valioso fica inerte. Três
agravantes que fecham a conta: a fonte de conteúdo é o **Postgres**, não o sistema de arquivos —
o que anula o trunfo de roteamento por arquivo e exigiria em produção um processo Node que a VPS
de 4 vCPU (com dois pose-workers) não tem folga para hospedar; o encanamento atual foi *medido*
e é caro de refazer (o `gzip_http_version 1.0` que transformou 11.532.084 bytes em 3,2 MB no
waterfall de um celular real); e a coerência com a régua que a SPEC-025 já aplicou ao recusar
50 KB de `i18next`. O substituto tem ~150 linhas de script de build. A ADR-010 é o que torna a
decisão barata de errar: SITE e APP já são bundles e origens distintos, então o site sai para
artefato próprio no dia em que virar operação de conteúdo — e o `/app/` nunca vai junto.

**Rejeitado, de novo e por um motivo novo: decidir idioma por IP.** A SPEC-025 já havia recusado
GeoIP pelo argumento da pessoa (quem mora fora e fala português deve receber português). Apareceu
um segundo argumento, independente e mais duro: **o Googlebot rastreia dos Estados Unidos** —
redirecionar `/` por IP ou por `Accept-Language` faria o robô ver só a versão inglesa e apagaria
a portuguesa do índice. Virou invariante escrita da SPEC-026: nenhuma das três camadas do idioma
de acesso redireciona ninguém. O aviso client-side substitui o redirect, e vai **na língua de
destino** — um francês em `/` lê `View in English →`, não uma frase em português explicando que
existe inglês.

**Curado × traduzido, como promessa de produto.** `pt-BR` e `en` são curados (tom de treinador,
revisados, layout conferido); qualquer outra língua é tradução automática **do navegador**, e o
produto não promete qualidade nela. Rejeitado traduzir os dicionários por máquina para N idiomas:
a string passaria a morar no bundle com a marca do produto em cima, assumindo uma qualidade não
revisada, e multiplicaria a T-155 por N a cada release. É o que permite ser global sem prometer
quarenta idiomas.

**Metadados de rota mudam de endereço: saem do HTML e entram no dicionário.** `title` e
`description` viram chaves do namespace `site`, resolvidas no pré-render. A consequência é o
ponto todo: `tsc -b` passa a reprovar rota nova sem título em inglês, pelo portão que a T-142 já
construiu — sem regra nova e sem ninguém lembrar de conferir. É o critério 7 da spec, irmão do
critério 5 da SPEC-025.

**Uma tabela de rotas, quatro saídas.** Roteador, pré-render, `sitemap.xml` e `hreflang` passam a
ser derivados de `web/src/site/routes.ts`. Foi a independência entre esses quatro que produziu o
`hreflang` inerte: quatro lugares que precisam concordar e nenhum mecanismo obrigando. Com fonte
única, "rota nova sem sitemap" deixa de ser *possível* em vez de deixar de ser *esquecido* — a
mesma doutrina do dicionário tipado da SPEC-025.

### Descobertas registradas no caminho

Cinco armadilhas foram para o §Notas técnicas da spec, cada uma com a task dona: o `hreflang`
relativo (T-160); o `<font>` que o Google Translate embrulha em cada nó de texto e faz o React
quebrar com `removeChild` ao redesenhar — risco concentrado em `hud/StatsBar.tsx` e
`hud/CoachTip.tsx`, que trocam texto durante o treino (T-162); o `try_files` que devolve **200**
com a home para qualquer URL errada, o *soft 404* (T-158); `SiteApp.tsx:22` decidindo idioma por
`=== 'en'` em vez de `matchLocale()`, que mandaria `/es/` para o português em silêncio (T-162); e
`/en/index.html` sem a regra de `no-cache` que os outros dois entries têm — irmão exato do bug
que aquelas linhas existem para evitar (T-158).

### Pendências

- A SPEC-026 está em **`draft`**. Vai para `approved` na revisão do Daniel, e é o que libera as
  outras nove tasks.
- A **T-155** (revisão de tradução e layout da Fase 7) continua `todo` e não foi absorvida por
  esta frente — é trabalho de qualidade da i18n, não de descoberta.

## 2026-08-18 (76) · T-156 — O fuso do fogo: a virada do dia passa a ser a de quem treina

**O que foi feito.** `FUSO_DO_FOGO` deixou de ser São Paulo para todo mundo. O dia a que uma
sessão pertence, a meta diária e o TTL do cache do engajamento passam a ser resolvidos no fuso
de quem treina, declarado pelo aparelho num cabeçalho `X-Timezone`. Módulo novo
(`server/api/fuso.py`), `dia_sp` → `dia_do_fogo(quando, fuso)`, `Sessao.dia` → `dia_em(fuso)`,
`resumo(..., fuso=)`, `ttl_ate_a_virada(agora, fuso)`, o fuso na chave do cache, `X-Timezone` no
CORS, e o cliente mandando o fuso e alinhando o fogo fantasma do visitante ao mesmo relógio.

**O bug não aparece como erro — aparece como streak que quebra sozinho.** Quem treina às 22h em
Lisboa tinha a sessão contada no dia seguinte, e via a sequência zerar por causa de um fuso, não
de um treino. É o pior modo de falha possível numa mecânica de retenção: silencioso, e do lado de
quem estava certo. O argumento que a SPEC-019 usou para escolher SP contra UTC ("meia-noite UTC é
21h no Brasil") passou a valer, palavra por palavra, contra o próprio SP.

### As decisões

**Cabeçalho do aparelho, e não campo no perfil — divergindo do que a spec previa.** A Fase
Evolução da SPEC-019 dizia "fuso por usuário (campo no perfil, default SP)". Implementei
diferente e atualizei a spec dizendo por quê: a mesma pessoa treina no celular em viagem e no
notebook em casa, e "hoje" é o do relógio que ela está olhando. Campo no perfil exigiria conta —
treinar sem conta é garantia da SPEC-011 — e manteria sincronizada à mão uma resposta que o
navegador já dá sozinho. É a mesma doutrina do `Accept-Language` (SPEC-025 §3.4): o cliente
resolve, o servidor obedece. O campo de perfil continua fazendo sentido como **override**
explícito, e ficou registrado na Evolução como isso.

**O default continua São Paulo, e é conservador de propósito.** Cliente antigo, `evalctl`, teste
e qualquer chamada sem o cabeçalho veem exatamente o dia de antes. Trocar o default para UTC
seria uma "correção" que quebraria streaks reais para consertar um caso que ainda não existe.

**`dia_sp` virou `dia_do_fogo`, e o rename é o ponto.** O nome passou a mentir no instante em que
o fuso deixou de ser sempre o de São Paulo — um parâmetro novo num nome velho teria deixado a
mentira no código. Mesma razão de `Sessao.dia` (`@property`) virar `dia_em(fuso)`: uma
propriedade sem argumento só poderia responder pelo default, e responderia **com a cara de quem
sabe a resposta certa**, que é exatamente como um bug de fuso passa despercebido.

**A invalidação do cache parou de apagar chave.** A chave ganhou o fuso como quinta dimensão, e
fuso não se enumera: são centenas de nomes IANA, e o `_limpar` roda fora de qualquer requisição
(signal de `SessionResult`/`User`), sem `X-Timezone` nenhum para saber quais existem. O `for`
sobre os locales que a T-143 escreveu — já declarado lá como remendo — simplesmente não escala
para a dimensão nova, e varrer por padrão (`KEYS df:eng:*`) é a operação que trava um Redis em
produção. Então a invalidação passou a **mudar o endereço**: um selo de versão por usuário entra
na chave, e trocá-lo torna inalcançável tudo que foi escrito antes, em qualquer fuso e qualquer
idioma, de uma vez. Custa uma leitura a mais por payload; em troca, o `_limpar` deixou de ter um
`for` sobre uma dimensão e de estar errado sobre a outra.

**Por que o fuso precisa estar na chave se o dia já está.** Duas pessoas podem estar no mesmo
dia-calendário e discordar sobre a que dia pertence uma sessão da madrugada. O payload guardado
traz streak e meta **já contados**; sem o fuso na chave, o primeiro a ler grava a contagem dele
para quem vier depois no mesmo dia.

**Três testes existentes foram reescritos para cobrar efeito, não mecanismo.** Eles espiavam
`cache.get(chave)` para provar a invalidação — o que testava a implementação de ontem. O que a
spec promete é que a leitura seguinte enxergue a sessão nova, e é isso que eles cobram agora. Um
helper (`chave_real`) concentra a montagem da chave para os dois testes que ainda plantam valor
envenenado de propósito.

**O fogo fantasma do cliente seguiu junto, e pela razão original.** `engagement/fire.ts` fixava
`America/Sao_Paulo` com uma justificativa explícita: o número do visitante tem de bater com o da
conta no instante seguinte ao cadastro. A justificativa está intacta e é ela que exigiu a
mudança — com o servidor resolvendo pelo `X-Timezone` do aparelho, continuar fixo em SP é que
passaria a divergir, para todo mundo fora do Brasil.

**E o teste dele só passava no Brasil.** `diaDoFogo` ganhou um parâmetro `timeZone` opcional que
**só o teste usa**: as asserções antigas (`'2026-08-15T01:30:00Z'` → `'2026-08-14'`) dependiam do
relógio da máquina que roda a suíte. Um teste que só passa em quem mora no Brasil não prova nada
sobre um produto que a task existe para tirar do Brasil.

**Medições.** `ruff check .` limpo; `pytest` 1177 passed (1161 + 16 novos em `tests/test_fuso.py`).
`npm run lint`, `typecheck` limpos; `npm run test` 684/684 (+4); `build` OK. As três coisas que o
fuso decide têm teste próprio, incluindo o **cruzado** que é o bug em si: derivar com o fuso de um
e perguntar "hoje" com o do outro devolve zero sessão hoje.

**Não verificado nesta sessão**: o caminho real com um aparelho fora do Brasil. O teste ponta a
ponta prova que o cabeçalho chega e separa a chave, mas "abrir o app em Lisboa às 22h e ver o
fogo aceso" é medição de aparelho real — entra na T-155.

**Pendências.** Uma, em Descobertas (`[T-156]`), e ela **não é desta task**: `ruff format --check .`
está vermelho no `master` desde a T-145/T-146 — seis arquivos, confirmado com as mudanças desta
task guardadas no `stash`. O CI roda esse comando, então ele está reprovando. Sai em commit
`operação:` próprio, logo a seguir. Lição irmã da `[T-154]`: o AGENTS.md §Fluxo lista
`ruff check` e **não** lista `ruff format --check` — gate que a checklist não nomeia é gate que
ninguém roda.

---

## 2026-08-18 (75) · T-154 — Os portões: dois novos, e os dois acharam bug na primeira execução

**O que foi feito.** O critério 5 da SPEC-025 — *"um commit que acrescenta uma frase em
português e esquece o inglês não passa nos gates que já existem"* — é o único que vale para
sempre, e esta é a task que o transforma em máquina. `no-literal-string` global (os sete
overrides por pasta viraram um bloco só), dois portões novos varrendo o código-fonte
(`web/src/i18n/portoes.test.ts`), a paridade de placeholder generalizada aos nove namespaces, e
as três linhas de processo (AGENTS.md, as duas skills, o checklist de deploy).

### Os dois portões novos, e o que cada um encontrou

Os dois nasceram de Descobertas registradas pelas tasks anteriores — o que já é o sistema
funcionando: quem viu o buraco não o consertou fora de hora, escreveu onde ele estava.

**1. Texto fora de JSX (Descoberta `[T-149]`).** O `no-literal-string` roda em
`mode: 'jsx-only'`, que olha JSXText e JSXAttribute **e nada mais** — uma frase nascida num
módulo `.ts` passa batido. A varredura nova procura literal com caractere acentuado fora de
comentário. **Achou na primeira execução**: `` `Falha ao iniciar o pipeline de pose:
${error.message}` `` vivo em `useEdgePipeline.ts`. A T-149 traduziu o ramo `:` do ternário e
deixou o ramo `?` em português — texto de produto, numa tela que já se dizia traduzida, invisível
para todos os gates anteriores. Virou `session:pipeline.start_failed_detail`.

**2. Cabeçalho de idioma (Descoberta `[T-153]`).** A T-153 consertou à mão três chamadas que não
mandavam `Accept-Language`, e registrou que a mão era o problema: nenhum gate olha header. O
portão novo cobra que todo arquivo que chama `apiBaseUrl()` importe `localeHeaders`. **Achou na
primeira execução**: `session/quota.ts`, a QUINTA chamada, que a T-153 não tinha visto — e o
`message` dela é o `Plan.quota_message` do painel, traduzido por locale desde a T-146. Quem
trocasse o app para inglês continuaria lendo o aviso de limite em português.

**Os dois foram verificados por mutação**, não por fé: reintroduzindo o literal em
`startGate.ts` e tirando o `localeHeaders` do `quota.ts`, cada um falha nomeando o arquivo.

### A lição que a mutação ensinou sobre o próprio portão

A primeira versão do portão do cabeçalho lia o arquivo **cru** e dava por coberto um arquivo
cujo `localeHeaders` aparecia só dentro de um comentário — o comentário que eu tinha acabado de
escrever explicando o header. O teste de mutação passou verde e não devia. **Portão que lê
comentário acredita em promessa, não em código**; agora os dois tiram comentário antes de
procurar, e foi por isso que os dois viraram um arquivo só (`portoes.test.ts`), compartilhando
o `semComentarios` e a leitura do fonte.

### As decisões

**Por que "literal acentuada" e não "qualquer literal".** A alternativa era `mode: 'all'` no
ESLint para os `.ts`, e ela passaria a cobrar tradução de slug (`'jumping_jack'`), chave de
armazenamento (`'digitalfit.locale'`), nome de header e tipo de evento — centenas de exceções, e
portão cheio de exceção deixa de ser lido. A heurística é estreita de propósito e mira **a
direção do erro que existe**: quem escreve este projeto escreve em português. Uma frase nova em
inglês esquecida não seria pega, e está escrito no arquivo que não seria.

**`import.meta.glob('?raw')` em vez de `node:fs`.** O `tsconfig.app.json` não carrega
`@types/node` — é um app de navegador, e trazer a tipagem inteira do Node para ler arquivo num
teste seria pagar caro por pouco. De quebra, some a armadilha do caminho com espaço ("Digital
Fit" vira `Digital%20Fit` num `URL.pathname`, e foi assim que a primeira versão quebrou).

**O `no-literal-string` global tinha um só resíduo**: `Digital Fit` no `BrandMark`. É NOME do
produto, não texto de produto — mesma categoria do `Category` que guarda `forca` e não `"Força"`
—, e ficou com `eslint-disable` e o porquê no ponto. Que sete tasks de migração tenham deixado
exatamente uma linha para o global encontrar é o melhor sinal de que a migração por diretório
funcionou.

**A paridade de placeholder virou varredura.** Era uma chamada por namespace, escrita à mão
(desenho certo enquanto seis raias corriam em paralelo). Agora percorre `dict/pt-BR/index.ts`:
o décimo namespace entra sozinho, a mesma propriedade que faz o `TKey` crescer sem manutenção.

**Processo.** `AGENTS.md` §Fluxo ganhou o item 4 (texto novo nas duas línguas, conteúdo no
painel/YAML, data e número pelos formatadores, chamada nova com `localeHeaders`); a
`df-executor` ganhou a mesma regra na seção de testes; a `df-spec` ganhou a pergunta que decide
a forma da task — *de qual das cinco fontes de texto esta frase vem?* —, porque responder tarde
é o que produz metade da tela numa língua. E o `docs/DEPLOY.md` ganhou o `i18n_status` antes de
anunciar versão, com a razão de ele **não** bloquear deploy: falta de tradução degrada com
honestidade (cai no pt-BR da coluna base), então travar o deploy custaria mais do que o buraco.

### O que NÃO foi feito, e é o mais importante desta entrada

**Os gates do `web/` não rodam no CI.** O `.github/workflows/ci.yml` roda `ruff` e `pytest` e
mais nada. Os quatro portões de i18n do cliente existem, são verdes e foram verificados por
mutação — mas só reprovam **quem roda os gates localmente**. Um PR que esqueça o `en` passa no
CI hoje. Isso é escopo declarado da **T-027**, que continua `todo`, e que deixou de ser tarefa
de higiene: ela é a outra metade do critério de aceite 5. Está registrado como Descoberta
`[T-154]`, e a frase honesta enquanto isso é: *"não passa nos gates que já existem" vale para a
sessão de trabalho, não para o repositório*.

**Medições.** `npm run lint` limpo com a regra global (1 exceção, justificada no ponto),
`npm run typecheck` limpo, `npm run test` 680/680 (+8), `npm run build` OK. `ruff check .`
limpo, `pytest` 1161 passed — inclusive os testes de paridade dos YAML
(`test_i18n_messages.py`, `test_feedback.py`), que já rodavam no CI desde a T-144/T-145 e são a
metade do critério 5 que **já** está protegida no repositório.

**Pendências.** Uma, em Descobertas (`[T-154]`): os gates do web fora do CI, que é a T-027. As
três descobertas anteriores (`[T-148]`, `[T-149]`, `[T-153]`) foram fechadas aqui e marcadas
como tal no BACKLOG.

---

## 2026-08-18 (74) · T-153 — O seletor de idioma, e as três chamadas que não diziam a língua

**O que foi feito.** O controle que faltava para o trabalho das seis tasks anteriores ser
alcançável por alguém: `i18n/LocaleSwitch.tsx` (o desenho), `i18n/switchLocale.ts` (a troca no
app), `i18n/http.ts` (o cabeçalho), `siteLocaleHref` em `shell/origins.ts` (as duas URLs do
site), e as duas superfícies — rodapé da folha de conta no app, pastilha acima da barra no site.

### A descoberta que a task revelou (e que só um seletor poderia revelar)

**Três das quatro chamadas à API nunca mandaram o idioma do cliente.** Só o `authedFetch`
acrescentava `Accept-Language` com o locale resolvido; o `GET /api/config`, o
`POST /api/sessions` e o relatório montam os próprios headers e ficavam com o `Accept-Language`
que o **navegador** acrescenta sozinho. Enquanto o idioma do app era o do navegador, os dois
coincidiam sempre — o buraco era real desde a T-143 e invisível por construção. O seletor o
expôs no primeiro toque: troca para inglês, catálogo continua em português.

Fechado com `i18n/http.ts` (`localeHeaders()`), uma cópia só, usada pelas quatro. O
`authedFetch` largou a própria versão. O teste verifica o header nas duas rotas revalidadas e
foi conferido por mutação: tirando o `localeHeaders()` de `serverConfig.ts`, ele falha.

### As decisões

**Trocar a preferência não basta, e é por isso que `switchLocale` existe.** A SPEC-025 §Notas
técnicas nomeia dois caches que continuariam falando a língua velha: o ETag do
`GET /api/config` (que inclui o locale desde a T-143, então o `If-None-Match` guardado é o da
língua anterior e o servidor devolve 200 — mas só se alguém pedir) e o cache de engajamento, por
`(usuário, dia, locale)`, que traz nome de conquista já renderizado. `force: true` no segundo
porque houve **fato novo**, não suspeita.

**A ordem é síncrona primeiro, rede depois.** `setLocale` roda antes e a tela troca no mesmo
quadro do toque; as duas revalidações saem por baixo, sem `await` e sem tela de carregamento.
Prender a troca à rede faria um seletor que não responde em avião — e o que vem do servidor é
minoria do texto (o embutido já está traduzido desde a T-152). Falha de rede é silenciosa pelo
mesmo motivo do `fetchServerConfig` no boot: idioma não é operação que possa falhar na cara de
quem acabou de trocar.

**Um componente, duas regras incompatíveis, nenhum `if`.** O `LocaleSwitch` não conhece store,
não sabe revalidar e não sabe navegar: recebe `onSelect` (app) **ou** `hrefOf` (site). É essa
ignorância que mantém o bundle da landing sem `session/` e `engagement/` dentro (ADR-010) — e
foi medido, não suposto: o `site.js` foi de 9,86 kB para 10,05 kB, +0,19 kB, o custo do próprio
componente e nada mais.

**No app o seletor fica FORA dos dois ramos da folha de conta.** Visitante e logado veem o mesmo
controle, porque idioma não é assunto de conta — treinar sem conta é garantia da SPEC-011, e um
seletor que só existisse para quem entrou seria exatamente a pequena punição por não se
cadastrar que a preferência de aparelho evita. No rodapé, separado por linha como a zona de
perigo: é ajuste, não ação.

**No site é um par de LINKS, e isso não é inconsistência.** `/` e `/en/` — as mesmas URLs que os
`hreflang` de cada `index.html` já declaravam uma à outra desde a T-147. O hash viaja junto
(`siteLocaleHref(locale, hash)`): quem está em Sobre e troca de idioma continua em Sobre, porque
perder a tela seria o preço de ter escolhido o idioma. E visitar `/en/` **não** grava preferência
nenhuma — a regra do site é a URL, a do app é o aparelho (SPEC-025 §Escopo), e o `SiteApp` já
sincronizava o store com o `<html lang>` estático desde a T-147.

**"Português" e "English" são iguais nos dois dicionários.** Convenção de seletor de idioma, e a
única que funciona: quem procura este controle normalmente não lê a língua em que a tela está, e
"Portuguese" não ajudaria quem abriu o app em inglês por engano. Chave igual, valor igual, com o
porquê escrito no dicionário para ninguém "consertar" depois.

**`LOCALES` em `i18n/locale.ts`** dá a ordem do seletor (`pt-BR` primeiro porque é a fonte, não
por preferência de quem lê) — e um terceiro idioma aparece no controle sozinho ao entrar nesse
array, o mesmo teste de arquitetura que o `TKey` já passa.

**Medições** (dev server real, medido por JS — nada alegado):

- App, `#/preparar` → Perfil: o seletor mostra "IDIOMA · Português · English" com Português
  ativo. Um toque em English e, **sem recarregar** (`performance.getEntriesByType('navigation')`
  continua com 1 entrada): `<html lang>` = `en`, `digitalfit.locale` = `en`, o próprio rótulo do
  seletor vira "LANGUAGE", a tela atrás vira "Setup" / "Let's set up your workout" / "Turn on
  camera", a tab bar vira Home/Progress/Analytics/Profile, e uma chamada nova a `/api/config`
  aparece nos `resource entries`.
- **`/api/engagement` não foi chamada nesta medição, e está certo**: sem conta o
  `refreshEngagement` sai antes de tocar a rede (XP e conquistas não existem para o visitante,
  §Planos). O caminho com conta é o que o teste `switchLocale.test.ts` cobre — com usuário no
  store, as duas rotas saem, ambas com `Accept-Language: en`.
- Site, `/#/sobre`: o par de links aparece acima da barra, "Português" com `aria-current` e o
  English apontando para `/en/#/sobre`, cada um com o próprio `hreflang`. Clicando: URL
  `/en/#/sobre`, `<html lang>` = `en`, título "About Digital Fit", `<title>` da aba trocado.
- **O site não obedeceu ao `localStorage`, e isso é a regra funcionando**: com
  `digitalfit.locale` = `en` guardado do teste anterior, `/` continuou em português. A URL manda
  no site; o aparelho manda no app.

**Gates.** `npm run lint` limpo, `npm run typecheck` limpo, `npm run test` 678/678 (+6),
`npm run build` OK. Python intocado: `ruff check .` limpo, `pytest` 1161 passed.

**Pendências.** Uma, em Descobertas (`[T-153]`): o buraco do `Accept-Language` foi fechado, mas
**nenhum portão o teria pego** — uma chamada nova nasce sem idioma e nada acusa. É irmã da
Descoberta `[T-149]` (a regra não vê string fora de JSX) e das duas a T-154 precisa decidir o
que fazer.

---

## 2026-08-18 (73) · T-151 — `account` + `errors`: a Onda 2 fecha, e o plural sai dos ternários

**O que foi feito.** A última raia da Onda 2 (SPEC-025): `account` (82 chaves — conta, quota,
fogo, XP, conquistas) e `errors` (6 — as falhas de rede). Onze arquivos migrados, mais os dois
débitos que a T-150 deixou registrados e esta task recolheu.

**"API fora do ar" existia em três cópias, e esta era a única task que podia juntá-las.** A
admissão (T-149), a busca do relatório (T-150) e o `auth/api` (esta) escreviam a mesma frase em
namespaces diferentes — não por descuido, mas porque **namespace é a unidade de paralelismo da
Onda 2** e escrever no arquivo alheio teria colidido entre raias. A T-151 é a que toca as três,
e o namespace `errors` existia vazio esperando exatamente isso. Agora é uma frase, uma casa, e
o teste diz por quê.

**As datas do Progresso e do Analytics voltaram a falar a língua da tela.** Era o gap que a
T-150 mediu e declarou: `historyDate` formatava com `toLocaleTimeString('pt-BR')` e devolvia
"hoje 12:03" com a tela inteira em inglês. Agora sai de `formatTime`/`formatDate` mais as chaves
`account:date.*` — medido: "today 12:19 PM". **"hoje"/"ontem" continuam decididos por diferença
de dia de CALENDÁRIO**, e não pelo `Intl.RelativeTimeFormat`: a regra de produto é "que dia foi
isso", e o `RelativeTimeFormat` responderia "há 14 horas", que é outra pergunta. Data inválida
continua `—` nas duas línguas, com teste — ausência não se traduz.

**Segundo array de dias da semana em português, mesma origem.** `INICIAIS_DA_SEMANA` no
`engagement/calendar.ts` era gêmeo do `DIAS_DA_SEMANA` que a T-150 matou no Progresso — duas
cópias do calendário brasileiro, em dois arquivos, escritas por tasks diferentes. Sumiu; o
painel do fogo usa o mesmo `weekdayNarrowLabels()`. O `offset` da grade continua calculado em
`calendar.ts` e continua abrindo na segunda.

**Seis ternários de plural viraram baldes.** `streak === 1 ? 'dia seguido' : 'dias seguidos'`,
`guardadas === 1 ? ' treino guardado' : ...`, `alvo === 1 ? 'sessão' : 'sessões'`,
`grade.ativos` dias treinados — cada um era uma regra de português embutida num componente.
Agora todos são `.one`/`.other` resolvidos pelo `Intl.PluralRules` (plano §2.7), e o `TKey` já
aceitava a chave-base porque a T-150 abriu esse caminho na véspera.

**O `key` do React não pode ser texto traduzido.** `parcelasDeXp` devolvia
`{ rotulo: 'sessão', valor }` e o `XpLine` usava `parcela.rotulo` como `key`. Com o rótulo
traduzido, trocar de idioma remontaria a lista inteira — e duas línguas com a mesma palavra
("reps" nas duas) colidiriam. Passou a devolver `{ id, rotulo, valor }`: o `id` é o slug estável,
o `rotulo` é o que se lê. Tem teste.

**`fireAriaLabel` monta por template, não por concatenação.** Era
`` `${dias}, ${meta}${onde}` `` — três partes coladas na ordem do código. Virou
`account:fire.aria` = `'{days}, {goal}{where}'`: a ordem passa a ser do dicionário, que é onde
ela pode mudar de língua. Mesma doutrina do `vgate.dont_show_hint` (T-148) e do `zoom.aria`
(T-149).

**Uma chave para "nível", com o CSS decidindo a caixa.** A seção do Perfil escrevia `nível`
(minúsculo, `.account__eng-label` não transforma) e o painel escrevia `Nível` (maiúsculo, mas
`.v2-label` já aplica `text-transform: uppercase`). Duas chaves seriam duas traduções da mesma
palavra para manter uma diferença que o CSS apaga — uma chave só, e quem precisa de caixa alta a
recebe da folha de estilo.

**Testes** (+15, total 672): quota e datas nas duas línguas (incluindo o `—` da data inválida e
a prova de que o CORPO do aviso continua vindo do servidor, não do dicionário); os quatro
plurais da conta; `parcelasDeXp` com `id` estável e rótulo traduzido; a falha de rede em inglês
nas três chamadas pela mesma chave; e a paridade de `{placeholder}` estendida a `account` e
`errors` — o helper da T-148 serve agora seis namespaces. Sete testes existentes passaram a
fixar o locale antes de cobrar a frase.

**Medições** (dev server real, uma sessão semeada no `localStorage`, medido por JS):

- `en`, folha da conta: "Log in" / "Create account", campos NAME (OPTIONAL)/EMAIL/PASSWORD,
  "I already have an account", "Not now", e o argumento do funil no singular certo —
  "**1 workout saved** on this device — clearing your browser takes them away."
- `en`, chip do fogo: `aria-label` "1 day in a row, daily goal 1 of 1, saved on this device only"
  — as três partes montadas pelo template.
- `en`, painel do fogo: "Your consistency", "day in a row", "Best streak: 1", o bloco fantasma
  inteiro, calendário `M T W T F S S`, dia com `aria-label` "18, trained", "1 day trained this
  month", "TODAY’S GOAL".
- `en`, Analytics: a coluna de datas agora diz "today 12:19 PM" — o gap da T-150, fechado.
- `pt-BR`, as mesmas telas: idênticas ao que eram (incluindo `S T Q Q S S D` e "18, treinou").
- **Não verificado nesta sessão**: o `AchievementToast` (depende de conquista nova chegando do
  servidor), o bloco de quota esgotada e a galeria de conquistas com dado real — todos exigem
  conta e servidor. Cobertos por dicionário, paridade e, no caso da quota, teste de
  `quotaNotice` nas duas línguas; a tela fica para a T-155.

**Gates.** `npm run lint` limpo, `npm run typecheck` limpo, `npm run test` 672/672,
`npm run build` OK. Python intocado: `ruff check .` limpo, `pytest` 1161 passed.

**Pendências.** Nenhuma nova. As duas descobertas da T-150 foram fechadas aqui e marcadas como
tal no BACKLOG. **A Onda 2 terminou** — os nove namespaces existem e estão preenchidos, e a
T-154 (portões) já pode ligar o `no-literal-string` global; a Descoberta `[T-149]` continua
valendo para ela: a regra não enxerga string fora de JSX, e é lá que mora boa parte deste texto.

---

## 2026-08-18 (72) · T-150 — `report` + `progress`: o passado do treino nas duas línguas

**O que foi feito.** Os dois últimos namespaces de leitura da Onda 2: `report` (23 chaves — o
relatório do fim, `report/ReportSheet`, `reportSummary`, `sessionReport`) e `progress` (41 —
`screens/ProgressScreen` e `AnalyticsScreen`). Junto vieram os dois itens que a linha da task
pedia por escrito: a troca dos `toLocaleDateString('pt-BR')` pelos formatadores e a morte do
`DIAS_DA_SEMANA` montado à mão.

**O calendário brasileiro estava embutido em um array de sete letras.**
`const DIAS_DA_SEMANA = ['S','T','Q','Q','S','S','D']` — o cabeçalho da grade do mês. Em inglês
ele mostraria "S T Q Q S S D" sobre uma tela escrita "Progress", e nenhum lint acusaria, porque
letra solta não parece frase. Virou `weekdayNarrowLabels()` em `i18n/format.ts`, que pergunta ao
`Intl`. **A semana continua abrindo na segunda**, e isso é decisão de produto, não de locale: a
agregação (`inicioDaSemana`) e a matemática da grade (`(getDay() + 6) % 7`) contam assim, e um
cabeçalho que mudasse de primeiro dia por idioma desalinharia as bolinhas em inglês. O que o
`Intl` decide é a LETRA, não por onde a semana começa — e o teste cobra as duas coisas: pt-BR
devolve exatamente o array antigo (prova de que o produto em português não mudou) e en devolve
`M T W T F S S`, na mesma ordem.

**Segundo separador decimal escrito à mão, mesma armadilha da T-149.** `formatKcal` fazia
`.toFixed(1).replace('.', ',')`, então uma tela em inglês diria "4,9 kcal". Agora sai do
`formatNumber`, com teste nos dois idiomas. Vale registrar o padrão: **em duas tasks seguidas o
bug de i18n mais difícil de ver não foi frase nenhuma — foi número.**

**O runtime ganhou plural sem forma base.** As contagens do Progresso eram
`sessions.length === 1 ? 'treino' : 'treinos'` espalhados pela tela. Viraram `.one`/`.other` com
`{n}`, como manda o `resolveFromTable` — mas aí `t('progress:metric.days')` não compilava: `TKey`
saía das chaves do dicionário, e a base `metric.days` não é uma delas. A saída óbvia seria
cadastrar uma chave base redundante (`'metric.days': 'dias'` ao lado de `'metric.days.other':
'dias'`) — duplicação de TEXTO a serviço do compilador, exatamente o que o dicionário existe para
evitar. Em vez disso, `TKey` passou a incluir a base derivada dos baldes (`PluralBase`, um
condicional distributivo de ~6 linhas em `i18n/index.ts`). A T-151, que é a task do plural por
`Intl.PluralRules`, encontra isso pronto.

**`ESTIMATED_LABEL` virou função, e a chave dele ficou no namespace `session`.** Constante
resolvida no import congelaria a palavra no idioma de quando o bundle carregou — terceira vez que
esta lição aparece (`EXERCISE_CATALOG` na T-152, `CAMERA_LABEL` na T-149). A chave foi para
`session:label.estimated` e não para `progress`, porque **namespace segue a TELA, não o arquivo
que calcula**: quem desenha o rótulo é o card de kcal do treino ao vivo. O arquivo
(`session/kcal.ts`) é que era escopo desta task.

**Duas frases com marcação no meio, terceira vez** (`note.local_*` do Progresso, com
`<strong>neste aparelho</strong>`): mesmo `lead`/`strong`/`tail` da T-148 e da T-149. Já é
padrão da casa, não decisão nova.

**`reasonText` traduz até o desconhecido.** `REASON_TEXT` virou `REASON_KEY`
(`Record<string, TKey>`): o `SessionEndReason` continua sendo o contrato do
`workers/shared/events.py`, e o fallback `'Sessão encerrada'` também passou a ser chave — um
motivo do futuro não pode devolver português para quem está em inglês.

**Testes** (+10, total 661): `reasonText` nas duas línguas incluindo o fallback; `formatKcal`
com o separador por idioma; falha de rede do relatório em inglês; `weekdayNarrowLabels` nos dois
locales (com a prova de que pt-BR não mudou); plural de `metric.days`/`metric.workouts` sem forma
base; `analytics.range` interpolando e pluralizando na mesma chave; e a paridade de
`{placeholder}` estendida a `report` e `progress` — o helper da T-148 agora serve quatro
namespaces. Dois testes existentes passaram a fixar o locale antes de cobrar a frase.

**Medições** (dev server real, histórico de 4 sessões semeado no `localStorage`, medido por JS):

- `en`, `#/progresso`: "Your training over time", métricas WORKOUTS/REPS/DAYS, mês "AUGUST",
  cabeçalho da grade `M T W T F S S`, semanas `07/27 · 08/03 · 08/10 · 08/17` (mês/dia, como o
  `en` manda), "BY EXERCISE" com "2 workouts", nota "This is the history kept **on this device**".
- `en`, `#/analytics`: "Training analysis", "from 38 to 40 reps/min across 2 workouts", "PACE
  CONSISTENCY / lower is steadier", "steady across sessions", e a correção vinda do catálogo do
  treinador ("Reach your arms higher overhead").
- `pt-BR`, as mesmas telas: idênticas ao que eram — mês "AGOSTO", letras `S T Q Q S S D`, semanas
  `27/07 · 03/08…`, `title` do dia "Treinou em 09/08/2026".
- **Gap medido e declarado**: com a tela em inglês, a coluna de datas continua em português
  ("hoje 12:03", "15 de ago. 12:03"). É o `historyDate` de `auth/accountSummary.ts`, que a linha
  da **T-151** reivindica — ficou de fora de propósito. Registrado em Descobertas para a T-155
  não o encontrar como bug novo.
- **Não verificado nesta sessão**: o `ReportSheet` em tela. Ele só abre no fim de uma sessão
  real, e a câmera está bloqueada no navegador do painel. O texto está coberto por dicionário,
  paridade e teste de `reasonText` nas duas línguas; a aparência fica para a T-155.

**Gates.** `npm run lint` limpo, `npm run typecheck` limpo, `npm run test` 661/661,
`npm run build` OK. Python intocado: `ruff check .` limpo, `pytest` 1161 passed.

**Pendências.** Duas, em Descobertas: as três cópias de "API fora do ar" (`admission`,
`sessionReport`, `auth/api`), que só a T-151 pode consolidar no namespace `errors` sem colidir
com ninguém; e as datas ainda em pt-BR, que somem quando a T-151 tocar o `accountSummary`.

---

## 2026-08-18 (71) · T-149 — Namespace `session`: o treino inteiro nas duas línguas

**O que foi feito.** A maior raia da Onda 2 (SPEC-025): 75 chaves em
`dict/{pt-BR,en}/session.ts` e dezoito arquivos sob a regra — a capa e os avisos da câmera
(`capture/CameraView`, `useCamera`, `useEdgePipeline`), o aquecimento do pipeline
(`pose/assetWarmup`), a medição do corpo, os conselhos de cena (`scene/sceneQuality`), as
recusas da admissão (`session/admission`, `useSession`), o CTA de dois degraus
(`session/startGate`), o HUD (`hud/CoachTip`, `StatsBar`, `GetReady`, `TimerRing`,
`CountdownSetting`, `ZoomControl`) e as duas telas do `screens/SessionScreen`.

**A descoberta que muda o desenho do portão: metade deste texto não mora em JSX.** As raias
anteriores (`site`, `catalog`, `funnel`) eram quase só componente, e ali o
`i18next/no-literal-string` acha tudo. Aqui não: a recusa de quota, o conselho de luz, o rótulo
do CTA e o progresso do download nascem em módulo `.ts`, e o `mode: 'jsx-only'` não olha para
eles. Achei-os por leitura, arquivo a arquivo — o que funciona uma vez e não é portão nenhum.
Está registrado como Descoberta `[T-149]` com as duas saídas possíveis para a T-154; o que **não**
fiz foi inventar a regra aqui dentro, porque escolher entre `mode: 'all'` ruidoso e um teste de
varredura é decisão da task dos portões, não desta.

**O separador decimal era um bug de idioma disfarçado de formatação.** `warmupLabel` montava os
MB com `.toFixed(1).replace('.', ',')` — a vírgula brasileira escrita à mão. Numa tela em inglês
o app diria "42% · 4,2 de 10,0 MB" e ninguém chamaria isso de bug de tradução, porque número não
parece texto. Agora sai do `formatNumber` (`i18n/format.ts`, T-142), e o teste novo cobra os dois
lados: `'42% · 4,2 de 10,0 MB'` em pt-BR, `'42% · 4.2 of 10.0 MB'` em en. É a armadilha §2.6 do
PLANO-I18N pega em flagrante.

**Zero tem frase própria, e quem diz isso é o dicionário.** `countdownLabel(0)` era
`'sem preparação'` por um ternário. Virou o balde `.zero` do `resolveFromTable` (T-142):
`countdown.value.zero` em cada língua (`'sem preparação'` / `'no countdown'`), com
`'{n}s de preparação'` / `'{n}s countdown'` para o resto. O mesmo par existe para o rótulo curto
da célula de 92 px (`Off` / `3s`). Nenhum `if (n === 0)` sobrou no componente — a regra de zero é
de tradução, não de layout.

**`session/preferences.ts` entrou fora da lista da task, e de propósito.** Ele hospeda o
`countdownLabel`, que é justamente o que o `aria-label` do `CountdownSetting` (esse sim listado)
interpola. Deixá-lo para depois entregaria um controle com metade do rótulo em português numa
tela em inglês. A justificativa está no docstring da função, não só aqui.

**O que ficou em português de propósito.** O chip de diagnóstico do `CameraView` (`pose gpu`,
`seq 412 · 14,9fps`, `176 lm`, o botão `parar`) e o conselho de "suba a stack
(`docker compose up`)" continuam crus, com `eslint-disable` de bloco e a razão escrita no ponto:
são a mesma categoria que a SPEC-025 §Escopo já excluiu ao deixar o painel admin em pt-BR —
ferramenta de operação do Daniel, não superfície de quem treina. O `devTools` liga por build de
dev ou conta `is_admin`; ninguém mais os vê.

**Duas frases com `<strong>` no meio, de novo.** A do `GetReady` ("Fique parado. Comece o
**polichinelo** quando aparecer **VAI!**") virou `hint_lead` + `hint_mid`, com o nome do
exercício e o `getready.go` reaproveitado no negrito — mesma solução do `view.why.*` da T-148, e
o "VAI!"/"GO!" sai de uma chave só, usada no dial e na frase.

**`sceneQuality` continua puro onde importa.** `CONSELHOS` deixou de ser
`Record<SceneCode, string>` (congelado no import) e virou `Record<SceneCode, () => string>` —
mesma técnica dos getters de `exerciseViews.ts` na T-152. `measureScene`/`avaliarCena` seguem
decidindo por número, e o `SceneCode`, que é o contrato lido pelo `acumular`/`confirmado` e
pelos testes antigos, nunca passa por tradução. O teste novo prova exatamente isso: código igual
nas duas línguas, frase diferente.

**Testes** (+8, total 651): rótulo do CTA nas duas línguas com a AÇÃO inalterada (`ligar`/
`iniciar` são contrato); `countdownLabel` com o zero nas duas; `warmupLabel` com o separador
decimal por idioma; recusa da admissão em inglês (`/API is down/`); conselho de cena com código
estável e texto traduzido; e a paridade de `{placeholder}` estendida ao namespace `session` — o
helper `esperaMesmosPlaceholders` que a T-148 criou virou função reusável, chamada agora por dois
namespaces. Verificada por mutação: apagando o `{total}` de `live.subtitle` no `en`, a suíte
falha nomeando a chave. Quatro testes existentes passaram a fixar o locale antes de cobrar a
frase, em vez de herdar o que o `detectLocale()` resolver no ambiente do vitest (que, sem
`localStorage` e sem `navigator.languages`, é `en` — foi assim que eles quebraram, e a quebra
estava certa).

**Medições** (dev server real, medido por JS):

- `en`, `#/preparar`: "Setup" / "Let’s set up your workout", capa da câmera "Camera off",
  CTA "Turn on camera", pill "Turn on the camera to frame yourself", rótulos
  Exercise/Camera/Set/Reps/Duration/Angle/Estimated calories/Get ready, steppers com
  `aria-label` "Decrease Set"…, `aria-label` da preparação "Countdown before counting starts:
  3s countdown. Tap to change.", title do stepper travado "Configurable duration: coming soon".
- `en`, `#/treino`: "Live Workout" / "Push-up • Set 1/1", cards Reps/Angle/Calories, anel
  "Time left", botão central com `aria-label` "Start workout", unidade "kcal".
- `pt-BR`, as mesmas duas telas: idênticas ao que eram antes da migração.
- **Não verificado nesta sessão**: `GetReady`, os banners de aquecimento/cena e o card do
  treinador ao vivo exigem câmera, e o navegador do painel bloqueia `getUserMedia`. O texto
  deles está coberto por dicionário + paridade + (no caso da cena) teste próprio, mas a
  aparência em tela é pendência do Daniel — e cai naturalmente na T-155, que é a passada em
  aparelho real nas duas línguas.

**Gates.** `npm run lint` limpo (com o bloco novo ligado), `npm run typecheck` limpo,
`npm run test` 651/651, `npm run build` OK. Python intocado, rodado mesmo assim: `ruff check .`
limpo, `pytest` 1161 passed.

**Pendências.** Duas, em Descobertas: o buraco do portão fora de JSX (`[T-149]`, para a T-154) e
os três componentes de HUD que ninguém importa — `StatsBar`, `CoachTip`, `ExerciseCard` —,
traduzidos porque a linha da task os nomeia, e candidatos a remoção em task própria.

---

## 2026-08-18 (70) · T-148 — Namespace `funnel`: o caminho de escolher e aprender, nas duas línguas

**O que foi feito.** As onze superfícies da raia `funnel` da Onda 2 (SPEC-025) saíram do
português embutido e passaram a ler `t('funnel:…')`: Escolha (`screens/ChooseScreen`,
`ExerciseRails`), Guia (`screens/GuideScreen`), a escolha de variação de câmera
(`ui/ViewPicker`, `hud/ViewConfirm`), os dois herdados do funil antigo (`hud/ExercisePicker`,
`ui/ExerciseDemo`), o card da vitrine (`screens/ExerciseCards`) e os três módulos sem texto
(`screens/funnel.ts`, `session/guideGate.ts`, `session/viewGate.ts`). `dict/{pt-BR,en}/funnel.ts`
nasceram com 31 chaves cada, e o `no-literal-string` foi ligado para esses arquivos.

**A fronteira que este namespace desenha: moldura aqui, conteúdo lá.** Nome do exercício, grupo
muscular, passos do guia, instrução de cena e rótulo de vista NÃO entraram no `funnel` — vêm do
`catalog` (T-152) ou do servidor (T-146). É por isso que `guide.demo_alt` guarda
`'Demonstração do exercício {exercise}'` e não a palavra: o nome não é desta camada. A tela
verificada no navegador prova a costura — o `alt` da foto grande do Guia lê
`Demonstração do exercício Flexão de braço` em pt-BR e `Push-up demonstration` em en, com a
moldura vindo daqui e o nome vindo do catálogo.

**Frase repetida com o namespace `site` é repetição de propósito.** "Escolha seu exercício"
existe duas vezes (`site:choose.kicker` na vitrine, `funnel:choose.title` no app). São bundles
diferentes, superfícies diferentes, que podem divergir sem que nenhuma esteja errada —
compartilhar a chave amarraria a landing à tela de treino por acidente de tradução.

**As duas frases com `<strong>` no meio.** O "por quê" do `ViewPicker` e o do `ViewConfirm`
carregam negrito DENTRO da oração, e o termo em negrito é o rótulo da vista ("De lado"/"de
frente") ou a palavra que a frase existe para dizer ("zero"). Uma chave só com HTML embutido
exigiria `dangerouslySetInnerHTML`; um `<strong>` com literal solto seria exatamente o que a
regra desta task veio proibir. Solução: pares `<termo>_term` + `<termo>_text`, com o negrito no
markup e a frase no dicionário. O `vgate.why_tail` (hoje só `'.'` nas duas línguas) existe por
causa disso — em pt-BR e en a oração acaba logo depois do negrito, mas quem traduzir para uma
língua que não acaba aí tem onde pôr o resto, sem chave nova.

**`vgate.dont_show_hint` interpola o rótulo do card em vez de escrevê-lo.** A dica manda a
pessoa procurar um card pelo nome ("você continua trocando pelo card 'Câmera'"), e um nome que
não bate com o que está na coluna é pior que dica nenhuma. `{card}` recebe
`t('funnel:view.label_compact')` — a mesma chave que desenha o rótulo. Medido no navegador em
inglês: a dica diz "Camera" e o card diz CAMERA.

**`card.duration` ('30s') entrou no dicionário, e `role`/`aria-*` não.** A duração da sessão é
unidade escrita ("30s" e "30 sec" são a mesma sessão em duas línguas), então é texto. Já
`role="radio"`, `role="dialog"`, `aria-modal`, `aria-labelledby` e `aria-hidden` são vocabulário
da ARIA — contrato do navegador e do leitor de tela, nunca frase que alguém lê — e entraram no
`jsx-attributes.exclude` do override, junto de `figuraClassName` (que é `className` com outro
nome). `aria-label` e `alt` ficaram deliberadamente FORA da exclusão: são os ~30 rótulos de
acessibilidade que a SPEC-025 §Entidade conta como texto, e é por eles que a regra roda em
`mode: 'jsx-only'` em vez do padrão `jsx-text-only`.

**O teste que o `tsc` não faz.** `dict/typeParity.proof.ts` garante paridade de CHAVE desde a
T-142, mas ninguém olhava DENTRO do valor: um `en` que escrevesse `'Demo'` onde o `pt-BR` tem
`'Demonstração: {exercise}'` compila limpo, passa no lint e só some com o nome do exercício em
produção, na língua que ninguém abre para conferir. Entrou um teste que compara os placeholders
chave a chave em `funnel` — e ele foi verificado por mutação, não por fé: apagando o
`{exercise}` do `en`, a suíte falha nomeando a chave (`{ chave: 'demo.alt', ph: [] }` contra
`ph: ['exercise']`). Só `funnel` de propósito; generalizar para os nove namespaces é portão, e
portão é a T-154 (registrado em Descobertas).

**Medições** (dev server real, Chrome do painel, medido por JS — não alegado):

- `en`, `/app/#/exercicios`: "Choose your exercise" / "Quick workouts, real results", faixas com
  `aria-label` "Cardio exercises" / "Strength exercises" / "Core exercises", selos "30s", alts
  "Demo: Jumping Jack"…
- `en`, `/app/#/guia/flexao`: kicker, título de vista, a frase do "por quê" montada inteira
  ("Both count your reps. From the side … from the front …"), "Set up your scene:", CTA e
  "Skip the example" — nenhuma palavra em português na tela.
- `en`, trava da variação (`.vgate`): "Before you turn the camera on" / "Where are you putting
  your phone?" / "…your workout can end at zero." / "Confirm and turn on camera", `radiogroup`
  com `aria-label` "Camera position".
- `pt-BR`, as mesmas três telas: texto **idêntico ao de antes da migração**, incluindo a frase
  longa do `viewpick__why` conferida caractere a caractere.
- Site: `/en/` desenha os cards com alt "Demo: …" e `/` com "Demonstração: …" — o
  `ExerciseDemo`/`ExerciseCards` seguem o locale da URL (regra do `SiteApp`, T-147) mesmo com
  `digitalfit.locale` em `pt-BR` no aparelho. Era o risco real de componente compartilhado entre
  os dois bundles, e não se materializou.

**Gates.** `npm run lint` limpo (com a regra nova ligada), `npm run typecheck` limpo,
`npm run test` 643/643 (639 antes + 4 novos), `npm run build` OK. Lado Python intocado, rodado
mesmo assim: `ruff check .` limpo, `pytest` 1161 passed.

**Pendências.** Uma, em Descobertas (`[T-148]`): a paridade de `{placeholder}` só cobre
`funnel`; generalizar na T-154. A raia `session` (T-149) continua em português na
pré-configuração — é o esperado, e aparece lado a lado com o `funnel` já traduzido em quem
abrir `#/preparar` agora.

---

## 2026-08-18 (69) · T-146 — Tradução do conteúdo do banco: três tabelas, um fallback só

**O que foi feito.** A "Tabela de tradução" que a SPEC-025 §3.6 já tinha desenhado (e a
alternativa rejeitada — `JSONField` chave-valor) virou código: três tabelas novas
(`ExerciseTranslation`, `ExerciseGuideStepTranslation`, `PlanTranslation`), uma migration
(`0022_traducoes`, schema puro, nenhum dado migrado — as colunas de `Exercise`/`Plan`/
`ExerciseGuideStep` continuam sendo o pt-BR), `exercises_for()`/`config_payload()` resolvendo
por locale com fallback campo a campo, inline no painel admin, e `manage.py i18n_status`.

**A forma da tabela.** Cada uma tem FK exclusiva para a linha que traduz (`exercise`, `plan`,
`guide_step`) + `locale` (`UniqueConstraint` no par) + as colunas tipadas espelhando as da
fonte — `display_name`/`muscle_group`/`default_tip`/`scene_tip` para exercício, `nome`/
`quota_message` para plano, `texto` para passo do guia. `locale` sai de
`TRANSLATABLE_LOCALE_CHOICES = [(l, l) for l in LOCALES if l != SOURCE_LOCALE]` — hoje só
`en`, e um terceiro idioma entra em `api.i18n.LOCALES` sem tocar nesta tabela. `clean()`
recusa uma linha em `pt-BR`: a fonte não tem linha própria aqui, teria o dado duplicado dentro
de si mesmo.

**O fallback é campo a campo, não linha a linha.** `_traduzir_catalogo`/`_traduzir_plano` (novas,
em `config.py`) sobrepõem só o que a tradução preencheu; campo em branco na tradução — ou
tradução ausente inteira — cai na coluna base. Testado explicitamente: uma tradução com
`muscle_group=""` mantém o `display_name` traduzido e usa o `muscle_group` do pt-BR, nunca os
dois em branco. Guia por passo usa o mesmo princípio, casado pela FK real ao `ExerciseGuideStep`
(não por índice de lista) — a lição de não confiar em posição quando existe identidade.

**Onde a tradução entra sem tocar no que já era de outra task.** `exercises_for(locale=
SOURCE_LOCALE)` por padrão — quem chama sem passar locale (a admissão, em `sessions.py`)
recebe exatamente o comportamento de ontem. `config_payload` ganhou o mesmo parâmetro e passou
a sobrescrever `plan.name`/`plan.quota_message` com a tradução resolvida **depois** de chamar
`capabilities_for` (intocada) — não dava para tocar nela sem sair do escopo combinado com o
orquestrador (`config_etag` e `_mensagens_de_feedback` são de outras tasks). A única mudança
fora de `config.py` foi `views.py`: `config_payload(usuario)` virou `config_payload(usuario,
locale=locale)` — sem isso o `locale` já resolvido pela T-143 entraria no ETag e nunca no corpo.

**Painel.** `ExerciseTranslationInline` ao lado do `GuideStepInline` em `ExerciseAdmin`, e
`PlanTranslationInline` em `PlanAdmin` — diretos, porque a FK de cada um aponta pro modelo da
própria tela. A tradução do passo do guia não coube nesse padrão: o admin do Django não aninha
`TabularInline` dentro de `TabularInline`, e a FK de `ExerciseGuideStepTranslation` é para
`ExerciseGuideStep`, que só existia como inline. Solução: registrar `ExerciseGuideStep` também
como tela própria (`ExerciseGuideStepAdmin`), só para hospedar o inline da tradução — o passo
continua nascendo e se reordenando onde sempre nasceu, dentro do exercício.

**`manage.py i18n_status`** (`api/i18n_status.py` + comando, no padrão do `exercise_health`
da T-104): varre `Exercise`/`ExerciseGuideStep`/`Plan` habilitados e lista, por locale, todo
campo com conteúdo na fonte e sem contrapartida traduzida. A regra que evita ruído: campo em
branco na própria fonte (ex. `Exercise.scene_tip` do agachamento, `Plan.quota_message` do
assinante) não é buraco — não há o que traduzir ali, e reportar isso teria acostumado quem lê o
comando a ignorar a lista. `--todos` inclui exercício desligado; `--json` para CI/DEVLOG.

**Testes** (`tests/test_i18n_content.py`, 33 novos): forma da tabela (choices, `clean()`,
`UniqueConstraint`), fallback campo a campo em `exercises_for`/`config_payload` (completo,
parcial, ausente, degradação de banco fora do ar), `i18n_status` acusando e deixando de
acusar um buraco real, e quatro testes ponta a ponta pelo painel de verdade (`client.post` no
formulário do admin, com o `management_form` do inline) — não só a função pura. Um teste
existente (`test_editar_o_plano_no_painel_muda_a_admissao_sem_restart`) precisou do
`management_form` do novo inline (`translations-TOTAL_FORMS` etc.) para continuar postando; sem
isso o Django recusa o POST com um erro que não aparece em `adminform.form.errors`.

**Gates.** `ruff check .` limpo. `pytest -q`: 1132 passed (929 antes desta task + os 33 novos +
o ajuste do teste do painel). `makemigrations --check --dry-run` sem pendência.

**Pendências.** Nenhuma. `docs/PLANO-I18N.md §3.6` previa "sugestão automática de tradução no
painel" para a Fase Evolução (SPEC-025) — não entrou aqui, e não deveria.

---

## 2026-08-18 (68) · T-145 — Texto do servidor sai do código, entra em arquivo

Escopo: `server/api/i18n/messages.{pt-BR,en}.yaml` + o carregador; `ACHIEVEMENTS` perde nome e
descrição; `detail` de erro voltado ao cliente em `auth.py`/`sessions.py`; teste de paridade.
Worktree isolado, em paralelo com a T-146 (tradução do conteúdo do banco) — não toquei em
`server/api/config.py`, que é território dela.

### O que saiu

- **`server/api/i18n/messages.py`**: `Messages` (dataclass `achievements`/`errors`) + `load(locale)`
  com `lru_cache(maxsize=8)`, mesmo padrão do `_mensagens_de_feedback` em `config.py`. Fallback é
  **por chave**, não por arquivo inteiro (diferença proposital em relação ao `FeedbackCatalog`,
  T-144): uma conquista ou um erro ausente no locale pedido cai na entrada de `SOURCE_LOCALE`
  sem derrubar o resto do arquivo — rede de segurança para um deploy no meio de uma tradução,
  não um caminho planejado, porque o teste de paridade já cobra os dois arquivos com o mesmo
  conjunto de chaves.
- **`server/api/i18n/messages.{pt-BR,en}.yaml`**: duas seções, `achievements` (as 7 conquistas
  de `ACHIEVEMENTS`, chave = slug) e `errors` (9 chaves usadas em `auth.py`/`sessions.py`).
  Interpolação por `str.format` (`{ceiling_s}`, `{email}`).
- **`Conquista` (`api/engagement.py`) perdeu `nome`/`descricao`** — fica só `slug` + `predicado`,
  e `to_dict()` devolve só `{"slug", "earned"}`. O módulo continua sem I/O e sem saber de locale
  (a promessa do topo do arquivo, cobrada por `test_o_modulo_puro_nao_importa_django`).
- **`engagement_cache._derivar(usuario, *, locale)`** ganhou o parâmetro que faltava — antes
  ignorava `locale` de propósito ("o conteúdo ainda não varia por língua"), que era exatamente o
  buraco que esta task fecha. `_conquistas_traduzidas()` acrescenta `name`/`description` a cada
  conquista a partir do YAML, e o resultado é o que vai para o cache — a chave já levava o locale
  desde a T-143, só o conteúdo é que ainda não variava.
- **`auth.py`**: `email_required`, `email_invalid` (com `{email!r}` interpolado), `password_required`,
  `email_taken`, `invalid_credentials`, `refresh_required`, `refresh_invalid`, `auth_required`
  saíram do código para o catálogo, resolvidos por `resolve_locale(request)` em cada view.
  `Credentials.parse()` ganhou `locale` como parâmetro.
- **`sessions.py`**: `CountedUnavailable` — a recusa do modo contado (403, "seu plano não chega
  lá") — monta o texto pelo catálogo; `resolve_set()` ganhou `locale` (default `SOURCE_LOCALE`,
  porque também é chamada sem requisição — `evalctl`, teste). `views.py._admitir` resolve o
  locale da requisição e passa adiante; é a única linha que toquei em `views.py`.

### O que ficou como estava (e por quê)

Mensagem de contrato/desenvolvedor não entrou no catálogo — quem a lê é quem manda a requisição
errada, não quem preenche formulário:

- `"corpo deve ser objeto JSON"` (`auth.py` × 2, `sessions.py`): dado explicitamente pela task
  como o exemplo do que fica.
- `sessions.py::SessionRequest.parse` — `"exercicio desconhecido: ..."`, `"requested_mode
  invalido: ..."`, `"probe_result deve ser objeto"`: violação de contrato do corpo, não erro de
  digitação de gente (o exercício e o modo vêm de catálogo fechado do cliente).
- `auth.py::_atualizar_perfil` — `"meta invalida: ...Use um de: ..."`, `"nenhum campo editavel no
  corpo"`: `daily_goal` é escolhido por seletor fixo na UI; só dispara com corpo malformado.
- `validate_password` (Django) continua fora do catálogo: o texto é do próprio
  `django.contrib.auth.password_validation`, e o projeto não ativa `django.utils.translation`
  (painel fica em `USE_I18N = False`, SPEC-025 §Escopo) — já não segue `locale` hoje, e ligar a
  tradução dele é escopo maior que esta task.

### Descoberta registrada, não corrigida

`server/api/views.py` também tem `detail` de erro claramente voltado ao cliente ("quota
indisponivel agora", "este exercicio nao esta disponivel...", "autenticacao necessaria" duplicado
em `_historico`/`engagement`, "relatorio nao encontrado"/"ainda nao disponivel" etc.) que a
spec/backlog não citaram no escopo desta task — só `auth.py` e `sessions.py`. Fica pela metade:
um `en-US` que esbarra numa quota estourada ainda lê português. Registrado no BACKLOG
(`[T-145]`) para task própria.

### Medições

- `ruff check .`: limpo.
- `pytest -q`: 1128 testes coletados, suíte inteira verde (`exit 0`).
- Critérios de aceite conferidos: (1) `GET /api/engagement` em `en` não devolve nome/descrição em
  português (`test_conquista_traz_nome_e_descricao_no_locale_pedido`); (2) trocar `Accept-Language`
  muda o corpo na mesma leitura, sem esperar cache expirar (mesmo teste, mais os de
  `test_auth.py` para `detail`); (5) paridade de chaves entre `messages.pt-BR.yaml` e
  `messages.en.yaml` é teste vermelho se uma faltar (`tests/test_i18n_messages.py`). Critérios 3
  e 4 são do site/painel — fora do alcance desta task (server, catálogo de código).

### Pendências geradas

- `views.py` sem localizar (Descoberta acima) — falta task.
- Terceiro idioma, tradução assistida no painel: Fase Evolução da spec, não tocada.

---

## 2026-08-18 (67) · T-152 — Namespace `catalog`: o embutido offline nasce nas duas línguas

Escopo: SPEC-025 Onda 2, namespace `catalog`. Migrou o catálogo embutido de exercícios
(`session/catalog.ts`), as variações de câmera da flexão (`session/exerciseViews.ts`) e —
herança explícita da T-144 — o mapa `CODE_MESSAGES` do card do treinador
(`session/coachCard.ts`). `ui/exerciseFigures.ts` entrou no gate do ESLint por ser a mesma pasta
migrada, mas não tinha texto para mover (é registro slug→ícone, puro).

### O problema que não é óbvio: texto de módulo congela no idioma do import

`EXERCISE_CATALOG` e `EXERCISE_VIEWS` são objetos montados **uma vez**, na primeira importação
do módulo. Se os campos de texto (`display_name`, `muscle_group`, `default_tip`, `scene_tip`,
`label`, `short`, `phone`, `guide_steps[].text`) fossem strings soltas com `t()` chamado na
montagem, o valor ficaria congelado no idioma detectado NAQUELE instante — o mesmo bug que o
comentário de `TABS` em `shell/TabBar.tsx` (T-142) já registrava para não repetir. A saída:
todo campo de texto virou **getter** (`get display_name() { return t('catalog:...') }`), que
chama `t()` de novo a cada leitura, não na montagem. `category`, `maturity`, `demo_img`,
`dot_color`, `main_angle` e os caminhos de imagem continuam literais — vocabulário de contrato
e caminho de arquivo não são texto.

`categoryLabel(slug)` e `textForCode(code)` recebem a chave em **tempo de execução** (slug e
código não são literais estáticos), então não davam para tipar contra `TKey` sem um `as`
mentiroso. Ganharam `tDynamic(chave, fallback)`, nova função em `i18n/index.ts` — irmã de `t()`,
mas devolve `fallback` (o slug/código cru) em vez da chave namespaced quando não encontra nada,
preservando a doutrina "feio de propósito, para ser visto" que `categoryLabel` e `textForCode`
já tinham antes desta task. Testada em `i18n/index.test.ts`.

`useCatalog()` passou a assinar `useI18nStore` além de `useConfigStore`: os getters do embutido
já respondem certo em qualquer leitura, mas sem o locale nas dependências do `useMemo` o
componente não teria motivo para re-renderizar ao trocar de idioma.

### O embutido de `CODE_MESSAGES` (herança da T-144)

`session/coachCard.ts` tinha um mapa `Record<string, string>` só em pt-BR, reservado
explicitamente para esta task no DEVLOG da T-144. Virou `textoEmbutido(code)`, usando
`tDynamic('catalog:code.${code}', code)` — as 11 mensagens (`OUT_OF_FRAME`...`CRUNCH_TOO_FAST`)
foram para `catalog:code.*`, com o `en` reaproveitando literalmente o texto de
`workers/analysis_worker/feedback/catalog.en.yaml` (T-144): é o mesmo aviso dito pelo servidor
quando há rede e pelo embutido quando não há, e ninguém deveria notar a troca. `COACH_TITLE`
virou `coachTitle()` (função interna, `catalog:coach.title`) pelo mesmo motivo dos getters acima.

### `CENA_PADRAO` mudou de forma, e por isso `GuideScreen.tsx` mudou uma linha

`CENA_PADRAO` era uma `const` exportada e consumida direto em `screens/GuideScreen.tsx`
(`view?.scene_tip ?? info.scene_tip ?? CENA_PADRAO`). Virou `cenaPadrao()` pela mesma razão dos
getters — e por não poder ser getter fora de um objeto/classe, o único jeito honesto era função.
Ajuste mecânico de uma linha em `GuideScreen.tsx` (chamar `cenaPadrao()`), sem tocar no texto
próprio daquela tela (pertence à T-148, namespace `funnel`, ainda não migrada).

### Testes existentes que quebrariam calados

`session/catalog.test.ts`, `catalogGroups.test.ts`, `serverConfig.test.ts`,
`exerciseViews.test.ts`, `coachCard.test.ts` e `report/reportSummary.test.ts` checavam texto em
pt-BR direto (`'Agachamento'`, `'Força'`, `'Apareça inteiro no quadro'`...). Locale ativo em
teste (`vitest` roda em `environment: 'node'`, sem `window`) é `'en'` por default
(`DEFAULT_LOCALE`, SPEC-025 §3.3) — sem travar o locale, essas asserções passariam a falhar
silenciosamente contra texto em inglês. Cada arquivo ganhou `useI18nStore.getState().setLocale
('pt-BR')` (top-level ou `beforeEach`, seguindo o padrão já usado em `auth/api.test.ts`).
Acrescentei também casos novos provando as DUAS línguas (não só que o pt-BR sobrevive) em
`catalog.test.ts`, `exerciseViews.test.ts` e `coachCard.test.ts` — é o critério 1 da SPEC-025 e
o ponto real desta task.

### Chaves criadas (namespace `catalog`, 56 no total)

`category.*` (4), `scene.padrao`/`scene.chao` (2), `exercise.<slug>.*` para os quatro exercícios
embutidos (24, com `guide_step.0..2`), `view.flexao.<profile|frontal>.*` (14), `coach.title`
(1), `code.<CODE>` para os 11 códigos do contrato. Tradução em tom de treinador, não literal.

### Gates

`npm run lint` (0 erros), `npm run typecheck` (`tsc -b --force`, 0 erros), `npm run test`
(639/639, 57 arquivos — 634 preexistentes + 5 novos). Worktree precisou de `git merge master`
antes de começar: o branch tinha sido criado antes de T-141/T-142/T-143/T-144 aterrissarem em
`master`, e o runtime de i18n (pré-requisito direto) não existia ainda nele.

### Pendências

Nenhuma nova. `ui/exerciseFigures.ts` não tinha texto a migrar — entrou no override do ESLint
só por doutrina de pasta, não por ter algo a corrigir.

---

## 2026-08-18 (66) · T-147 — Namespace `site`: a landing e o Sobre em duas línguas, e um terceiro entry point

Onda 2 da SPEC-025, primeira raia a fechar. Escopo: `site/IndexScreen`, `AboutScreen`,
`SiteBar`, `SiteApp` migrados para `t('site:...')`, mais o `index.html` por idioma que a spec
pede em §Escopo — Site por URL (`/` = pt-BR, `/en/` = en, `hreflang` recíproco). O worktree
onde a task rodou tinha nascido antes da T-141/T-142 fecharem em `master` — primeiro passo foi
`git merge master` (fast-forward) para trazer o runtime de i18n e o dicionário vazio de `site`
antes de escrever qualquer coisa em cima.

- **49 chaves no namespace `site`** (`dict/pt-BR/site.ts` / `dict/en/site.ts`): nav, hero,
  features, CTA, mini-HUD decorativo, seção "escolha seu exercício", rodapé institucional
  (reaproveitado entre `IndexScreen` e `AboutScreen` — é o mesmo texto nas duas telas), tela
  Sobre e a barra do site. Rótulos de acessibilidade inclusos: `alt` da imagem do hero,
  `aria-label` da nav do `SiteBar`, `title="Em breve"` dos links desativados do Sobre. Tradução
  em tom de produto — "Treine melhor. / Evolua sempre." virou "Train smarter. / Keep evolving.",
  não "Train better. Evolve always." (que soaria traduzido, não escrito em inglês).
- **Título e `<em>` que mudam de escopo entre idiomas**: o `<h1>` do hero e o subtítulo da
  seção "escolha seu exercício" tinham o `<em>` (só cor de destaque via CSS, não itálico —
  conferido em `styles.css`) em volta de UMA palavra («Evolua», «resultados reais»). Manter a
  palavra exata sob `<em>` prenderia a tradução a uma ordem de frase que o inglês não segue.
  Reestruturado para o `<em>` envolver a LINHA/oração inteira («Evolua sempre.» /
  «Keep evolving.»), preservando o efeito visual sem prender a estrutura da frase a um idioma.
- **`index.html` por idioma** (critério 3 da SPEC-025): `en/index.html` novo, terceiro entry no
  `rollupOptions.input` do Vite (`siteEn`), mesmo bundle `/src/entries/site.tsx` do `index.html`
  da raiz — só o `<html lang>` estático muda entre os dois. `hreflang` recíproco nos dois
  (`pt-BR` ↔ `en`), `title`/`meta description` traduzidos. Achado no caminho: o plugin de HTML
  do Vite trata QUALQUER `<link href>` como referência de asset a copiar/hashear, sem olhar o
  `rel` (`DEFAULT_HTML_ASSET_SOURCES.link.srcAttributes = ['href']`) — `href="/"` no `hreflang`
  quebrava o build com `EISDIR` (tentava ler o diretório raiz como arquivo). Resolvido com o
  atributo `vite-ignore` nos dois `<link rel="alternate">`, que o próprio plugin reconhece para
  pular o processamento de asset naquele nó.
- **Decisão nova, registrada aqui porque não estava em nenhum código existente: o site decide o
  locale pela URL, não pelo `useI18nStore` do app.** `SiteApp.tsx` lê `document.documentElement.lang`
  no import do módulo (mesmo timing de `detectLocale()` em `i18n/store.ts` — computado de saída,
  sem flash) e chama `useI18nStore.setState({ locale })` DIRETO, nunca `setLocale()`: a escolha é
  da URL desta visita, não uma preferência para persistir em `digitalfit.locale` — abrir `/en/`
  não pode mudar o idioma que o `/app/` abre depois. É a leitura literal de SPEC-025 §Escopo
  ("site por URL, app por preferência" — regras diferentes de propósito, não inconsistência).
- **ESLint**: acrescentado `src/site/**/*.{ts,tsx}` ao mesmo padrão de override por pasta que a
  T-142 abriu (`i18next/no-literal-string`, `mode: 'jsx-only'`). Duas exceções documentadas no
  próprio código: `active` (prop de `SiteBar`, slug de rota — vocabulário de contrato, não
  frase) entrou no `jsx-attributes.exclude` do override; `176°` do mini-HUD decorativo
  (`aria-hidden`) ganhou um `eslint-disable-next-line` pontual — é unidade, não texto de
  produto, igual às outras leituras de amostra da mesma grade (`1/1`, `12`, `87`, `124`), que já
  passavam sozinhas por serem só dígitos.
- Gates: `npm run lint` limpo, `npm run typecheck` limpo, `npm run test` — 57 arquivos / 632
  testes verdes, `npm run build` — três entries (`site`, `siteEn`, `app`) gerados, `dist/en/index.html`
  conferido manualmente (lang, title, description, hreflang, bundle `site` compartilhado).
- Sem pendências novas para o BACKLOG — `nav.ts`/`nav.test.ts` do site não tinham texto visível
  (roteador puro por hash), ficaram fora da migração por não terem o que migrar.

---

## 2026-08-18 (65) · T-142 — Runtime i18n do cliente: consertando o que a sessão anterior deixou pela metade

Sessão que retomou trabalho não commitado (a anterior caiu no meio). O grosso de `web/src/i18n/`
já existia e estava certo — `t()`, plural, interpolação, store, detecção/persistência de locale,
`<html lang>` no `AppShell`, o namespace piloto `shell` migrado em `TabBar.tsx` e o `Accept-Language`
no `authedFetch` (que já cobre metade da T-143 do lado do cliente). O trabalho desta sessão foi
consertar três defeitos concretos e fechar os gates — nenhuma decisão de arquitetura nova.

### Defeito 1 — o tipo do dicionário congelava os valores

`dict/pt-BR/shell.ts` fazia `export type Shell = typeof shell` sobre um objeto `as const`: o
tipo carregava os LITERAIS ('Início', 'Perfil', ...), então `dict/en/shell.ts` nunca compilava
('Home' não é atribuível a 'Início'). Trocado, nos nove namespaces (`account`, `catalog`,
`errors`, `funnel`, `progress`, `report`, `session`, `shell`, `site`), por
`Record<keyof typeof x, string>` — larga o valor, mantém exatamente as chaves. Chave faltando
vira erro de propriedade ausente; chave sobrando vira erro de "excess property" (a checagem de
objeto literal do `tsc`, que só dispara porque `dict/en/<ns>.ts` atribui um objeto literal, não
uma variável). O mesmo ajuste teve de subir para `i18n/index.ts`: `DICTS` era tipado como
`Record<Locale, typeof dictPtBR>`, o que forçava o `en` (valores `string` largos) a bater literal
por literal com o `pt-BR` — trocado por um `DictShape` mapeado (`{ [N in keyof typeof dictPtBR]:
Record<keyof (typeof dictPtBR)[N], string> }`), que é o mesmo raciocínio do namespace aplicado ao
dicionário inteiro.

### Defeito 2 — `typeParity.proof.ts` inconsistente

Depois do defeito 1, sobrava um erro no arquivo-prova: o segundo `@ts-expect-error` (chave
sobrando, `tab.extra`) ficava colado em cima da chamada `aceitaShell({...})`, mas o `tsc` reporta
erro de "excess property" na PROPRIEDADE em si, não no literal inteiro — o `@ts-expect-error`
sobrava (`TS2578: Unused directive`) e o erro real (`TS2353`) vazava sem supressão. Movido para
cima da linha `'tab.extra': 'x',`. Verifiquei a prova de verdade: afrouxei `Shell` para
`Record<string, string>` de propósito e confirmei que `npm run typecheck` cai (dois
`Unused '@ts-expect-error'` + um erro em `index.ts`, porque `DictShape` também não bate mais) —
depois restaurei e o typecheck voltou a ficar verde. O arquivo continua sendo prova de verdade,
não decoração.

### Defeito 3a — fallback de locale caía em pt-BR em vez de en

`locale.test.ts` cobre "sem `window` nenhum (SSR/Node puro) a leitura não lança" e esperava
`DEFAULT_LOCALE` (`'en'`), mas `detectLocale()` devolvia `'pt-BR'`. Causa: `idiomasDoNavegador()`
checava só `typeof navigator === 'undefined'` — e a partir do Node 21 o runtime expõe um
`navigator` global PRÓPRIO (não é polyfill de teste, é o Node de verdade), com
`navigator.language` vindo do locale do SISTEMA OPERACIONAL do processo (nesta máquina, `pt-BR`).
Em ambiente `environment: 'node'` (SSR/testes), isso fazia o boot "adivinhar" o idioma pela
máquina que roda o servidor, não pelo visitante — o mesmo erro de raciocínio que já tirou GeoIP
de cogitação na SPEC-025 §3.3. Corrigido checando `typeof window === 'undefined'` primeiro:
`navigator` só é sinal do idioma do VISITANTE quando existe um `window` por trás — sem `window`
não há navegador de verdade para perguntar, e a cadeia cai direto no fallback `en`. Não muda
nenhum outro teste: os que instalam `window` fake (`installStorage()`) continuam decidindo pelo
`navigator` real do processo, sem cravar o valor (só verificam "não lança").

### Defeito 3b — plural pt-BR, n=0: decisão do balde `.zero`

`Intl.PluralRules('pt-BR').select(0)` devolve `'one'` — é o CLDR, verificado direto no Node desta
máquina — então `resolveFromTable` batia em `.one` para `n=0` e devolvia "0 repetição", enquanto
o teste esperava "0 repetições" (o jeito natural de escrever isso em pt-BR). O motor continua
sendo `Intl.PluralRules`, sem cair para um `if (n === 1)`: acrescentei um balde OPCIONAL `.zero`
que, quando existe na tabela, vence antes da categoria do CLDR — só para `n === 0`; sem `.zero`
cadastrado, a categoria do CLDR normal decide (o que, para pt-BR, é `.one`, mesmo `n` sendo
zero). Comentário no `resolveFromTable` documenta o motivo. `index.test.ts` ganhou dois casos
novos no lugar do que estava incorreto: um provando que SEM `.zero` a tabela segue o CLDR ao pé
da letra (`0 repetição`, categoria `.one`), outro provando que COM `.zero` na tabela o balde
vence (`0 repetições`) sem interferir em `n=1`/`n=2+`.

### O que mais faltava (não listado como defeito, mas parte do escopo da T-142)

`eslint.config.js` já importava `eslint-plugin-i18next` (dependência instalada em `package.json`)
mas a regra nunca tinha sido de fato ligada — nem no `plugins`, nem em nenhum bloco `files`. Sem
isso o portão do §4 do plano (a regra de "texto novo entra nas duas línguas na mesma task") não
existia de verdade. Acrescentado um bloco `files: ['src/shell/**/*.{ts,tsx}',
'src/app/AppShell.tsx']` com `i18next/no-literal-string` em modo `jsx-only` (o padrão da lib,
`jsx-text-only`, só pega texto de nó JSX — `jsx-only` também pega string solta em atributo:
`aria-label`, `alt`, `title`, `placeholder`, como o plano pede). Verifiquei nos dois sentidos:
reintroduzi uma string literal em `aria-label` do `TabBar.tsx` e confirmei que `npm run lint`
reprova; restaurei e voltou a ficar limpo.

### Gates (todos verdes)

- `npm run lint` — limpo.
- `npm run typecheck` (`tsc -b --force`) — limpo.
- `npm run test` (`vitest run`) — 57 arquivos, 631 testes, todos passando.

### Pendências geradas

- Nenhuma decisão de arquitetura nova em aberto. O caminho segue T-142 → Onda 2 (T-147…T-152) →
  T-154, como o plano já previa.
- A árvore já tinha, de sessão anterior e não mexida aqui, `web/public/img/herofamale.png`
  (untracked) — mencionado também na entrada da T-141, segue fora do escopo desta task.

---

## 2026-08-18 (64) · T-144 — Feedback por idioma, e a autoridade de texto que mudou de lado

Escopo: catálogo do worker + a prioridade do texto no cliente (SPEC-025, Onda 1). Worktree
isolado, em paralelo com a T-143 — as duas tocaram `server/api/config.py`, mas em funções
diferentes (`_mensagens_de_feedback` aqui, `config_etag` lá), e o merge fechou por hunk.

### O que saiu

- **`workers/analysis_worker/feedback/catalog.en.yaml`**, par do `catalog.pt-BR.yaml`. Tradução
  em tom de treinador, não literal — `severity` e `priority` são regra, não texto, e ficaram
  idênticos de propósito.
- **`FeedbackCatalog.load(locale="pt-BR", *, path=None)`** resolve `catalog.<locale>.yaml` ao
  lado do módulo. Idioma sem arquivo cai no pt-BR: nunca estoura, nunca devolve catálogo vazio.
  `path` continua existindo como escotilha para os testes que precisam de um YAML malformado.
- **`_mensagens_de_feedback(locale)`** com `lru_cache(maxsize=8)` em vez de `maxsize=1`. O cache
  antigo era global de processo: o primeiro cliente a pedir decidia a língua de todo mundo até o
  processo reiniciar.
- **Testes**: resolução por locale, ausência de arquivo caindo no pt-BR, e paridade de chaves
  entre idiomas com cobertura de todo o enum `Code` — chave nova em um idioma só é teste
  vermelho, não bug descoberto em produção.

### A decisão que vale registrar

**A autoridade do texto do feedback passou do evento para o catálogo local**
(`web/src/session/coachCard.ts`): era `entry.message ?? textForCode(code)`, virou
`textForCode(code)` primeiro, com `message` como último recurso. O worker só fala pt-BR e não vai
receber o locale — levá-lo até lá custaria três camadas de encanamento (cliente → `POST
/sessions` → estado no Redis → worker) para um problema que o cliente já resolve sozinho, porque
recebe o catálogo inteiro na própria língua pelo `GET /api/config`. A detecção de "catálogo local
não conhece este código" usa o eco do próprio código que `textForCode` devolve nesse caso.
`FeedbackIssued` ganhou o docstring correspondente em `workers/shared/events.py`: campo aditivo,
nada quebra, `PROTOCOL_VERSION` não sobe.

### Pendências geradas

- O embutido de `CODE_MESSAGES` nas duas línguas saiu do escopo desta task e foi para a **T-152**
  (namespace `catalog`): ele precisa do runtime de i18n que a T-142 está construindo, que não
  existia nesta árvore. É o fallback offline — sem rede, o card ainda cai em pt-BR.
- `config_payload` ainda não resolve locale; quem passa o idioma para `_mensagens_de_feedback`
  chega com a T-146.

---

## 2026-08-18 (63) · T-143 — Negociação de locale, e os caches que não sabiam que ela existia

Escopo: servidor apenas (SPEC-025, Bloco de i18n — T-144 traduz conteúdo, T-146 cataloga; esta
task é o mecanismo de transporte por baixo dos dois). Worktree isolado, em paralelo com a T-144
mexendo em `config.py` no mesmo arquivo — por isso o diff em `config.py` é uma função só.

### Um desvio que precisa ficar registrado antes do resto

`specs/SPEC-025-internacionalizacao.md` e `docs/PLANO-I18N.md`, que o contrato desta task manda
ler, **não existem neste worktree** — `specs/` para em SPEC-024, `docs/` não tem `PLANO-I18N.md`,
e `BACKLOG.md` não tem linha para T-143 (nem para T-141…T-146; a última linha real é a T-140).
Busquei em todo o worktree (case-insensitive, `i18n`/`internacional`/`plano-i18n`) e no histórico
de commits deste branch — nenhum rastro. As três outras worktrees paralelas partem do mesmo
commit (`2078df0`), então não é um branch desatualizado em relação aos outros.

O que a instrução da task continha, porém, era um contrato completo e conferível: assinaturas,
prioridade de resolução, as três dimensões de cache exatas com os valores de HOJE citados
literalmente (`config_etag` era `(config_version, plan_slug, is_admin)`; `chave_de_cache` era
`(user_pk, dia)`; o `Vary` de `/api/config` era só `Authorization`). Conferi cada uma dessas
afirmações contra o código antes de escrever a primeira linha — todas bateram, inclusive o
detalhe de que `Conquista.to_dict()` embute `name`/`description` como texto pronto dentro do
payload que o cache guarda. Decidi implementar por esse contrato (é preciso, testável e bate com
a realidade do código), e registrar a lacuna aqui em vez de tentar adivinhar ou de travar a
sessão inteira. **Pendência real**: alguém com acesso ao histórico completo (ou à conversa que
gerou a task) precisa commitar `SPEC-025`/`PLANO-I18N.md` de verdade, reconciliados com o que
saiu daqui — abri uma sugestão de sessão separada para isso. Não toquei em `BACKLOG.md` (não
está na lista de arquivos da task, e a linha da T-143 não existe para eu marcar `done`).

### As decisões desta task

**1. `resolve_locale` pesa o `Accept-Language` por `q`, não pega o primeiro item.** A spec cita
quatro exemplos de normalização (`pt`, `pt-br`, `pt_BR`, `pt-BR;q=0.9`) como se o cabeçalho
trouxesse um valor só, mas um cabeçalho de verdade é `en-US,en;q=0.9,pt-BR;q=0.8` — pegar o
primeiro item por posição erraria a preferência real sempre que o navegador listar um idioma não
suportado na frente. Implementei o parser completo (separa por vírgula, lê `;q=`, ordena por
peso com a ordem de chegada como desempate) porque os quatro exemplos são um subconjunto do que
esta função precisa resolver todo santo dia, e resolver só o subconjunto seria escrever o defeito
que os testes não pegariam (nenhum dos quatro exemplos tem mais de um idioma).

**2. `?locale=` desconhecido cai no `DEFAULT_LOCALE`, não volta a espiar o cabeçalho.** A spec
diz "`?locale=` (override explícito) > `Accept-Language` > `'en'`" e não cobre o caso de um
override que não normaliza para nada. Duas leituras possíveis: ignorar o override ruim e cair
para o cabeçalho, ou tratá-lo como qualquer valor desconhecido (→ default). Escolhi a segunda:
"override explícito" quer dizer que a pessoa pediu aquele idioma explicitamente, e inventar uma
segunda regra de prioridade escondida dentro da primeira (override presente mas ignorado)
seria menos previsível que a normalização de sempre. Testado nos dois arquivos (função pura em
`test_i18n.py`, rota real em `test_locale_via_query_param_vence_o_cabecalho_tambem_na_rota`).

**3. `DEFAULT_LOCALE = "en"` é literal da spec, e o código teria puxado para `pt-BR` sem ela.**
Todo conteúdo hoje é português hardcoded — seria fácil "corrigir" o default para `SOURCE_LOCALE`
por analogia. Mantive `en` porque é isso que a task pede e faz sentido de produto (visitante sem
cabeçalho reconhecível tem mais chance de estar fora do Brasil que dentro), mas registro que os
dois papéis — "língua de origem do conteúdo" e "língua de quem não disse nada" — são
deliberadamente distintos (`SOURCE_LOCALE` vs `DEFAULT_LOCALE`), e um teste
(`test_default_locale_e_en`) trava essa distinção contra o instinto óbvio de igualá-los.

**4. `engagement_cache.chave_de_cache` existe como função nova, e não como edição da de
`engagement.py`.** A task nomeia literalmente `engagement_cache.chave_de_cache(...)`, mas a
função pura que hoje monta `df:eng:{user}:{data}` mora em `api/engagement.py` — que está na
lista de proibidos (T-144 não mexe nela, mas o motivo dela ser pura e pequena é o mesmo motivo
de eu não dever mexer: SPEC-019 promete `(user, dia)` sem I/O e sem locale, e locale é harness de
transporte da SPEC-025, não regra de derivação). Resolvido compondo por cima: uma função NOVA,
literalmente acessível como `engagement_cache.chave_de_cache(user_id, hoje, locale)`, que chama
`regra.chave_de_cache(user_id, hoje)` (a de `engagement.py`, intocada) e acrescenta `:{locale}`.
Satisfaz a letra do critério 4 (a chave é alcançável exatamente pelo caminho que a task nomeia)
sem tocar no arquivo proibido nem no contrato puro da SPEC-019.

**5. A invalidação varre `LOCALES` inteiro, não só o locale de quem escreveu.** `_limpar` roda
fora de qualquer requisição — é `post_save` de `SessionResult`/`User`, sem `Accept-Language`
nenhum para escolher UMA chave. Se ela apagasse só uma, a outra ficaria servindo engajamento
velho até a próxima escrita ou a meia-noite — o mesmo bug do critério 4, só que pela porta da
invalidação. `test_invalidar_apaga_a_chave_de_todo_locale` prova as duas metades juntas: os dois
locales aquecidos, o `post_save` disparado, os dois apagados, os dois recalculando fresco.

**6. `GET /api/engagement` não ganhou `Vary: Accept-Language`.** É a única rota afetada que já
usa `Cache-Control: no-store` — sem cache HTTP nenhum, `Vary` não tem o que declarar. A dimensão
de locale dela mora inteira do lado do Redis (`chave_de_cache`), não do lado do navegador/proxy.
Documentei a omissão no próprio comentário da view para quem for procurar o `Vary` e não achar.

### O que foi feito

- `server/api/i18n/__init__.py` (novo pacote): `LOCALES`, `SOURCE_LOCALE`, `DEFAULT_LOCALE`,
  `resolve_locale(request)` — duck-typed para `rest_framework.request.Request` (`.query_params`)
  e `django.http.HttpRequest` (`.GET`), sem depender de nenhum dos dois para ser testado.
- `server/api/config.py`: só `config_etag` — ganhou `locale: str = DEFAULT_LOCALE` como quarta
  dimensão do hash. Nada mais no arquivo mudou (import de `DEFAULT_LOCALE` à parte).
- `server/api/engagement_cache.py`: `chave_de_cache` nova (locale sobre a chave pura),
  `payload_de(usuario, *, locale=DEFAULT_LOCALE)`, `_limpar` varrendo `LOCALES`.
- `server/api/views.py`: `config()` resolve locale, repassa a `config_etag`, `Vary` ganha
  `Accept-Language`; `engagement()` resolve locale e repassa a `payload_de`.
- `server/core/cors.py`: `Accept-Language` em `ALLOWED_HEADERS` (preflight).
- Nada em `models.py`, `engagement.py`, `auth.py`, `sessions.py`, `workers/`, `web/` — conferido
  por `git diff --stat` ao final, não só por intenção.

### Verificação dos critérios de aceite

- **1** (`resolve_locale`, normalização, constantes): `tests/test_i18n.py` — 20 testes, pura,
  sem banco. Cobre os quatro exemplos literais da spec, variantes de inglês, cabeçalho com peso
  (incluindo `;q=` malformado), prioridade do override e o fallback `.GET`/`.query_params`.
- **2** (locale na quarta dimensão do ETag): `test_locale_diferente_muda_o_etag` (unitário) e
  `test_trocar_de_locale_nao_devolve_304` (rota real: ETag obtido em pt-BR, pedido em en com o
  mesmo `If-None-Match`, **200 com corpo**, não 304) em `tests/test_catalog_api.py`. O
  contrapositivo (`test_mesmo_locale_continua_custando_304`) prova que a revalidação normal não
  quebrou. `test_normalizacao_do_accept_language_produz_o_mesmo_etag` prova que `pt`/`pt-br`/
  `pt_BR`/`pt-BR;q=0.9` colapsam no mesmo ETag — a normalização não é só da função pura.
- **3** (`Vary` inclui `Accept-Language`): assert acrescentado em
  `test_config_responde_privado_e_com_etag` (continua provando `Authorization` junto).
- **4** (`chave_de_cache` inclui locale): `test_locale_diferente_nao_le_o_cache_do_outro_locale`
  (semear a chave de um locale com um valor sentinela não vaza para o outro),
  `test_mesmo_locale_continua_lendo_do_proprio_cache` (contrapositivo) e
  `test_invalidar_apaga_a_chave_de_todo_locale`, em `tests/test_engagement_api.py`.
- **5** (CORS aceita `Accept-Language`): `test_o_preflight_aceita_o_cabecalho_de_idioma` em
  `tests/test_cors.py`, no mesmo padrão do teste existente para `If-None-Match`.
- **6** (mecanismo, não texto): coberto pelos testes acima — nenhum depende de
  `catalog.en.yaml` ou de conteúdo traduzido; todos comparam ETags/corpos/chaves com o mesmo
  payload em português nos dois locales, provando o transporte, não a tradução.

### Medições

- `uv run ruff check .` — limpo.
- `uv run ruff format --check .` — limpo nos arquivos desta task; **um arquivo pré-existente,
  fora do escopo** (`tests/test_sessions.py`, dois `next(...)` que o formatador colapsaria numa
  linha) já estava fora de formato no commit-base deste worktree, antes de qualquer edição minha
  (`git status`/`git diff --stat` confirmam que nunca toquei nele). Não corrigido — não está na
  lista de arquivos desta task.
- `uv run pytest` — suíte completa: **1095 passed**. Rodando só os arquivos tocados: 197 passed.
- Durante a sessão, `/home` bateu em 0 bytes livres por alguns minutos (provável concorrência das
  worktrees paralelas de T-144/T-145 no mesmo disco) e `ruff format`/cache falharam com ENOSPC.
  Contornado redirecionando `RUFF_CACHE_DIR`/`TMPDIR` para `/tmp` (partição diferente, com
  espaço) só para os comandos desta sessão — nenhum arquivo do projeto foi apagado ou movido. O
  disco já tinha ~5 GB livres de novo antes do fim da sessão; registrado caso volte a acontecer
  em sessões-irmãs.

### Pendências geradas

- `specs/SPEC-025-internacionalizacao.md` e `docs/PLANO-I18N.md` precisam existir de verdade no
  branch, reconciliados com esta entrada (é o registro mais próximo do contrato que existe hoje).
  `BACKLOG.md` também precisa das linhas T-141…T-146 (a última linha real é T-140).
- O corpo de `GET /api/engagement` ainda não varia por locale — só a chave que o guarda. Isso é
  correto para esta task (T-144/T-146 trazem o catálogo de tradução), mas quem for ligar a
  tradução do nome/descrição de conquista precisa passar `locale` para dentro de `_derivar`, que
  hoje ignora esse parâmetro de propósito.
- `_mensagens_de_feedback()` (o dicionário código→texto pt-BR do `GET /api/config`) não entrou
  nesta task por estar explicitamente reservada à T-144 em paralelo — ela também não passa por
  `resolve_locale` ainda, e vai precisar quando a T-144 chegar lá.

---

## 2026-08-18 (62) · T-141 — SPEC-025: o plano vira spec, e nada foi decidido de novo

Sessão de projeto, não de código. Fonte única: `docs/PLANO-I18N.md`, já escrito e com todo o
mapeamento e as decisões de arquitetura tomadas e aprovadas fora desta sessão — o trabalho aqui
foi **transcrever**, pela skill `df-spec`, para o formato de spec da casa e desdobrar em tasks.
Nenhuma decisão nova, nenhum código tocado.

### O que saiu

- **`specs/SPEC-025-internacionalizacao.md`**, `Status: approved` direto — não `draft`, porque a
  aprovação já aconteceu na elaboração do plano, não nesta sessão. `Camada: transversal` (é a
  primeira spec a levar esse rótulo: toca cliente, api, worker e HTML ao mesmo tempo, sem ser
  dona de nenhuma camada sozinha). Depende de SPEC-008 (catálogo de feedback), SPEC-011
  (negociação por `Accept-Language`, conta anônima), SPEC-013 (dicionário do cliente) e SPEC-018
  (config/painel, tabela de tradução).
- **Linha nova no índice de `specs/README.md`.**
- **`## Fase 7 — Internacionalização (SPEC-025)` no `BACKLOG.md`**: as 16 tasks do §5 do plano
  (T-141…T-156), em cinco tabelas — Onda 0 (o contrato, esta task), Onda 1 (4 raias, fundações),
  Onda 2 (6 raias, uma por namespace de dicionário), Onda 3 (fechamento) e uma trilha paralela
  (T-156, fuso). Ondas, dependências e tamanhos (P/M/G) preservados do plano; onde ele não dava
  um código de spec por task (Ondas 2 e 3 são lá tabelas de Namespace/Arquivos e de Dep, não de
  Spec), o código foi inferido do conteúdo real de cada uma — por exemplo T-148 (namespace
  `funnel`) aponta para a SPEC-015 porque é literalmente o funil que ela nomeia, e T-151 (fogo,
  XP, conquistas) aponta para a SPEC-019 pelo mesmo motivo. É leitura do que já existe, não
  arquitetura nova.
- `docs/PLANO-I18N.md` entra no commit junto: é a `Referência` da spec, e ela citar um arquivo
  de fora do histórico não faria sentido.

### O que a spec registra, e não decide

Duas partes do plano mereciam ficar escritas com o mesmo peso de qualquer outra decisão desta
casa, porque são o tipo de coisa que se perde se só viver num documento de planejamento:

- **A inversão do `coachCard` é a maior alavanca do plano, e vira decisão de contrato.**
  `feedback.issued.message` deixa de ser autoridade de texto — o `code` é. O cliente já recebe o
  dicionário completo no `GET /api/config`, na sua língua; inverter `entry.message ??
  textForCode(entry.code)` resolve o idioma inteiro sem tocar em `POST /sessions`, Redis ou
  worker. O campo `message` continua no evento (vira diagnóstico/legado) — mudança
  aditiva-compatível, `PROTOCOL_VERSION` não sobe. A nota correspondente no docstring de
  `FeedbackIssued` (`workers/shared/events.py`) fica para a T-144, que é quem codifica a
  inversão — registrar a decisão aqui e implementá-la lá são sessões diferentes, e escrever a
  nota no código agora seria tocar código sem task.
- **As três armadilhas de cache (ETag, `lru_cache(maxsize=1)`, chave de engajamento) viram
  Notas técnicas da spec e, por tabela, critério de aceite da T-143.** Nenhuma aparece como erro
  — todas aparecem como "às vezes o app está na língua errada", o tipo de bug que some na
  primeira tentativa de reproduzir.

### Pendências geradas

- Nenhuma decisão de arquitetura em aberto — o plano já chegou fechado; o que resta é sequenciar.
  O caminho crítico (plano §6) é T-141 → T-142 → (T-149 ‖ T-150 ‖ T-151) → T-154; a Onda 1
  inteira roda em paralelo à escrita da T-142, e T-146/T-156 não bloqueiam ninguém.
- A árvore já tinha, antes desta sessão, `web/src/session/exerciseViews.ts` modificado e duas
  imagens novas em `web/public/img/` (`guia/flexao-frente-1.jpg`, `herofamale.png`) — trabalho de
  outra sessão, não mexido e não commitado aqui.

---

## 2026-08-17 (61) · T-136 — A série resolvida na admissão: modo, meta e teto do servidor

Terceira perna do Bloco C (SPEC-023). A T-134 escreveu o carimbo, a T-135 ensinou o worker a
encerrar por meta — e as duas dependiam de alguém **decidir** o modo. Esta task é esse alguém:
`POST /api/sessions` passa a resolver `set_mode`, `target_reps`, o teto e o carimbo de série,
junto de quota, duração, countdown e cloud, na fronteira da API e uma vez por sessão (P1 da
SPEC-018). O cliente pede; o servidor resolve; o worker obedece ao evento.

### As três decisões desta task

**1. "Generoso" virou número — e o número virou duas coisas.** A §4 diz que o gate do modo
contado é ter `session_max_s` generoso, sem dizer quanto. A admissão precisa da régua para
responder sim ou não, então ela existe agora: `COUNTED_MIN_CEILING_S = 60`, o dobro da janela
livre. O argumento está escrito na constante: teto menor que isso não é teto de série, é a
mesma janela competitiva com outro nome — e o modo contado existe para ser o oposto dela.
Ficou constante de código, e não campo do painel, porque derivá-la de um valor editável
(`default_duration_s`) deixaria alguém destravar o modo contado em plano que não o suporta
mexendo em outra coisa. A régua fica parada; o que o painel move é o teto de cada plano.

**2. A migration `0021` sobe o teto da assinatura para 180 s, e isso quebra um precedente de
propósito.** Sem ela a task entregaria uma trava perfeita numa capacidade que nenhum plano tem:
os três saíram da `0006` com `session_max_s = 30`, então o modo contado nasceria recusado para
todo mundo, inclusive para quem paga, até alguém lembrar de mudar um número no painel — e a
T-137 construiria o montador de série para ninguém. A `0006` documentou que migration de infra
não entrega mudança de produto; aqui a mudança de produto **é** a task, e ela aparece no nome do
arquivo, que é a mesma inversão que a `0010` fez com a quota do Free. Três minutos = 15
repetições a 5 rpm; mais lento que isso não é treinar devagar, é ter parado. Free e visitante
ficam nos 30 s — é o cadeado da SPEC-016, e o modo livre de 30 s continua completo.

O piso do código (`_FLOOR_PLAN["subscriber"]`) subiu junto, e é o único lugar onde ele deixa de
ser "o produto de ontem". É de propósito e tem teste: um Postgres fora do ar não pode tirar do
assinante o modo que ele acabou de pagar (P2), e se um dos dois números andar sozinho o modo
contado passa a existir ou sumir dependendo de o banco estar de pé.

**3. A vaga cloud passou a durar a série, não o ticket.** Achado ao codar, e é defeito que esta
task criaria: `create_session` pedia a vaga com `ttl_ms = ticket_ttl_s`, e até aqui os dois
davam no mesmo (30 s de sessão dentro de 45 s de TTL + 15 s de graça), então a vaga sempre
expirava depois do fim, por construção. Com uma série contada de 3 min o semáforo devolveria a
vaga aos 60 s **com a pessoa ainda treinando**, e uma 4ª sessão cloud entraria: três
`pose-worker` viram quatro e o orçamento de VPS que a SPEC-009 protege vira ficção. Agora o
prazo é `max(ttl_s, duration_s)` — o `max` é o que mantém o modo livre com o número de antes,
provado em teste parametrizado (livre 45 s, contado 180 s). Não registrei como Descoberta
porque não é achado alheio: é o rombo que a própria T-136 abriria.

### O que foi feito

- `api/config.py`: `COUNTED_MIN_CEILING_S`; `Capabilities.allows_counted` (a régua) e
  `Capabilities.target_reps()` (a meta, no clamp da faixa dos steppers que o painel já publica —
  ter uma régua para desenhar o montador e outra para admitir a série é o que transforma um
  cliente adulterado numa meta de 500 reps); `session.counted` no `GET /api/config`.
- `api/sessions.py`: `SetPlan` (a série como o servidor a resolveu, com a duração dentro —
  no modo contado ela **é** a resolução, e um teto separado do modo é o par que alguém esquece
  de atualizar junto); `resolve_set()` como função pura sobre o plano; `CountedUnavailable`;
  os quatro campos no `SessionRequest` (pedido, não resolução) e no ticket de volta.
- `api/views.py`: a recusa 403 `counted_unavailable` **antes** do Redis e da quota — recusar
  depois de consumir o contador cobraria da pessoa um treino que ela não chegou a fazer.
- `workers/shared/events.py`: `_as_set_mode` virou `parse_set_mode` (público, como
  `parse_camera_view`), para a admissão e o worker normalizarem o campo com a mesma régua.
- Migration `0021_teto_da_serie_contada`, simétrica na volta e só tocando quem ainda está no
  valor neutro (lição da `0010`: migration não sobrescreve decisão de operação).
- Nada em `web/` (é a T-137), nada em `exercises/`, nada no report-builder.

**A recusa é dita, não contornada.** Degradar o contado para livre em silêncio seria "gentil" e
mentiroso: a pessoa pediu 15 repetições sem pressa e receberia 30 s de janela, com o relatório
contando outra coisa. O 403 traz o motivo em português e o `session_max_s` do plano; quem
escolhe o que fazer com isso é o cliente da T-137.

### Verificação dos critérios de aceite

- **2b** (plano de 30 s recusa com motivo legível): na régua,
  `test_plano_de_30s_nao_tem_onde_a_serie_contada_acontecer`; pelo HTTP real,
  `test_o_free_recebe_recusa_legivel_em_vez_de_serie_cortada` — 403, `code`,
  `session_max_s: 30`, e a prova de que **nada nasceu**: nenhum evento publicado e
  `SessionClaim.objects.count() == 0`. Mais o outro lado (`assinante` treina contado com teto
  180 no ticket **e** no evento) e o painel mandando (`session_max_s=30` na assinatura derruba
  o modo sem deploy).
- **4** (forjar o cliente não muda nada): meta parametrizada (999 → 30, 1 → 5, 0 → 15, 20 → 20);
  `duration_s`/`session_max_s` no corpo ignorados; e a costura inteira em
  `test_a_meta_forjada_nao_encerra_a_serie_onde_o_cliente_quis` — o evento que a view publicou
  vai para o `AnalysisRouter` de verdade, 35 repetições de polichinelo entram e a série fecha em
  `target_reached` com `rep_count == 30`. É o critério provado onde ele importa: não que o
  número certo aparece no ticket, mas que é **por ele** que a série termina.
- **9**, metade da API (corpo sem os campos da spec abre nos defaults):
  `test_corpo_sem_os_campos_da_serie_abre_nos_defaults` e
  `test_modo_de_serie_invalido_cai_no_livre_em_vez_de_derrubar` — mesma tolerância da vista da
  T-111: erra a escolha, perde a escolha, não o treino.
- **3** (regressão do modo livre): `test_modo_livre_nao_passa_por_nada_disto` (o caminho livre
  sai antes da régua do contado, então nem plano curto nem meta no corpo o alcançam) e o gate de
  contagem do corpus (`test_corpus_regressao`) verde no `pytest`. **Não** rodei `evalctl` sobre
  os vídeos desta vez, e o motivo é verificável: o diff desta task é API + contrato, e a bancada
  não carrega nada disso — a prova estrutural está na entrada da T-135.
- Carimbo da §3: `set_index`/`set_total` incoerentes (4 de 3, índice sem total) viram `0/0`, a
  sessão avulsa de todo o passado. O servidor não é dono do treino na Fase Inicial, então não
  tem o que validar aí além da coerência interna — e "série 4 de 3" no relatório seria número
  errado na tela, que é pior do que número nenhum (SPEC-014).
- Fora do alcance desta task: **1** e **2** são do worker (T-135, feitos); **5**, **6**, **7**,
  **8** são do cliente (T-137/T-138); **10** continua coberto pela T-135; **11** é a T-139.

### Pendências geradas

- **A T-140 deixou de ser hipótese.** A Descoberta `[T-135]` (`target_reached` não cai em balde
  nenhum do `exercise_health`) virou task no Bloco C. Antes desta entrega o problema era
  inalcançável — nenhuma sessão podia terminar por meta; agora falta só o cliente da T-137. Ela
  é **pré-requisito de produção do modo contado**, não da T-137.
- O `SessionTicket` do cliente (`web/src/session/admission.ts`) ainda não espelha os quatro
  campos novos; é escopo da T-137 e não quebra nada hoje (campo JSON a mais é ignorado).
- `GET /api/config` agora responde `session.counted` — é o que a T-137 deve ler para decidir se
  oferece o montador de série, em vez de recomparar `max_s` por conta própria.

### Gates

`ruff check` limpo; `ruff format --check` limpo nos arquivos tocados; `pytest`
**1051/1051** (eram 1020 na T-135; +31 testes). `makemigrations --check` não detecta modelo
pendente — a `0021` é só dados. Nada de web, nada de infra.

---

## 2026-08-17 (60) · T-135 — Modo contado no analysis-worker: a meta encerra a série

Segunda perna do Bloco C (SPEC-023). A T-134 carregou o carimbo; esta task é a primeira em que
alguma coisa **decide** com ele. Escopo: só o worker. A admissão continua sem resolver modo
(T-136) e o cliente continua sem HUD contado (T-137) — nenhuma sessão de produção termina em
`target_reached` ainda, e é de propósito.

### As duas decisões desta task

**1. A meta fecha no caminho do frame, não no `tick`.** A série contada acaba dentro do
`_on_pose_frame`, no frame em que a N-ésima repetição foi detectada — e o `session.completed`
sai com o `ts` daquele frame. Fechar no `tick` seguinte seria mais simples e estaria errado
pelo motivo que a spec inteira existe: o número que o modo contado promete é o **tempo até a
meta**, e um fim carimbado no tick carregaria o atraso do loop do worker dentro dele. É a mesma
razão pela qual a T-049 pôs o countdown no servidor e não na animação. O fim é appendado
**depois** do feedback engine, senão o HUD congelaria em 14/15 numa série que terminou completa.

**2. O teto trocou de relógio — e só no modo contado.** No `expiry_reason`, o prazo 1 deixou de
ser um `if` e virou um `if self.counted / elif`: no livre continua sendo a janela de parede da
SPEC-009, no contado passa a ser `last_ts - exercise_started_ts >= duration_s`, o relógio dos
frames. A troca é o que separa os dois modos, e não é preciosismo: a janela do livre é
competitiva de propósito (30 s de parede iguais para todo mundo), enquanto a série contada é o
oposto — *"um aplicativo que não te apressa"* —, e cortá-la porque a rede engasgou seria cobrar
de quem treina uma latência que não é dela. De quebra é o que faz replay reproduzir o mesmo fim
(critério 10). Nasceu daqui o `exercise_started_ts`, par do `exercise_started_wall_ms` já
existente, ancorado no mesmo instante ("o JÁ") e medido no `ts` do cliente.

Isso não abre sessão pendurada, que era a objeção óbvia: sem frame chegando o `ts` para de
andar e o `no_data` fecha em 10 s; com frames de `ts` congelado (cliente quebrado), o teto
absoluto de vida fecha em `timeout`. As duas redes de segurança continuam sendo de parede, que
é onde elas têm de estar.

### O que foi feito

- `workers/analysis_worker/router.py`: `set_mode`/`target_reps`/`exercise_started_ts` no
  `SessionState`; `counted` como predicado único (exige modo contado **e** meta > 0 — modo
  contado com meta 0 é contrato malformado e degrada para livre, porque um `reps >= 0` fecharia
  a série na repetição zero, exatamente a cara de app quebrado que a T-112 já pagou para
  aprender); fim por meta no caminho do frame; teto por `ts` no `expiry_reason`.
- `_encerrar()` extraído: os três passos de todo fim decidido pelo servidor — tirar do
  dicionário, deixar a lápide, devolver a vaga cloud — agora moram num lugar só. O fim por meta
  é um **caminho de fim novo**, e caminho de fim esquecido come vaga cloud para sempre (SPEC-009,
  critério 2); foi separar esses passos que produziu o bug da T-077. O `tick` passou a usá-lo.
- Nada em `exercises/`, nada na API, nada no cliente, nada no report-builder.

### Verificação dos critérios de aceite

- **1** (meta encerra na N-ésima rep, não no teto): `test_meta_encerra_a_serie_no_frame_da_nesima_repeticao`
  — 15 reps, meta 15, `reason=target_reached`, `rep_count=15` e `ts` do fim **igual** ao da 15ª
  `rep.detected`. Mais `test_meta_atingida_fecha_a_porta_para_o_resto_da_serie`: fixture de 20
  reps com meta 15 produz 15 `rep.detected` e descarta o resto pela lápide.
- **2** (estouro do teto): `test_estourar_o_teto_termina_em_completed_sem_erro` — 10 de 15,
  `reason=completed`, `rep_count=10`, `router.sessions == {}`.
- **3** (regressão do modo livre): duas provas, uma estrutural e uma medida. Estrutural:
  `test_modo_livre_nao_fecha_pelo_ts_dos_frames` — os mesmos frames que fecham a série contada
  pelo teto deixam a sessão livre **aberta**, com as 10 reps contadas. Medida: `evalctl run` nos
  três vídeos de polichinelo do corpus deu **20 / 13 / 19**, que é exatamente o que o
  `manifest.yaml` documenta (rótulos 20/15/21 com `conhecido: 0 / -2 / -2`). E o motivo de nem
  poder ser diferente ficou provado, não alegado: a bancada **não carrega o `router.py`** —
  `sorted(m for m in sys.modules if "analysis_worker" in m)` depois de importar `eval.pipeline`
  traz `calibration` e `exercises`, e `"workers.analysis_worker.router" in sys.modules` é
  `False`. O único arquivo de produção que esta task tocou está fora do caminho do corpus.
- **9** (evento anterior à spec abre nos defaults): `test_sessao_sem_os_campos_da_spec023_abre_no_modo_livre`,
  no roteador (a T-134 já cobria no contrato). Mais `test_modo_livre_ignora_target_reps`: os dois
  campos andam juntos, `target_reps` sozinho não encerra nada.
- **10** (replay reproduz o mesmo fim): `test_a_serie_contada_e_a_mesma_em_qualquer_relogio_de_parede`
  — mesmas frames com duas paredes a 30 dias de distância (o desvio que a T-078 mediu em
  produção) dão o mesmo motivo, a mesma contagem e o mesmo `ts` de fim.
- Vaga cloud no caminho novo: `test_a_meta_devolve_a_vaga_cloud`.
- **Todos os testes do modo contado rodam com a parede congelada**, e isso é parte do
  argumento: com a parede parada nenhuma regra de parede pode fechar a sessão, então o que
  fechou, fechou pelo `ts`.
- Fora do alcance desta task: **2b** e **4** são da admissão (T-136); **5**, **6**, **7** e **8**
  são do cliente (T-137/T-138); **11** é da derivação de cadência (T-139).

Conferido de passagem, porque falharia só em produção e só na primeira série contada:
`SessionResult.reason` é `CharField(max_length=16)` e `"target_reached"` tem 14 caracteres. Cabe.

### Pendências geradas

- Descoberta **`[T-135]`**: `target_reached` não cai em nenhum balde do `exercise_health` — a
  taxa de zero-rep da SPEC-020 sai de `reason == "completed"` e a cadência mediana também, então
  a série contada entra no `total` e desaparece do resto. Precisa estar resolvido antes de o
  modo contado chegar em produção (ou seja, antes da T-136 ir ao ar), e a decisão é da SPEC-020.

### Gates

`ruff check` limpo; `ruff format --check` limpo nos dois arquivos tocados; `pytest`
**1020/1020** (eram 1010 na T-134; +10 testes, todos do modo contado). Nada de web, nada de
migration, nada de infra nesta task.

---

## 2026-08-17 (59) · T-134 — Contrato do treino: `set_mode`, `target_reps`, `set_index`, `set_total`

Abre o Bloco C (SPEC-023): raia contrato → worker → api → client do modo contado (meta de
reps, sem pressa, com descanso entre séries). Esta task é só o contrato — nada decide fim de
série por meta ainda (T-135), nada resolve o modo na admissão (T-136), nada no cliente.

**Achado ao carregar a spec, antes de escrever uma linha: `mode` já existe.** A SPEC-023
nomeava o campo novo `mode` (`"livre"` | `"contado"`). Mas `session.started` **já tem** um
`mode` — o de extração de pose (`edge`/`cloud`, SPEC-001), presente no contrato, na coluna
`SessionResult.mode` e no `to_report()`. São dois eixos independentes da mesma sessão (por
onde os keypoints saíram × como a série termina) e a spec, ainda `draft`, não tinha percebido
a colisão. Seguido o AGENTS.md à risca: a spec foi corrigida antes de codar, não driblada em
silêncio. Renomeado para `set_mode` — ecoa `set_index`/`set_total`, que já eram vocabulário de
série na própria spec. Registrado na SPEC-023 §2 com uma nota explicando o porquê.

### O que foi feito

- `workers/shared/events.py`: `SetMode` (novo enum, `LIVRE`/`CONTADO`) com docstring explicando
  a não-colisão com `Mode`; `SessionEndReason.TARGET_REACHED`; quatro campos aditivos em
  `SessionStarted` (`set_mode`, `target_reps`, `set_index`, `set_total`), todos com parsing
  tolerante — igual a `config_version`/`countdown_s`: valor ausente ou torto vira o default
  (`livre`/`0`), nunca derruba o `session.started` inteiro. `PROTOCOL_VERSION` não sobe (a
  spec já justificava isso na §Eventos).
- `workers/report_builder/builder.py`: os quatro campos viajam do `_SessionBuffer` para o
  `SessionReport` — consolidação pura, sem decisão nova (quem decide fim por meta é a T-135).
- `server/api/models.py` + migration `0020_treino_em_series`: colunas aditivas em
  `SessionResult` (mesmo padrão da `config_version`, T-075) e no `to_report()`.
- Nada tocado em `server/api/sessions.py` (admissão): `SessionStarted` já é construído lá sem
  os quatro campos novos, então toda sessão de hoje continua abrindo em modo livre avulso sem
  precisar de nenhuma mudança — é a prova viva de que o contrato é aditivo de verdade, não só
  na letra.

### Verificação dos critérios de aceite tocados por esta task

- **9** (evento sem os campos abre nos defaults): `test_session_started_sem_campos_da_t134_e_aditivo`.
- Tolerância a lixo (mesmo espírito do 9, para valor presente mas torto):
  `test_set_mode_torto_vira_livre_em_vez_de_derrubar_o_evento`,
  `test_carimbos_de_serie_tortos_viram_zero_em_vez_de_derrubar_o_evento`.
- Não-colisão com `mode`: `test_set_mode_nao_colide_com_o_modo_de_extracao`.
- Round-trip msgpack/stream dos quatro campos e de `TARGET_REACHED`: entradas novas em
  `PAYLOADS` (`tests/test_events.py`), cobertas pelos testes parametrizados existentes.
- Consolidação chega ao Postgres, não só ao dataclass em memória:
  `test_relatorio_carrega_os_carimbos_de_serie_da_abertura`,
  `test_sessao_sem_abertura_usa_defaults_de_serie`, e as asserções novas em
  `test_persist_faz_upsert_por_session_id`/`test_relatorio_pela_api`.
- Os critérios que dependem de contagem por meta, teto e admissão (1, 2, 2b, 4-8) ficam para
  T-135/T-136 — esta task não decide fim de série, só carrega o carimbo.

### Gates

`ruff check` limpo; `ruff format --check` limpo no que esta sessão tocou (`tests/test_sessions.py`
já estava fora do formato antes desta task, não mexido); `makemigrations --check` sem
pendência; `migrate` aplica limpo em SQLite; `pytest` **1010/1010**.

---

## 2026-08-17 (58) · operação: renumeração do Bloco C (SPEC-023)

O Bloco C (`BACKLOG.md`) reusava T-111/T-112/T-113 para as tasks do treino contado — os mesmos
IDs das tasks de Tier C (flexão/abdominal) que já estavam `feito`. Colisão encontrada numa
avaliação geral do projeto, antes de abrir a primeira task do Bloco C. Renumerado para
T-134…T-139 (contíguo com T-114/T-115/T-116, que não colidiam mas ficaram junto para o bloco
ler como uma sequência só). Atualizada a referência em `docs/IDEIAS-2026-08-05-conversa.md`
(§Bloco 2). Nenhum código tocado.

---

## 2026-08-17 (57) · T-113 — flexão e abdominal para todo mundo, com os lastros diferentes

Pedido direto: ao deslogar, os dois somem, e o Daniel quer os dois visíveis para qualquer
pessoa. Migration 0019 põe `flexao` e `abdominal` em **`validado`** — o único degrau que aparece
para anônimo e Free.

**O que essa linha custa, dito antes de fazer e registrado depois de feito.** Os dois chegam
com lastro muito diferente:

| exercício | corpus real | erro medido | vai a `validado` porque |
|---|---|---|---|
| `flexao` | 8 itens, 5 com rótulo contado a mão | **0,20 rep** (MAE) | tem medição |
| `abdominal` | **nenhum vídeo de gente** | — | decisão de produto |

O abdominal está exatamente na posição em que a flexão estava quando passou 19 h em produção
contando zero — o incidente que originou o `test_corpus_regressao.py`. Se ele contar errado,
contará errado para todo visitante, e não há um número neste repositório que preveja isso. A
dívida continua declarada em `SEM_MATERIAL_REAL`, o teste que a cobra continua de pé, e o freio
de mão é o campo Maturidade no painel: rebaixa numa edição, sem deploy. Um único vídeo de
abdominal fecha a lacuna — a mesma bancada que mediu a flexão hoje mede ele em minutos.

O `down` da migration devolve cada um ao degrau que a medição sustenta (`flexao` → `calibrado`,
`abdominal` → `beta`), e não os dois ao mesmo lugar: um `down` simétrico apagaria a diferença
que o `up` documenta.

### Os testes que travavam a maturidade viraram testes da regra

Quatro deles cobravam o catálogo do dia (`== ["jumping_jack", "squat"]`) para provar que `beta`
não vaza. Com nenhum exercício em `beta`, eles passariam por vacuidade. Agora cada um **planta**
um `beta` e cobra a regra em cima dele — medem a trava, não o inventário.

---

## 2026-08-17 (56) · T-112 — a trava que existe porque zero repetição é lido como "app ruim"

A T-111 deu duas vistas à flexão e um controle na coluna da pré-configuração. O controle resolve
para quem procura; esta task é sobre quem **não sabe que precisa procurar**. O risco, dito pelo
Daniel e correto: a pessoa não percebe a escolha, monta a cena da vista errada, o treino termina
em **zero**, e zero não é lido como "montei errado" — é lido como "esse app não funciona". Ela
desinstala antes de descobrir que havia um botão.

### O desenho

Uma trava no caminho do **"Ligar câmera"**, e não numa tela de ajustes: o próximo gesto de quem
confirma é pegar o celular e pôr no chão (ou em pé). Perguntar depois seria perguntar tarde.

- **Cards grandes, os dois visíveis.** Não é um `<select>` porque as opções não são valores de um
  campo — são duas montagens de cena, e o que se compara é *o que fazer com o celular*, não o
  nome da vista. Esconder uma atrás de menu é a falha que a trava veio consertar.
- **Responsivo por grid** (`auto-fit` + `minmax(150px, 1fr)`): lado a lado quando cabe, empilhado
  quando não. Sem media query e sem medir em JS. Medido: lado a lado a 375 px e a 904 px,
  empilhado a 320 px. Em tela baixa (≤ 620 px de altura) o parágrafo de apoio some primeiro,
  porque os cards e o botão é que precisam caber.
- **Checkbox "não mostrar novamente" desmarcado por padrão**, e isso é a decisão de produto da
  caixa: quem chega pela primeira vez não tem como saber que vai querer dispensá-la. Marcar por
  conveniência seria decidir por ela na tela que existe para ela decidir. O rótulo diz para onde
  a escolha vai embora ("você continua trocando pelo card Câmera") — sem isso, "não mostrar" lê
  como "perdi o controle", e aí ninguém marca, ou marca e se arrepende sem caminho de volta.

### Três regras, e a terceira é a que evita virar praga

1. Só aparece para exercício que **tem** variação. Polichinelo e agachamento nunca a veem.
2. Só aparece **uma vez por visita**. Confirmou, ligou a câmera, tocou em "Iniciar" — não
   pergunta de novo (`confirmadoPara`, estado do componente, não armazenamento).
3. Quem dispensa nunca mais a vê **naquele exercício**. A dispensa é por slug, como o guia visto
   e a própria variação: no dia em que outro exercício ganhar vistas ele terá uma decisão de cena
   própria para ensinar, e herdar o "já sei" da flexão devolveria a sessão zerada.

Sem armazenamento (Safari privado) a trava **aparece**. É o lado certo do erro: perguntar de novo
custa um toque, não perguntar custa a sessão inteira.

### O buraco que quase passou

A trava intercepta o `iniciar`, não o botão — e por isso cobre também quem **trocou de exercício
com a câmera já ligada**. Nesse caminho o CTA está em "Iniciar Exercício", e uma trava presa ao
rótulo "Ligar câmera" deixaria a pessoa entrar no treino sem nunca ter visto a pergunta.

Confirmar também **segue o degrau interrompido** (liga a câmera, ou entra no treino se ela já
estava ligada), em vez de devolver a pessoa ao mesmo botão para tocar de novo.

### Verificado no navegador, não só por teste

Ciclo inteiro numa stack isolada: a trava abre no "Ligar câmera", **bloqueia o CTA de trás**
(`elementFromPoint` devolve a própria trava), a escolha grava e reflete no card da coluna, o
segundo toque na mesma visita não pergunta, o reload sem dispensa pergunta de novo, marcar o
checkbox grava `digitalfit.view_gate_off.flexao=1`, e depois disso ela some e o card da coluna
continua lá. Polichinelo: nem trava, nem card.

---

## 2026-08-16 (55) · T-111 — a flexão contava zero de lado, e a culpa era do porteiro

Cinco vídeos novos de flexão no corpus (três de perfil, dois de frente) e o pedido: melhorar,
deixar a vista ser escolhida por quem treina, habilitar o exercício. A primeira medição, antes
de tocar em nada, dizia que não havia nada de sutil para ajustar:

| vídeo | rótulo | contava |
|---|---|---|
| lateral, série 1 | 16 | **0** |
| lateral, série 2 | 16 | **0** |
| lateral, série 3 (fadiga) | 11 | 3 |
| frontal, 20 lentas | 20 | 11 |
| frontal, 5 pegadas × 5 | 25 | 19 |

MAE 9,14 repetição. Um exercício que estava em produção (invisível, `beta`) e que, na vista que
o próprio Guia ensina, **não contava absolutamente nada**.

### O rótulo veio antes do conserto, e um dos vídeos não era o que dizia ser

O vídeo lateral tem 82 s e o nome dizia "16 repetições". Assistido, é um time-lapse de rede
social: cartela "Meta: 3 x 15" e "Intervalo 80 segundos" entre as séries. Não é uma série
contínua — é três, com os intervalos cortados —, e o README do corpus é explícito em que corte
no meio invalida a contagem.

Foi fatiado em três clipes, um por série, e cada um rotulado **aqui**: vale a vale do ângulo de
cotovelo cru (sem FSM, sem limiar), com conferência visual nos frames de início e fim. Deu 16,
16 e 11. O "16" do nome era a primeira série.

Conferência independente que vale mais que o método: rodada no vídeo inteiro, a bancada conta
**43** — exatamente 16 + 16 + 11. As três contagens somam sozinhas.

Os dois frontais têm o rótulo dentro do próprio vídeo (um conta em voz alta e por legenda,
"1… 3 4… 5 meus parabéns soldado"; o outro anuncia "5 NORMAIS ✅ 5 ABERTAS ✅…"). São 20 e 25.

### Um defeito só, em duas vistas: porteiro alimentado por grandeza que se move

De frente, `wrists_below_hips` (distância pulso→quadril) cai de 1,19 para 0,20 torsos quando o
peito desce. O porteiro de chão exige 0,30. Ele fechava **no fundo de cada repetição**, e
`_abandon_attempt()` descartava a tentativa em curso — a repetição que a pessoa acabara de fazer
sumia calada, sem contagem e sem crítica. Nove das vinte.

De perfil, o mesmo com `plank_height >= 0,25`: no fundo a altura do ombro sobre a mão cai a
0,205. Quem descia **mais** era quem tinha mais chance de perder a rep.

E, ainda de perfil, um segundo defeito: a profundidade era medida contra a maior altura da
sessão, que os frames de montagem da prancha fixavam em 0,914 enquanto o topo de cada repetição
ficava em 0,70. Razão 0,77, contra um `sobe` de 0,93 que **nunca** era cruzado. Daí o 0/16.

### Os dois consertos, medidos separados

| desenho | MAE | exatos |
|---|---|---|
| hoje | 9,14 | 0/7 |
| só porteiro com histerese | 7,00 | 1/7 |
| só profundidade pelo cotovelo | 3,43 | 3/7 |
| **os dois** | **1,29** | **4/7** |

São independentes e somam: a histerese conserta a frente (11 → 20), o cotovelo conserta o
perfil (0/0/3 → 16/16/11). Restrito aos cinco vídeos de rótulo verificado, **MAE 0,20**.

1. **Porteiro com histerese**: entrar exige a evidência forte de sempre (a que recusa gente em
   pé, intacta), permanecer exige só que a mão continue no nível do quadril ou abaixo, e sair
   exige que a fraca falhe por 400 ms seguidos. É a mesma histerese que a FSM já usa, uma
   camada antes.
2. **Profundidade pelo ângulo do cotovelo nas duas vistas**, contra o maior ângulo da própria
   pessoa. O módulo já declarava que de lado o cotovelo é honesto (dobra no plano da imagem);
   faltava usá-lo. A altura da prancha continua viva para `hip_line` e `ready_pose`.

Varreduras (o platô, não o pico):

| eixo | valores que dão contagem idêntica | escolhido |
|---|---|---|
| `off_floor_ms` | 250 · 400 · 500 · 750 | **400** |
| `stay_wrists_below_hips` | 0,00 · 0,10 | **0,00** |
| `down_depth` (com `up` 0,80) | 0,60 · 0,63 · 0,66 | **0,63** (inalterado) |

**Nenhum limiar de profundidade mudou.** O conserto é estrutural, e a varredura confirma que
0,63/0,80 continua no meio do platô depois dele. `up_depth` = 0,80 é o que o perfil decide: com
0,90 as três séries laterais desabam para 2/4/4, porque de lado quase ninguém trava o cotovelo.

As duas contagens que já existiam (v1 52, v2 43) **não se mexeram** — é o que separa conserto
estrutural de ajuste ao rótulo.

### A vista virou pergunta, não palpite

`CameraView` entrou no contrato (`events.py` primeiro, como manda o AGENTS) e viaja no
`session.started`: pré-config → `POST /sessions` → analisador. A detecção geométrica continua
existindo e continua acertando as sete fixtures — mas agora é **fallback**, não caminho do
produto. Motivo: a vista troca o porteiro, e uma detecção que oscile no meio da série troca a
régua com a pessoa em movimento. Vista desconhecida ou ausente não derruba a admissão; vira
"ninguém disse".

O despacho mora no `get_analyzer()`, não no router: quem declara o atributo `view` recebe, quem
não declara ignora. Um `if slug == "flexao"` no worker seria a primeira pedra do caminho que a
SPEC-007 proíbe.

Na tela, segmentado e não ciclo — as duas opções pedem que a pessoa faça algo **diferente** com
o celular, e um controle que mostrasse só a atual esconderia metade da decisão. Aparece na
pré-config (card estreito, "Lado/Frente" + onde o celular vai) e no Guia (rótulo inteiro, mais a
frase do que se ganha e se perde em cada vista). Trocar no Guia reescreve os passos e a
instrução de cena; a escolha é por exercício e sobrevive à sessão.

### Promoção

`flexao` vai a **`calibrado`** (migration 0018) — a primeira promoção do produto, e a primeira
coisa dentro do Laboratório 🧪 que a 0017 abriu e que estava vazio. Aparece para assinante e
admin; para o Free continua invisível, porque a prateleira do Free é `validado` e `validado`
exige a paridade edge×cloud×navegador e a semana em produção que só o uso real produz.

**Verificado no navegador** (stack isolada, banco descartável): a flexão aparece no catálogo, o
controle troca passos e cena no Guia, a escolha chega na pré-config, o card cabe na coluna de
92 px sem quebrar linha e sem rolagem horizontal.

### Pendências

- `[A/T-111]` — a variação mora no bundle do cliente, como a figura do exercício: variação nova
  exige deploy. Levá-la ao painel é task própria.
- O `abdominal` continua `beta` e continua sem um único vídeo de gente real — a mesma posição de
  que a flexão está saindo.
- `validado` da flexão depende da semana em produção. O relógio só começa agora.

---

## 2026-08-16 (54) · operação — o painel não era o nginx

Sessão de conserto, sem task: `/painel` devolvia 404 em produção e a investigação estava indo
para o nginx. Medido antes de tocar em qualquer coisa, contra o domínio no ar:

| URL | resposta |
|---|---|
| `/painel` | `301` → `/painel/` |
| `/painel/` | `404`, `text/html; charset=utf-8`, com `X-Frame-Options: DENY` |
| `/static/painel/digitalfit.css` | `200 text/css` |

**O nginx estava certo desde o começo.** O `301` prova o `location = /painel`; o CSS em
`text/css` prova o `location /static/` chegando no whitenoise dentro do container da api. E o
404 é o do **próprio Django** — corpo do `ERROR_PAGE_TEMPLATE`, headers do `SecurityMiddleware`.
Ou seja: a requisição atravessava tudo e morria em `build_urlpatterns` com `ADMIN_ENABLED`
desligado.

### A armadilha que fazia isso parecer um problema de rota

`docker compose restart` **não recarrega o `.env.prod`** — reinicia o processo com o ambiente
que o container já tinha. Editar a variável e dar `restart` não muda nada e não emite erro
nenhum. O único caminho que existia para aplicar era o `up` completo, que rebuilda o bundle do
Vite por minutos para trocar um booleano — caro o bastante para o operador preferir o `restart`
que não funciona.

### O que passou a existir

- `./scripts/prod.sh painel on|off` — escreve no `.env.prod`, recria **só** a api
  (`up -d --force-recreate --no-deps api`, sem rebuild) e confere que a rota respondeu.
- `./scripts/prod.sh painel` — diagnóstico. Imprime o valor no arquivo **ao lado do valor que o
  container está rodando** (é a divergência que nenhum log mostrava) e cruza dois códigos HTTP:
  o da porta local da api e o do domínio público. O par separa os dois modos de falha que se
  confundem — `404` do Django (rota desmontada) contra `200` do container do web (a landing).
- `./scripts/prod.sh exec` — **existia na documentação e não no `case`**. README e `DEPLOY.md`
  o citam em seis lugares, incluindo o `createsuperuser`, que é o único jeito de criar a
  primeira conta do painel. A instrução documentada caía em "comando desconhecido".

O diagnóstico foi exercitado nos quatro cenários (painel desligado, falta de `location`, tudo
certo, api fora do ar) com o `codigo_painel_*` injetado, e o caso público bateu no domínio real.

### Pendência

Nada disso foi **aplicado** em produção: a VPS do Digital Fit não é a do MCP `ssh-vps`. Falta
rodar `./scripts/prod.sh painel on` lá.

---

## 2026-08-15 (53) · T-090 — o catálogo do produto encolhe pela metade, e está certo

Task de regra: o eixo maturidade entra **dentro** do `exercises_for()` que a T-074 criou, valendo
no `GET /api/config` e na admissão pelo mesmo resolvedor. O que ela faz é pequeno; o que ela
**revela** não é.

### O número que muda hoje

`flexao` e `abdominal` nascem `beta` na migration 0012, e `beta` é ferramenta de dev — nunca
liberado por plano (SPEC-020 §Maturidade). Medido depois da mudança:

| quem | vê |
|---|---|
| anônimo | `jumping_jack`, `squat` |
| Free | `jumping_jack`, `squat` |
| assinante | `jumping_jack`, `squat` |
| `is_admin` | `abdominal`, `flexao`, `jumping_jack`, `squat` |

**O catálogo visível vai de 4 exercícios para 2.** Está certo pela spec — um `beta` tem limiares
calibrados só contra o boneco sintético, e o `[A/T-106]` é a prova documentada de que isso não
sobrevive a gente de verdade. Também é honesto pelo que a T-110 mediu: a contagem da flexão é
sensível ao limiar de profundidade em quem faz repetição rasa.

Mas é uma mudança de produto grande, e a saída dela não é código: é **promover os dois**, o que
depende do corpus da T-108 — gravação. Enquanto isso, o app oferece dois exercícios.

### A ortogonalidade que precisou de `if`

`MATURITY_RANK` resolveria o eixo com uma comparação: `beta` vale 0, e os dois valores que o
`Plan` aceita valem 1 e 2. Só que resolveria **por acidente**. Bastaria alguém gravar
`min_maturity="beta"` por SQL — fora do formulário que valida — para o laboratório inteiro abrir
para todo mundo. O `if` explícito é o que transforma "acontece de funcionar" em regra, e tem
teste que faz exatamente esse `UPDATE`.

Mesma família: maturidade **desconhecida** (valor fora do vocabulário, linha editada por fora,
deploy pela metade) some para quem não é admin. Tratá-la como `validado` liberaria justamente o
caso em que ninguém sabe o que aquilo é.

### O vazamento de primeiro paint

O catálogo embutido do cliente é o do primeiro paint e do offline, e listava os quatro — então
quem abrisse o app veria, por um instante, dois cards que o `POST /sessions` recusa. É o
`[A/T-051]` na janela mais curta e mais difícil de reproduzir que existe.

O embutido passou a declarar `maturity` e a ser filtrado a `validado` antes de o servidor falar.
**`validado` e nada além**, porque o cliente não sabe o plano nem o `is_admin` nesse instante —
quem tem direito a mais espera a resposta, que vem em milissegundos e manda.

Cinco testes existentes quebraram, e vale dizer por quê: eles afirmavam
`currentCatalog() === EXERCISE_CATALOG`, identidade do objeto. A propriedade que **descreviam** é
"o embutido continua no ar", e essa continua verdadeira. Passaram a afirmar a propriedade.

### Uma decisão de dado que a task precisou tomar

A migration 0006 semeou os três planos com `min_maturity: "validado"` — neutro e correto naquele
dia, porque nada lia a coluna. Com a regra ligada, o valor deixa de ser neutro: com `validado` em
todos, o eixo existiria sem nunca mudar nada para ninguém, e o Laboratório 🧪 que a SPEC-020
§Planos dá ao assinante não existiria.

Migration 0017 abre o Laboratório, **só na linha do assinante e só se ela ainda estiver no valor
semeado**. Quem já mexeu pelo painel decidiu alguma coisa, e um deploy que desfaz a edição
quebraria em silêncio a promessa inteira da SPEC-018. Não muda nada observável hoje — nenhum
exercício está em `calibrado`.

### Gates

`ruff check` e `format --check` limpos; `pytest` **971 passando** (+8 sobre os 963 da T-078).
Web: `lint` sem warnings, `tsc -b` limpo, **571 testes** (+4), `npm run build` OK.

### Pendências

- **O app oferece dois exercícios até a T-108 dar corpus.** É a consequência de produto desta
  task, e é o argumento mais concreto que existe para priorizar a gravação: cada dia com o eixo
  ligado é um dia com metade do catálogo fora do ar.
- **A recusa da admissão não diz o motivo.** Continua `exercise_unavailable` com a frase genérica
  — o cadeado com motivo distinto ("assinante" ≠ "em validação" ≠ "crie conta") é a T-091, e a
  SPEC-020 pede que os motivos sejam visualmente distintos lá, não aqui.
- **Sem catálogo no banco, a admissão volta a aceitar qualquer slug registrado**, `beta`
  inclusive. É o caminho degradado que a T-074 já tinha (P2: o produto de ontem), e ele só
  dispara com a tabela inteira ilegível — mas agora ele **abre** o que a regra fecha. Não mexi:
  fechar também deixaria a tela Escolha vazia num soluço de banco. Fica registrado porque a
  escolha mudou de peso com esta task.

---

## 2026-08-15 (52) · T-078 — o relatório para de subtrair um relógio do outro

A Descoberta `[A/T-077]` estava aberta desde julho, e não é cosmética: além de errar a duração
em silêncio, ela **matava o report-builder** com `DataError: integer out of range` quando o
desvio passava dos 24,8 dias em que o `PositiveIntegerField` estoura. Também é pré-requisito da
T-112 — "tempo até a meta" é exatamente o número que ela erra.

### O que estava misturado

`buffer.last_ts` era o `max` do `ts` de **todos** os eventos, e a duração saía de
`last_ts − started_ms`. Só que `started_ms` vem do `session.calibrated` (relógio do **cliente**,
`ts` do frame) e um dos eventos do balde vem da API:

| evento | quem publica | relógio |
|---|---|---|
| `session.started` | `api/sessions.py` | **servidor** |
| `session.calibrated`, `rep.detected`, `feedback.issued`, `scene.warning` | analysis-worker | cliente (`ts` do frame) |
| `session.completed` | analysis-worker | cliente — `estado.last_ts` |

Medido no teste, com um celular 30 dias atrasado em relação ao servidor: a duração de uma sessão
normal de 30 s saía **2.592.000.000 ms**. Depois da correção, 30.000.

### A hipótese da Descoberta que estava errada

A proposta original sugeria usar a origem do evento para separar. Não funciona: `session.started`
e `session.completed` são **ambos `Source.SYSTEM`** — o `source` diz "não veio de um humano", não
diz de qual relógio. O que separa é *quem publica*, e isso não está no envelope.

Então virou uma lista nomeada de um item só (`_EVENTOS_DO_RELOGIO_DO_SERVIDOR`), com um teste que
quebra se um segundo evento da API entrar no stream sem alguém revisar a lista. É a trava que
importa: o bug voltaria calado no dia em que a API publicasse qualquer outra coisa.

O `session.completed` **não** precisou sair da conta, e vale dizer por quê: ele usa o `ts` do
último frame e só cai no relógio do servidor quando não houve frame nenhum — e nesse caso a
calibração também não aconteceu, então a duração já era zero por outro caminho.

### O teto, e por que ele grava zero em vez do teto

A exclusão resolve o desalinhamento entre servidor e cliente. Sobra o resíduo: o relógio do
**próprio cliente** andando no meio da sessão (troca de fuso, NTP, hora ajustada à mão) — o
comentário do `SessionState` já avisava disso, e o relatório não seguia o próprio conselho.

O teto sai da **própria sessão**: o `session.started` já carrega `duration_s`, resolvido pela API
a partir do plano (SPEC-018). Sessão de 30 s que reporta 10 minutos é implausível; a mesma
duração numa sessão admitida como 600 s é honesta. Sem `session.started` (builder que subiu no
meio), cai num teto absoluto de 6 h — muito abaixo dos 24,8 dias do estouro e muito acima de
qualquer treino.

Acima do teto grava **zero, não o teto**. Gravar o teto seria inventar um tempo que ninguém
treinou, e a cadência derivada dele mentiria com cara de número medido. Zero já significa "não
sei" neste campo, o `cadence_rpm` e as janelas saem zerados junto — e o log diz o resto, com os
dois timestamps.

### Gates

`ruff check` e `format --check` limpos; `pytest` **963 passando** (+7 sobre os 956 da T-089).
`web/` não foi tocado.

**Os testes foram conferidos contra a ausência do conserto**: revertendo só a linha da exclusão,
dois deles falham e o log imprime os 2.592.000.000 ms. Teste de regressão que passa com e sem o
conserto não é teste de regressão.

### Pendências

- **Nenhum relatório já gravado foi corrigido.** As sessões com duração torta que existam no
  banco continuam lá; recalcular exigiria replay do stream, e os eventos não são retidos por
  tanto tempo. Quem for olhar histórico antigo precisa saber disso.
- **O teto de 6 h é generoso demais para o produto de hoje** (sessões de 30 s). Foi escolhido
  para não recusar sessão honesta de uma configuração futura; se o `Plan.session_max_s` continuar
  em 600 s, dá para apertar bastante — mas apertar sem necessidade é criar um jeito novo de
  perder dado bom.
- **A T-112 pode andar.** Era a única dependência dela além da T-111.

---

## 2026-08-15 (51) · T-089 — as conquistas, e a única que pode ser perdida

Última do M1. Catálogo de 7 predicados puros, lista no `GET /api/engagement`, galeria no painel
e aviso de conquista nova por diff local. **O M1 fecha aqui** — o fogo acende, sobrevive ao
cadastro, aparece na tela e agora premia.

### A conquista que pode ser tirada de volta

`semana-cheia` é "meta batida 7 dias seguidos", e a meta é campo **mutável** do perfil. A
consequência: subir de `casual` para `intenso` pode **apagar** uma conquista já mostrada; descer
faz o contrário, concede retroativamente.

O incômodo é que a SPEC-019 já tinha feito exatamente este raciocínio — na §XP, para tirar o
bônus de meta batida da fórmula:

> *"Quem estava em `intenso` e muda para `casual` faria todos os dias passados virarem 'meta
> batida' de uma vez, e o XP saltaria retroativamente"*

O argumento foi aplicado ao XP e não à conquista, que a mesma spec continua nomeando como
"gatilho" da meta. Implementei como a spec manda — não é ambiguidade, é uma escolha explícita
dela — e registrei a Descoberta `[T-089]` com as três saídas possíveis. **Perder um troféu por
mudar de configuração é pior que nunca tê-lo ganho**, e a saída mais barata (declarar que a
galeria é um retrato de agora, não um histórico) não custa código, só decisão.

### O primeiro acesso não dispara sete avisos

O detalhe que mais moldou o código do cliente. O servidor não guarda "notificado em" — a spec
recusa a tabela —, então o aviso é um diff contra o `localStorage`. Ingenuamente, quem já
treinava antes desta task abriria o app e receberia **sete toasts de uma vez**, alguns de
conquistas ganhas meses atrás.

A primeira leitura marca tudo como visto **em silêncio**. É a mesma escolha do `guide_seen`: a
marca existe para não repetir, não para celebrar retroativamente. Tem teste, e tem o irmão dele:
armazenamento quebrado (Safari privado) degrada para *"tudo visto"*, nunca para *"tudo novo"* —
sete avisos por causa de um storage indisponível seria pior que aviso nenhum.

### Decisões

- **O catálogo é do servidor, inteiro, com `earned` em cada linha.** Mandar só as ganhas
  obrigaria o cliente a ter a lista completa escrita nele — e aí o catálogo estaria em dois
  lugares, que é o `[A/T-051]` de sempre. A galeria desenha as bloqueadas apagadas mas
  **legíveis**: esconder o que falta faria da tela um troféu, e a mecânica existe para ser um
  objetivo.
- **`centena` é por exercício, `milheiro` é no total**, e há teste separando os dois: somar tudo
  daria a "centena" a quem fez 50 de cada, que é outra coisa e mais fácil.
- **`Agregados` é um objeto, e não a lista de sessões.** Predicado que pudesse varrer o histórico
  por conta própria acrescentaria uma passada por conquista nova, sem ninguém notar — e todas são
  calculadas a cada leitura. Uma passada só, em `_agregar`.
- **O diff das conquistas mudou de lugar durante a implementação.** Nasceu num `useEffect` do
  toast e o lint reprovou (`set-state-in-effect`). A regra estava certa por um motivo melhor que
  o dela: o diff pertence ao **instante em que o dado chega**, não à renderização — com o toast
  desmontado (painel fechado, outra tela), a conquista se perderia. Foi para o store.
- **A galeria mora no painel, e o Perfil abre o painel.** A spec pede "galeria no Perfil";
  desenhá-la nos dois lugares criaria duas telas para manter iguais.
- **Ordem do catálogo é do fácil ao difícil**, com teste. Uma vitrine que abrisse com `milheiro`
  apagado diria a quem acabou de chegar que o jogo não é para ela.

### Gates

`ruff check` e `format --check` limpos; `pytest` **956 passando** (+11 sobre os 945 da T-088).
Web: `lint` sem warnings, `tsc -b` limpo, **567 testes** (+9), `npm run build` OK.

### Pendências

- **A Descoberta `[T-089]` precisa de decisão de produto** antes de alguém ganhar e perder uma
  `semana-cheia` de verdade. Hoje ninguém tem 7 dias de histórico em produção — a janela para
  decidir barato é agora.
- **A galeria não foi verificada no navegador**, porque ela só existe para quem tem conta e isso
  exige a stack inteira de pé. Coberta pelos testes dos dois lados; o que foi medido no navegador
  na T-088 foi o caminho do visitante, que não tem conquista.
- **Conquistas por categoria de exercício continuam de fora**, como a spec prevê: dependem da
  SPEC-020 dar categoria ao catálogo (T-090). O campo `tem_categorias` existe em `Agregados` e
  está sempre `False` — é o gancho, não a implementação.
- **`sem-reparo` conta sessões limpas de qualquer tamanho.** Dez sessões de uma repetição limpa
  valem tanto quanto dez de trinta. Não é errado pela spec, mas é farmável.
- `web/public/img/herofamale.png` segue sem task e fora dos commits (sétima entrada seguida).

---

## 2026-08-15 (50) · T-088 — o fogo aparece, e sabe de quem é o número

Terceira do M1. As duas anteriores puseram o fogo no servidor e o fizeram sobreviver ao
cadastro; esta o põe na tela. Fecha o marco em produto funcional — chip na Início, painel com
calendário, seção no Perfil, "+XP" no relatório e o fogo fantasma do visitante.

### A regra que desenhou o código todo

O critério de aceite 8 é curto e decide a arquitetura: *"anônimo nunca vê número do servidor;
logado nunca vê número calculado no cliente"*. A escolha entre as duas fontes acontece **uma
vez**, no `useEngagement`, e chip, painel e Perfil recebem o mesmo objeto sem saber de onde veio.
Componente que decidisse sozinho acabaria decidindo diferente — e a divergência apareceria como
dois números de fogo na mesma tela.

Duas consequências que valem estar escritas:

- **Logado sem resposta do servidor mostra `--`, não cai no fantasma.** Seria tentador: o
  histórico está ali, a função existe. Mas seria o número do cliente na tela de quem tem conta,
  que é literalmente o que o critério proíbe.
- **Medido no navegador: com visitante, nenhuma requisição a `/api/engagement` sai.** A rede
  confirma o que o código promete — o anônimo não recebe zeros do servidor porque nem pergunta.

### A decomposição do "+XP" vem do servidor, e isso não é preguiça

A tentação era espelhar a fórmula em TypeScript: são três constantes. Mas a fórmula é
**versionada** (`XP_FORMULA_V`), o que é outra maneira de dizer que ela vai mudar — e no dia da
mudança um dos dois lados ficaria para trás, em silêncio, porque nenhum teste compara Python com
TypeScript. É o `[A/T-051]` de novo, com pontos no lugar de exercícios.

Então nasceu `decomposicao_de_xp` no mesmo módulo que soma o total, e o relatório passa a trazer
`xp: {total, session, reps, clean, formula_v}`.

**O enriquecimento mora na view, não no `to_report()`**, por duas razões que se somam: aquele
payload é o replay-derivável da SPEC-010 (o que sai dos eventos, e nada além), e XP não existe
para o visitante (§Planos). A view sabe se há conta; o modelo não sabe e não deve saber. Visitante
recebe o relatório sem a chave — e não com zeros, que ele leria como "não valeu nada".

### O fogo fantasma, e o fuso que quase estragou tudo

O visitante deriva o fogo do `localStorage` que a T-121 já mantinha. Com **zero proteções**
(§Planos), a regra do servidor colapsa em "dias seguidos terminando hoje ou ontem" — então não há
espelho da mecânica de proteção no cliente, só a versão degenerada dela.

O detalhe que exigiu cuidado é o fuso. `history/aggregates.diaLocal` usa o fuso de quem lê, e
está certo lá ("que dia foi para mim"). Aqui a pergunta é outra: *que dia o servidor vai dizer
que foi*, porque este número tem de bater com o da conta no instante seguinte ao cadastro. Um
fogo fantasma de 3 que virasse 2 assim que a conta existe destruiria a confiança na mecânica no
primeiro contato — e por culpa de um fuso, não de um treino. `engagement/fire.ts` usa
America/Sao_Paulo fixo, igual ao servidor.

O calendário do painel herda a mesma disciplina: usa `diasAtivos` (SP + sessão válida) e **não**
`diasComTreino` (fuso local + qualquer sessão). O docstring da segunda já avisava do risco; o
calendário é a explicação visual do fogo, e um dia aceso na grade que não conta para a sequência
seria uma contradição na mesma tela, sem nada explicando.

### Medido no navegador

Verificado com histórico local semeado (sessões em D, D-1, D-2 e D-4):

| o que | resultado |
|---|---|
| chip | `🔥 3` — o D-4 fica de fora, porque visitante não tem proteção |
| anel da meta | cheio (1/1) |
| calendário | 4 dias acesos, hoje marcado, 16 dias futuros apagados |
| painel do visitante | aviso "vive só neste aparelho" + CTA, **sem** XP, nível ou seletor de meta |

**Um bug de layout apareceu na medição e foi corrigido**: a 320 px o chip passava por baixo do
título (−14 px de sobreposição). Media query a ≤360 px encolhe chip e título; refeita a conta,
sobra folga em todas as larguras medidas — 320 (12 px), 360 (32 px), 375 (13 px), 430 (41 px).
O anel **não** foi sacrificado no aperto: a meta é metade da informação que o chip carrega.

### Decisões

- **`--` e não `0` enquanto o servidor não respondeu**, e as regras de texto moram em
  `format.ts`, fora dos `.tsx`. São regras de honestidade (SPEC-014), não desenho: num arquivo
  próprio elas têm teste e não dependem de renderizar componente.
- **O rótulo do fantasma também vai no `aria-label`.** O ponto cinza do chip não existe para
  quem não vê a tela, e "3 dias seguidos" sem a ressalva seria uma promessa falsa em áudio.
- **Parcela zerada some da linha de XP.** "limpa +0" não é informação, é ruído com cara de
  repreensão — a ausência do bônus comunica sem apontar o dedo.
- **A galeria de conquistas do Perfil não foi desenhada.** A mesma linha da spec a pede, mas o
  catálogo de predicados é a T-089: uma vitrine vazia diria "você não conquistou nada" sobre uma
  mecânica que ainda não foi ligada.
- **`refreshEngagement` sem conta zera o store**, em vez de só não buscar: um payload sobrando
  ali seria o fogo de outra pessoa esperando para aparecer depois de um logout.

### Gates

`ruff check` e `format --check` limpos; `pytest` **945 passando** (+4 sobre os 941 da T-087).
Web: `lint` **sem warnings**, `tsc -b` limpo, **558 testes** (+37), `npm run build` OK.
Verificação no navegador por JS (screenshot trava neste ambiente, quirk conhecido).

### Pendências

- **O caminho de quem tem conta não foi verificado no navegador** — exigiria a stack inteira de
  pé (Postgres, Redis, Django) e o dev server do web sozinho não a tem. Está coberto ponta a
  ponta pelos testes de API, e o que foi medido no navegador foi o caminho do visitante.
- **O calendário do logado lê o histórico, que o servidor corta em 50 sessões** (`HISTORY_LIMIT`).
  Para a grade de um mês isso basta hoje; para quem treinar duas vezes por dia por um mês, não.
  O fogo em si não sofre — ele vem do `GET /api/engagement`, que lê todas as datas.
- **Nível continua sem nome.** A tela mostra "Nível 2". A spec pede nomes "definidos com o
  produto", e continua valendo o pedido da entrada 48.
- **Nenhum toast de nova conquista**, porque não há conquista (T-089).
- `web/public/img/herofamale.png` segue sem task e fora dos commits (sexta entrada seguida).

---

## 2026-08-15 (49) · T-087 — a conta deixa de custar o histórico

Segunda do M1, e a que torna a T-086 honesta: sem ela, o fogo derivado do servidor **recomeça do
zero no dia do cadastro**. A dor de perder a sequência seria causada exatamente pela ação que o
app pediu que a pessoa fizesse — e a spec usa essa dor como CTA ("crie uma conta para não
perdê-lo"). Prometer isso e depois zerar seria a pior versão possível da mecânica.

### O que mudou, em três linhas

O `POST /api/auth/register` passa a ler o `X-Device-Id` (o mesmo cabeçalho do trial) e a rodar um
`UPDATE` em `SessionClaim` com `user IS NULL AND device_id = X`. Como o fogo é **derivação** das
claims, adotar a claim adota a sequência junto — não há nada a migrar, nada a recalcular.

Medido no teste do critério de aceite 5: três dias seguidos como visitante, conta criada no
terceiro, `GET /api/engagement` responde `streak: 3` e `GET /api/sessions?mine` devolve as três.
Antes desta task o mesmo caminho daria **1**.

### A função que precisou nascer, e por quê

`quota.device_id_from` **gera** um id quando não vem nenhum — é o que faz o trial funcionar na
primeira visita, e está certo lá. Aqui seria errado: um id inventado não pertence a aparelho
nenhum, e a única coisa que ele faria é adotar zero claims com ar de que tentou. Separei
`device_id_declarado`, que devolve `""` quando não veio nada válido, e `device_id_from` passou a
ser ela mais o `uuid4`. Uma regra, dois usos, nenhuma cópia.

### As três fronteiras, e a que mais protege

A spec enumera três, e cada uma tem teste próprio:

| fronteira | o que o teste prova |
|---|---|
| **só claims órfãs** | dois cadastros no mesmo celular: o primeiro leva 2 sessões, o segundo leva **0** |
| **uma vez** | idempotente por construção — depois da primeira passada não há mais claim órfã |
| **só no registro** | `login` com o mesmo cabeçalho adota nada; não existe rota "importar aparelho" |

A primeira é a que mais protege, e a mais fácil de perder numa refatoração: sem o filtro
`user IS NULL`, o segundo a se cadastrar no mesmo celular levaria as sessões do primeiro — e o
primeiro veria o próprio histórico desaparecer, sem erro nenhum em lugar nenhum.

### Decisões

- **O corpo do cadastro devolve `adopted_sessions`.** A spec não pede, e ele existe para a tela
  poder confirmar a promessa que o CTA fez. **Zero é resposta legítima** — quem cria conta antes
  de treinar não perdeu nada —, e é por isso que o campo não some quando é zero: sumir obrigaria
  o cliente a tratar ausência como "não sei".
- **Sem `try/except` na adoção.** Seria um `UPDATE` num índice logo depois de um `INSERT` que
  acabou de dar certo; engolir exceção aqui produziria contas silenciosamente sem histórico, que
  é o bug mais difícil de perceber e o mais fácil de causar.
- **Sem invalidar o cache de engajamento depois de adotar.** A conta nasceu nesta mesma
  requisição e ninguém leu o engajamento dela antes da linha da adoção — não há chave para
  derrubar. Escrito no docstring porque é o tipo de "otimização ausente" que parece esquecimento.
- **O `Authorization` NÃO vai junto no cadastro** (só o `X-Device-Id`). Quem se cadastra não está
  logado; mandar um access velho na requisição que existe para criar a conta diria o contrário.
  Tem teste dos dois lados.
- **`AccountUser` do cliente ganhou `daily_goal`.** Rabo da T-086: o servidor já mandava o campo
  e o espelho do cliente não o conhecia. Espelho incompleto é o `[A/T-051]` recomeçando.

### Gates

`ruff check` e `format --check` limpos; `pytest` **941 passando** (+16 sobre os 925 da T-086).
Web: `lint` limpo, `tsc -b` limpo, **521 testes** (+2).

### Pendências

- **A adoção não alcança um segundo navegador.** Quem treinou como visitante no Chrome e criou
  conta no Firefox não leva o histórico do Chrome — a spec limita a adoção ao momento do registro,
  de propósito, e a alternativa seria um botão "importar aparelho" com todas as fronteiras
  reabertas. Registrado na Descoberta `[T-121]`, que esta task fechou no resto.
- **Aparelho compartilhado adota sessão de outra pessoa.** Limitação que a spec declara e aceita:
  é o mesmo furo do trial por device-id, e fechá-lo exigiria fingerprinting.
- **Nada disso aparece na tela ainda.** O `adopted_sessions` volta no corpo e ninguém o lê; o
  rótulo "guardado neste aparelho" do Perfil continua sem contrapartida no cadastro. É a T-088.
- `web/public/img/herofamale.png` segue sem task e fora dos commits (quinta entrada seguida).

---

## 2026-08-15 (48) · T-086 — o fogo, e as duas palavras que decidiam produto

Primeira task do M1 (SPEC-019) e abertura do Bloco B. O Bloco A ficou travado em gravação
(T-108/T-109 esperam vídeo), e o M0 já fechou o pré-requisito técnico: o fogo é uma leitura do
histórico, e o histórico passou a atualizar na T-121…T-125.

A task era pequena no papel — uma função pura, uma rota, uma coluna. Mas a spec **se contradizia
em dois pontos**, e os dois decidem o número que aparece na tela.

### 1. `max(plano_atual, plano_free)` protegia todo mundo, menos quem ela existia para proteger

A §Downgrade da SPEC-019 é uma seção inteira sobre um problema real: no dia em que a assinatura
vence, as proteções caem de 2 para 1, um dia falho que já estava perdoado deixa de estar, e um
fogo longo encurta **na hora exata em que a pessoa está decidindo se renova**. Não é bug de
cálculo; é churn produzido pela mecânica de retenção.

A fórmula que a seção prescrevia não faz isso. Para quem foi rebaixado, `plano_atual` **é** free:
`max(1, 1) = 1`. Medido na fixture da sequência de 10 dias que atravessa julho gastando duas
proteções lá:

| piso histórico | fogo corrente |
|---|---|
| teto do catálogo (2) | **10** |
| a fórmula da spec (1) | **7** |

Sete. A fórmula era a única frase daquela seção que discordava do resto dela — e do critério de
aceite 10, que diz com todas as letras que isso não pode acontecer.

Corrigido para `max(plano_atual, teto_do_catalogo)`, com o custo escrito na spec: quem **nunca**
assinou também recebe o teto para trás. Sem histórico de plano por data — que a própria spec
rejeitou, para não transformar plano em série temporal — não há como distinguir "tinha direito"
de "não tinha". Das duas imprecisões possíveis, esta erra para o lado de não apagar fogo de
ninguém, que é o lado que a seção inteira escolheu.

### 2. "no meio de uma sequência" dava de graça a mecânica que se pretende vender

O §Vocabulário definia proteção como "dia falho perdoado **no meio** de uma sequência". Lida ao
pé da letra, a proteção só age entre dois dias treinados — e aí ela é **invisível no único
momento em que importa**: quem treinou seg/ter/qua e faltou na quinta abre o app na sexta e vê
fogo **0**. Só depois de treinar de novo ele volta a 4.

Isso não é proteção, é ressurreição retroativa. E ressurreição é exatamente o **reacender**, que
a mesma spec pôs atrás de pagamento na Fase Evolução. Dar de graça, por ambiguidade de redação,
a mecânica que se pretende vender é pior que o caso de borda que a redação queria evitar.

O critério de aceite 4 já dizia o certo sem a ressalva ("dia falho com proteção disponível não
apaga o fogo"), e é ele que valeu. Decisão levada ao Daniel antes de codar, e confirmada.

Duas consequências ficaram declaradas na spec e em teste:

- **Hoje nunca é dia falho.** O dia não acabou; cobrar proteção às 00h01 puniria um treino que
  ainda pode acontecer às 22h.
- **O dia protegido não entra na contagem.** Ele não foi treinado, apenas não interrompeu — o
  fogo conta dias *ativos*, e a spec diz "dias ativos consecutivos".

### O que ficou de fora, e por quê

**`achievements` não está no payload.** O catálogo de conquistas é a T-089. Uma lista vazia seria
pior que a ausência: o cliente a leria como "esta pessoa não conquistou nada", que é uma
afirmação — e falsa. Chave nova é aditiva, entra sem quebrar ninguém.

**Nível não tem nome.** A spec diz "nomes definidos com o produto"; inventar copy dentro de uma
task de derivação seria decidir produto por conveniência. A tela mostra "Nível 3" até alguém
batizar.

**O ramo `hold` existe escrito e testado**, e nenhum exercício o alcança: a coluna
`hold_valid_ms` chega na T-098. É o que o `scoring` por parâmetro compra — no dia do wall sit
muda o mapa que a view passa, não a regra.

### Decisões

- **`engagement.py` não importa Django, e tem teste que cobra isso.** A promessa da spec é que
  "recalcular do zero dá o mesmo resultado", e uma função que lê o relógio por dentro não pode
  provar isso. `hoje` é parâmetro; as fixtures são listas de datas escritas à mão.
- **A metade com I/O virou `engagement_cache.py`, e não o fim do `views.py`.** Os signals são
  ligados no `AppConfig.ready()`, e importar `api.views` de lá arrasta `api.sessions` →
  `workers.analysis_worker` para dentro do *startup* do Django — descoberto na cara dura: o
  `makemigrations` quebrou com `ModuleNotFoundError: No module named 'workers'`. Engajamento não
  tem nada que ver com o registro de FSMs.
- **A consulta não usa `HISTORY_LIMIT`.** O histórico mostra as 50 últimas; o fogo precisa de
  todas as datas. Cortar em 50 encurtaria a sequência de quem treina todo dia — exatamente quem
  a mecânica existe para premiar. Tem teste com 60 dias.
- **A data vai na chave do cache**, como a spec exige. O payload muda **sozinho** à meia-noite,
  sem escrita nenhuma para disparar signal; uma chave sem data serviria o fogo de ontem até a
  pessoa treinar de novo, ou seja, exatamente até deixar de precisar da informação.
- **Invalidar por `SessionResult` custa uma consulta**, porque o relatório **não sabe de quem é**
  — e não pode saber, senão deixa de ser derivável por replay (SPEC-010). O dono vive no
  `SessionClaim`. É uma vez por sessão, no processo do report-builder, fora do hot path.
  Confirmado que o caminho real dispara: `update_or_create` chama `.save()`.
- **`PATCH /api/me` com lista de campos permitidos**, não `PATCH` genérico sobre o modelo — que
  deixaria `is_admin` e `plan` a um campo de distância de serem editáveis pelo dono da conta.
  Corpo sem campo conhecido responde 400: 200 faria a tela dizer "salvo" sobre nada.
- **Anônimo recebe 401, não um corpo de zeros.** Zeros do servidor seriam indistinguíveis de
  "nunca treinou" para um cliente descuidado, e a spec pede o contrário — que ninguém confunda o
  fogo fantasma local com o do servidor.

### Gates

`ruff check` e `format --check` limpos; `pytest` **925 passando** (+64 sobre os 861 da T-110),
zero falhas. `web/` não foi tocado. Dez dos onze critérios de aceite têm teste próprio; o 5 é da
T-087.

### Pendências

- **O critério 5 não foi verificado e não podia ser**: "cadastro com device_id que tem sessões
  anônimas já nasce com o fogo" é a T-087. Enquanto ela não chega, existe teste declarando o
  estado de hoje — sessão anônima do mesmo aparelho **não** entra no fogo de quem tem conta.
  Junto com a Descoberta `[T-121]`, é a próxima da fila.
- **Nada disso está na tela.** Chip, anel, painel e "+XP" no relatório são a T-088; o
  `GET /api/engagement` responde e ninguém o chama ainda.
- **`LEVELS` acima do quinto degrau é invenção minha** seguindo o espaçamento da spec, e o nome
  de cada nível não existe. Vale revisar com o produto antes da T-088 desenhar a barra.
- **O piso histórico de proteções é constante em código** (`PROTECOES_TETO = 2`), e não uma
  consulta ao maior `streak_protections_month` do banco. De propósito: o valor de um plano **de
  hoje** não pode decidir o perdão de um mês que já passou. Se algum dia nascer um plano com 3,
  esta constante precisa subir junto — e é o tipo de coisa que se esquece.
- `web/public/img/herofamale.png` segue sem task e fora dos commits (quarta entrada seguida).

---

## 2026-08-15 (47) · T-110 — o vídeo parou de opinar sobre o corpo

Última perna do Bloco A que dava para executar sem gravação nova (T-108 e T-109 esperam vídeo).
A Descoberta `[A/T-106]` estava aberta desde a flexão: `x` é dividido pela largura do frame e
`y` pela altura, então uma distância horizontal e uma vertical do mesmo tamanho real saem com
números diferentes — e a diferença é o formato do vídeo.

### A parte da Descoberta que estava errada

A medição dela estava certa. A conclusão, não: *"os dois exercícios existentes escapam por
acidente feliz"*. `ankle_spread` (razão de dois horizontais) e `hip_height` (um vertical sobre
o torso) escapam mesmo. Mas ninguém olhou os **ângulos**:

| feature | conta | mistura eixos? |
|---|---|---|
| `arm_angle` (polichinelo) | `atan2(dx, dy)` | **sim** |
| `knee_angle` (agachamento) | `hypot(ax, ay)` | **sim** |
| `elbow_angle` (flexão) | `hypot` dos dois lados | **sim** |
| `shoulder_to_torso` (decisor de vista da flexão) | `hypot` ÷ `hypot` | **sim** |

Os três primeiros carregam limiar. E o quarto tem um comentário no código dizendo *"não herda
formato de vídeo nem distância de câmera"* — que era falso.

Isso fecha por si a segunda saída que a task oferecia ("declarar por escrito que toda feature é
razão no mesmo eixo"): **nenhuma redação salva um ângulo**. Ângulo é mistura de eixos por
definição. Sobrou uma saída só, e é a certa.

### A correção, e por que `x` vira altura e não o contrário

`x *= largura ÷ altura` põe os dois eixos em unidades de **altura de frame**. Poderia ser o
inverso (`y` para largura) — o resultado normalizado é idêntico, porque tudo é dividido pelo
torso depois. A diferença aparece em `torso`, que sai em unidades de frame e **é a régua de
distância da SPEC-003**. Tronco de gente em pé é quase todo `y`; convertendo nessa direção, a
régua quase não se move:

```
fixture                                    torso hoje  torso T-110   delta   avisos de cena
polichinelo-01                                 0.2253       0.2253    0.0%   idênticos
polichinelo-03                                 0.1189       0.1188   -0.1%   idênticos {TOO_FAR: 10}
agachamento-frente-…-v1                        0.1262       0.1262   -0.0%   idênticos {TOO_FAR: 18}
flexão-frente-50-…-v2                          0.1913       0.1876   -1.9%   idênticos {OUT_OF_FRAME: 46}
```

Máximo 1,9%, e **zero mudança de aviso de cena nos seis vídeos**. A escolha de direção se pagou
exatamente onde eu tinha medo dela.

### A revarredura que a task pedia voltou limpa

| fixture | antes | depois |
|---|---|---|
| polichinelo-01 (paisagem 854×480) | 20 | **20** |
| polichinelo-02 (retrato) | 13 | **13** |
| polichinelo-03 (retrato) | 19 | **19** |
| agachamento (retrato) | 18 | **18** |
| flexão v1 (retrato) | 52 | **52** |
| flexão v2 (retrato) | 50 | **43** |

E a convergência que era o objetivo: a mesma largura de ombros lia **0,348** torsos em paisagem
e **0,898–1,168** em retrato — espalhamento 3,4×. Agora lê **0,619 / 0,658 / 0,504**.

### O único número que mudou, e por que ele não foi "consertado"

A flexão v2 caiu 7 repetições. A tentação era retunar `frontal_down_depth` de 0,63 para 0,74 —
a varredura mostra que isso devolve o 50 exato. Não fiz, por três razões que se somam:

1. **0,74 *é* `frontal_shallow_depth`**, o limiar de "rasa demais". Mover a contagem para lá é
   apagar a crítica para salvar o número.
2. **O rótulo "50" não vale.** Veio do título do vídeo de rede social, e a Descoberta
   `[A/T-108]` já declarou isso. Ajustar limiar contra ele é ajuste ao ruído.
3. **A pessoa da v2 realmente não desce.** Fundo mediano de cotovelo: **91,9°** (paralelo).
   A v1, que não mudou de contagem, desce a 55,2°. No espaço distorcido a mesma v2 lia 76,6° —
   o retrato esticava a componente horizontal e fazia a flexão parecer mais funda do que era.

E as 7 repetições não sumiram caladas: viraram **7 `PUSHUP_TOO_SHALLOW`**. Saíram da contagem e
entraram na crítica, que é onde pertenciam.

**O aval da correção não vem de rótulo nenhum.** Braço travado no topo é ~180° por anatomia,
não por opinião. A leitura vai de 164,7° → **171,2°** (v1) e 170,9° → **174,5°** (v2). Quatro
medidas, todas andando na direção de uma verdade conhecida de antemão. É a única evidência
disponível que não depende de ninguém ter contado certo.

### Decisões

- **`width`/`height` por frame, não por sessão.** O aparelho gira no meio do treino. Carimbar a
  dimensão no `session.started` seria assumir que ninguém vira o celular.
- **Os dois juntos ou nenhum.** Uma dimensão sozinha não define aspecto; aceitá-la produziria um
  frame que se diz medido sem estar.
- **Ausência significa isotrópico**, e é isso que dispensa o bump de `PROTOCOL_VERSION`: cliente
  antigo com servidor novo (e o contrário) continuam se entendendo, e fixture velha continua
  dando o número velho. Tem teste dos dois lados.
- **As dimensões saíram de `conditions` para o topo da fixture.** Elas já existiam em
  `conditions.video` no gravador do navegador — mas `conditions` é campo livre por contrato
  (SPEC-012), e derivar geometria de campo livre é acidente esperando acontecer.
- **O HUD do cliente corrige junto.** O ângulo ao vivo (T-044) é espelho declarado da FSM; se o
  servidor corrigisse e ele não, quem filma em retrato veria na tela um número que o servidor
  não reconhece. O teste de isotropia do lado TS é o que trava isso.
- **`evalctl stack` manda as dimensões.** Sem isso a perna da stack (T-133) voltaria a medir num
  espaço diferente do navegador — as três pernas mediriam duas coisas.

### Gates

`ruff check` e `format --check` limpos (157 arquivos); `pytest` **861 passando** (+17 sobre os
844 da T-104), zero falhas, sem variável na linha de comando. Web: `lint` limpo, `tsc -b` limpo,
**519 testes** (+6). Rodado em worktree isolado (`spec-006/t-110-espaco-isotropico`), a pedido.

### Pendências

- **Nenhum vídeo de gente foi filmado em paisagem além do `polichinelo-01`.** A convergência foi
  medida com uma amostra de paisagem só. Ela é forte (3,4× → 1,3×) mas um segundo vídeo em
  paisagem, de outro exercício, seria a confirmação honesta. Entra junto com a T-108.
- **A flexão continua `beta`, e agora com um motivo a mais**: a v2 mostra que a contagem dela é
  sensível ao limiar de profundidade em quem faz repetição rasa. Isso não se resolve sem os 8
  vídeos rotulados da T-108 — e quando resolver, a varredura tem de ser refeita **neste** espaço.
- **A T-109 não foi reaberta.** A margem de 3,4 pontos do agachamento que ela descreve foi medida
  no espaço antigo; a correção mexe em `hip_height` pela via do `torso` (≤ 1,9%), o que não muda
  a ordem de grandeza. Continua esperando corpus, como a própria linha dela diz.
- `web/public/img/herofamale.png` segue sem task e fora dos commits (terceira entrada seguida).

---

## 2026-08-13 (46) · T-104 — a promoção deixa de ser opinião

O critério de `validado` da SPEC-020 é "< 20% de sessões zero-rep por uma semana", e até hoje
ninguém media isso. Critério mensurável sem instrumento vira opinião — e foi por opinião que o
polichinelo e o agachamento chegaram a `validado`.

### A tabela, contra o banco de verdade

```
saude dos exercicios · ultimos 30 dia(s)
exercicio               maturidade   sessoes  completas  zeradas    taxa   sem dado   cadencia  veredito
Polichinelo             validado         211         17        2   11.8%  171 (81%)   50.0 rpm  ok
Agachamento             validado          17          4        0    0.0%   13 (76%)   27.3 rpm  poucas (<5)
Flexão de braço         beta              28         17        6   35.3%   11 (39%)   38.2 rpm  ATENCAO
Abdominal               beta               0         --       --      --         --         --  sem sessao
```

Quatro coisas verdadeiras, na primeira execução:

1. **A flexão em 35,3% é passado.** Os 6 zeros são de 2026-08-06, entre 04:05 e 04:27,
   `config_version 7` — a janela da regressão da entrada 40, corrigida às 04:34. Na janela de
   7 dias que a spec pede, a flexão dá **0,0% e `ok`**. A janela não é parâmetro de conforto:
   é o que separa "está quebrado" de "esteve quebrado".
2. **O agachamento não tem sessões suficientes para veredito**, e o comando diz isso em vez de
   inventar um. Quatro sessões completas não sustentam promoção nem rebaixamento.
3. **`no_data` domina** — 171 de 211 no polichinelo. O comando o mostra ao lado, nunca dentro
   da taxa, e a legenda diz o que fazer com ele.
4. **O abdominal está no ar sem nenhuma sessão real.** É a mesma dívida que o
   `SEM_MATERIAL_REAL` do `test_corpus_regressao.py` declara, agora visível pelo lado da
   produção também.

### A palavra que virou o critério

A SPEC-020 dizia "taxa de sessões zero-rep < 20%". A leitura literal disso é o que custou as
semanas da T-133. A spec foi corrigida para dizer **`completed`**, com o motivo escrito: das
quatro razões de fim, só ela significa que a análise correu até o fim. `no_data`, `aborted` e
`timeout` falam de captura, desistência e TTL.

Duas travas de leitura ficaram embutidas no comando, e são a parte que mais protege:

- **`no_data` fora da taxa.** Tem teste próprio, e o docstring dele explica o caso do
  agachamento — quem simplificar isso um dia vai encontrar a conta de volta.
- **Abaixo de 5 sessões completas, sem veredito.** Duas sessões com um zero dariam "50%".
  Rebaixar um exercício por isso é decidir no ruído, e a spec pede uma semana, não duas sessões.

### Decisões

- **A conta mora em `api/exercise_health.py`, não no comando.** O painel lê os mesmos números:
  dois lugares calculando "taxa de zero-rep" acabariam discordando, e no dia em que
  discordassem ninguém saberia qual acreditar.
- **A faixa do painel só grita o que exige ação** — exercício **no ar** acima do limite. Um
  painel que grita errado ensina o operador a ignorar a faixa, que é o único lugar onde o
  grito certo vai aparecer. Tem teste dos dois lados: o caso que avisa, e o caso `no_data` que
  não pode avisar.
- **Exercício desligado continua na tabela.** Ele foi desligado justamente porque alguém viu um
  número aqui; sumir com a linha apagaria a prova.
- **Slug que saiu do catálogo também.** As sessões dele não sumiram do banco.
- **`--json`** porque este número vai para o DEVLOG toda vez que alguém promover ou rebaixar.

### Gates

`ruff check` e `format --check` limpos; `pytest` com **844 passando** (+14). Rodado também
contra o Postgres de dev pelo container (`docker compose exec api`), que é o uso real.

### Pendências

- **O veredito ainda não decide nada sozinho**, e é de propósito: promoção e rebaixamento
  continuam sendo mudança de `maturity` no painel, por gente. Automatizar isso é a Evolução da
  SPEC-020 e precisa de mais de uma semana de dado real antes de ser desenhado.
- **Os números acima são de banco de desenvolvimento.** 171 `no_data` de polichinelo com 3,3 s
  de média é assinatura de quem abre e fecha o app. O critério da SPEC-020 só passa a valer
  quando o comando rodar contra produção — o que ainda depende do lançamento.
- **`no_data` continua sem dono.** Agora ele é visível e nomeado, mas o que fazer quando um
  usuário real cai nele (a tela mostra relatório vazio) não está desenhado em spec nenhuma.

---

## 2026-08-13 (45) · T-133 — o agachamento nunca esteve quebrado

Etapa 1.1 da corrida ao MVP: medir a contagem no caminho que o usuário usa, antes de mexer em
limiar nenhum. O item era bloqueante de propósito — a T-109 estava marcada **alta** com a
descrição "agachamento não conta em produção", e mexer no `squat.py` sem medir seria chute.

**A medição desmontou a premissa.** O agachamento conta. Sempre contou.

### As três pernas, no mesmo vídeo

| perna | o que ela prova | agachamento |
|---|---|---|
| bancada (`evalctl`, vídeo inteiro de 36 s) | a FSM | **18/18** |
| **stack real** (admissão + WS + janela de 30 s) | o caminho | **15** |
| navegador (sessão **#220**, 2026-08-05) | a extração WASM | **15** |

O 18 → 15 é o teto de 30 s comendo os últimos 6 s do vídeo, não erro de contagem.

E a terceira linha não é aproximação. A sessão #220 do banco e o replay de hoje batem em tudo:

| | #220 (navegador, 08-05) | #247 (stack, hoje) |
|---|---|---|
| reps | 15 | 15 |
| `cadence_windows` | `[1,2,3,2,3,2,2]` | `[1,2,3,2,3,2,2]` |
| `scene_warning_counts` | `{"TOO_FAR": 17}` | `{"TOO_FAR": 17}` |
| `duration_ms` | 33002 | 33010 |

Uma perna usa MediaPipe WASM no navegador, a outra usa keypoints extraídos pelo MediaPipe do
Python. Chegam ao mesmo lugar, janela por janela. **A paridade das três pernas está fechada
para o agachamento** — e ela nunca tinha sido medida porque o instrumento previsto exigia
alguém abrir um navegador.

### De onde veio o "0 em produção"

Do banco, lido errado. As 13 sessões de agachamento com zero repetição são **todas**
`reason: no_data` — o servidor fecha a sessão quando passa 10 s sem frame (SPEC-009, critério
4). Elas são de 2026-07-29/30, antes de existir vídeo de agachamento no corpus. `no_data` não
é "contou zero": é "parou de chegar frame".

Quebrando por motivo, o quadro muda de assunto:

| exercício | `completed` | zeros entre os `completed` | `no_data` |
|---|---|---|---|
| squat | 2 | **0** | 13 |
| jumping_jack | 15 | 2 | 169 |
| flexao | 13 | 6 | 11 |

Os 6 zeros da flexão são de 2026-08-06 entre 04:05 e 04:27, `config_version 7` — a janela exata
da regressão que a entrada 40 descreve, corrigida às 04:34 (a sessão seguinte conta 20) e hoje
protegida pelo `test_corpus_regressao.py`. **Nenhum dos quatro exercícios tem contagem quebrada
em aberto.**

Aviso honesto sobre esses números: é banco de desenvolvimento. 169 `no_data` de polichinelo com
3,3 s de média é a assinatura de alguém abrindo e fechando o app, não de usuários. As linhas
`completed` são análises de verdade; as taxas, não.

### O instrumento (T-133): `evalctl stack`

A T-040 desenhou a terceira perna como um arquivo exportado pelo painel de dev — manual por
construção. A pendência ficou aberta semanas, e nesse meio-tempo uma afirmação errada
envelheceu no manifest e virou task de alta prioridade.

O que a passada manual prova é a **extração** (WASM × Python). O **caminho** — admissão,
WebSocket, msgpack, preparação, teto de 30 s, relógio do servidor — não precisa de navegador:
basta empurrar uma fixture de keypoints pelo mesmo cano. É o que o comando faz, e é a única
das três pernas que dá para automatizar.

```
uv run python -m eval.evalctl stack eval/fixtures/<fixture>.json --api http://localhost:8090
```

O corpus inteiro pela stack, hoje:

| fixture | rótulo | bancada | stack | motivo |
|---|---|---|---|---|
| agachamento-…-v1 | 18 | 18 | 15 | completed |
| flexão-frente-50-…-v1 | 50 | 52 | 37 | completed |
| flexão-frente-50-…-v2 | 50 | 50 | 21 | completed |
| polichinelo-01 | 20 | 20 | 19 | completed |
| polichinelo-02 | 15 | 13 | 10 | **no_data** |
| polichinelo-03 | 21 | 19 | 16 | **no_data** |

Os dois `no_data` são o mesmo fenômeno das sessões de julho, reproduzido de propósito: os
vídeos têm 12 s e 20 s, acabam antes do teto de 30 s, e a sessão morre de silêncio. É a prova
direta de que `no_data` e "contou zero" são coisas diferentes — aqui o `no_data` veio com 10 e
16 reps contadas.

### Decisões

- **A Descoberta `[A/T-106]` foi marcada REFUTADA, com o motivo escrito.** A medição original
  era honesta; a conclusão não seguia dela. Os "três vídeos do corpus" eram de **polichinelo**
  — gente em pé o tempo todo — e a descida foi extrapolada pela proporção do boneco sintético.
  Apagar a descoberta esconderia o erro de método, que é a parte que vale.
- **A T-109 foi rebaixada de alta para média, e mudou de descrição.** O que sobra de real é a
  margem: a pessoa medida desce a 50,7% da altura de quadril em pé, o limiar abre em 54,1% —
  **3,4 pontos**. Quem parar no paralelo conta 0. Continua valendo trocar o absoluto por razão,
  mas isso é robustez, não conserto, e não se mexe antes da T-108 dar corpus para revarrer.
- **A T-104 ganhou um requisito.** `exercise_health` tem de quebrar por `reason`. "Taxa de
  zero-rep" somando `no_data` com `completed` de contagem zero é exatamente a métrica que fez o
  agachamento parecer quebrado — e é o critério de `validado` da SPEC-020, que ficaria medindo
  conexão em vez de contagem.
- **O comando não entra na CI.** Precisa da stack de pé; é medição de integração, de quem está
  investigando. O gate barato continua sendo o `test_corpus_regressao.py`.

### Gates

`ruff check` e `ruff format --check` limpos. `pytest` com **830 passando** (+6), sem variável de
ambiente na mão — a T-076 continua valendo. `websockets` entrou no extra `eval` do
`pyproject.toml`, com import tardio em `eval/stack.py` para não pesar em quem só roda
`evalctl run`.

### Pendências

- **A passada manual do navegador continua pendente**, agora com o escopo certo: ela mede
  extração, não caminho. A extensão do Chrome não estava pareada nesta sessão
  (`list_connected_browsers` devolveu vazio), então a perna do navegador aqui é o registro
  **histórico** da sessão #220 — que bate exatamente, mas é de 2026-08-05, `config_version 6`.
  O replay de hoje sob `config_version 8` dá o mesmo 15, então não há regressão entre as duas.
- **O `TOO_FAR` do agachamento merece olhar.** 17 avisos de cena e 9 feedbacks emitidos numa
  sessão que contou certo: para caber o corpo inteiro num agachamento a pessoa **precisa** ficar
  longe, e o porteiro de cena chama isso de erro. Não bloqueia a contagem, mas é conselho
  impossível de seguir aparecendo na tela de quem fez tudo certo.
- **`no_data` é a maior massa de sessões do banco (193 de 246)** e ninguém sabe o que ele
  significa para um usuário de verdade. É pergunta para a T-104 responder com dado de produção.
- `web/public/img/herofamale.png` continua sem task e fora dos commits.

---

## 2026-08-13 (44) · T-076 — o gate que dependia de alguém lembrar

Abertura da corrida até o MVP (plano aprovado nesta data: Bloco A + M1 do engajamento +
operação, pagamento por último). Etapa 0 é medir o estado real antes de mexer em qualquer
coisa — e a primeira medição já cobrou uma dívida.

**O estado como estava.** `uv run pytest`, sem variável nenhuma, **não roda**: a suíte inteira
morre em `redis.exceptions` na coleta. Com `DJANGO_DB_SQLITE=1 DJANGO_CACHE_LOCMEM=1` na linha
de comando, **823 passam e 1 falha** — `test_smoke.py::test_settings_leem_ambiente`, que afirma
`ENGINE == postgresql` justamente enquanto a suíte roda em SQLite. Os dois sintomas são o mesmo
defeito, descrito em duas Descobertas (`[A/T-072]` e `[A/T-106]`) e nunca fechado.

**A causa.** `tests/conftest.py` fazia `os.environ.setdefault("DJANGO_DB_SQLITE", "1")` contando
ser lido antes do `django.setup()`. O `pytest_load_initial_conftests` do pytest-django força a
leitura do settings **antes** dos conftests, então as duas linhas chegavam tarde. O contorno
virou hábito: quem rodava a suíte passava as variáveis na mão. *Gate que depende de alguém
lembrar de uma variável não é gate* — e é sobre este que a corrida inteira se apoia.

**A correção: `server/core/settings_test.py`.** Das duas saídas que a Descoberta propunha
(`pytest-env` ou módulo de settings), a segunda não precisa de dependência nova e resolve por
construção — o módulo **é** o que o Django importa, então o ambiente está ajustado antes de
qualquer leitura, em qualquer ordem de import. Ele ajusta duas variáveis e faz
`from core.settings import *`: o teste roda contra a configuração de verdade, e opção nova
nasce valendo sem ninguém lembrar de copiar.

**Decisões:**

- **`setdefault`, não atribuição.** Quem quiser rodar a suíte contra Postgres de verdade
  (`DJANGO_DB_SQLITE=0` na frente do comando) continua mandando. O módulo escolhe o default,
  não sequestra a escolha.
- **O teste contraditório passou a cobrar a REGRA, não o valor.** `test_settings_leem_ambiente`
  agora importa `core.settings` num **subprocesso** com o ambiente controlado e verifica as duas
  pontas: sem `DJANGO_DB_SQLITE` dá `postgresql` e o `REDIS_URL` do ambiente; com ela, `sqlite3`.
  Em processo não teria como perguntar nada — `django.conf.settings` guarda uma cópia feita no
  `setup()`, e a suíte já subiu em SQLite. O subprocesso é o recurso que o
  `test_workers_nao_importam_django`, logo abaixo dele, já usava pelo mesmo motivo: a pergunta é
  sobre o que acontece na **importação**.
- **As variáveis da suíte são removidas do ambiente do subprocesso** (`DJANGO_DB_SQLITE`,
  `DJANGO_CACHE_LOCMEM`, `DJANGO_DB_SQLITE_PATH`). Sem isso o teste do caminho de produção
  herdaria o SQLite do processo pai — e passaria por engano, que é exatamente o erro que ele
  existe para não repetir.
- **A `conftest.py` ficou só com o que precisa de fixture** (a limpeza de cache do rate limit
  entre testes). Escolha de banco e de cache saiu de lá, e o docstring que prometia uma ordem de
  execução que não existe mais saiu junto.

**Um achado de graça no mesmo caminho:** `ruff format --check .` acusava
`tests/test_catalog_api.py` — e a CI **roda esse comando**. É a Descoberta `[T-075]` ("o
repositório já anda fora do formatador") materializada num push que teria falhado. Formatado, e
o repositório inteiro está limpo (152 arquivos).

**Gates:** `ruff check` limpo, `ruff format --check` limpo, `pytest` **824 passando, zero
falhas, sem uma única variável na linha de comando**. Web verde e intocado (45 arquivos, 513
testes), rodado só para carimbar a linha de base da Etapa 0.

**Pendências:**

- Ninguém abriu o GitHub Actions nesta sessão (não há `gh` na máquina), então "a CI está verde"
  segue sendo suposição — vale conferir junto com a T-027, que é onde o lado web entra na CI.
- `web/public/img/herofamale.png` está sem versionar e sem task; ficou de fora dos commits desta
  sessão por não pertencer a nenhuma.

---

## 2026-08-07 (43) · T-130 — o painel ganha pele, e passa a existir no domínio

Pedido do Daniel: *"preciso que o admin da produção esteja com white noise, quero um admin
personalizado pensado no caso de uso e já coloque jasmine como template e depois personalize
com o mesmo estilo do front-end. Confira se está tudo configurado corretamente para que eu
consiga acessar o admin pelo django e pelo domínio"*.

**A descoberta que muda a ordem de importância do pedido.** O whitenoise estava configurado
desde a T-072 — middleware, `collectstatic` no build da imagem, `CompressedStaticFilesStorage`.
O que faltava era **alguém chegar até ele**. O `./scripts/prod.sh nginx` imprime um server
block com quatro `location`: `/ws/`, o regex `^/(api/|healthz|readyz)`, e `/`. O caminho do
painel e `/static/` não casam com nenhum dos três primeiros, então caem no `/` — o container do
**web**, cujo nginx interno faz `try_files $uri $uri/ /index.html`. Consequência medida:

| pedido | o que voltava |
|---|---|
| `https://dominio/painel/` | a **landing do produto**, com status `200`. Não 404 — não parece erro de rota |
| `/static/painel/*.css` | `text/html`, que o navegador recusa como folha de estilo → painel **sem estilo nenhum** |

Ou seja: o sintoma que motivou o pedido ("o admin da produção precisa estar com whitenoise")
não era o whitenoise. Era o roteamento. Corrigido no gerador do bloco, não na documentação:
`prod.sh nginx` passou a imprimir `location /<ADMIN_PATH>` (com o `301` do caminho sem barra
final), `location /static/`, e as duas linhas de `allow`/`deny` já comentadas. Verificado
ponta a ponta com um nginx de verdade na frente do processo: `/sala-de-maquinas` → 301,
`/sala-de-maquinas/` → 302 para o login, CSS → `200 text/css`. `nginx -t` limpo.

**CSRF_TRUSTED_ORIGINS virou a quinta derivada do `DOMAIN`.** Mantida a mão, era a única
variável cujo esquecimento só aparece no momento do `403` do POST de login, atrás do proxy que
termina TLS. Preenchida no `.env.prod`, o valor de lá continua vencendo.

**O tema.** django-jazzmin (AdminLTE 4 + Bootstrap 5.3) com os tokens da SPEC-014 por cima —
os mesmos `#05070d`, `#4d8cff`, `#8b5cf6`, Manrope/Space Grotesk, raio 16px do cliente. O
grosso do CSS é sobrescrever as **variáveis** do Bootstrap, não classe por classe: assim pega
componente que a folha nunca cita, inclusive os que o jazzmin ganhar numa atualização.

**Decisões:**

- **`jazzmin` antes de `django.contrib.admin` é o tema inteiro**, e falhar nisso não produz
  erro nenhum — só a tela antiga de volta. Virou teste (`test_jazzmin_vem_antes_do_admin`).
- **`changeform_format = "single"`, e não as abas de fábrica.** Os `fieldsets` deste projeto
  carregam avisos que mudam a operação ("`daily_sessions = 1` no plano default desliga o
  produto"). Aba é conteúdo atrás de um clique, e aviso escondido é aviso que não existe.
- **`admin/includes/fieldset.html` foi copiado e corrigido.** O do jazzmin imprime a descrição
  sem `|safe` (o do Django usa) e dentro do título, em itálico: a tela mostrava literalmente
  `<b>Validade</b> vazia = sem prazo`. Agora a descrição é um bloco no corpo do card. É o único
  arquivo do tema copiado inteiro, e está anotado como tal.
- **O menu lateral continua sendo gerado pelo Django.** Montá-lo à mão daria os grupos
  "Suporte / Configuração / Auditoria" na barra, ao preço de um modelo novo registrado em
  `api/admin.py` não aparecer em lugar nenhum. A curadoria por caso de uso vive no dashboard,
  onde ficar desatualizada não esconde nada.
- **O dashboard responde as perguntas com que se ABRE um painel**, não "onde eu mudo X":
  sessões e reps de hoje, contas ativas, exercícios no ar, versão da configuração valendo. Mais
  uma faixa de avisos para o que é **silencioso** — exercício sem MET ou sem cadência (o card
  de calorias mostra `--`, descoberta que a T-128 pagou), plano default ausente, `anon`
  ausente. Consulta que falhar devolve `None` e a faixa some: P2 da SPEC-018 na forma "nenhum
  número derruba o painel".
- **`User.get_all_permissions()` precisou existir.** O jazzmin chama isso em toda página
  (`utils.get_view_permissions`), e o modelo não tem `PermissionsMixin` por decisão da
  SPEC-011 — o resultado era `AttributeError` na primeira tela depois do login. Implementado a
  partir do **registro de apps**, não da tabela `auth_permission`: sem consulta por página, sem
  depender do `post_migrate`, e impossível de divergir do `has_perm` logo acima.
- **Rótulos em pt-BR por `verbose_name`** (migration `0015`, `AlterModelOptions` — não toca no
  banco). "Session claims" e "Session results" vinham do vocabulário do event bus, não do de
  quem atende suporte. `django.contrib.admin` virou `core.apps.PainelAdminConfig` só para o
  grupo se chamar "Auditoria" em vez de "Administration".
- **`DJANGO_DB_SQLITE_PATH`**: abre o painel na máquina de quem desenvolve sem Postgres. Em
  memória não serviria — `runserver` é multithread, cada conexão ganharia um `:memory:` próprio
  e o login voltaria para a tela de login sem erro no log. Alvo `painel` no `.claude/launch.json`.

**Gates:** `ruff check` limpo, `ruff format --check` limpo, suíte inteira verde (829 testes),
9 casos novos em `tests/test_admin_panel.py`. `collectstatic` roda (246 arquivos com o jazzmin
dentro). `nginx -t` do bloco gerado, limpo.

**Pendências:**

- **O chrome do Django/jazzmin segue em inglês** ("Home", "Save", "Recent actions", "Log
  entries") porque `USE_I18N = False`. Ligar traduz o painel inteiro de graça, mas também
  traduz as mensagens dos `AUTH_PASSWORD_VALIDATORS`, que a API devolve em
  `POST /api/auth/register` — é mudança de payload do produto, e por isso ficou fora desta
  task. Decisão do Daniel.
- Falta a passada em produção: `./scripts/prod.sh up` + `./scripts/prod.sh nginx`, colar o
  bloco novo, recarregar o nginx e conferir os dois `curl` que a `docs/DEPLOY.md` agora traz.

---

## 2026-08-07 (42) · T-129 — gravar o produto sem gravar o diagnóstico

Pedido do Daniel: *"quero adicionar uma flag enquanto estiver como adm que é 'record' aonde eu
consigo upar video mas continuar com o design de interface do usuario, sem log e tal"*.

**O que faltava.** Duas coisas estavam coladas desde a T-040/T-048, e nunca havia razão para
que estivessem: a **origem de vídeo em arquivo** e o **diagnóstico na tela** viviam atrás do
mesmo booleano. Ligado (`is_admin` ou build de dev), dá para entrar com um mp4 — e vem junto o
chip com `pose gpu · 24.1fps · 33 lm`, o botão de gravar fixture, o "baixar json" e o texto de
erro que manda rodar `docker compose up`. Desligado (`?dev=0`), a tela é exatamente a do
produto — e só a câmera entra. Para filmar material do app com um vídeo controlado, era preciso
o meio, que não existia.

**A terceira posição do gate.** `?record=1` concede a origem em arquivo e **retira** o
diagnóstico. Duas linhas em `dev/gate.ts`, e nenhuma delas em componente:

```
devToolsAllowed   → false quando ?record=1 (mesmo para admin)
recordModeAllowed → is_admin || build de dev, e só com ?record=1 na URL
```

**Decisões:**

- **O corte mora no gate, não no JSX.** Esconder o chip no `CameraView` e deixar o texto "suba
  a stack (`docker compose up`)" vazar pelo aviso de gateway fechado seria a mesma tela vazando
  por outro buraco — e esse texto já é decidido por `devTools`. Uma fonte, um corte.
- **Modifica, nunca concede** — a regra da T-048 vale igual. `?record=1` na mão de um visitante
  é inerte, porque a permissão continua sendo `is_admin`, que só o `manage.py admin_tools`
  concede (nenhuma rota da API aceita o campo).
- **`?dev=0` continua sendo o desligador geral**, inclusive sobre o `record`: quem pede a tela
  limpa de verdade não quer nem o botão de escolher arquivo no meio dela.
- **O botão vive dentro da capa da câmera, e some sozinho.** Escolher o arquivo é a alternativa
  a "Ligar câmera", e é ali o único momento em que a escolha existe. Carregado o vídeo,
  `startFile` põe `cameraStatus = 'ready'`, a capa inteira sai da tela — **a gravação não tem
  um único frame com vestígio do modo**. Foi por isso que ele não virou um pill flutuante sobre
  o palco: qualquer coisa ancorada no palco apareceria no material.
- **Aparece também na capa compacta da pré-configuração**, ao contrário do controle de dev, que
  é excluído lá (`!compactCover`). A pré-config é justamente a tela que se quer gravar; excluí-la
  seria excluir o caso de uso.
- **Sem componente novo.** O `VideoSourceControl` ganhou `variant="record"`, que esconde o nome
  do arquivo e o "baixar json" — os dois são diagnóstico — e reusa o container `stage__dev` para
  herdar o desespelhamento e o posicionamento por tela que já estavam afinados; o modificador
  `--rec` só tira a pílula preta.

**Gates:** `npm run lint`, `npm run typecheck`, `npm run test` (45 arquivos, 513 testes) verdes.
Nada de Python foi tocado. 9 casos novos em `dev/gate.test.ts`, incluindo o que impede a
regressão que interessa: **nunca os dois modos ao mesmo tempo**.

**Pendências:** falta a passada manual no celular — abrir `?record=1` logado como admin, entrar
com um mp4 e conferir que a gravação de tela não mostra nada fora do produto.

---

## 2026-08-07 (41) · T-128 — o kcal para de faturar tempo de tela

Pedido do Daniel: *"quero que o kcal seja baseado nas repetições, porém se o ritmo for mais
intenso ele ganha um multiplicador"*. É uma correção, não um enfeite — e o defeito era meu, da
T-063.

**O que estava errado.** A T-063 entregou a fórmula clássica do Compendium, `MET × 3,5 ×
peso / 200 × minutos`, e ela está certa. O insumo é que não era o que a tela precisa: o número
sobe com o **relógio**, não com o esforço. Medido lado a lado no catálogo real, a coluna
"antes" é uma constante — 4,9 kcal em 30 s de polichinelo, tanto faz se a pessoa fez 40
repetições ou ficou parada olhando a câmera. Num app cuja razão de existir é contar repetição
por visão computacional, ignorar a contagem e faturar tempo de sessão é a mentira mais fácil de
não perceber: ninguém compara duas sessões de 30 s lado a lado.

**A spec foi corrigida antes do código** (AGENTS.md §Quando em dúvida). A SPEC-016 §Fase
Inicial dizia "cálculo MET client-side"; passou a descrever a fórmula por repetição, e o
critério 3 ganhou dois sub-critérios verificáveis — 3.1 "o número não anda sem repetição" e 3.2
"ritmo acima da referência rende mais, dentro de faixa travada".

```
kcal_por_rep = (MET × 3,5 × peso / 200) / cadência_referência
kcal         = reps × kcal_por_rep × m(cadência_medida)
```

**Decisões, e o que foi rejeitado:**

- **A cadência de referência virou coluna (`Exercise.ref_cadence_rpm`), não constante no
  cliente.** É o que faltava para a T-063 poder fazer a conta certa: o MET de tabela não é um
  número solto, ele descreve gasto *a uma intensidade*, e sem saber qual não há como converter
  "por minuto" em "por repetição". E é propriedade do movimento — 20 rpm é rápido para
  agachamento e lento para polichinelo —, então um mapa em código seria o `[A/T-051]`
  recomeçando, três semanas depois de a T-074 fechá-lo.
- **Coluna e valores na mesma migration.** Uma cadência `0` não é estado neutro: `0` significa
  desconhecido, e desconhecido apaga o card (`--`). Subir a coluna vazia e preencher depois
  seria desligar o kcal do produto entre dois deploys.
- **O multiplicador é modesto (K = 0,25) de propósito.** O ganho principal de quem acelera já
  está contado antes dele: mais rápido = mais repetições = mais calorias, linearmente. Este
  fator é só a perda de economia de movimento (mais aceleração e frenagem por repetição, menos
  aproveitamento elástico). Um valor alto aqui contaria a velocidade duas vezes — foi a
  primeira coisa que quase fiz.
- **Duas defesas, não uma.** Trava em [0,9 – 1,3] **e** janela mínima de 6 s antes de a
  cadência valer. Não são redundantes: a janela existe porque com 3 s decorridos uma repetição
  a mais move a cadência em 20 rpm e o card ficaria piscando durante justamente o trecho em que
  a pessoa se ajusta; a trava existe porque uma sequência de falsos positivos produziria um
  pico. Medido: 120 reps em 10 s dá multiplicador bruto 4,35, travado em 1,30.
- **Sem MET ou sem cadência, `--` — nunca cair de volta no cálculo por tempo.** O fallback
  silencioso reintroduziria o defeito exatamente no caminho degradado, onde ninguém olha.
- **Isto aproxima o kcal da regra da SPEC-014, não afasta.** Antes o único insumo era o relógio
  do próprio cliente. Agora são três, e dois vêm do servidor: MET e cadência do catálogo, e as
  repetições do `rep.detected` contado pelo analysis-worker. Só o peso continua premissa — e
  segue marcado `estimado` na tela até a T-065.

**Propriedade que amarra as duas versões:** no ritmo de referência a fórmula nova dá exatamente
o mesmo número da antiga (25 polichinelos em 30 s = 50 rpm = 4,9 kcal). A mudança não reescala
o produto; ela faz o número responder a quem está treinando. Tem teste dedicado.

**Verificação medida** (fórmula rodada contra o `GET /api/config` do stack real, 70 kg):

| Cenário | Antes (MET × min) | Agora (por rep) |
|---|---|---|
| parado 30 s, 0 polichinelos | 4,9 | **0,0** |
| devagar: 15 em 30 s | 4,9 | 2,6 |
| referência: 25 em 30 s | 4,9 | **4,9** |
| intenso: 40 em 30 s | 4,9 | 9,0 |
| agachamento: 10 em 30 s | 3,1 | 3,1 |
| agachamento: 20 em 30 s | 3,1 | 7,7 |

Catálogo servido depois da migration (`config_version` 8): polichinelo MET 8,0 @ 50 rpm =
0,196 kcal/rep · agachamento 5,0 @ 20 = 0,306 · flexão 8,0 @ 25 = 0,392 · abdominal 3,8 @ 20 =
0,233.

Gates: `ruff` limpo, `pytest` 817 verdes, `npm run lint`/`typecheck`/`test` verdes (505),
`makemigrations --check` sem drift.

**Sem passada de navegador**, e diferente da T-063: a extensão do Chrome não estava conectada
nesta sessão. A lacuna que ela cobriria — a fiação catálogo → tela — virou teste de integração
em `serverConfig.test.ts`: payload do servidor → store → catálogo mesclado → `liveKcal`, os
três caminhos (com cadência, sem servidor, e servido com cadência `0`). O que continua **não**
observado ao vivo é o card subindo repetição a repetição num treino real; é o que vale olhar no
próximo teste no celular.

**Pendências:** as quatro cadências são premissa de tabela, não medição de bancada — entram
como dado justamente para poderem ser corrigidas pelo painel quando o corpus da SPEC-012 tiver
algo melhor a dizer. Um teste do servidor (`test_todo_exercicio_tem_cadencia_de_referencia`)
cobra o par MET+cadência do catálogo inteiro, para exercício novo não nascer com o card mudo.

## 2026-08-06 (40) · T-042 — o gate de contagem, e por que ele não usa vídeo

Pergunta do Daniel depois do caso da flexão: *"como posso blindar para que todo push ou deploy
teste que todos os exercícios estão contando como deveriam?"*. É a T-042, que estava no backlog
desde a Fase 1 e tinha um obstáculo concreto: **os vídeos não estão no git** (50 MB,
`.gitignore`), e a CI não instala MediaPipe.

**A saída foi não versionar vídeo, e sim keypoints.** O `evalctl --save-keypoints` e o formato
`KeypointFixture` já existiam desde a T-039; faltava usá-los como gate. Medido: os sete vídeos
viram 9,7 MB de JSON, **1,9 MB depois da compressão do git**. O teste roda em milissegundos —
JSON → FSM, sem MediaPipe, sem decodificar vídeo, sem baixar o modelo de 17 MB.

**Não precisou de passo novo na CI.** O gate é um arquivo em `tests/`, então ele entra pelo
`uv run pytest` que já roda em todo push e todo PR. A CI continua sem o extra `eval`, e isso
deixou de ser uma limitação: a extração já aconteceu, uma vez, na máquina de quem gravou.

**A prova de que serve para alguma coisa** (rodada antes de commitar, com os limiares de hoje
contra os cenários de regressão):

| cenário | agachamento | flexão frontal |
|---|---|---|
| hoje | 18 | 50 |
| limiar `down_hip_height` apertado para 0,60 | **0** | — |
| porteiro de chão só de perfil (o estado do commit `eb14b5e`) | — | **0** |

A segunda linha é o caso real: o commit da T-106 que consertou "a flexão contava braço
levantado" apagou a contagem frontal no mesmo movimento e foi para produção. Com este arquivo,
ele teria falhado no push.

**Decisões.**

- **Cobra a contagem de HOJE, não o rótulo.** `expected_reps` da flexão veio do **título** do
  vídeo (`[A/T-108]`); cobrar acurácia contra rótulo herdado seria ajustar o produto a um
  número que ninguém verificou. O snapshot pergunta a coisa certa — "isto mudou sem alguém
  pedir?" — e a distância até o rótulo continua sendo medida pelo `evalctl`, que é onde ela
  pertence.
- **O compilado `frente&lado` ficou de fora do mapa.** Ele conta 0 hoje, e é um vídeo de rede
  social com cortes de câmera; carimbar esse zero transformaria um número ruim em contrato. Um
  terceiro teste garante que nenhuma OUTRA fixture fique fora sem querer.
- **`SEM_MATERIAL_REAL = {"abdominal"}`.** O teste que exige um vídeo por exercício no ar
  falharia hoje: o abdominal está em produção desde a T-107 e o corpus nunca teve um vídeo
  dele — a mesma posição em que a flexão estava. Travar o push de todo mundo por causa disso
  seria transformar um achado em pedágio, então a dívida ficou **escrita e visível**, com um
  teste extra que impede alguém de esconder exercício novo na lista.
- **O corpus ganhou o primeiro vídeo de agachamento** (do Daniel, 720×1280, frontal, 36 s), e
  com ele o manifest ganhou o que faltava para o exercício existir na bancada.

**O que este gate NÃO pega, dito por escrito no próprio arquivo**: mudança na extração (versão
do modelo ou do MediaPipe) — a fixture congela a saída do extrator de propósito, para isolar a
FSM; e a perna do navegador, manual por construção (`[A/T-040]`). São exatamente as duas coisas
que explicariam o caso ainda aberto do vídeo de agachamento contando 0 em produção.

**Gates.** `ruff check` e `format --check` limpos; `pytest` com **814 passando** (+9), mesma
exceção de ambiente das entradas anteriores.

**Pendências.** O lado **web continua sem CI nenhuma** (T-027): `lint`, `typecheck` e `test`
só rodam na máquina de quem escreve. E nada impede um deploy de commit vermelho — `prod.sh up`
não olha a CI.

---

## 2026-08-06 (39) · O plano de uma conta vira comando, e sai de dentro de um `.sh`

Pedido do Daniel: o `scripts/activate-subscriber.sh` (commitado ontem, sem task) devia morrer e
a função dele passar a viver dentro do `prod.sh`. Ele foi mais longe do que parecia.

**O que o script fazia de errado.** Ele abria `docker compose exec -T api python manage.py
shell` e mandava um bloco de Python por heredoc **não citado**. Duas consequências:

- `print(f"✗ Erro: Usuário {$EMAIL} não encontrado")` virava, depois da expansão do shell,
  `f"...{ana@exemplo.com}..."`. O Python lê isso como `ana @ exemplo.com` — o operador de
  multiplicação de matriz — e levanta `NameError`. **Medido**, não deduzido: o caminho feliz
  rodava normalmente; quem digitasse o e-mail errado é que recebia um traceback no lugar da
  mensagem escrita justamente para esse caso.
- `docker compose exec` **sem `-f docker-compose.prod.yml`**. Na VPS isso aponta para o
  `docker-compose.yml` de desenvolvimento, cujos containers não estão de pé — e a ajuda do
  próprio `prod.sh` já avisa em maiúsculas: *"Use SEMPRE o script, nao `docker compose -f …`
  direto"*.

Além disso: e-mail default embutido (`daniel@digitalfit.com`), plano fixo em `subscriber`,
prazo fixo em 365 dias, e nenhuma forma de **ver** o plano de alguém ou de **desfazer**.

**A regra saiu do shell e virou `manage.py plano`**, no mesmo padrão do `admin_tools` — que já
era o precedente da casa para "mexer em conta pela linha de comando". O `prod.sh` ganhou
`cmd_plano`, que só encontra o container certo e repassa os argumentos: a regra é testável e o
script é encanamento.

    ./scripts/prod.sh plano ana@exemplo.com                    # mostra
    ./scripts/prod.sh plano ana@exemplo.com --set subscriber   # 365 dias
    ./scripts/prod.sh plano ana@exemplo.com --clear            # volta ao default
    ./scripts/prod.sh plano --list

**Decisões.**

- **Comando de manage, não função de shell.** Três coisas que o `.sh` não tinha como pagar: o
  ORM valida (plano inexistente devolve a lista do que existe), dá para testar sem docker e sem
  VPS, e roda igual em qualquer ambiente — quem escolhe é o `manage.py`.
- **Ler é o modo default.** Sem `--set` e sem `--clear`, o comando **mostra** e não muda nada.
  O script anterior só sabia escrever; a pergunta mais comum do suporte ("essa conta é
  assinante?") não tinha resposta.
- **Vencido é dito com todas as letras.** `capabilities_for` já rebaixa a conta vencida na
  leitura, sem cron. Uma saída que só mostrasse a data deixaria quem lê achando o contrário.
- **`--clear` existe porque desfazer tem de ser tão fácil quanto fazer.** Era a assimetria mais
  cara do script antigo: promover custava um comando, despromover custava abrir o shell.
- **O prazo continua sendo o `plan_until` que já existe.** Nenhuma coluna nova, nenhum job de
  expiração — a decisão de quem rebaixa a conta vencida é da leitura, e continua sendo.

**Gates.** `uv run ruff check .` e `ruff format --check` limpos; `uv run pytest` com **805
passando** (+13, `tests/test_plano.py`), a mesma exceção de ambiente das entradas anteriores
(`test_settings_leem_ambiente`, que falha por causa do override de banco que esta máquina
exige e passa sozinho). `bash -n scripts/prod.sh` limpo e o caminho de recusa exercitado à mão:
sem a api de pé, o comando morre com mensagem e código 1.

**Pendências.**

- **Não consegui exercitar o `cmd_plano` de ponta a ponta** — não há docker de pé nesta
  máquina. O que foi verificado é a sintaxe, o despacho, a ajuda e a recusa; o `compose exec`
  em si só o primeiro uso na VPS confirma.
- **A docstring do `admin_tools` promete `./scripts/prod.sh exec api …`, que não existe.**
  Encontrado ao procurar o precedente; não consertado, porque está fora do que foi pedido.
  Vira Descoberta `[scripts]` no BACKLOG.

---

## 2026-08-06 (38) · T-127 — o rumo de uma correção passa a comparar treinos comparáveis

O terceiro achado de ler as telas do M0 com o catálogo de hoje. `contagens()` parte as sessões
ao meio no tempo e compara a média por sessão das duas metades — honesto com um exercício,
mentiroso com quatro.

**O caso.** Quem agachou em agosto e trocou para flexão em setembro lia "desça mais no
agachamento — **diminuindo** entre as sessões". Não diminuiu: as flexões entravam no
denominador como sessões em que a correção não apareceu. A tela informava mudança de catálogo
como se fosse mudança de corpo — exatamente o número que a SPEC-014 §Desvios manda não mostrar.

**A regra nova.** O rumo de um aviso só compara sessões dos exercícios em que **aquele aviso já
apareceu**. Duas consequências de desenho:

- **O conjunto de exercícios é observado, não declarado.** Nada de um mapa "código → exercícios
  que o emitem" no cliente: ele envelheceria a cada exercício novo, e o cliente não sabe (nem
  deve saber) o que cada FSM emite. Ele lê o que o histórico mostra.
- **Isso reaplica o gate de honestidade num escopo menor**, e de graça: com duas sessões de
  agachamento e uma de flexão, o agachamento ganha rumo e a flexão não. Antes a flexão herdava
  um rumo do tamanho da amostra alheia.

**O total continua sendo do histórico inteiro.** Só o *rumo* é restrito: "quantas vezes isso me
aconteceu" é uma pergunta sobre tudo o que fiz; "estou melhorando nisso" é uma pergunta sobre o
exercício em que isso acontece.

**Gates.** `npm run lint`, `npm run typecheck`, `npm run test` (490, +3), `npm run build`.

**Pendências.** A forma deste erro se repete em qualquer agregação futura que cruze exercícios
— registrado como Descoberta `[T-127]`, com o XP da SPEC-019 e a comparação de cadência da
SPEC-023 §6 como os próximos candidatos.

---

## 2026-08-06 (37) · T-055 — o histórico diz qual exercício foi feito

Task antiga (estava no backlog desde a Fase 2), destravada pelo mesmo motivo que as outras
duas: com quatro exercícios contando, "12 reps" numa lista deixou de ser uma linha legível.

**Três telas.**

- **Relatório**: nome do exercício acima do motivo de encerramento. Faz mais falta agora do que
  quando a task nasceu — o relatório pode ser reaberto do Progresso e do Analytics, longe do
  treino que o gerou.
- **Perfil**: cada linha do histórico ganha o exercício sobre a data, empilhados numa coluna.
  Quatro campos lado a lado quebrariam o nome no meio numa folha estreita.
- **Progresso**: o "último treino" passa a sair do **store de histórico**.

**O último treino era a última brecha da SPEC-024 §1.** A T-124 manteve aquele card lendo o
`report` do store de sessão, que é a sessão *corrente deste aparelho*. Quem entrasse na conta
em outro celular via 50 sessões na tela e nenhum "último treino": o `last_report` local estava
vazio. Agora é `sessions[0]` — a lista já chega ordenada da mais recente —, e o card ganhou a
data, que antes seria redundante e agora é necessária.

**Sem teste automatizado, e declarado.** As três mudanças são apresentação em componente React,
e a suíte web roda sem DOM (`environment: 'node'`). O que dava para testar como regra já é
testado: `getExercise` com slug desconhecido (T-074) e a ordem do histórico (T-121).

**Gates.** `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`.

**Pendências.** Verificação visual em navegador continua pendente desde a T-124/T-125 — e agora
inclui a linha de duas alturas do Perfil e o nome no topo do relatório.

---

## 2026-08-06 (36) · T-126 — o relatório para de falar em CAIXA ALTA

Continuação do M0, olhando as telas novas com o catálogo de **hoje** em vez do de quando elas
foram escritas. O primeiro achado não estava no Progresso nem no Analytics: estava no relatório
do fim do treino, e está em produção desde que o agachamento entrou.

**O sintoma.** `textForCode` conhecia cinco códigos — os três de cena e os dois do polichinelo.
O Tier C trouxe seis códigos de execução (`SQUAT_TOO_SHALLOW`, `PUSHUP_TOO_SHALLOW`,
`HIPS_SAGGING`, `HIPS_PIKED`, `CRUNCH_TOO_SHALLOW`, `CRUNCH_TOO_FAST`) e nenhum tinha frase. Em
"o que melhorar", quem terminava um agachamento lia `SQUAT_TOO_SHALLOW`: o nome da constante,
em caixa alta, depois de suar. A T-125 só ampliou o alcance ao pôr as mesmas contagens numa
segunda tela.

**Por que ninguém viu.** O HUD ao vivo nunca dependeu daquele mapa — o `feedback.issued` chega
com a frase pronta do catálogo do worker. E o único exercício que contava de verdade era o
polichinelo (`[A/T-106]`), cujos dois códigos por acaso estavam no mapa. Duas coincidências
sustentando uma tela.

**A correção, em três degraus.**

1. **`web/src/lib/events.ts` volta a ser espelho.** O arquivo se declara espelho de
   `events.py` e estava parado na Fase 0: o `Code` de lá cresceu, o de cá não.
2. **`GET /api/config` passa a servir o catálogo de texto** (`_mensagens_de_feedback`), lido do
   **mesmo** `catalog.pt-BR.yaml` que o motor carrega. É o que a SPEC-018 §C já prometia —
   "as frases que a pessoa lê suando; você vai querer reescrevê-las sem deploy" — valendo
   também para o relatório, e não só para o HUD.
3. **`textForCode` fica com três degraus**: servidor, embutido completo, o próprio código.

**Decisões.**

- **Não copiei as frases para o bundle.** Seria a mesma decisão que causou o bug, só que maior:
  dois arquivos de texto para manter em sincronia. O embutido continua existindo (primeiro
  paint, offline), mas agora está **completo**, e o servidor vence quando chega — a mesma
  doutrina do catálogo de exercícios da T-074.
- **O último degrau continua feio de propósito.** Código desconhecido aparece como código. Foi
  assim que este bug foi descoberto, e um "—" educado no lugar o teria escondido para sempre.
- **`lru_cache` no lado do servidor**, e não cache do Django: o YAML é do deploy, não do banco.
  Mudou o arquivo, mudou o processo. Falha na leitura devolve `{}` e o cliente cai no embutido
  (P2 da SPEC-018: configuração indisponível nunca derruba resposta).
- **Dicionário vazio no payload é lido como "não sei"**, igual à lista vazia do catálogo: o
  store guarda `null` em vez de `{}`, senão um soluço do servidor faria toda frase do relatório
  virar código na tela.
- **`TOO_FAR` mudou de texto**, e isto é conserto e não estilo: o cliente dizia "afaste-se
  menos: você está longe demais" enquanto o HUD, ao vivo, dizia "aproxime-se da câmera". Duas
  vozes para o mesmo aviso, uma delas dizendo o contrário do movimento pedido.

**O gate que fecha a porta.** `todo código do contrato tem texto embutido` percorre
`Object.values(Code)` e exige frase para cada um. Código novo em `events.ts` sem frase quebra o
teste — não a tela de quem acabou de treinar. Do lado do servidor, dois testes: o payload cobre
todo `Code`, e payload e motor leem o mesmo catálogo (a promessa do `[A/T-051]`, aplicada a
texto).

**Gates.** `npm run lint`, `npm run typecheck`, `npm run test` (487, +4), `uv run ruff check .`.

**Sobre o `pytest` desta sessão.** Redis e Postgres não estão de pé nesta máquina (nenhum
contêiner do compose rodando), e sem eles a suíte inteira erra na conexão — nada a ver com esta
task. Rodou em duas partes que juntas a cobrem: `DJANGO_DB_SQLITE=1 DJANGO_CACHE_LOCMEM=1 uv
run pytest` passa tudo **exceto** `test_settings_leem_ambiente`, que falha por causa do próprio
override (ele afirma que o settings lê Postgres do ambiente); e esse teste passa sozinho com
`DJANGO_CACHE_LOCMEM=1`. Vale subir o compose antes do próximo gate de verdade.

**Pendências.** Nenhuma nova. A `hint` viaja no payload e ainda não tem consumidor — o
relatório mostra só a `message`; ela está lá porque o catálogo a tem e cortá-la obrigaria a
mexer no servidor de novo quando a tela quiser explicar o "como".

---

## 2026-08-06 (35) · T-125 — o Analytics para de prometer e começa a medir

Última task do M0. A tela era um card e três bullets dizendo o que viria; agora tem quatro
blocos, todos sobre `SessionReport[]`: **ritmo por exercício** (linha), **constância do ritmo**
sessão a sessão, **o que mais aparece** (correções + rumo) e **enquadramento** (avisos de cena).

**O gate de honestidade fica visível, e é o melhor da tela.** Exercício com uma sessão só não
ganha gráfico: ganha a frase "mais um treino de agachamento e o ritmo vira linha", **no lugar**
do desenho e não abaixo dele. Isso não é um `if` que alguém precisou lembrar — o `tendencia`
viaja dentro da série desde a T-123, e quem desenha recebe o aviso junto com os pontos.

**Decisões.**

- **Linha em `<polyline>` SVG, sem biblioteca.** São pontos num path; trazer um motor de
  gráfico engordaria o bundle de um app que já roda inferência de pose no celular. Custo
  medido: o bundle foi de 263,20 kB para 268,21 kB (79,74 → 80,91 kB gzip) — 5 kB para as duas
  telas novas inteiras.
- **`vector-effect: non-scaling-stroke`** é obrigatório com `preserveAspectRatio: none`: sem
  ele o traço engrossaria junto com o eixo esticado e viraria uma faixa.
- **Escala é o intervalo da própria série**, como o `cadenceBars` do relatório já fazia: escala
  fixa achataria a variação que o gráfico existe para mostrar. Série constante desenha no meio
  — dividir por zero mandaria a linha para fora do quadro.
- **Constância vira `±X%`, não coeficiente de variação.** "±12%" é uma frase que alguém entende
  sobre o próprio treino; "0,12" é um número de estatística. Sessão com menos de duas
  repetições não entra na lista, pela mesma razão do `null` na T-123.
- **Correções e avisos de cena têm a MESMA forma**, seguindo o precedente do `improvements()`
  do relatório: para quem treinou, "suba mais os braços" e "você saiu do quadro" são a mesma
  pergunta — o que eu faço diferente da próxima vez.
- **Verde para correção que diminui, âmbar para a que aumenta, nada de vermelho.** Isto é
  treino, não erro de sistema; e o rumo só aparece quando existe (uma sessão não tem duas
  metades para comparar).
- **Reaproveita os contêineres do Progresso** (`prog__section`, `prog__exercicios`) de
  propósito: são a mesma família de informação, e dois tratamentos fariam parecer dois
  produtos.

**Medições**: lint, typecheck, 483 testes web e build de produção verdes. CSS 46,18 kB
(9,10 kB gzip).

**Pendência declarada, a mesma da T-124**: **sem verificação visual em navegador** — a extensão
do Chrome não está conectada nesta sessão. Comportamento e dados estão cobertos por teste; o
layout (linha SVG esticada, barras percentuais, grade de 7 colunas) foi verificado por build e
leitura. É o tipo de coisa que só o celular desmente.

---

## 2026-08-06 (34) · T-124 — o Progresso deixa de ser uma sessão

A tela mostrava **um** treino (`digitalfit.last_report`) e um parágrafo dizendo que histórico,
sequência de dias e evolução por semana eram "em breve" — com a nota de cabeçalho invocando a
régua da SPEC-014 §Desvios. A nota estava certa quando foi escrita. O que mudou não foi a
régua: é que o dado passou a existir e ninguém tinha voltado para ligá-lo.

Agora: três números no topo (treinos, repetições, dias), **grade do mês**, **quatro semanas em
barras**, **totais por exercício**, e o último treino como destaque no fim — onde ele passa a
ser o detalhe, não a tela inteira.

**Decisões de desenho.**

- **Mês de calendário, não "últimos 30 dias".** Mesma razão da semana de calendário na T-123: a
  pessoa lê o mês em que está, e uma janela deslizante faria o mesmo treino mudar de lugar todo
  dia. A grade abre na segunda, casando com `inicioDaSemana`.
- **Dia com treino é roxo cheio, não contorno.** À distância de um braço — que é como o produto
  é usado — a borda some e a grade vira ruído uniforme. Hoje ganha um `outline` azul, que é
  informação diferente e por isso forma diferente.
- **Semana sem treino fica com o trilho vazio**, não com uma barra de 1px: o zero tem de
  parecer zero. É a mesma família de decisão do `--`.
- **A escala das barras é a maior semana da própria pessoa**, não um alvo. Não existe meta
  nesta spec (meta é SPEC-019), e inventar um teto viraria uma cobrança que ninguém combinou.
- **Zero cálculo no componente.** Tudo vem de `history/aggregates.ts`. A única função de data
  aqui é `chaveDoDia`, e ela existe para casar com o formato do `diaLocal` — as duas pontas têm
  de gerar a mesma chave, senão a grade não acende.
- **Nenhuma cor nova**: só tokens da SPEC-014.
- **O rótulo "neste aparelho"** aparece quando a fonte é local, com o convite a criar conta —
  e o aviso de "não consegui atualizar" quando a fonte é o servidor e a última revalidação
  falhou. É o critério 5 aparecendo na tela que a spec nomeia.

**Sem kcal e sem fogo.** Os dois cabiam visualmente e nenhum dos dois é derivável do que se
mede hoje: kcal precisa do peso (SPEC-017) e fogo precisa da regra de sessão válida e do fuso
fixo (SPEC-019). Antecipar qualquer um dentro de uma task de Fase Inicial é exatamente o que a
AGENTS §3 proíbe.

**Medições**: lint, typecheck e 483 testes web verdes; `npm run build` fecha em 268 ms com CSS
de 45,35 kB (8,90 kB gzip) e o bundle do app em 263,20 kB (79,74 kB gzip).

**Pendência declarada**: **não houve verificação visual em navegador**. A extensão do Chrome
não está conectada nesta sessão ("Browser extension is not connected"), então o layout foi
verificado por build e por leitura, não por medição de geometria como manda o quirk registrado
para este projeto. O que está em risco é layout, não comportamento — mas a grade de 7 colunas e
as barras com altura percentual são exatamente o tipo de coisa que só o aparelho real desmente.
**Vale um olhar no celular antes de considerar a tela pronta.**

---

## 2026-08-06 (33) · T-123 — as leituras do histórico, puras

`history/aggregates.ts`: nove funções, nenhuma lê relógio, rede ou store. "Hoje" é parâmetro,
como manda a doutrina de derivação (`context/conventions.md`). 28 testes, sem mock de tempo.

**A decisão que evita uma briga futura: o nome `diasComTreino`.** A SPEC-024 §4 pede a grade do
mês marcando o dia em que a pessoa treinou. A SPEC-019 tem **"dia ativo"** como vocabulário
vinculante, e lá ele exige sessão *válida* (`rep_count ≥ 1`, "senão abrir a câmera por 30 s vira
fazenda de fogo"). São conceitos diferentes com a mesma cara. Chamar este de "dias ativos"
garantiria o pior desfecho no M1: o fogo acendendo num dia que esta grade não marcou, ou o
contrário, e ninguém sabendo qual das duas está errada. Dois nomes, dois conceitos.

**Outras decisões.**

- **Semana de calendário (segunda a domingo), não janela de 7 dias corridos.** A pessoa compara
  com o que ela chama de semana; uma janela deslizante faria o mesmo treino mudar de semana a
  cada dia que passa. Semana vazia entra com zero — o buraco é a informação.
- **Cadência nunca mistura exercícios.** rep/min de polichinelo e de agachamento são grandezas
  de movimentos com duração diferente: a linha misturada oscilaria conforme o que a pessoa
  escolheu treinar, não conforme ela melhorou.
- **Consistência de ritmo é relativa à própria média** (coeficiente de variação), não em ms.
  300 ms de desvio é muito num polichinelo e pouco num agachamento — é a mesma doutrina das
  features da FSM, razão contra si mesmo. Teste cobre: rápido e lento igualmente regulares
  empatam.
- **`null` com menos de duas repetições**, em vez de `0`. Zero afirmaria regularidade perfeita
  que ninguém mediu — a régua do `--` aplicada a um número derivado.
- **Rumo das correções compara MÉDIA POR SESSÃO**, não total absoluto. Quem treinou o dobro de
  vezes acumularia o dobro de correções sem ter piorado em nada. Tem teste dedicado: total
  recente maior, média por sessão menor, resposta "caindo".
- **Margem de 10% antes de chamar de mudança.** Sem ela, 2 contra 2,1 viraria "está piorando", e
  a tela informaria ruído de amostra como notícia sobre o corpo de alguém.
- **`tendencia: boolean` dentro da própria série**, em vez de um `if` na tela. É o critério 7
  (gate de honestidade) tornado difícil de burlar: quem for desenhar a linha na T-125 recebe o
  aviso junto com os pontos, e não precisa lembrar da regra.
- **Relatório antigo sem `feedback_counts`/`scene_warning_counts` não derruba nada** — os campos
  entram com `?? {}` e há teste.

**Gates**: lint, typecheck e 483 testes web verdes (28 novos). Python não tocado.

**Critérios da SPEC-024 nesta task**: 7 (gate de honestidade, testado nos dois lugares onde
existe — série de cadência e rumo das correções), 9 (tudo puro, sem rede e sem relógio de
verdade), 10 (gates). Nenhuma tela mudou: T-124 e T-125 é que consomem isto.

**Pendências geradas**: nenhuma.

---

## 2026-08-06 (32) · T-122 — o dado acorda quando alguém olha

Os três gatilhos do contrato de frescor, ligados. O que não existia em `web/src` antes desta
task: **um `visibilitychange`**. Nenhum. Quem guardava o celular no bolso e voltava não
remontava componente nenhum, e a tela ficava com o número de quando o aparelho foi guardado.

**Os três, e onde cada um mora.**

| Gatilho | Onde | Passa pelo debounce? |
|---|---|---|
| entrar na tela | `useFreshHistory()` (Progresso, Analytics, Perfil) | sim |
| página voltar a ficar visível | mesmo hook, `visibilitychange` | sim |
| fim de sessão | `applyReport` em `store/session.ts` | **não** |

O terceiro não mora numa tela de propósito: ele não depende de haver tela aberta. E ignora o
debounce porque ali houve um **fato novo**, não uma suspeita — esperar 30 s para mostrar o
treino que a pessoa acabou de fazer é literalmente a queixa que originou a spec.

Entrou um quarto, que a task não enumerava e sem o qual o contrato tem buraco: **troca de
identidade**, no `AppShell`. Depende de `contaId` **e** de `status` porque nenhuma das duas
cobre a outra — sair da conta mantém o id em `null` e muda só o status; trocar de conta mantém
o status em `authenticated` e muda só o id.

**Decisões.**

- **Debounce de 30 s.** Foco é barato de ganhar: alternar entre Progresso e Analytics, ou
  entre abas, ganharia foco várias vezes por minuto em cima de um dado que só muda quando a
  própria pessoa treina — e esse caso tem gatilho próprio.
- **Abortar não é falhar.** O `catch` do `refreshHistory` distingue os dois: pedido substituído
  sai calado, porque marcar `loadError` ali acenderia o aviso de "pode estar velho" justamente
  no instante em que um dado mais novo está a caminho. Testado com uma resposta segurada à mão.
- **`fetchHistory` ganhou `signal`** (parâmetro opcional, aditivo — nenhum chamador existente
  mudou). O `AbortController` é o que impede a resposta lenta de pousar por cima da recente e
  fazer a tela voltar no tempo; o bug clássico de stale-while-revalidate.
- **`deveRevalidarAoMudarVisibilidade` é função exportada**, não `if` dentro do hook. O
  `visibilitychange` dispara nas duas pontas e só a volta interessa; a suíte roda em
  `environment: 'node'` e sem extrair a regra ela só seria verificável à mão, num celular.
- **O hook entrou no Progresso e no Analytics agora**, antes de as telas desenharem o histórico
  (T-124/T-125). Deixar para depois faria a tela nova nascer com o defeito que a spec conserta.
- **O aviso de falha é discreto** ("Não consegui atualizar agora — pode faltar algo recente") e
  só aparece com dado bom na tela. O número não está errado, só pode não ser o último; um erro
  em vermelho por causa de um Wi-Fi ruim assustaria à toa.

**Medições.** `npm run lint`, `npm run typecheck`, `npm run test` (455 testes, 44 arquivos),
`uv run ruff check .` e `uv run pytest` verdes. Python não foi tocado.

**Critérios da SPEC-024 nesta task**: 2 e 3 verificados em `refresh.test.ts` — uma requisição
depois de `FRESH_MS`, nenhuma antes, e `force` furando a janela. 5 verificado nos dois lados
(store e refresh). O ramo do `AbortController` tem teste próprio, com a primeira resposta
segurada até a segunda aterrissar.

**Pendência declarada, não escondida**: o *fio* do `visibilitychange` (addEventListener no
`document` real e a limpeza no unmount) **não tem teste** — a suíte roda sem DOM e o projeto
não tem setup de teste de componente React. A regra que ele carrega tem teste; o registro do
ouvinte foi verificado por leitura. Vale um teste de verdade no dia em que houver DOM na
suíte, e isso é decisão de infraestrutura, não desta task.

---

## 2026-08-06 (31) · T-121 — o histórico ganha dono, e o visitante ganha passado

Primeira task do M0. Entra `web/src/history/` com quatro arquivos e sai a segunda verdade:
`store/account.ts` não guarda mais `history`/`historyStatus`.

**O que ficou onde, e por quê.**

- `localHistory.ts` — `digitalfit.history`, teto `HISTORY_CAP = 50`. Todo acesso passa por
  aqui pelo motivo do `auth/storage.ts`: o `localStorage` **falha de verdade** (Safari privado
  lança ao escrever), e um `setItem` solto derrubaria o fim do treino por causa de um registro
  de progresso. Teste cobre o caso (`readOnly: true` não lança).
- `merge.ts` — puro, sem import de store nenhum. União por `session_id`, servidor vencendo,
  ordenado por `created_at` desc, cortado no teto.
- `store.ts` — zustand, dono das sessões conhecidas.
- `refresh.ts` — a única porta para a rede. Fica fora do store porque o store guarda estado e
  isto conhece **identidade**; sem essa fronteira um teste de merge precisaria de `fetch`.

**Decisões.**

- **`record` no `applyReport`, não numa tela.** É o único lugar por onde todo relatório
  consolidado passa — `session.report.ready` e o repique do `waitForReport` chegam os dois
  nele. Pôr numa tela faria o histórico do visitante depender de ele ter aberto o Perfil.
  Efeito colateral: **o critério 1 da spec já está atendido nesta task**, sem esperar a T-122.
  A sessão entra na lista no instante em que o relatório existe; o Perfil lê o store e sobe.
- **`record` idempotente por `session_id`, substituindo.** O relatório chega duas vezes e as
  duas entradas contariam o mesmo treino. Substitui em vez de ignorar porque a segunda versão
  é a mais consolidada.
- **`loadError` separado do `status`.** São duas perguntas — "tenho o que mostrar?" e "o que
  mostro pode estar velho?" — e colapsá-las obrigaria a escolher entre esvaziar a tela e mentir
  que está tudo fresco. `status: 'error'` só quando **não há nada** na tela; com dado, a falha
  vira `loadError` e a lista fica. É o critério 5, já implementado e testado aqui.
- **`startLoad` não mostra "carregando" em cima de dado bom** — metade do
  stale-while-revalidate da T-122 já nasce aqui, porque é onde a máquina de estados mora.
- **`setUser` e `reset` chamam `history.reset()`.** A regra ("trocar de identidade não mostra
  as sessões de quem estava antes") continua sendo do store de conta mesmo com o dado tendo
  mudado de casa. `reset` não apaga: recai no local, que é de quem usou **o aparelho**.
- **A migração do `last_report` não sobrescreve** um histórico que já existe, e o `last_report`
  continua existindo para o seu outro trabalho — lembrar se a folha estava aberta no F5.

**O rótulo honesto, onde ele coube.** O Perfil do visitante é um formulário de login, e não
virou painel: ganhou **uma linha** — "3 treinos guardados neste aparelho — limpar o navegador
leva embora. Com conta, ficam." Ela é o CTA de conta mais verdadeiro que existe hoje, e é o
único honesto enquanto a T-087 (adoção das sessões do aparelho no cadastro) não existir. O
painel desses números é o Progresso, na T-124. No Perfil do logado, a linha "Mostrando o que
está guardado neste aparelho" só aparece quando o servidor não respondeu.

**Gates**: `npm run lint`, `npm run typecheck`, `npm run test` (443 testes, 42 arquivos — 38 nos
novos e nos tocados), `uv run ruff check .` e `uv run pytest` verdes. Python não foi tocado;
rodado para não confundir o estado desta task com o do T-108 em andamento (também verde).

**Critérios da SPEC-024 nesta task**: 1 (teste em `store/session.test.ts` — a sessão entra na
hora), 5 (`store.test.ts` — falha mantém a lista), 6 (`merge.test.ts` — conta uma vez), 9
(tudo puro, sem rede e sem relógio de verdade), 10 (gates). Os critérios 2 e 3 são da T-122; o
4 depende do Progresso (T-124) — o dado local existe e é testado, a tela ainda não o desenha.

**Pendências geradas**: nenhuma task nova. Registrada uma Descoberta sobre sessões que só o
aparelho tem quando há conta.

---

## 2026-08-06 (30) · SPEC-024 — o histórico tem três verdades e nenhuma acorda

O Daniel: *"progresso e analytics… está na hora de ter uma utilidade maior e também sempre que
você focar neles os dados estarem atualizados, isso eu digo para todas as páginas que têm dados
e histórico, incluindo o perfil. Elas estão inúteis."*

**A varredura confirmou as duas metades da queixa, e a segunda é pior que a primeira.**

- *Inúteis*: `ProgressScreen.tsx:22` lê só `digitalfit.last_report` — **uma** sessão, do
  `localStorage`. `AnalyticsScreen.tsx` não lê dado nenhum: é um card e três bullets de "em
  breve". As duas telas foram escritas assim de propósito (a nota de cabeçalho invoca a régua
  de honestidade da SPEC-014 §Desvios, e estava certa **na época**) — o que mudou é que o dado
  passou a existir e ninguém voltou para ligá-lo.
- *Desatualizados*: `AccountSheet.tsx:176` busca o histórico com guarda
  `if (historyStatus !== 'idle') return`. Uma vez por login, **nunca mais**. Treinou, voltou no
  Perfil, vê o número de antes; só logout ou F5 corrigem. E não existe um `visibilitychange` em
  lugar nenhum de `web/src` — verificado por grep, não por memória.

**A descoberta que muda o tamanho do trabalho**: `SessionResult.to_report()`
(`server/api/models.py:539`) já devolve o relatório **inteiro** de até 50 sessões em
`GET /api/sessions?mine` — `exercise`, `created_at`, `cadence_windows`, `rep_durations_ms`,
`feedback_counts`, `scene_warning_counts`. Progresso e Analytics úteis não esperam backend
novo; esperam alguém ler o que já desce pelo fio e é descartado na tela. Por isso a Fase
Inicial da spec é **cliente puro**.

**Decisões (e o que foi rejeitado):**

- **Anônimo tem histórico local** (`digitalfit.history`, teto 50 = o `HISTORY_LIMIT` do
  servidor). Escolha do Daniel entre as duas alternativas apresentadas; a outra era "só com
  conta", mais simples e melhor funil, descartada porque hoje a maioria dos usuários é anônima
  e as telas continuariam vazias para quase todo mundo. Teto igual ao do servidor de propósito:
  dois tetos fariam a mesma pessoa ver históricos de tamanhos diferentes antes e depois do
  cadastro.
- **Merge por união de `session_id`, servidor vence — nunca soma.** Somar contaria em dobro
  toda sessão feita logado. Um total desatualizado a pessoa desconfia; um total dobrado ela
  acredita.
- **Frescor por foco, não por timer.** Polling rejeitado: o dado só muda quando a própria
  pessoa treina, e ela treina *neste* aparelho, onde o fim de sessão já é um fato conhecido —
  um timer gastaria bateria e rede num app que já mantém câmera e WebSocket abertos para
  descobrir o que o cliente acabou de fazer. Revalidar a cada render também rejeitado: põe o
  gatilho na árvore do React em vez de num fato do usuário.
- **Debounce de 30 s, exceto no fim de sessão** — ali existe fato novo, não suspeita.
- **`last_report` não é fundido no histórico**: aquela chave guarda também se a folha estava
  aberta no F5, que é estado de navegação. Fundir faria um dado de UI viajar dentro do dado de
  treino.
- **Gate de honestidade**: abaixo de 2 sessões do mesmo exercício, nenhuma tendência é
  desenhada. Gráfico com um ponto não é gráfico — é a sugestão de uma tendência que ninguém
  mediu. É a régua da SPEC-014 §Desvios aplicada a série temporal.
- **Fuso**: dia-calendário de quem lê (como o `historyDate()` já faz), divergindo **de
  propósito** do America/Sao_Paulo fixo que a SPEC-019 escolhe para o fogo. Aqui a pergunta é
  "que dia era para mim"; lá é "o mesmo dia para todo mundo".

**Posição no plano**: entra como **M0 da Fase 5, antes do M1**. O fogo/meta/XP do M1 são
leituras do histórico — construir aquela UI sobre um dado que não atualiza seria pôr contador
novo em cima de fundação torta. T-121…T-125, com T-123 paralela a T-122.

**Pendências geradas**: nenhuma task nova fora do M0. T-055 (histórico diz qual exercício)
ganhou relevância — ajuda o M0 e não o bloqueia. T-087 (adoção das sessões do aparelho no
cadastro) é o que torna verdadeiro o CTA de conta que o rótulo "neste aparelho" oferece.

**Status**: `draft`, aguardando revisão do Daniel. Nada implementado.

---

## 2026-08-06 (29) · T-108 (parte) — a flexão de frente, e a tese que estava errada

O Daniel quis "ângulo habilitável por exercício", começando pela flexão de frente: *"o celular
no chão em pé pegaria bem também para detectar em pouco espaço, de lado já ocupa mais"*. A
`flexao.py` respondia que isso é impossível — "de frente uma flexão é um corpo encolhendo
contra a lente e não há feature que sobreviva" (SPEC-020, Tier C). Ele trouxe dois vídeos.

**A tese estava meio certa e meio errada, e a metade errada é a que importa.** O encolhimento
existe e é violento — mas ele **é** a feature. O que a bancada mediu, antes de qualquer código:

| grandeza (razão, mesmo frame) | flexão perfil | flexão frente | em pé (real) |
|---|---|---|---|
| ombros ÷ tronco aparente | 0,12 | **1,9–48** | 0,29–1,26 |
| tronco \|dx/dy\| (porteiro antigo) | 1,56–3,47 | 0,00–1,19 | 0,00–0,13 |
| pulso − quadril | 0,48–0,77 | 0,25–2,74 | **≤ 0,16** |

- **Diagnóstico do 0 de 50.** O porteiro era `trunk_spread ≥ 1,2`; de frente o vetor
  ombro→quadril aponta para a lente, o `dx` some, o gate nunca abre. Máximo observado no vídeo
  inteiro: 0,66. A FSM ficava congelada — não era limiar mal calibrado, era feature cega.
- **Porteiro novo: `pulso − quadril`, e vale nas DUAS vistas.** A mão está no chão e o quadril
  está mais longe da lente; num plano que se afasta, mais longe é mais alto na imagem. Em pé
  o máximo medido em três vídeos reais é 0,16, o limiar ficou em 0,30 — quase o dobro de folga.
- **A vista se lê sozinha** em `ombros ÷ tronco`: 16× de separação entre perfil (0,12) e frente
  (≥1,9), limiar em 1,0 no meio do vão. Ninguém configura nada. `PushUpAnalyzer(view=...)`
  força, e é o gancho para a escolha na tela que o Daniel pediu.
- **De frente quem conta é o ângulo do cotovelo**, dividido pelo topo da própria pessoa —
  mesma doutrina do perfil (razão contra si mesmo), outra grandeza. A altura do ombro, que
  sustenta o perfil, balança de 0,3 a 2,3 torsos aqui porque cada rep muda a distância da lente.

**Varredura (o número que escolheu o limiar).** O par de menor erro bruto era (0,60/0,86), com
erro 1 — e é lixo: 0,86 fica 0,001 abaixo do menor topo medido, ajuste ao rótulo. As
distribuições dão a janela real: **todo fundo de rep < 0,585, todo topo > 0,859**, então a
histerese tem de viver nessa folga. Dentro dela, **20 pares dão contagem idêntica** — platô, não
pico. Escolhido (0,63 / 0,80), e o 0,63 tem justificativa independente: é o equivalente exato
dos 107° de cotovelo que o perfil já usa (107 ÷ 171).

| desce | sobe | v1 (50) | v2 (50) |
|---|---|---|---|
| 0,60–0,70 | 0,74–0,85 | 52 | 50 |
| 0,60 | 0,88 | 42 | 50 |
| 0,60 | 0,92 | 6 | 49 |

**Resultado, pelo pipeline real (`evalctl`): 0/50 e 0/50 → 52/50 e 50/50.**

**A cena mentia duas vezes, e consertar uma só teria piorado.** Nos prints de produção o
produto dizia "Você saiu do quadro" a sessão inteira com o enquadramento perfeito: o tornozelo
é âncora obrigatória e de frente tem visibilidade **0,09 em 100% dos frames**. Mas a checagem de
distância também estava errada (0,07–0,33 contra faixa 0,45–0,98, **98–100% dos frames fora**);
corrigir só a âncora trocaria "saiu do quadro" por "aproxime-se".

- `SceneHints` ganhou `frame_anchors` — o exercício declara o que precisa estar visível, como
  já declarava a postura. A flexão declara tronco+braços (0–4% de frames ruins), sem tornozelo.
- Deitado, a distância virou **a maior separação entre as âncoras**, que não pressupõe eixo
  nenhum. Medido: perfil longe 0,08, perfil bom 0,19, frontal 0,66–0,95.
- Avisos nos vídeos reais: **26 → 0** (v1) e **26 → 2** (v2, os frames em que o modelo perde o
  pulso de verdade).

**O `evalctl` pegou um bug que o teste não pegou.** A primeira versão emitia `HIPS_SAGGING` x35
**e** `HIPS_PIKED` x17 na mesma série — `hip_line` traça a reta sobre o tornozelo, que de frente
é adivinhado. Crítica contraditória é crítica inventada. De frente o produto agora **conta e não
julga** postura, e o teste passou a varrer os dois desalinhamentos (a versão anterior só
exercitava o quadril alinhado e passava sem provar nada).

- **Gerador**: boneco frontal montado em 3D e **projetado em perspectiva** — de frente a
  perspectiva não é detalhe de desenho, é o fenômeno medido. As razões que ele produz batem com
  as dos vídeos reais (`sh/torso` 1,4–8,8 contra 1,9–48; cotovelo 54–180 contra 35–176). Foi ele
  que expôs `min_shoulder_to_torso=1,5` fechando o porteiro **no topo** da rep (onde o
  encolhimento é mínimo): virou 1,0, frouxo de propósito, porque quem recusa gente em pé é o
  outro porteiro, com folga de verdade.
- Gates: `ruff check`/`format` e `pytest` (792) verdes; 26 testes novos em
  `tests/test_flexao_frontal.py`.

**Maturidade continua `beta`, e o motivo é o rótulo.** Os dois vídeos são de rede social e o
"50" veio do título, não de contagem própria — o README do corpus é explícito que rótulo
herdado envenena a bancada. O v1 conta 52 num platô estável, o que tanto pode ser acerto do
algoritmo quanto rótulo errado. Promover a `calibrado` exige os 8 vídeos com contagem do Daniel.

**Nota de produção (acrescentada no commit, sessão seguinte).** Este trabalho ficou 19 h na
árvore sem commit, e nesse intervalo o Daniel testou a flexão frontal **em produção** (conta
admin, vídeo do corpus pela fonte de vídeo da T-040): contava zero. Produção roda o que está
commitado, e o que está commitado é o porteiro de perfil. Medido hoje, o mesmo vídeo em três
revisões:

| revisão | `flexão-frente-v2` |
|---|---|
| `a1003ad` (05/08 20:03, antes do porteiro) | 51 |
| `eb14b5e` → HEAD (**o que está em produção**) | 0 |
| esta árvore | 50 |

O commit que consertou o "braço levantado" apagou a contagem frontal no mesmo movimento, e
ninguém tinha como saber: naquele momento não havia teste nem vídeo de flexão frontal no
repositório. A lição não é sobre a flexão — **conserto de porteiro é conserto de recall, e
perda de recall não quebra teste nenhum**. Quem gritou foi o corpus, um dia depois, e por
acaso.

---

## 2026-08-06 (28) · T-120 — o treino só começa com a câmera ligada

Pedido direto do Daniel, em paralelo à SPEC-023. O CTA da pré-configuração fazia duas coisas
num toque só: `cameraControls.start()` **e** `navigate({ screen: 'treino' })`, na mesma linha.
Quem chegava com a câmera desligada — todo mundo, na primeira vez — saía da pré-configuração
no instante em que o navegador abre o diálogo de permissão. O treino começava por cima do
popup, e enquadramento, espelhar, zoom e o aviso de cena da T-085 passavam batidos. Com
permissão negada era pior: navegava igual, para uma tela de treino sem imagem nenhuma.

- **A regra virou função pura** (`web/src/session/startGate.ts` + teste), como o portão de
  partida da T-069: `ctaDeInicio(cameraStatus)` devolve ação, rótulo e travamento. `ready` é o
  **único** estado cuja ação é `iniciar` — e isso é o que o teste cobra, varrendo os outros
  quatro. Regra de ordem se testa com tabela de estados; montar React aqui não provaria mais.
- **`denied` e `error` continuam clicáveis**, com o mesmo rótulo de `idle`. O motivo da falha
  já está escrito na capa da `CameraView`; o que sobra ao botão é a única saída útil, que é
  tentar de novo depois de liberar a permissão. Só `requesting` desabilita — enquanto o
  navegador decide, tocar de novo não reabre nada.
- **A ordem do portão de quota não mudou** (SPEC-016, critério 1): o limite é verificado antes
  de tudo, inclusive antes de ligar a câmera. Quem esgotou não dá permissão para ouvir "não".
- **Efeito colateral bom no treino**: o mesmo `iniciar` é o play do FAB da tela de treino
  quando a câmera caiu. Antes ele navegava para a tela onde já se estava; agora liga a câmera
  e fica, que é o que aquele botão sempre quis dizer.
- Ajustes de texto e forma: o pill da janela dizia "A câmera abre aqui — alinhe-se à guia"
  (descrição de janela vazia) e passou a dizer "Ligue a câmera para se enquadrar"; o ícone do
  CTA acompanha o rótulo (▶ só quando é treino mesmo — um play ao lado de "Ligar câmera"
  prometeria o que o toque não faz); `.v2-cta:disabled` perde o glow e mantém o texto legível.
- Gates: `npm run lint`, `npm run typecheck` e `npm run test` verdes (39 arquivos, 416 testes,
  4 novos). Verificado no navegador: com a permissão bloqueada, o toque no CTA mantém a rota
  em `preparar` (`location.hash` vazio) e mostra "Permissão negada" — que é exatamente o caso
  que antes ia parar num treino cego. O caminho com câmera concedida não é testável no browser
  controlado (sem dispositivo); fica para a passada no aparelho real.
- Spec atualizada junto (AGENTS: a spec vence): SPEC-014 §3, critério 3 e Revisão 2026-08-06.

---

## 2026-08-06 (27) · SPEC-023 e a Fase 6 — o treino ganha ritmo, e o lançamento ganha ordem

Sessão de projeto, não de código. Entrada: dois áudios de uma conversa do Daniel com um amigo
(19min30s + 4min18s), transcritos localmente. Saíram `docs/IDEIAS-2026-08-05-conversa.md`
(a fonte, no papel que a rodada de 2026-07-30 teve para as SPEC-019…022), a **SPEC-023** e a
**Fase 6** no BACKLOG (T-111…T-119 + o agrupamento dos blocos A/B).

### A transcrição, e por que ela custou duas passadas

O áudio está **clipado, não só ruidoso**: um ventilador soprava no microfone, a banda 0–60 Hz
é a mais forte do arquivo (15–30 dB acima da fala), e ela saturou o pré-amplificador. Amostra
mediana em 32.700 de 32.768; 38,5% no fundo de escala. Medições, para não repetir o caminho:

- passa-alta + `afftdn` + `adeclip`: **empate** com o original — filtro remove ruído, não
  devolve amplitude cortada no teto;
- `large-v3` (modelo maior): **pior** que `large-v3-turbo` (1.152 × 1.428 caracteres no mesmo
  trecho, mais uma frase alucinada). Modelo grande é mais cauteloso e desiste de trecho
  ininteligível; em áudio destruído, arriscar recupera mais palavra aproveitável;
- **desligar o VAD: +26%** de conteúdo. Era ele que marcava como silêncio os trechos falados
  por cima do ventilador. Foi o único ganho real.

A segunda passada não trouxe só volume: trouxe a analogia da pipoca inteira com os números
certos, o diferencial "treinar com amigos" entre os dois planos pagos, e três ideias que a
primeira tinha perdido por completo (§2.14, §2.16, §2.17 do documento).

### SPEC-023 — as decisões, e o que foi rejeitado

A frase que originou tudo: *"um aplicativo que não te apressa e também não te atrasa"*.

- **Uma série É uma sessão.** Não foi decisão nova — a Evolução da SPEC-009 já dizia "cada
  série é uma sessão do ponto de vista do admission control". A spec executa isso em vez de
  brigar com ele. **Rejeitado**: encadear sessões de 30 s dentro de uma série (resetaria
  baseline e estado da FSM a cada 30 s).
- **O descanso não é sessão, não é evento, não existe no servidor.** Três motivos: não segura
  slot de cloud (o semáforo protege inferência, e descanso não infere); repetição feita no
  descanso não conta de graça, sem regra nova; e nenhuma tabela nova — o treino é a sequência
  de `SessionResult` que produziu.
- **O treino NÃO vira entidade persistida.** Só dois carimbos aditivos (`set_index`,
  `set_total`), na natureza do `config_version` da T-075. **Rejeitado**: tabela `Treino` —
  princípio de derivação da SPEC-019, não há fato aqui que não seja derivável.
- **Teto de série sem coluna nova — e essa decisão foi CORRIGIDA no meio da sessão.** O
  primeiro desenho criava `Plan.set_ceiling_s`, argumentando que a janela competitiva não pode
  virar o teto de quem é lento. O argumento vale para o **`duration_s` do evento** e não vale
  para a coluna: `session_max_s` (T-073) nunca foi a janela, é o teto do plano. Fui conferir o
  modelo antes de fechar e a coluna proposta era redundante. Ficou o número que já existe —
  `Plan.history_limit` é o precedente de coluna que nasce, ninguém lê e apodrece
  (Descoberta `[T-073]`). O Free ter `session_max_s = 30` deixa de ser problema e vira o gate:
  modo contado é benefício de plano pago, e o Free fica no modo livre, que é completo.
- **Modo livre entra como teste de regressão, não como refatoração.** É o comportamento de
  hoje; o que ele ganha é nome. Só o modo contado exige código novo.
- **O gesto de prontidão é edge-only, e isso está declarado.** Durante o descanso não há
  sessão nem worker, então quem detecta é o cliente — e no modo cloud o cliente não extrai
  pose. Toque e temporizador são a saída universal; o gesto **acelera**, nunca é a única saída.
- **Estar em posição ≠ estar pronto.** É por isso que o gesto vive aqui e o gate por pose
  continua na SPEC-004/T-030: entre séries a pessoa já está no lugar certo e ainda está
  recuperando o fôlego.
- **`PROTOCOL_VERSION` não sobe**, com uma ressalva honesta que a SPEC-021 não precisou dar: lá
  o aditivo era um *tipo* de evento (consumidor antigo ignora), aqui é um *valor novo num enum
  existente*, que um `_as_enum` estrito recusaria. O que salva é a direção do risco —
  `target_reached` só é produzido depois do deploy e replay antigo nunca o contém. Se algum
  consumidor passar a ser versionado à parte, a linha vira dívida.

### Fase 6 — a ordem, e a correção que fiz na ordem do Daniel

Ele mesmo enunciou a sequência no áudio: *"base → conseguir a assinatura → agora eu tenho que
manter as pessoas → depois os profissionais"*. A única troca que a Fase 6 faz é **retenção
antes de assinatura** — ninguém assina um app que usou uma vez.

O Bloco A não tem task nova: são T-104/T-108/T-109/T-110 agrupadas para dizer que vêm primeiro.
Motivo escrito no backlog: hoje o catálogo tem **um** exercício que conta de verdade (o
agachamento está no ar, `validado`, contando zero — Descoberta `[A/T-106]`), e cobrar por isso
é o pior cenário possível.

### Pendências geradas

- **A SPEC-023 nasce `draft`** e espera revisão do Daniel, como as 019…022 esperaram.
- **T-078 virou pré-requisito da T-112**: o `duration_ms` do relatório mistura dois relógios, e
  com duração variável "tempo até a meta" é exatamente o número que ele erra. Deixou de ser
  cosmético.
- **Decisão comercial em aberto, bloqueando só a T-117**: um plano pago ou dois, e o preço
  (R$ 15/20/30 foram todos ditos; prevalece 15/20). O trecho de preço é o mais afetado pelo
  áudio ruim — vale conferir de ouvido em `~/Documentos/transcricoes/*— LIMPO.flac` antes de
  fixar número em tela.
- **"Quanto tempo você tem?" precisa entrar na SPEC-022** antes de ela ser implementada: o
  motor pesa objetivo, idade e IMC e não tem tempo disponível, que é a variável mais decisiva
  na prática e a mais barata de coletar.
- Não commitei: a árvore tem trabalho de outra sessão em `workers/analysis_worker/` e
  `eval/corpus/manifest.yaml` que não é meu.

## 2026-08-06 (26) · O exemplo guiado passa a depender de quem é — e duas regressões das faixas

### O exemplo por identidade, não por histórico

A regra da SPEC-015 era "uma vez por exercício, para todo mundo". Ela tratava o exemplo como
**onboarding** — algo que se consome e se encerra. Só que ele não é isso: ele é a instrução de
ENQUADRAMENTO, e enquadramento errado não deixa a pessoa insegura, deixa a sessão zerada (a
T-106 gastou uma task inteira nisso). "Já viu uma vez" nunca foi a mesma pergunta que "já sabe".

O eixo virou a identidade (`session/guideGate.ts`):

- **sem conta** → o exemplo abre toda vez que a pessoa TROCA de exercício;
- **com conta** → nunca abre sozinho; o link "ver exemplo" se destaca enquanto aquele
  exercício não tiver sido visto, e emudece depois.

Decisões:

- **Trocar de exercício, e não cada sessão.** O pedido original era "sempre que for treinar",
  mas o app abre direto na pré-config — o gatilho teria que ir para o botão de play, virando
  pedágio de todo treino. Fricção que a conta remove é o que a SPEC-011 recusa por escrito, e o
  `preferences.ts` já dizia em comentário que isso seria "uma pequena punição por não se
  cadastrar". Séries repetidas não passam pelo funil e continuam livres.
- **As duas decisões saem da MESMA função.** Separadas, divergiriam até existir o absurdo — o
  exemplo abre sozinho *e* o link pisca pedindo que o abram. Há um teste que varre as quatro
  combinações só para provar que esse estado não é representável.
- **Antes do `fetchMe`, quem responde é o refresh guardado.** O status nasce `unknown` e a
  ponte `#/ex/<slug>` do site dispara o funil num efeito de boot. Esperar a rede ali abriria o
  exemplo na cara de quem tem conta, vindo do site — o incômodo que a mudança existe para tirar.
  Refresh vencido faz alguém deslogado perder o exemplo automático; é o erro barato dos dois,
  porque o link continua na tela, destacado.
- **O `guide_seen` continua sendo gravado.** Deixou de decidir a abertura para decidir o
  destaque — inclusive para quem vira assinante depois: exercício que já viu como anônimo
  nasce sem destaque.
- **O link virou chip.** Era texto sublinhado de 9px; para quem tem conta ele agora é o ÚNICO
  caminho até o exemplo, e o que ninguém enxerga não é um caminho. 74×36px com ícone. O
  destaque respira 2,2s × **3 e para** — contagem finita porque animação infinita numa tela
  onde se fica parado esperando a câmera vira tique, o oposto de "não invasivo".
  `prefers-reduced-motion` recebe a borda acesa, sem pulso.

### Duas regressões da entrada (25), achadas medindo no navegador

1. **As fotos da Escolha não carregavam — nenhuma.** `loading="lazy"` herdado do card antigo:
   dentro de um contêiner com `overflow-x: auto` o Chrome nunca dispara o carregamento
   (`currentSrc` vazio, `complete: false`, com o card visível na tela). Provado nos dois
   sentidos: imagem idêntica sem `lazy` carrega, e remover o atributo em runtime carrega na
   hora. O `lazy` virou opt-in no `ExerciseDemo`, com a armadilha documentada; só a vitrine do
   site liga, onde a rolagem é a do documento e o adiamento funciona de verdade.
2. **A media query media a tela errada.** `@media (min-width: 700px)` para agrandar o card
   casava com o MONITOR, não com o quadro: o app vive dentro do `.app__phone`, que é
   `max-width: 430px` em qualquer tela. No desktop dava cards de 196px num quadro de 430px —
   um layout que nenhum celular veria. Removida, com um comentário no lugar dizendo que o
   instrumento correto seria container query.

Medido depois das duas: 4/4 imagens carregadas, card de volta a 160px, e a Escolha inteira
cabendo **sem rolagem** (800px de conteúdo em 800px visíveis, com 4 exercícios).

Gates: `typecheck`, `lint`, `build` limpos; `vitest` 412/412 (+10 em `guideGate.test.ts`).

Pendências geradas:

- **A SPEC-015 agora contradiz o código.** Ela diz "o guia só aparece sozinho na primeira vez";
  o código diz "depende de ter conta". O AGENTS manda comportamento nascer de spec — falta a
  revisão da SPEC-015 (ou uma SPEC nova) para o texto voltar a valer.
- **A rota de quem TEM conta não foi verificada ponta a ponta.** Sem backend local o `fetchMe`
  falha e o status resolve para `anonymous` — comportamento correto, mas impede o teste real.
  Cobertura hoje é só unitária (10 casos).
- **O `ExercisePicker` troca de exercício sem passar pelo funil.** Hoje é inofensivo (fica
  oculto na pré-config pelo `compactCover`, só aparece na capa do treino antes da câmera subir),
  mas é uma segunda porta para a mesma decisão. Se um dia voltar a aparecer, o exemplo não abre.
- **As fotos são 900×900 numa caixa 138×92**: com `contain` sobram 23px de vazio de cada lado.
  `aspect-ratio: 1` resolveria (foto a 138×138, zero barra) ao custo de ~45px por card. Decisão
  do Daniel, ainda não tomada.

---

## 2026-08-05 (25) · T-091 (metade layout) — a Escolha vira faixas por categoria

A tela Escolha empilhava um card de ~305px por exercício. Com dois exercícios aquilo cabia na
tela; com os quatro de hoje já são ~1.220px de rolagem, e o Lote 1 da SPEC-020 (T-092…T-095)
mais o wall sit levariam a ~3.000px — a tela deixaria de ser uma escolha e viraria um catálogo
que se percorre.

**A troca que resolve não é encolher o card, é trocar o eixo.** Cada categoria virou uma faixa
horizontal (`screens/ExerciseRails.tsx`): a altura da tela passou a escalar com o número de
CATEGORIAS — vocabulário fechado em código, quatro — e não com o de exercícios. Estimativa pelo
box model: ~630px hoje, ~850px com dez exercícios. A rolagem lateral fica dentro da categoria,
que é onde a comparação de verdade acontece ("qual cardio eu faço hoje?"), não entre elas.

Decisões:

- **O card grande não morreu, virou do site.** `ExerciseCards` agora é exclusivo do Index, onde
  a foto grande é o argumento de venda e rolar é o comportamento esperado de uma página de
  marketing. Com o app fora, sumiram os props `grid`/`openInApp` e o ramo de botão.
- **"ver todos" existe porque a faixa esconde.** É a fraqueza conhecida do formato: o que está
  fora do quadro não se anuncia. O botão abre a categoria numa grade — e só aparece com mais de
  2 exercícios, senão prometeria revelar o que já está à vista. O limite é constante e não
  medido por JS de propósito: medido, o botão apareceria e sumiria na rotação do aparelho.
- **A faixa sangra até a borda da tela** (`margin-inline: -16px`). Card cortado na margem é o
  que anuncia que há mais para o lado; terminando alinhada ao texto, a faixa lê como fileira
  completa. Junto vai `overscroll-behavior-x: contain`, senão o gesto lateral vira "voltar".
- **`groupByCategory` é regra pura no `catalog.ts`, não lógica na tela.** A ordem em que as
  categorias se apresentam é conteúdo, igual ao `CATEGORY_LABELS`. E é a única parte disto que
  dá para cobrar por teste — a suíte do web roda em `node`, sem DOM.
- **Categoria desconhecida vira seção com o slug cru, e não some.** O servidor pode servir
  categoria que este cliente não conhece; engolir o exercício aqui seria o `[A/T-051]` de volta
  pelo outro lado — existe no servidor, a admissão aceita, e a tela não mostra. Feio é
  aceitável; sumir é bug.
- **`ui/ExerciseDemo.tsx`**: a regra "sem foto, desenha a figura" agora existe uma vez só. Ela
  passou a valer em duas telas com visuais diferentes, e escrita duas vezes se perde uma —
  exercício novo chega antes da foto, e a tela que esqueceu o fallback põe ícone de imagem
  quebrada no lugar da pose.

Gates: `typecheck`, `lint`, `build` limpos; `vitest` 402/402 (7 novos em `catalogGroups.test.ts`).

Pendências geradas:

- **O T-091 continua `todo`** — esta entrada entrega só a metade layout. Cadeados com motivo
  (progressão ≠ plano ≠ conta) e selo Laboratório 🧪 dependem do eixo maturidade da T-090.
- **A trilha Fundamentos (T-097) pede uma seção no TOPO da Escolha.** As faixas deixam o lugar
  livre, mas ninguém verificou se anel de progresso + cadeado cabem no card da faixa ou se a
  trilha precisa do card grande de volta. Decidir quando a T-097 chegar.
- **Não foi verificado em aparelho.** Os números de altura são do box model do CSS, não medidos.

---

## 2026-08-05 (24) · T-106/T-107 — os exercícios de chão ganham foto (e o hero perde 1,8 MB)

Os dois exercícios de chão subiram sem foto de demonstração, caindo na figura do exercício. A
figura é o fallback certo, mas não é o produto: ao lado do polichinelo e do agachamento
fotografados, os dois novos pareciam inacabados. Quatro fotos geradas no Kairogen
(`nano-banana-pro`, 6 créditos cada, dentro do teto de 7 pedido), no mesmo padrão das que já
existiam: 900×900 JPEG, 89–96 KB, ginásio escuro, esqueleto neon, grade cyan no chão.

**A decisão de conteúdo que importa: as quatro fotos são de PERFIL, com a câmera no chão.** A
demo do Guia é a primeira coisa que ensina o enquadramento, e enquadramento errado num
exercício de chão não é estética — é a sessão inteira sair zerada (a validação de cena mede a
extensão do corpo no eixo horizontal, e de frente uma flexão é um corpo encolhendo contra a
lente). Uma foto frontal aqui seria uma instrução errada com cara de instrução certa.

**Sobre gerar as fases certas.** As duas primeiras tentativas de "fundo da flexão" saíram em
prancha: com uma imagem de referência em prancha, o modelo preserva a pose e ignora a
instrução de dobrar o cotovelo. O que funcionou foi **abandonar a referência** e descrever a
cena inteira em texto, com a pose descrita espacialmente ("peito a 5 cm do chão", "ombros mais
baixos que os cotovelos", "antebraços verticais"). Com a fase certa em mãos, aí sim a
referência serve — o topo da flexão e o topo do crunch saíram de primeira usando a imagem
irmã como referência, e é o que garante que o par tenha o mesmo homem, a mesma cena e o mesmo
enquadramento. Custo total: 30 créditos, 5 gerações, 4 aproveitadas.

**O hero da landing.** A imagem da atleta estava em `herofamale.png` com **1,9 MB** — 21× o
peso das outras, num PNG, na primeira tela que qualquer visitante abre. Virou
`hero-female.jpg`, 900×900, 91 KB, mesmo tamanho renderizado. O PNG original fica fora do
repositório (não versionado): é o negativo, não o produto.

**Duas coisas que a verificação no app revelou, e que valem mais que as imagens:**

1. **Quem coloca foto em produção é a migration, não o `catalog.ts`.** Com a API no ar, o
   cliente usa o catálogo do SERVIDOR (o `[A/T-051]` resolvido pela T-074) — o `catalog.ts` é
   só o default embutido para o primeiro paint e o modo offline. Editar o cliente e esquecer a
   migration deixaria a foto invisível para todo mundo que tem rede. Por isso a `0013` existe,
   e por isso ela só preenche quem está com o campo **vazio**: um `demo_img` já trocado pelo
   painel não pode ser sobrescrito por deploy.
2. **Mudança de dado por migration não invalida o snapshot de configuração.** A `0013` alterou
   o banco e o `GET /api/config` continuou servindo a foto vazia: a invalidação normal é por
   `post_save`, que uma migration com modelo histórico não dispara. Não é bug — o próprio
   `config.py` documenta o TTL de 5 minutos justamente para este caso, e no deploy o processo
   reinicia de qualquer forma. Vale saber ao testar: ou espera 5 minutos, ou reinicia a API.

**Verificação:** os quatro cards da Escolha desenham foto (nenhuma imagem quebrada, `900×900`,
mesma altura de card); o Guia dos dois de chão mostra demo + três passos ilustrados + a frase
de cena correta; `GET /api/config` devolve os quatro `demo_img` preenchidos depois da migration.
Gates: `ruff` limpo, pytest verde (menos a falha pré-existente do `test_smoke`), web
lint/typecheck/test verdes (395).

---

## 2026-08-05 (23) · T-106 — a flexão contava braço levantado: o porteiro de postura

Teste em produção, no mesmo dia: *"dependendo da posição ele já contava, quando levantava ele
contava, meio que parece que ele conta diferentes posições"*. Reproduzido no gerador antes de
qualquer conserto: **pessoa em pé levantando e baixando os braços 10 vezes = 10 flexões
contadas.**

A causa é uma só, e é de desenho. A feature mede a altura do ombro sobre o pulso, e ela vale:

- **+0,734 torsos** em pé com os braços baixos;
- **+1,147 torsos** na prancha;
- **−0,734 torsos** em pé com os braços no alto.

Ou seja: em pé, baixar os braços é indistinguível de estar na prancha, e levantá-los é
indistinguível de descer a flexão. A feature media a coisa certa e **nunca perguntava quem
estava sendo medido**. O `ready_pose` sabia a diferença, mas ele só serve ao gate de prontidão
(SPEC-004, ainda não ligado) — a FSM nunca o consultava.

**O conserto: um porteiro de postura antes da FSM**, com duas perguntas escolhidas por medição,
as duas razões no mesmo eixo (imunes à anisotropia do `[A/T-106]`):

| situação | tronco `dx/dy` | mão↔chão | passa? |
|---|---|---|---|
| prancha | 2,46 | 0,13 | sim |
| flexão no fundo | 3,86 | 0,18 | sim |
| flexão de joelhos | 1,56 | 0,13 | sim |
| em pé, braços baixos | 0,00 | 1,78 | **não** |
| em pé, braços no alto | 0,00 | 3,78 | **não** |
| agachado | 0,00 | 1,23 | **não** |

Limiares em 1,2 e 0,5, no meio de uma folga de ordem de grandeza — a decisão não é apertada
entre 1,1 e 1,3, é 0,0 contra 2,5, e é isso que a faz sobreviver a ruído e câmera torta.

**Decisões do conserto:**

- **Frame fora de posição congela E descarta a tentativa**, silenciosamente. Não é o mesmo que
  `degraded` (dado ruim): quem se levantou não fez uma repetição incompleta, fez outra coisa —
  e criticar a execução de quem está saindo do chão seria ruído. Entrou `frames_off_posture` no
  `summary()`, separado de `frames_degraded`, porque é a primeira pergunta a fazer quando uma
  sessão de flexão volta zerada.
- **A referência da prancha só cresce com o porteiro aberto.** Sem isso, os frames em pé (0,73)
  entrariam na mesma referência dos de prancha (1,15) e a profundidade passaria a ser medida
  contra um corpo que ninguém fez.
- **A referência passou a exigir dois frames seguidos** (`min` com o frame anterior). Um único
  frame em que o modelo erra o ombro inflaria a prancha para sempre, e daí em diante nenhuma
  flexão de verdade voltaria a marcar 1,0. O primeiro frame ainda vale por si: semear baixo é
  inofensivo (a referência só cresce), semear alto é o que a persistência impede.
- **Flexão de joelhos entrou no gerador** (`PushUpPose(on_knees=True)`). O porteiro usa como
  "chão" o ponto mais baixo da perna — joelho ou tornozelo —, e essa promessa estava no
  comentário sem fixture nenhuma por trás. Agora tem: 10/10 reps, zero frame fora de posição.
- **O abdominal NÃO ganhou porteiro**, porque não tem o bug — e isso foi medido, não suposto: em
  pé o joelho fica sempre abaixo do quadril, então a referência sai negativa (−0,52 em pé,
  −0,32 agachado, −0,37 na marcha, contra o mínimo de +0,25) e a feature devolve zero. Inventar
  um porteiro sem reprodução seria calibrar contra nada. O que entrou foi o **teste** que
  transforma a proteção de acidente em invariante: quem trocar a referência do joelho descobre
  no pytest, não em produção.

**Verificação:** o caso relatado vai de 10 reps para 0; em pé parado, agachando e marchando
também dão 0; e o caminho realista (chega em pé → 6 flexões → levanta) conta exatamente 6,
tanto na FSM quanto pelo `evalctl` com calibração (10/10). Nenhum teste antigo mudou de
resultado.

---

## 2026-08-05 (22) · T-106/T-107 — flexão e abdominal, e a descoberta de que o agachamento não conta

Dois exercícios de chão (SPEC-020 **Tier C**), a capacidade de motor que o Tier C exigia, e uma
medição que deveria mudar a prioridade do backlog.

### A descoberta, primeiro, porque ela é maior que a task

**O agachamento está no ar, `validado`, e não conta uma única repetição em gente de verdade.**

Antes de escolher qualquer limiar, rodei o pipeline REAL sobre o corpus que já existe — vídeo →
MediaPipe → `normalize()` → `SquatAnalyzer.features()`. Uma pessoa **em pé** lê:

| vídeo | `hip_height` em pé (mediana) | frames que o squat leria como agachado |
|---|---|---|
| polichinelo-01 | 1,310 torsos | 0 / 124 |
| polichinelo-02 | 1,609 torsos | 0 / 61 |
| polichinelo-03 | 1,440 torsos | 0 / 101 |

O limiar de "agachado" é **0,72**, calibrado contra um boneco sintético que diz que em pé se lê
1,02 (perna de 1,05 torsos; gente real tem ~1,7). Descendo na mesma proporção que o gerador
(×0,62), um agachamento paralelo de verdade chega a ~0,89 — nunca cruza o limiar. O módulo
avisava por escrito que os números vinham do gerador e "errar para menos é o lado seguro"; a
medição mostra que o lado seguro também é o lado que não conta. Virou **T-109 (alta)** e
Descoberta `[A/T-106]`.

Junto veio uma segunda: **o espaço normalizado é anisotrópico**. O MediaPipe divide `x` pela
largura e `y` pela altura, então a mesma largura de ombros lê 0,352 torsos no vídeo em paisagem
e 1,188 no vídeo em retrato (razão 3,37; o formato do quadro sozinho prevê 3,16). Os dois
exercícios existentes escapam por acidente — `ankle_spread` é razão de dois horizontais,
`hip_height` é vertical sobre um torso quase vertical. Num corpo **deitado** o acidente acaba: o
torso é horizontal e o movimento é vertical. Virou T-110.

### O que essas duas medições fizeram com o desenho dos exercícios novos

A regra que os dois módulos seguem, e que é a resposta às duas descobertas: **feature é razão
entre duas medidas do mesmo eixo do mesmo corpo, nunca constante em torsos**.

- **Flexão** — `depth` = altura atual do ombro sobre a mão ÷ a maior altura que ESTA pessoa
  mostrou na sessão (a prancha dela). Cancela o torso, o formato do vídeo, a distância da câmera
  e o tamanho da pessoa. Sobra "quanto do seu próprio braço você dobrou".
- **Abdominal** — `lift` = subida do ombro ÷ altura do joelho. Aqui a referência **não precisa de
  memória**: o joelho dobrado com o pé apoiado é uma altura vertical estável que existe em todo
  frame, inclusive no primeiro. É por isso que o joelho dobrado virou requisito de medição no
  Guia, e não detalhe de execução.

Limiares escolhidos por tabela medida no gerador (as duas estão nos docstrings dos módulos):

| flexão — cotovelo | `depth` |   | abdominal — tronco | `lift` |
|---|---|---|---|---|
| 172° (prancha) | 1,000 |   | 4° (deitado) | 0,097 |
| 130° | 0,909 |   | 20° | 0,474 |
| 115° | 0,846 |   | 25° | 0,586 |
| 100° | 0,768 |   | 30° (crunch cheio) | 0,694 |
| 90° (fundo) | 0,709 |   | 40° | 0,892 |

Descer conta em `depth < 0,82` (~107° de cotovelo) e subir conta em `lift > 0,52` (~22° de
tronco). Os 90° de cotovelo e os 30° de tronco não são invenção: são o padrão de execução que
NASM/ACE descrevem (flexão até ~90° ou peito perto do chão; crunch até as escápulas saírem do
chão, lombar apoiada). Os limiares ficam um pouco **abertos** em relação ao padrão de propósito —
um `beta` que não conta nada nunca recebe corpus para deixar de ser `beta`, que é exatamente
como o agachamento chegou onde chegou.

### A capacidade de motor que o Tier C exigia

A SPEC-007 manda parar e registrar quando um exercício novo precisa de mudança fora de
`exercises/`. Precisou, e a lacuna era real: **a validação de cena mede distância pela altura
cabeça→tornozelo**, e numa flexão a cabeça e o tornozelo ficam quase na mesma altura. A medida
dá ~0, e o produto pediria "aproxime-se" a sessão inteira com o enquadramento perfeito.

Resolvido pelo contrato, não por tabela de slug: `Posture` (`standing`/`floor`) entrou no
`scene_hints()` do analisador, o `SceneValidator` passou a ler dali a postura e a faixa, e o
router liga os dois na abertura da sessão. Default = `standing` com a faixa da SPEC-003, então
**nenhuma sessão existente muda de resultado** — há teste cobrando isso.

O mesmo problema tinha uma versão de texto que teria estragado a sessão do usuário: a tela do
Guia dizia, fixo, "celular apoiado na vertical, uns 2 metros". Virou `scene_tip` por exercício
(coluna, editável no painel), com a frase antiga de fallback.

### Decisões menores, com o motivo

- **Nada de sinal de qualidade para "puxar o pescoço" no abdominal.** Era o candidato óbvio (a
  literatura cita muito), mas o boneco não sabe assinar o sentido dele: cabeça flexionada num
  corpo deitado gira o nariz por cima do peito, e o sinal na projeção lateral muda conforme onde
  a cabeça pivota. Sondei e o valor foi na direção contrária à intuição. Sinal que o gerador não
  sabe assinar não vira limiar — o erro de execução que sobrou é a **cadência**
  (`CRUNCH_TOO_FAST`, < 800 ms por rep), que se mede com relógio e não com geometria.
- **Crítica de postura sai JUNTO com a repetição, não no lugar dela.** Quadril caído é uma flexão
  que aconteceu e foi mal feita; rep rasa é uma flexão que não aconteceu. `HIPS_SAGGING` e
  `CRUNCH_TOO_FAST` acompanham o `rep.detected`; `PUSHUP_TOO_SHALLOW` e `CRUNCH_TOO_SHALLOW`
  substituem-no. É a distinção que os dois primeiros exercícios não precisaram fazer.
- **`HIPS_SAGGING` e `HIPS_PIKED` são dois códigos, não um com sinal.** O conserto é oposto
  ("contraia o abdômen" × "abaixe o quadril") e um código só obrigaria o texto a falar dos dois.
- **A flexão nunca lê fase inicial `PEAK`.** A referência da prancha é o próprio primeiro frame,
  então `depth` vale 1,0 por construção. Quem começa a captura no fundo perde **uma** repetição —
  troca deliberada, e é a que o contrato de `initial_phase` manda fazer ("rep fantasma é pior que
  rep perdida"). O abdominal não tem esse limite, porque a referência dele existe no frame 1.
- **Os dois nascem sem foto de demonstração.** `demo_img` vazio virou estado suportado: a tela
  desenha a **figura** do exercício em vez de apontar para um arquivo que não existe. Antes, um
  `src` vazio renderizava ícone de imagem quebrada. Trocar por foto depois é edição no painel.
- **Gerador com proporções próprias para o corpo deitado**, medidas no corpus (braço 1,15 torsos,
  perna 1,65 — contra 0,75 e 1,05 do boneco em pé). Não corrigi o boneco em pé: mexer nele muda
  toda fixture do polichinelo e do agachamento, e essa correção é a T-109.

### O que fica pendente, e o que precisa de decisão

- **`beta` está visível para todo mundo, porque a T-090 não existe ainda.** A SPEC-020 diz que
  `beta` só aparece com `is_admin`, mas a regra que lê `Plan.min_maturity` é a T-090, que está
  `todo`. Na prática, subindo assim, os dois exercícios aparecem no catálogo de qualquer usuário
  com o selo `beta` no payload e nenhuma tela mostrando esse selo (T-091 também `todo`). Foi a
  escolha consciente para permitir teste em produção; desfazer é um clique em `enabled` no
  painel, que é exatamente para isso que a coluna existe.
- **Nenhum vídeo real por trás dos limiares.** O guia de gravação dos dois exercícios já está em
  `eval/corpus/README.md`, com as três diferenças que importam (celular deitado, countdown na
  posição do exercício, calcanhar perto do quadril) e a nota sobre corpus público com `pushup`/
  `situp` já rotulados. Promoção a `calibrado` é a T-108.
- **Não testado em aparelho.** A verificação foi feita no navegador (catálogo, cards, Guia); o
  caminho câmera → worker com uma pessoa deitada de verdade é o que a T-108 vai exercitar.
- **`main_angle` continua `none` nos dois.** De lado, o ângulo do cotovelo é honesto e daria uma
  barra de métricas de verdade — mas o cliente só sabe desenhar abdução de braço, e ampliar a
  união é a Descoberta `[A/T-074]`, que já previa este momento.

**Gates:** `ruff check` + `ruff format` limpos; `pytest` verde (só `test_smoke::test_settings_leem_ambiente`
falha, e é contradição pré-existente entre o teste e o `conftest` — Descoberta `[A/T-106]`);
`npm run lint`/`typecheck`/`test` verdes (395 testes, incluindo o de figura da T-082, que passou
a cobrar as duas figuras novas); `evalctl` conta 12/12 nos dois exercícios pelo caminho da
bancada, com calibração.

---

## 2026-08-01 (21) · T-063 — o Free ganha limite, e o limite ganha uma tela honesta

Quota diária por plano no servidor (`429 quota_exceeded`), sheet de limite com contagem e hora
de renovação, e kcal ao vivo no HUD. Fecha os quatro critérios da Fase Inicial da SPEC-016 — e
é o primeiro produto a **consumir** o `Plan` que a T-073 deixou pronto sem ligar nada.

**O que muda para quem usa:** a conta Free passa a ter 10 sessões por dia (a "proposta inicial"
da spec), a 11ª é recusada pelo servidor, e a tela avisa **antes de a câmera abrir**. O card
CALORIAS deixa de ser `--` durante o treino.

**Decisões, e o que foi rejeitado:**

- **`trial.py` virou `quota.py`, e a regra ficou uma só.** A SPEC-018 §A já dizia o que fazer:
  *"a identidade do contado muda, a regra não"*. Um módulo chamado "trial" contando as sessões
  de quem tem conta seria o convite a escrever o segundo contador — e dois contadores da mesma
  regra divergem no dia em que só um for corrigido. A chave do visitante continua `trial:` e
  **não** foi renomeada: renomeá-la zeraria o contador de todo mundo no deploy, dando um dia
  grátis a mais justamente a quem já tinha esgotado.
- **O piso do código do Free é 10, não 0.** Escrevi `0` (ilimitado) primeiro, para "degradar
  sem travar ninguém", e é a escolha errada: um soluço de Postgres entregaria sessões
  ilimitadas a todo mundo, em silêncio, até alguém olhar a fatura da VPS. Piso é *"o produto de
  ontem"*, e o produto de ontem tem limite. Há teste cobrando que a constante e a linha do
  banco digam o mesmo número.
- **Rota nova (`GET /api/quota`) em vez de um campo no `GET /api/config`.** O config seria o
  lugar óbvio e seria um bug: aquela resposta é cacheada por ETag de (versão, plano,
  `is_admin`), e nenhum dos três muda quando o contador anda — o `used` congelaria no primeiro
  valor do dia e a tela diria "restam 7" para sempre. Número errado na tela é pior que número
  nenhum (SPEC-014).
- **O pré-voo não é a trava, e há teste disso.** A spec é explícita: *"a UI apenas reflete e
  vende o upgrade, nunca é a única barreira"*. `test_pular_o_pre_voo_nao_ajuda` e
  `test_limite_no_corpo_da_requisicao_e_ignorado` existem porque o critério 4 é o mais fácil de
  fingir que se testou — um teste do caminho normal prova que o caminho normal funciona, não
  que não há outro.
- **Dois códigos de recusa, não um.** `trial_exhausted` (crie conta, resolve hoje) e
  `quota_exceeded` (a conta é que chegou ao limite). Um código só obrigaria o cliente a olhar
  se há usuário para escolher a mensagem — e o servidor já sabe. Convidar quem já tem conta a
  criar conta seria um conselho impossível de seguir.
- **A hora de renovação é formatada no cliente, a partir do instante.** O servidor conta o dia
  em UTC; escrever "renova à meia-noite" mentiria para quem está no Brasil, onde o contador
  vira às 21 h. Mandar o `resets_at` e formatá-lo no navegador mantém as duas coisas
  verdadeiras — e a tela de fato exibiu `Renova amanhã às 21:00`.
- **Não há botão de assinar.** A spec pede o CTA "ainda sem checkout — lista de espera/em
  breve", e um botão que não leva a lugar nenhum seria a primeira afordância inventada de um
  app cuja regra é mostrar `--` quando não há dado. Enquanto o checkout não existe, o convite é
  uma frase.
- **Kcal ao vivo não contradiz "a UI nunca mostra número inventado".** A regra proíbe número
  que o servidor não forneceu — e é por ela que FC continua `--`. Aqui os dois insumos que
  decidem o resultado vêm de fora do cliente: o MET é dado do catálogo servido (T-074, editável
  no painel) e o tempo é o da sessão que o servidor admitiu. O que o cliente põe de si é o
  peso, e ele entra marcado como `estimado` justamente por ser a única parte que não sabemos.
  **Sem MET não há conta e não há número** — volta `--`, sem a ressalva.
- **`message` vazio quando o plano é ilimitado.** Achado ao ler o corpo do assinante no `curl`:
  a resposta carregava "suas sessões de hoje acabaram" para quem não tem limite. Frase falsa
  esperando um consumidor descuidado que a exiba.

**Corrigido no navegador, não no editor:** o chip do Perfil dizia `0 de 10 hoje` (restantes) ao
lado do bloco que dizia `10 de 10 sessões de hoje` (usadas) — dois significados para a mesma
forma, na mesma tela. Só apareceu com a conta esgotada na tela real; virou `restam 0`.

**Verificação no stack real** (containers `digital-fit`, conta criada pela própria API):

| O que | Como | Resultado |
|---|---|---|
| Critério 1 — a 11ª é recusada | 11 `POST /api/sessions` numa conta Free nova | 10× `201` (`used` 1→10), a 11ª `429 quota_exceeded` |
| Critério 1 — antes da câmera | clicar "Iniciar Exercício" com 10/10 no app | sheet abriu, `video.srcObject` **nulo**, rota ficou na pré-config |
| O texto que a pessoa lê | DOM da folha de conta | "Você treinou muito hoje 🎉" · "10 de 10 sessões de hoje" · "Renova amanhã às 21:00" |
| Critério 2 — assinante | trocar o plano da MESMA conta esgotada e repetir | 3× `201`, `unlimited: true`, contador parado em `10` |
| Critério 4 — forjar o cliente | `X-Device-Id` novo + `daily_sessions: 999` no corpo | `429` — a chave da conta não tem aparelho dentro |
| Critério 4 — pular o pré-voo | `POST` direto, sem `GET /api/quota` | `429` |
| Chave e prazo do contador | `redis-cli` | `df:quota:{id}:2026-08-01` = `10`, TTL 172 706 s (48 h) |
| Critério 3 — MET real na mão do cliente | ler o catálogo servido no `localStorage` | polichinelo `met 8` → 4,9 kcal/30 s; agachamento `met 5` → 3,1 |
| Critério 3 — o card no HUD | rota `#/treino` no navegador | `0,0 kcal` + `estimado` — prova que o MET servido chegou ao componente |
| Critério 3 — sem MET, `--` | `docker compose stop api` + catálogo local apagado | `-- kcal`, **sem** a ressalva "estimado" |
| Custo do pré-voo | `performance.getEntriesByType('resource')` | 3 chamadas no boot — o mesmo que o `GET /api/config` que já existia |

O que **não** foi observado ao vivo: o kcal subindo durante uma sessão de verdade. O navegador
controlado não tem câmera, então o HUD foi visto com a sessão parada (`0,0`) — o que prova a
ligação (MET servido → componente), não o movimento. A fórmula tem teste de unidade com o
número conferido à mão; o movimento fica para o próximo teste no celular.

Gates: `ruff` limpo, `pytest` 678 verdes (+16), `npm run lint`/`typecheck`/`test` verdes (395,
+18), `makemigrations --check` sem drift, `manage.py check` com o painel ligado sem issues.

**Pendências e efeitos colaterais:** o banco de dev ficou com ~27 sessões de verificação, três
contas `t063-*` e a versão de configuração em `6` (o contador só anda para frente). Nenhuma
tela soma kcal entre sessões — conferido por busca em `ProgressScreen`, `AnalyticsScreen` e
`report/`, e garantido por construção: `session/kcal.ts` não tem estado. O acúmulo é capacidade
de assinante (`kcal_accumulation` no `Plan`) e é a T-064, junto com o peso real da T-065 —
enquanto ele não chega, os 70 kg continuam premissa declarada na tela.

## 2026-07-31 (20) · T-075 — o relatório passa a dizer sob qual configuração a sessão nasceu

`session.started` ganha `config_version` (aditivo, default `0`), a API carimba a versão que
valia na admissão, e o `SessionResult` guarda o carimbo. Fecha o critério 8 da SPEC-018 — o
último em aberto da Fase Inicial dela.

**A pergunta que este campo responde** é de suporte, não de produto: "este treino rodou antes ou
depois de eu mexer na configuração?". Até aqui a resposta era cruzar o horário do `LogEntry` do
painel com o `created_at` do relatório no olho. Agora é uma coluna, e o painel filtra por ela.

**Decisões, e o que foi rejeitado:**

- **Carimbo, não consulta.** O relatório copia a versão que veio no evento; nunca lê
  `SiteConfig` na hora de gravar. Ler o banco pareceria certo em todo teste feito no mesmo
  minuto e mentiria sobre toda sessão de ontem — e quebraria a promessa da SPEC-010 (relatório
  derivável 100% por replay, o mesmo motivo pelo qual o worker não tem ORM).
- **`config_version` sai de `caps` sozinho, sem parâmetro.** Duração e countdown são escolha da
  admissão (o cliente pede, o plano limita) e por isso viajam como argumento explícito. A versão
  não é escolha, é **procedência** da resolução que produziu `caps`. Fosse mais um parâmetro,
  esquecê-lo carimbaria `0` numa sessão cuja config veio do banco — e o relatório mentiria em
  silêncio, que é o defeito que o campo existe para eliminar.
- **Valor torto vira `0` em vez de derrubar o evento.** Um `_as_int` estrito recusaria o
  `session.started` inteiro, levando junto **exercício e modo** — que é o que o relatório de
  fato precisa. Metadado não pode custar o relatório; mesma escolha já feita para o countdown.
- **`0` significa "não registrada", e cobre três casos de propósito**: sessão anterior a esta
  task, builder que subiu no meio da sessão (não viu a abertura) e configuração fora do ar na
  admissão (P2). Nos três a resposta honesta é a mesma; carimbar a versão de agora seria pior.
- **Nenhuma tela do usuário mostra o número.** A SPEC-014 é vinculante para a UI e não pede
  número novo lá; quem pergunta é o operador, no painel. O tipo do cliente ganhou o campo mesmo
  assim, porque `sessionReport.ts` se declara espelho do `to_report()` — e espelho com campo
  faltando é o `[A/T-051]` recomeçando.

**Verificação no stack real** (containers `digital-fit`; o `df-teste` da sessão paralela seguiu
de pé nas portas +10):

| O que | Como | Resultado |
|---|---|---|
| Carimbo no evento | `POST /api/sessions` e ler `events.analysis` no Redis | `{… 'countdown_s': 3, 'config_version': 4}`, com `SiteConfig.version = 4` |
| Uma edição no painel entre duas sessões | salvar o plano `anon` (bump 4 → 5) e abrir a segunda | os relatórios saíram `config_version = 4` e `= 5` |
| O carimbo é do passado | com o banco já em `5`, reler o relatório da sessão antiga | continuou `4` |
| Migration | `migrate` → `migrate 0008` → `migrate` no Postgres do compose | aplica **e reverte** limpa |
| Painel | `manage.py check` com `DJANGO_ENABLE_ADMIN=1` + o teste que abre a changelist | sem issues, 200 |

Gates: `ruff` limpo, `pytest` 662 verdes, `npm run lint`/`typecheck`/`test` verdes (377),
`makemigrations --check` sem drift. **Sem passada de navegador**: a mudança no cliente é uma
linha de tipo (apagada na compilação) e nenhuma tela lê o campo — não havia o que observar lá
que o `curl` no stack real não tenha mostrado melhor.

**Pendências:** a Fase Inicial da SPEC-018 está inteira — critérios 1…11 cobertos. Ficaram no
stack de dev duas sessões de verificação e a versão de configuração em `5` (o contador só anda
para frente; desfazê-lo seria mentir para ele).

## 2026-07-31 (19) · T-074 — o catálogo passa a ter dono, e a admissão passa a travar

`Exercise` + `ExerciseGuideStep` no painel com a trava de slug, `exercises_for()` como
resolvedor único, `GET /api/config` servindo catálogo e capacidades, e o cliente consumindo. É
o fim do `[A/T-051]`: "o catálogo do cliente e o registro do servidor podem divergir sem
ninguém ver".

**A descoberta mais incômoda veio antes de codar**: `POST /api/sessions` não travava **nada**
além de `exercise in EXERCISES`. Desligar um exercício no painel o tiraria da tela e deixaria a
porta aberta para quem chamasse a API direto. A T-074 original nem mencionava admissão — foi a
revisão da Fase 0 que a colocou no escopo, e ela era mesmo o buraco.

**Decisões, e o que foi rejeitado:**

- **Um resolvedor, duas perguntas.** `exercises_for()` serve o catálogo *e* a admissão. Duas
  listas montadas por dois códigos divergiriam do pior jeito: um card na tela que o
  `POST /sessions` recusa. O teste central percorre o que o `GET /api/config` devolveu e abre
  sessão de cada um — se divergirem, ele quebra.
- **Degradação assimétrica, de propósito.** Sem catálogo no banco, `exercises_for` devolve o
  registro de código (comportamento de ontem). Mas a exclusividade por plano falha **fechada**:
  `min_plan` sem ordem resolvível some. Fechar tudo esvaziaria a tela Escolha num soluço de
  banco; abrir a exclusividade entregaria conteúdo pago. Cada lado falha para o lado certo dele.
- **O servidor SUBSTITUI o catálogo do cliente, não completa.** Exercício que o servidor não
  listou está desligado ou fora do plano; mantê-lo por herança do embutido recriaria exatamente
  o card que a admissão recusa.
- **Lista vazia quer dizer "não sei", não "não há exercício".** É o que o servidor manda com o
  banco fora, e o cliente guarda `null` em vez de `[]` — guardar `[]` apagaria a tela Escolha
  por causa de um soluço. Card em branco seria pior que card nenhum.
- **Categoria virou slug na migration, convertida e não copiada.** O cliente guardava `'Cardio'`
  e `'Força'` (strings de exibição); o rótulo agora é derivado por `categoryLabel()`. Copiar
  quebraria as conquistas da SPEC-019 e o mix da SPEC-022 em silêncio.
- **403 e não 404 na recusa por plano**: o exercício existe, o acesso é que não. E não 400,
  porque o corpo da requisição está correto — mudou a permissão, não a sintaxe.
- **`slug` vira somente-leitura depois de criado.** O `clean()` pega slug inexistente, mas não
  pega um slug VÁLIDO trocado por outro slug VÁLIDO — que é como se perde a ficha de um
  exercício, sem erro nenhum na tela.

**Dois defeitos que só o navegador mostrou** (e que `curl` e teste com `fetch` dublado
aprovavam):

1. **O `ETag` nunca chegava ao JavaScript.** Cross-origin, `resposta.headers.get('ETag')` volta
   `null` sem `Access-Control-Expose-Headers`. Medido: `localStorage` ficava vazio depois de
   três buscas bem-sucedidas. Sem erro nenhum — só o payload inteiro descendo para sempre. O
   CORS ganhou `Expose-Headers: ETag` e `If-None-Match` na lista do preflight, com dois testes.
2. **O ETag era decoração mesmo depois disso.** O `If-None-Match` só saía se houvesse catálogo
   em memória (senão um 304 deixaria o app sem catálogo) — e no boot o store nasce vazio, então
   nunca saía. A correção é hidratar do `localStorage` antes de falar com a rede: boot lê o
   disco, revalida, e o caso comum custa uma resposta sem corpo. Medido no navegador: 1954 bytes
   → `304`.

Também medido: o boot fazia **duas** buscas de config porque o efeito dependia de
`account.status`, que muda `unknown → anonymous` sem o plano mudar. Passou a depender do **id**
da conta — que no boot anônimo não muda, e na troca de conta muda.

**Verificação no stack real** (containers `digital-fit`, com o `df-teste` da sessão paralela
rodando em paralelo nas portas +10):

| O que | Como | Resultado |
|---|---|---|
| CA 3 da SPEC-018 + a metade que faltava | desligar `squat` no painel e chamar a API | catálogo encolheu para `['jumping_jack']` e `POST /sessions` devolveu **403 `exercise_unavailable`**, sem restart |
| Headers da resposta | `curl -i` | `ETag`, `Cache-Control: private, must-revalidate`, `Vary: Authorization` |
| Revalidação | `curl -H "If-None-Match: …"` | `status=304 bytes=0` |
| Painel → tela | renomear `squat` e recarregar o app | card passou a ler "Agachamento livre / Pernas, glúteos e core" |
| Rótulo de categoria | ler o DOM | `cardio → Cardio`, `forca → Força` |

Os dados de dev que mexi para medir foram restaurados ao final.

Gates: `ruff` limpo, `pytest` 644 verdes, `npm run lint`/`typecheck`/`test` verdes (377).
**Screenshot não foi possível** — trava neste browser controlado (quirk conhecido); tudo acima
foi medido por JS no DOM e por `curl`, que é o caminho que este projeto já usa.

**Pendências:** critérios 3, 4, 10 e 11 da SPEC-018 agora estão cobertos; o 8 (`config_version`
no relatório) segue com a T-075. Duas descobertas no BACKLOG: figura de pose de exercício que só
existe no servidor, e a divergência silenciosa entre o `main_angle` aberto do servidor e o
fechado do cliente.

## 2026-07-31 (18) · T-073 — configuração de negócio vira dado, sem mudar produto nenhum

`Plan` + `SiteConfig` + `User.plan/plan_until` + `capabilities_for()`, e a admissão passando a
resolver quota, duração, countdown, TTL e cloud por eles. A prova de que a task deu certo é
**nada ter mudado**: 623 testes verdes, e vários deles comparando o valor resolvido com a
constante que existia antes.

**Escopo travado antes de codar.** Entrou: os dois modelos, as duas telas de painel, o
resolvedor com cache, a migration de dados e a ligação na admissão. Não entrou: `Exercise` e
`GET /api/config` (T-074), `config_version` no evento (T-075), quota do Free e faixa de duração
do assinante (T-063/T-064), `FeedbackMessage` (Evolução da SPEC-018).

**Decisões, e o que foi rejeitado:**

- **`free.daily_sessions = 0` (ilimitado) na migration.** Hoje conta logada não tem quota
  nenhuma; a SPEC-016 propõe 10/dia e quem liga é a T-063. Entregar o limite novo já na
  migration faria a T-073 mudar o produto no dia do deploy, escondida atrás de "só
  infraestrutura". O teste `test_conta_logada_continua_sem_quota` existe para segurar isso.
- **O piso do código é por plano, não global** (`_FLOOR_PLAN`). Com o banco fora, o anônimo
  precisa cair em 3 sessões e na mensagem do trial — um piso único devolveria "ilimitado" para
  o visitante e abriria o funil inteiro justo quando o banco está ruim.
- **`capabilities_for` não levanta exceção, e o `except Exception` largo é intencional.** É o P2
  escrito como fluxo de controle: cache fora → consulta direta; banco fora → constante de
  ontem. A alternativa (deixar subir) é derrubar um treino por causa de configuração.
- **Expiração de assinatura resolvida na leitura, não por job.** Um cron que rebaixasse contas
  seria um segundo lugar onde o plano é decidido, e o dia em que não rodasse ninguém notaria.
- **O bump da versão usa `queryset.update()`.** `instance.save()` dispararia `post_save` de
  novo — a diferença entre um contador e um laço. Tem teste (`..._nao_entra_em_laco`).
- **Snapshot do catálogo inteiro de planos, não de um plano.** São três linhas e a consulta é a
  mesma; assim trocar o plano de uma conta não precisa de invalidação própria — o que muda é o
  ponteiro no `User`, lido a cada requisição.
- **TTL de 5 min no snapshot além do signal.** O signal é o caminho normal; o TTL é a rede para
  o que ele não cobre — `manage.py shell` com `.update()`, que não dispara `post_save`.
- **Plano não se apaga pelo painel.** `User.plan` é `SET_NULL`: apagar o `free` esvaziaria
  contas em silêncio, sem erro na tela. E `slug` vira somente-leitura depois de criado, porque
  o resolvedor procura `anon` por nome — renomear faria tudo cair no piso sem ninguém ver.
- **`CloudSlots` ganhou `grace_ms` como parâmetro** (default = a constante). O worker continua
  sem saber que existe banco (ADR-008); quem resolve capacidade é a API e passa o número.

**Medições e verificações (critérios da SPEC-018, um a um):**

| # | Critério | Como foi verificado |
|---|---|---|
| 1 | mudar `daily_sessions` vale sem restart | `test_editar_o_plano_no_painel_muda_a_admissao_sem_restart` — POST no formulário do painel → `capabilities_for` já devolve o novo valor |
| 2 | Postgres/Redis fora e a sessão ainda nasce | `test_banco_fora_do_ar_nao_levanta_e_devolve_o_piso` + `test_cache_fora_do_ar_cai_para_o_banco` (derrubados de propósito) |
| 5 | painel não responde no gateway | coberto pela T-072, ainda verde |
| 6 | só `is_staff` entra | coberto pela T-072, ainda verde |
| 7 | auditoria com autor e data | `LogEntry` conferido na edição de `Plan` |
| 9 | suíte com config vazia | `test_plano_apagado_da_tabela_cai_no_piso_do_proprio_slug` |

Gates: `ruff check` limpo, `pytest` 623 verdes, `manage.py check` sem issues,
`makemigrations --check` sem drift, e as migrations 0005/0006 aplicam **e revertem** limpas.
`web/` não foi tocada (nem podia: há alteração de UI em paralelo), então os gates do npm não
se aplicam. **Não abri o painel no navegador** — as telas novas são exercitadas por requisição
(`GET` 200 na lista e no change de `Plan` e `SiteConfig`), que é o que a lição do
`ContaCreateForm` da T-072 pedia, mas não é a mesma coisa que olhar.

**Pendências:** critérios 3, 4, 8, 10 e 11 da SPEC-018 são T-074/T-075 e continuam abertos.
Duas descobertas no BACKLOG: o dublê `admissao_falsa` que engole os kwargs da view (armadilha
para a próxima task que acrescentar argumento) e `Plan.history_limit`, coluna que existe e
ninguém lê ainda — é da T-064.

## 2026-07-31 (17) · Fase 0 da Fase 5 — revisão das SPEC-019…022 e reescrita de T-073/T-074

Alinhamento antes de codar: revisar as 4 specs em `draft` e garantir que o escopo do admin
(T-073/T-074) carrega o contrato que M1…M4 vão consumir. As quatro passaram a `approved`.
Comecei conferindo o código em vez de confiar no texto — duas premissas do BACKLOG caíram e duas
se confirmaram.

**Verificado (e o que mudou por causa disso):**

- `SessionResult.exercise` **já existe** (`server/api/models.py`). Confirma "T-055 ajuda mas não
  bloqueia": conquista `centena`, progresso de trilha e item do treino do dia estão de pé sem ela.
- O report-builder é `python manage.py report_builder` (compose). Confirma a aposta da SPEC-019 de
  que o `post_save` de `SessionResult` dispara num processo com ORM e Redis compartilhado.
- **`POST /api/sessions` não trava nada** além de `exercise in EXERCISES` (`sessions.py`). Não
  havia gancho de `enabled`/plano em lugar nenhum, e T-074 não mencionava admissão — mas o CA 3 da
  SPEC-018 a exige e o T-090 a pressupunha. Virou escopo explícito da T-074.
- **O `Plan` não tinha onde guardar 3 capacidades** que as specs já haviam atribuído a ele.

**Decisões (com as alternativas rejeitadas):**

- **Todas as colunas novas em T-073/T-074, não nos marcos.** `Plan` +
  `streak_protections_month`/`min_maturity`/`daily_workout`; `Exercise` + `met`/`maturity` e
  `category` como *choices*. Rejeitado "cada marco traz a sua": seriam 4 migrations e o
  `GET /api/config` mudaria de forma duas vezes depois de o cliente já lê-lo. O preço aceito é
  T-073/T-074 maiores, carregando coluna que só é usada depois — o comportamento continua com a
  spec dona.
- **`category` é código, não dado editável — a SPEC-018 cedeu para a SPEC-020.** A 018 a listava
  como apresentação; mas conquistas (019) e o mix por objetivo (022) consomem os *slugs*. Pior, a
  coluna nasce na T-074 populada com as strings de exibição de hoje (`'Cardio'`, `'Força'`): a
  migration **converte**, não copia, senão o primeiro consumidor a agrupar não acha nada.
- **`GET /api/config` é privado e o ETag precisa saber.** Com a SPEC-020 o payload varia por plano
  (o assinante vê o Laboratório). ETag só sobre `config_version` faria um proxy servir a resposta
  do assinante para o próximo Free — vazamento silencioso que fura o CA 1 da 020. Ficou
  `Cache-Control: private` + ETag por (versão, plano, `is_admin`).
- **XP só lê `SessionResult`.** O bônus "+15 meta batida" (019) e o "+25 treino do dia" (022) liam
  perfil **mutável**: trocar a meta ou o objetivo reescrevia quais dias passados contavam, e o XP
  histórico saltava sozinho — contradizendo, no único lugar onde importa, a promessa de
  recomputabilidade da 019. Rejeitado persistir a meta vigente por dia (primeiro estado
  não-derivável da spec, comprado por um bônus cosmético). A meta continua como anel do dia e
  gatilho de conquista; o treino do dia mantém a conquista `treino-do-dia-7`. Se um dia o bônus
  for necessário, o caminho é `daily_workout_done(user, date)` persistido — está na Evolução.
- **A chave de cache do engajamento leva a data**: `df:eng:{user}:{data_sp}`, TTL até a virada.
  Uma chave sem data só é invalidada por sessão nova, mas o payload muda **sozinho à meia-noite** —
  quem treinou 23h50 veria o fogo de ontem até treinar de novo, isto é, até deixar de precisar.
- **Downgrade nunca apaga fogo antigo** (regra do piso: `max(plano_atual, free)` para dias fora do
  mês corrente). Sem isso, vencer a assinatura derrubava proteções de 2 para 1 e um fogo de 40 dias
  virava 12 — churn produzido pela própria mecânica de retenção, no momento da renovação.
- **Trilha v1 aceita passo `calibrado`.** Com `validado`, os 4 do Lote 1 (que nascem `beta` e o
  T-096 leva só a `calibrado`) nunca abririam: a Fundamentos fecharia o M2 com 4 de 6 passos
  trancados para sempre — a "meia-mecânica no ar" que a Fase 5 proíbe por escrito. `beta` segue
  fora. Consequência registrada na spec: no M2 a Fundamentos do **Free** é curta (Laboratório é
  benefício de assinante), e por isso a tela precisa distinguir cadeado de progressão de cadeado
  de plano.
- **`PROTOCOL_VERSION` não sobe na SPEC-021** — decidido na spec em vez de deixar para a task. A
  mudança é aditiva nos dois lados; subir por mudança aditiva treina o projeto a ignorar o número.
- **Grandfathering declarado**: `jumping_jack` e `squat` nascem `validado` por decisão, não por
  medição (o squat nem corpus tem — T-053). Aplicar o critério retroativamente deixaria o Free sem
  exercício nenhum no dia da T-074. Está escrito na SPEC-018 para ninguém ler o selo como evidência.

**Pendências geradas:**

- **T-104** (nova): `manage.py exercise_health` — `validado` exige taxa de zero-rep < 20% e o
  instrumento não existia; sem ele, promoção de maturidade é opinião. Serve também para rebaixar.
- A SPEC-018 continua `draft` embora a T-072 já esteja `done` e T-073/074 sejam dela. Vale uma
  passada de status próprio.
- A dívida do grandfathering tem nome e dono: T-053 (corpus do agachamento) e a passada manual
  pendente da T-040 (paridade edge×cloud×browser).

## 2026-07-30 (16) · docs+skills — O novo rumo vira documentação oficial e skills de agente

Continuação da sessão (15): o Daniel pediu para **finalizar a documentação** assumindo a Fase 5
como o rumo do projeto, e criar **skills** que orientem agentes a executar cada spec/task com
entrega confiável e testável.

- **ARCHITECTURE.md v0.3**: §1 ganhou o "Rumo atual" (as duas teses: fábrica de exercícios
  com maturidade mensurável; engajamento como derivação, não estado) e §9 ganhou as Fases 4
  (entregue) e 5 (os 4 marcos M1–M4 com raias e pré-requisitos).
- **context/project.md**: rumo no topo, specs 018–022 na tabela de entidades, skills na lista
  de documentos — é o arquivo que toda sessão lê primeiro, então o rumo mora nele.
- **context/conventions.md**: duas seções novas com força de convenção — "Derivação"
  (derivação pura, fuso SP do engajamento vs UTC da quota, `XP_FORMULA_V`, cache nunca é
  fonte) e "Exercícios & maturidade" (checklist, escada, feature importada nunca copiada,
  "o eixo Z mente").
- **Skills em `.claude/skills/`** (versionadas no repo — viajam com o projeto e qualquer
  agente Claude Code as descobre):
  - `df-executor` — executa T-XXX: contexto mínimo na ordem certa, escopo travado ANTES de
    codar (Entra/Não entra/Descobertas), critérios de aceite viram testes ou verificações
    medidas, gates obrigatórios, DEVLOG com decisões, commit. Inclui a lista "O que NUNCA
    fazer" (antecipar Evolução, done com gate vermelho, segundo escritor do Postgres, mexer
    em limiar calibrado fora de task de calibração, número inventado em tela).
  - `df-exercise` — a fábrica: classificação por tier antes de codar, checklist DoD da
    SPEC-020 em 7 passos com caminhos reais, comandos do `evalctl`, escada de maturidade com
    evidência exigida por promoção, anti-padrões ("calibrar na própria webcam é beta").
  - `df-spec` — o padrão da casa em 8 regras (Fase Inicial mínima, decisões com dono e
    alternativa rejeitada, critérios mensuráveis, honestidade de UI, derivação primeiro, as
    três naturezas de configuração, eventos aditivos, orçamento da VPS) + desdobramento em
    tasks com raias e marcos funcionais.
- **AGENTS.md** aponta as skills como a forma operacional do fluxo (o fluxo manual continua
  sendo a fonte); **prompts/executor.md** marcado como superseded para agentes com skills;
  **README** ganhou o parágrafo de skills e do rumo.
- **Decisão**: skills no repo (`.claude/skills/`) e não em `~/.claude` — orientação de agente
  é parte do projeto, versiona com ele e vale para qualquer máquina/agente que clonar.
- **Pendências**: nenhuma nova; as da sessão (15) seguem (revisão das specs em draft).

## 2026-07-30 (15) · SPEC-019…022 — Do MVP ao produto de retenção (o "foguinho" e a fábrica de exercícios)

Sessão de projeto, não de código. Pedido do Daniel: pensar o produto à la Duolingo — recursos
crescentes por role (deslogado/free/assinante), uso diário ("foguinho"), seções/categorias, e
a lista de exercícios do mais fácil ao mais difícil sabendo que os difíceis pedem mais teste.
Saíram 4 specs (draft, aguardando revisão dele uma a uma) + a Fase 5 no BACKLOG (T-086…T-103,
4 marcos, 3 raias paralelas).

- **SPEC-019 Engajamento**: fogo/meta/XP/conquistas como **derivação pura** de
  `SessionClaim`+`SessionResult` — nenhum worker novo, nenhum contador para dessincronizar,
  ADR-008 intacto. Decisões com dono: virada do dia em America/Sao_Paulo fixo (diverge da
  quota da 016, de propósito — meia-noite UTC é 21h no Brasil e mataria a mecânica); fogo ≠
  meta (fogo = 1 sessão válida, meta é pessoal — meta agressiva não pode queimar constância);
  proteção de streak é **regra derivada** (N dias perdoados/mês), não item de inventário;
  sessão de 0 reps não conta nada (anti-farm); XP com bônus de execução limpa — o que o
  Duolingo não tem e o feedback engine dá de graça. Fogo fantasma do anônimo em localStorage +
  **adoção das SessionClaim do device no cadastro** (o fogo e o histórico sobrevivem à conta —
  a promessa do README vira literal).
- **SPEC-020 Catálogo**: o insight organizador é **dificuldade física ≠ dificuldade de
  detecção** — o roadmap ordena pelo eixo técnico em tiers (A: em pé/frontal/cíclico → A2:
  salto/assimetria → B: isométrico → C: chão → D: composto), e cada tier é uma capacidade do
  motor que destrava um LOTE. Escada de maturidade mensurável pela bancada
  (`beta`→`calibrado`→`validado`), Laboratório 🧪 = assinante beta-tester que gera corpus.
  Lote 1: marcha, elevação de braços, high knees, sumô (dois reusam features existentes).
  Trilha Fundamentos com progresso derivável (sem tabela de progresso).
- **SPEC-021 Isométricos**: modalidade `hold` (relógio de tempo válido com histerese, soma
  trechos, `degraded` congela, `hold.progress` no contrato, colunas aditivas no
  `SessionResult`). Primeiro exercício: wall sit — reusa a altura de quadril do squat, adia a
  prancha (hold+chão misturaria duas novidades). Habilita o "dia leve" que guarda o fogo.
- **SPEC-022 Treino do Dia**: seleção diária determinística (seed usuário+data) por objetivo,
  com ajuste de baixo impacto por idade/IMC declarados — personalização de treino, nunca
  prescrição de saúde. Assinante completo; Free vê as categorias do dia como teaser honesto.
- **Pendências geradas**: as 4 specs em `draft` esperam a revisão do Daniel; a Fase 5 depende
  de T-073/T-074 (Plan + catálogo servido) para o M2 e de T-063/T-064 para o gate do M4.
  Missões, ligas e push ficaram explicitamente em Evolução (cada um tem custo próprio).

## 2026-07-30 (14) · T-085 — Aviso de cena: o que a pessoa não vê do outro lado do celular

Pedido do Daniel na mesma conversa do probe: "celular a gente sempre suja a câmera, deixa
iluminação baixa e tal" — um aviso que orienta, **não impede**, e só na tela de Início, onde a
câmera já abre para teste antes de ir treinar.

- **Escopo travado antes de codar**: orienta e nunca bloqueia (o CTA não muda); só na
  pré-configuração; um canal só — o pill que já existe dentro da janela da câmera, que passa a
  mostrar o conselho no lugar da dica de enquadramento enquanto ele valer. Enquadramento a
  silhueta-guia já ensina sozinha; luz e lente suja são o que ninguém enxerga de onde está.
- **Roda no cliente porque SÓ pode rodar lá**: no modo edge nenhum pixel sobe (keypoint-first),
  então o servidor não tem o que olhar. Amostra de 160×120, 1×/s, num canvas fora do DOM —
  ~19k pixels contra as 15 inferências de pose por segundo que rodam no mesmo vídeo.
- **Os limiares saíram de medição, e a medição mudou o desenho duas vezes.** Sem corpus de cena
  ruim (o Daniel não quer gravar agora), o que deu para fazer foi medir os 3 vídeos do
  `eval/corpus` como estão e em variantes sintéticas (escurecidas ×0,25, borradas com boxblur 6)
  via ffmpeg, com exatamente as contas do cliente:

  ```
  vídeo            luz    estourado  varLaplaciano
  01 como está    244,6      92,8%          1792
  01 escurecido    60,9       0,0%           119
  01 borrado      244,7      89,2%           173
  02 como está    136,7       0,0%          2627
  02 borrado      136,7       0,0%           373
  03 como está    124,4       0,6%          2003
  03 borrado      124,2       0,6%           559
  ```

  - **Normalizar o laplaciano pelo contraste não serve para comparar cenas.** Era o meu plano
    inicial, porque a razão `varLap/contraste²` é imune à luz (o vídeo 01 vai de 1,32 a 1,40 ao
    ser escurecido). Só que entre cenas ela é inútil: o vídeo 03 **nítido** dá 0,15 e o vídeo 01
    **borrado** dá 0,16 — o limiar reprovaria a cena boa. A nitidez passou a usar o laplaciano
    cru, com **luz boa como pré-condição** — que é o que impede confundir escuro com borrado,
    já que escurecer também derruba o laplaciano (1792 → 119).
  - **Estouro alto não é contraluz.** O vídeo 01 tem 92,8% de pixels saturados e é cena BOA:
    fundo claro com a pessoa bem iluminada (o centro mede 244 também). Contraluz é fundo claro
    com sujeito ESCURO — a regra passou a olhar o centro do quadro, onde a silhueta-guia põe o
    corpo. Sem isso, o primeiro vídeo do corpus levaria um aviso errado.
- **Debounce de 2 amostras para acender E para apagar** (SPEC-003 pede 1s para ligar; nós
  amostramos 1×/s): alguém passando na frente da luz não dispara nada, e uma amostra boa solta
  não apaga um aviso que continua valendo.
- **A mensagem não afirma a causa.** Imagem sem detalhe pode ser lente suja, foco errado ou
  pouca luz; "Imagem sem nitidez · limpe a lente" pede a ação que resolve os três e custa 5
  segundos. Frases do tamanho da que já vive no pill (38 caracteres) — ele mora dentro da janela
  de 202px, e um parágrafo ali viraria outro problema.
- **Testes**: 15 novos em `sceneQuality.test.ts`, com os dois casos do corpus virando teste —
  "estouro alto com centro claro NÃO é contraluz" e "no escuro a queixa é a luz, nunca a
  nitidez". Mais parede lisa não virando acusação de lente suja.
- **Gates**: lint, typecheck e 360 testes verdes.
- **Não verificado**: a aparência do aviso em aparelho real. A extensão do browser caiu no meio
  da sessão, então a checagem visual (e o disparo com câmera de verdade) fica para o teste no
  celular. O risco de layout foi tratado na origem, encurtando as frases.
- **Pendências** (em Descobertas): faltam corpus de cena ruim e as métricas dentro do `evalctl`
  para o limiar sair da bancada e não de um script solto; e o aviso não é anexado ao relatório,
  que é o que a SPEC-003 pede para todo warning — sem isso a cena real dos usuários é invisível.

---

## 2026-07-30 (13) · T-084 — O probe media a câmera e culpava o aparelho

Relato do Daniel: iPhone bom, câmera boa, e o app escolhendo CLOUD quase sempre. A causa
estava numa linha do `measureProbeFps`:

```ts
if (video.currentTime !== lastVideoTime) { detectPose(...); frames += 1 }
probeFps = frames * 1000 / elapsed
```

- **O número só sobe quando chega frame novo.** Ou seja, `probeFps = min(fps da câmera,
  throughput do modelo)` — e no iPhone quem ganha essa disputa costuma ser a câmera: com pouca
  luz o iOS alonga a exposição e entrega 12–15fps. O probe lia 12, comparava com o limiar de 12
  e reprovava o APARELHO por causa da iluminação da SALA. `frameRate: {ideal: 30}` é dica, não
  garantia.
- **E o remédio era pior que a doença.** Cloud analisa JPEG de 320px a 10fps: cena escura fica
  PIOR lá, não melhor. Fora que são 3 vagas no semáforo (SPEC-009) — telefone capaz ocupando
  slot é slot faltando para quem precisa. Fica a regra: **cena ruim nunca é argumento para
  trocar de modo; é argumento para consertar a cena.**
- **A régua nova é latência**: mediana de ms por `detectForVideo`, que não depende da cadência
  da fonte. `fpsSustentavel = 1000 / mediana`. As 3 primeiras inferências saem da conta
  (compilação de shader chega a centenas de ms cada) e a janela estica de 2s para até 3s
  enquanto não houver 8 amostras — antes de estimar capacidade com quatro amostras, esperar
  mais 1s é barato.
- **Duas medidas, dois nomes.** A cadência da câmera continua medida, agora via
  `presentedFrames` do rVFC — contador do COMPOSITOR, que continua andando quando pulamos
  frames. Contar as nossas chamadas mediria o nosso gargalo e chamaria isso de "câmera lenta".
  Onde não há rVFC o número vira um piso, e o `cameraFpsSource` diz isso na cara: o aviso de
  cena da T-085 não pode acusar luz fraca em aparelho devagar.
- **O laço passou a ser o mesmo do pipeline** (`createVideoFrameLoop`, rVFC — como a SPEC-001
  já pedia). O probe tinha um `requestAnimationFrame` próprio, que é cadência de REPAINT: ele
  media o modelo através do compositor, e a tela onde o probe roda é a pré-configuração, com
  grade, varredura e — desde a T-080 — quatro painéis de desfoque sobre vídeo ao vivo.
- **Watchdog obrigatório junto do rVFC**: sem frame de câmera o callback nunca dispara e a
  promessa nunca resolveria — o app ficaria preso em "calibrando o dispositivo", sem erro e sem
  saída. Tem teste.
- **`sem_medida` agora vale EDGE, não CLOUD.** Ausência de evidência não é evidência contra: sem
  frame de câmera não há o que mandar ao servidor tampouco, então cloud não remedia esse caso.
  Falha COM exceção continua indo para cloud, onde o servidor é alternativa real. Mudança de
  regra registrada na SPEC-001.
- **Motivo da decisão exposto** (`probe_ok`, `probe_lento`, `sem_webgl`, `sem_simd`,
  `probe_falhou`, `sem_medida`) e visível no chip de diagnóstico junto dos dois fps. Sem isso,
  "meu aparelho vai para cloud" não tinha diagnóstico possível em campo.
- **Bug pequeno, efeito grande no iOS**: `detectWebgl()` criava um canvas, pegava contexto WebGL
  e nunca o devolvia. Roda a cada montagem do pipeline (parar/iniciar câmera, entrar e sair do
  treino), e o Safari de iPhone tem orçamento apertado de contextos vivos — contexto vazado aqui
  derruba o delegate GPU do MediaPipe mais adiante, que cai para CPU, que mede baixo, que vai
  para cloud. Agora chama `WEBGL_lose_context`.
- **Testes**: `runProbe.test.ts` novo, com câmera falsa. O caso central é "câmera a 10fps +
  modelo a 5ms" — a régua antiga reprovaria, a nova aprova e ainda reporta a câmera lenta em
  separado. Mais: modelo lento acusa modelo lento; frames apresentados contam mesmo quando não
  processados; sem frame nenhum resolve com `samples: 0`; exceção marca `failed`.
- **Gates**: lint, typecheck e 345 testes verdes.
- **Pendências** (em Descobertas do BACKLOG): o contrato tem campo para UM fps, então o fps de
  câmera não sobe — sem telemetria não há como calibrar o limiar de 12fps com dado real; e o
  próprio limiar sobreviveu à troca de régua sem revisão, o que é dívida consciente.

---

## 2026-07-30 (12) · T-082 — Figura de exercício por slug (e a trava para exercício novo)

O Daniel gostou do bonequinho neon e reparou que só havia o de polichinelo: o Agachamento
mostrava, no card Exercício da pré-configuração, um boneco de braços pro alto. Pedido em duas
partes — trocar a figura do card **e** deixar o mecanismo pronto para exercícios futuros.

- **A causa não era o desenho, era o reaproveitamento.** O card usava `IconLogo`, que é a
  assinatura da marca da T-081. Um componente servindo a dois donos (marca fixa por decisão de
  produto; figura que deve variar por exercício) só podia obedecer a um. Agora são famílias
  separadas: `IconLogo` continua sendo a marca, e a seção "figuras de exercício" do
  `ui/icons.tsx` traz `IconExJumpingJack`, `IconExSquat` e `IconExStanding`. A do polichinelo
  nasce com os mesmos pontos do logotipo — duplicação aceita de propósito, para a próxima
  mudança no logotipo não mexer numa pose de exercício.
- **`ui/exerciseFigures.ts` é o registro, e é o único lugar onde se adiciona.** Slug → figura,
  mais `FIGURA_PADRAO` (a neutra em pé). O componente `ui/exerciseIcon.tsx` só faz a ponte com
  o JSX; a separação em dois arquivos veio do aviso de fast refresh do ESLint (módulo que
  exporta componente E constante) e saiu melhor: o registro sendo dado puro é o que deixa o
  teste lê-lo sem renderizar nada — a suíte roda em `environment: node`, sem DOM.
- **A parte que o Daniel pediu de verdade: exercício novo ser "reconhecido".** É o
  `ui/exerciseIcon.test.ts`, que cruza `EXERCISE_KEYS` com `EXERCISE_FIGURES` nas duas direções
  (exercício sem figura, figura órfã) e falha nomeando o slug. Conferido injetando um `flexao`
  falso no catálogo: `exercícios sem figura em EXERCISE_FIGURES: flexao`. O bug consertado aqui
  é de processo — o agachamento entrou no catálogo em T-051 e nada no repositório lembrava que
  faltava desenhar a pose dele. Ponteiro para o registro também no cabeçalho do `catalog.ts`,
  que é onde a pessoa chega primeiro.
- **A medição derrubou o meu próprio desenho.** O primeiro agachamento tinha joelhos dobrados
  para fora, corretos, e razão largura/altura 0,65 contra 0,60 do polichinelo — a 22px as duas
  silhuetas eram a mesma mancha. O que distingue figura pequena é a proporção, não o traço.
  Cabeça foi de `cy=4.5` para `cy=7`, pés e braços abriram: **17×22 contra 14×23,5, razão 0,77
  contra 0,60**, topo começando 2,5 unidades mais abaixo. A regra que fica está no comentário
  da `IconExSquat`.
- **Verificação no caminho real** (`/app/#/preparar`, trocando `digitalfit.exercise` no
  localStorage), não só no componente: com `squat` o card renderiza `cy=7` e silhueta de razão
  0,77; com `jumping_jack`, `cy=4.5` e o `d` do X. Nos dois, 22×26px, `rgb(77,210,255)` e o
  mesmo `drop-shadow` — nenhuma linha de CSS foi tocada, a classe `.prep-cell__ex-icon`
  continua mandando. `computer screenshot` travou de novo (quirk já conhecido); a evidência é
  `getBBox`/`getComputedStyle`.
- **Gates**: `npm run lint`, `npm run typecheck` e `npm run test` (32 arquivos, 331 testes)
  verdes. Nada de Python foi tocado.
- **Pendências geradas**: a silhueta-guia da câmera continua em pose de polichinelo para todo
  exercício — é uma instrução na tela, não decoração, e incomoda mais que o card; proposta
  T-083. E a asserção de proporção mínima entre figuras, quando houver uma terceira. Ambas em
  Descobertas do BACKLOG.

---

## 2026-07-30 (11) · T-079/T-080/T-081 — Melhorias de UI pedidas pelo Daniel

Três pedidos depois de usar o app: o histórico do Perfil comendo a tela, o "Sair" parecendo o
botão certo de tocar, a câmera da pré-configuração pequena demais e o app sem marca.

- **T-080 · A câmera passou a ser a tela inteira e a moldura virou um recorte.** O vídeo vai a
  `inset: 0` e quatro painéis com `backdrop-filter: blur(16px) brightness(.42)` desfocam tudo
  que está fora da janela nítida. Os cards não se mexeram um pixel — passaram a flutuar sobre a
  área desfocada, que é justamente o que lhes dá contraste. Medido no browser: janela nítida
  202×719 no mesmo lugar de antes, painéis cobrindo 64px em cima, 150 embaixo e 112/116 nas
  laterais, colunas intactas em 92/96.
  - **Quatro retângulos e não um painel com máscara**: máscara sobre `backdrop-filter` ainda é
    terreno instável no Safari de iOS e o custo de desfoque é o mesmo (a área somada é a mesma
    tela). O preço é a janela ter cantos quase retos (8px em vez de `--radius-cam`): com raio
    grande, os cantos vazariam imagem nítida por fora da borda. Está em §Desvios da SPEC-014.
  - **`-webkit-backdrop-filter` explícito** nestes painéis (o resto do arquivo usa só a forma
    sem prefixo): o Safari só dispensou o prefixo na versão 18, e o produto é usado no celular.
    Sem ele o painel vira vidro chapado — legível, mas sem câmera atrás.
  - **A armadilha da T-071 voltou de outra porta**: com o palco valendo a tela toda, os avisos
    da CameraView (`bottom: 46px`) pousariam sobre a tab bar — o mesmo bug que já custou dois
    consertos no treino. Ficaram presos à janela nítida (`.sess__cam--prep .stage__banner`).
  - **`isolation: isolate` no `.sess__cam`** por duas razões: os overlays internos têm
    `z-index` entre si e não podem passar por cima dos cards (irmãos DEPOIS no DOM), e o
    contexto vira o backdrop root — o que os painéis desfocam é a câmera, e só ela.
- **T-079 · Perfil.** Histórico virou janela de 182px com rolagem própria (~4 linhas e meia; a
  meia linha é o que diz "tem mais aqui embaixo") e contagem de sessões no título da seção.
  E a hierarquia dos botões foi invertida: **Fechar** é o primário preenchido, **Sair da conta**
  é texto discreto em `--hot`, atrás de uma linha separadora e de uma confirmação de dois
  toques. A regra que fica: num painel, o botão preenchido é a ação que a pessoa veio fazer —
  ação destrutiva não usa a forma do primário.
- **T-081 · Assinatura da marca** (`ui/BrandMark.tsx`) em Escolha, Guia, Pré-config, Treino,
  Progresso, Analytics, Perfil e Relatório. Discreta por construção (caps de 8px, opacidade
  .34) e sem espaço próprio no layout: nas telas de conteúdo ocupa a linha que já era margem do
  título; sobre a câmera flutua no topo-esquerdo, na faixa que o cabeçalho centralizado deixa
  livre — medido, a marca acaba em x=86 e o cabeçalho começa em x=158. `aria-hidden`: é
  decoração, não navegação, e o nome do app já está no `<title>`.
- **Gates**: `npm run lint`, `npm run typecheck` e `npm run test` (31 arquivos, 329 testes)
  verdes. Geometria conferida por medição no browser (`getBoundingClientRect`), não por
  screenshot.
- **Pendência**: o desfoque só se julga com câmera de verdade — a validação de aparência fica
  para o teste no celular. Se o custo do `backdrop-filter` sobre vídeo ao vivo pesar em aparelho
  fraco, o caminho barato é baixar o raio de 16px para ~10px antes de trocar de técnica.

---

## 2026-07-30 (10) · T-077 — O relatório errado: a sessão era ressuscitada por frames atrasados

O Daniel fez 20 repetições e o banco gravou "4 reps · no_data". O relatório da sessão vinha
errado havia tempo, e o log do worker contou a história inteira:

```
19:00:07  aberta (jumping_jack, edge, 30s)
19:00:09  calibrada
19:00:39  encerrada pelo servidor (completed) com 26 reps   ← a contagem estava CERTA
19:00:39  aberta por pose.frame (sem session.started)       ← 71 ms depois, ressuscitou
19:00:40  calibrada
19:00:53  encerrada pelo servidor (no_data) com 4 reps      ← sobrescreveu o relatório bom
```

- **A causa é a junção de três decisões, cada uma correta sozinha.** (1) O worker abre sessão
  ao receber `pose.frame` sem `session.started`, para que corrida de eventos não custe
  repetição. (2) O cliente segue capturando depois do fim — o `session.completed` ainda tem de
  atravessar Redis, gateway e WebSocket, e a câmera não para sozinha. (3) O report-builder faz
  upsert por `session_id`, que é o que torna o relatório reproduzível por replay (SPEC-010).
  Juntas: o frame atrasado abre uma sessão com o MESMO id, ela conta o que a pessoa fizer
  depois do "pare", morre de `no_data` 10 s depois e o upsert troca o relatório bom pelo ruim.
- **Havia um teste defendendo a causa.** O `test_frames_depois_do_fim_abrem_sessao_nova_do_zero`
  existe desde a T-009 com a justificativa certa ("não pode somar repetição a uma sessão
  encerrada") e a conclusão errada. Reescrito: agora exige que o frame seja DESCARTADO, e olha
  para as três coisas ao mesmo tempo (nenhuma sessão viva, um único `session.completed`,
  nenhuma repetição a mais).
- **Conserto no servidor**: lápide de sessão encerrada (`ENDED_MEMORY_MS = 120 s`) marcada em
  TODO caminho que remove a sessão — inclusive o `tick`, que é por onde o caso real passou (o
  timer autoritativo dos 30 s). A memória é podada por tempo, não por quantidade: por número, o
  esquecido seria justamente o mais antigo, que é quem já não recebe frame.
- **Conserto no cliente** (economia, não garantia): `streamsFrames(status)` — a condição de
  enviar deixa de ser "tem `sessionId`" e passa a ser o estado da sessão. O id sobrevive de
  propósito ao fim (a tela do relatório precisa dele), e era esse detalhe que mantinha o loop
  transmitindo. Vale para os dois caminhos, edge e cloud (neste, cada frame é um JPEG).
- **Verificado no stack de pé**, e não só na suíte: 20 reps sintéticas + 67 frames atrasados →
  `descartando frames atrasados` no log, **um** relatório no Postgres, `20 reps · completed ·
  20400 ms`. As linhas de teste foram apagadas depois.

Descoberta grande no caminho, registrada e não consertada aqui: `duration_ms` mistura o relógio
do servidor (`session.started`) com o do navegador (`session.calibrated`, frames) — sai errado
em silêncio e, com relógios muito distantes, mata o report-builder com `DataError: integer out
of range`. Foi assim que apareceu: publiquei o repro com dois relógios e derrubei o processo.
**T-078.**

Gates: `ruff check` + `pytest` (593) e `npm run lint`/`typecheck`/`test` (329) verdes.

---

## 2026-07-30 (9) · T-072 — O painel existe (e o gateway não o serve)

Primeira task da SPEC-018: ligar o admin do Django e mais nada. Nenhum modelo de configuração
entra aqui — `Plan` e `Exercise` são T-073/T-074.

- **O que ligar custou, medido e não estimado**: 3 apps (`admin`, `sessions`, `messages`), 5
  middlewares, e os `context_processors` que estavam **vazios** (`settings.py`) — sem
  `auth`/`messages` ali o Django recusa subir (`admin.E402`/`E403`). Os apps entram
  incondicionalmente, e só a ROTA é condicional: apps atrás de `DJANGO_ENABLE_ADMIN` dariam
  estado de migration diferente por processo, e o sintoma seria um `django_session` que não
  existe justamente na máquina onde alguém acabou de ligar o painel.
- **`is_staff` é campo novo, não apelido de `is_admin`.** As contas que já têm `is_admin` foram
  concedidas sob a promessa escrita, no próprio modelo, de que a flag "não dá acesso a dado de
  ninguém". Unir as duas promoveria em silêncio quem já a tinha. Tem teste dizendo isso.
- **`has_perm`/`has_module_perms` no `User` em vez de `PermissionsMixin`**: respondendo pela
  conta inteira, o `ModelBackend` nunca é consultado e `auth_permission`/`auth_group` continuam
  sendo as tabelas vazias de `[A/T-022]`. Consequência aceita: quem entra no painel vê tudo que
  está registrado — granularidade entra junto com o mixin, se houver um segundo perfil.
- **Migration antiga precisou de `run_before`.** O `LogEntry` do admin tem FK para o
  `AUTH_USER_MODEL`, e a `swappable_dependency` aponta para a PRIMEIRA migration do app — que
  aqui é a `0001`, de quando ainda não havia usuário (a conta nasceu na `0002`). Sem ordenar,
  `admin.0001` roda antes de existir `api.user` e o `migrate` morre com "Related model
  'api.user' cannot be resolved".
- **A trava do gateway é do processo, não da variável** (`core/admin_gate.py`): o `ROOT_URLCONF`
  é o mesmo para os dois, e separar só por env cairia no dia em que alguém movesse
  `DJANGO_ENABLE_ADMIN` para o bloco compartilhado do compose. Verificado no compose de pé:
  `:8001/painel/` → 404, `:8001/healthz` → 200.
- **`is_staff` é somente leitura dentro do painel.** Conceder painel é a única escalada que o
  painel não faz sozinho; sai por `admin_tools --panel-on`, que exige shell. `is_admin`, esse
  sim, o painel concede.
- **`SessionResult`/`SessionClaim`/`LogEntry` entram somente leitura.** Editar um relatório à
  mão criaria uma linha que nenhum replay reproduz — a SPEC-010 promete o contrário.
- **Estáticos por whitenoise + `collectstatic` no build da imagem**, e não pelo nginx: o nginx
  da frente é o do Daniel e não é versionado aqui. Verificado no ar: `/static/admin/css/base.css`
  responde 200 com 22 kB.
- **Verificado no caminho real**, com o compose de pé: login por cookie + CSRF, índice do painel,
  troca de senha, `add` de conta, `sessionresult/add/` → 403, `/admin/` → 404. A conta de teste
  foi apagada ao fim.

Duas descobertas grandes, ambas no BACKLOG: a suíte **não** roda em SQLite (roda no Postgres do
compose, e a CI provavelmente está vermelha — T-076), e teste de formulário não cobre tela de
admin (o `add` de conta respondia 500 com o formulário passando nos testes).

Gates: `ruff check` + `ruff format --check` + `pytest` (591 testes) verdes; imagem do server
buildando com `collectstatic`.

---

## 2026-07-30 (8) · SPEC-018 + ADR-011 — Painel de administração e plano de configuração

Sessão de projeto, sem código. O Daniel quer trazer configuração (recursos do Free, do pago
etc.) para o admin do Django; o pedido virou spec completa.

- **O admin não existia por decisão, não por esquecimento.** `api/models.py:64` e a descoberta
  `[A/T-022]` registram o corte: `AbstractBaseUser` sem `PermissionsMixin`, `contrib.auth` só
  pelos hashers, "não há admin nem permissões". A decisão estava certa para o projeto de então —
  todo parâmetro era ou calibrado contra corpus (muda por commit e bancada) ou infra (muda por
  env). A SPEC-016 cria a primeira categoria nova: capacidade de plano é decisão comercial. Daí
  ADR-011 como *mudança de premissa*, não como correção de erro.
- **A restrição que desenhou tudo**: workers não têm ORM (ADR-008) e a SPEC-010 promete relatório
  derivável 100% por replay. Config lida do banco pelo worker faria o mesmo replay dar resultados
  diferentes, em silêncio. Regra da spec: **resolve na API, carimba no `session.started`** — que
  já é como `duration_s` e `countdown_s` funcionam. Para o que não é por sessão (textos de
  feedback), o caminho é snapshot no Redis escrito pelo Django, e fica para a Fase Evolução.
- **Fronteira explícita do que NÃO entra no painel**: limiares de FSM e de cena, normalização e
  filtros — a bancada da SPEC-012 varre os defaults do código, e valor mudado por formulário não
  tem fixture, muda contagem em silêncio e contamina o Parquet. Se um dia precisar variar, é
  perfil versionado carimbado na sessão, não campo solto.
- **Custo de ligar o admin levantado no código**, não estimado: 3 apps, 4 middlewares,
  `context_processors` hoje vazio (`settings.py:70`, o admin recusa subir sem `auth`/`messages`),
  `is_staff` novo no `User`, estáticos sem whitenoise nem rota no nginx, e `ROOT_URLCONF`
  compartilhado com o gateway — sem gate, o painel apareceria no processo de WebSocket.
- **`is_staff` novo em vez de reusar `is_admin`**: o docstring de `is_admin` promete que a flag
  "não dá acesso a dado de ninguém". Contas já concedidas sob essa promessa não podem virar
  acesso ao painel retroativamente.

Pendências geradas: T-072 (ligar o admin), T-073 (`Plan` + resolvedor), T-074 (`Exercise` +
`GET /api/config`), T-075 (`config_version` no evento e no relatório). T-063 e T-064 foram
reescritas para ler do `Plan` em vez de nascerem com constante nova — se forem feitas antes da
T-073, terão de ser reabertas.

---

## 2026-07-30 (7) · T-071 — Porcentagem de volta e o HUD do treino sem colisao

Dois ajustes pedidos pelo Daniel depois de o gzip entrar em producao, com foto do celular.

- **A porcentagem sumiu porque o gzip funcionou.** Meu guarda da T-070 zera o total quando a
  resposta vem comprimida (`Content-Length` e tamanho de rede; os bytes contados saem do stream
  descomprimido). Com gzip ligado, isso passou a valer sempre — e sobrava "3,4 MB baixados", sem
  denominador. Verificado que nao ha saida pelo servidor: sob gzip o nginx responde SEM
  `Content-Length` nem no GET nem no HEAD, e o `fetch` do browser proibe pedir `identity`
  (`Accept-Encoding` e cabecalho proibido).
- **Conserto**: o tamanho passa a vir de quem conhece os arquivos — o build.
  `scripts/setup-mediapipe.mjs` escreve `public/pose-assets.json` (nome → bytes DESCOMPRIMIDOS),
  e o cliente casa por basename, nao pela URL inteira, porque o caminho do wasm sai do
  FilesetResolver e pode vir absoluto ou com query. O `Content-Length` por HEAD fica como
  fallback para o caso sem manifesto e sem compressao. Total real medido: **16,5 MB** — o mesmo
  numero que o Daniel viu no waterfall.
- **O HUD embaralhado tinha uma causa de unidade.** A pilha do rodape e em px a partir de baixo,
  mas os cards de angulo/calorias estavam em `top: 46%`. Em tela alta os 46% caiam exatamente
  sobre a faixa dos avisos: na foto, o texto do modo cloud sai por baixo dos dois cards,
  ilegivel. Agora os quatro cards ficam em px fixos (64 e 188), o que torna a distancia entre os
  grupos independente da altura do aparelho — e agrupa os numeros no terco de cima, que serve ao
  objetivo de ler a 2 metros e deixa o meio da imagem livre.
- **Instrucao modal passou a mandar na tela.** `stage__prepare` ganhou `z-index` (os avisos do
  palco vinham depois no DOM e pintavam por cima da frase "Bracos ao lado do corpo…") e, durante
  a medicao, o cromo flutuante sai: cards, pill e aro somem. Todos mostravam `0`, `--` e o tempo
  cheio — nada contava ainda, e juntos eram o que tornava a tela ilegivel. Ficam o cabecalho, o
  toast do coach (que explica POR QUE a medicao nao fecha — na foto, "voce saiu do quadro") e a
  barra com o stop.
- **Aviso de cloud encurtado**: a versao longa explicava probe, extracao no servidor e ausencia
  de esqueleto em tres linhas. O "por que" e diagnostico e ja vive no chip de dev (o `*` de
  `forced`); no produto ficou uma linha com o que muda para quem treina. Tambem sai de cena
  durante a medicao.
- Medido no browser com todos os elementos presentes ao mesmo tempo, nos dois estados: medindo
  (cards/pill/aro ocultos, nada por cima da instrucao) e em andamento (folgas de 12 a 350px,
  nada por cima do aviso de cloud). Manifesto verificado no dev server, no `dist` e servido pelo
  nginx (200, `application/json`).
- A foto tambem confirmou, de passagem, o que a T-069 levantou como hipotese: **o aparelho do
  Daniel esta caindo em modo CLOUD** ("a analise roda no servidor") e recebendo `OUT_OF_FRAME`
  por estar perto demais da camera. Nao e bug — e o probe decidindo — mas explica a ausencia de
  esqueleto na tela dele.
- Gates: `tsc -b`, `eslint`, `vitest` 326/326 (3 novos em `assetWarmup`), build.

### Fechamento da sessão

Documentação varrida no fim: `docs/DEPLOY.md` ganhou a política de cache por caminho (a pergunta
"por quanto tempo o cache vale" tem resposta em quatro camadas, e `max-age=3600` NÃO significa
rebaixar em 1h — significa revalidar com `304` de 0 bytes); `web/README.md` foi corrigido, porque
dizia que `npm run dev` sobe o app em `localhost:5173` e desde a T-067 a raiz é o SITE (o app está
em `/app/`), além de ter a árvore de `src/` atualizada e o aviso morto sobre `hud/placeholders.ts`
substituído pela regra que vale hoje; o README da raiz aponta os dois bundles.

Gates finais de toda a stack: web (`tsc -b`, `eslint`, 326/326, build) e Python (`ruff` limpo,
`pytest` 577 passando) — o núcleo Python não foi tocado nesta sessão e continua verde.

Estado para a próxima sessão: T-067…T-071 done. Pendências no BACKLOG §Descobertas, em ordem de
valor: pré-carregar WASM/modelo antes da câmera (a maior melhoria de percepção que sobrou no
funil), gerar os `.gz` no build para o `gzip_static` pagar, capa da câmera desligada repetindo
escolhas no `#/treino`, caminho do WASM sem versão impedindo `immutable`, e `pose-assets.json` sem
política de cache. Nada bloqueia treinar.

## 2026-07-30 (6) · T-070 — A compressao nao existia em producao: `gzip_http_version` x `proxy_pass`

O Daniel testou depois do commit anterior: total ainda 16 MB, e recarregar a pagina baixava o
WASM de novo. Perguntou se o nginx da VPS afetava algo. Afetava — era a causa.

- **Causa raiz, reproduzida localmente em um comando**: `gzip_http_version` vale **1.1** por
  default, e `proxy_pass` fala **HTTP/1.0** com o upstream por default. Atras do nginx da VPS, o
  nginx do container RECUSAVA comprimir tudo — nao so o `.wasm`, tambem o CSS e o JS que a config
  antiga achava que comprimia desde sempre. Medido com o mesmo arquivo e a mesma config:
  HTTP/1.1 direto → `Content-Encoding: gzip`, 3,2 MB; HTTP/1.0 → 11.532.084 bytes, **o mesmo
  numero do waterfall do celular**. Foi o `curl --http1.0` que fechou o caso.
- **Licao sobre a minha verificacao anterior**: eu testei a config com `curl` HTTP/1.1 direto no
  container e declarei "verificado na imagem real". Estava certo sobre a imagem e errado sobre o
  CAMINHO — em producao ninguem fala HTTP/1.1 com aquele container. Verificar o componente nao e
  verificar a integracao.
- **Conserto**: `gzip_http_version 1.0` + `gzip_proxied any` (este cobre o vizinho: com `off`, o
  default, nginx nao comprime requisicao com cabecalho `Via` — o que aparece no dia em que um CDN
  entrar na frente) + `gzip_vary on` (com proxy no meio, resposta comprimida tem de se anunciar
  como variante). Verificado por HTTP/1.0 e com `Via` presente: 3,2 MB nos dois.
- **O cache tambem era o tamanho, nao o header.** O servidor esta correto: requisicao condicional
  devolve `304` com 0 bytes (verificado no `.wasm` e no `.task`). O que acontecia e que o
  navegador nunca GUARDAVA a entrada — o cache de disco do Chromium recusa entradas acima de uma
  fracao do tamanho total, e 11,5 MB passa desse limite. A prova estava no proprio waterfall do
  Daniel: com as MESMAS diretivas de cache (e o mesmo bloco `location`) e na mesma visita, o
  modelo de 5,5 MB voltava de `disk cache` em 15 ms e o WASM de 11,5 MB era baixado inteiro. A
  unica variavel era o tamanho. Comprimido (3,2 MB) ele cabe e passa a ser guardado — ligar o
  gzip nao e so "primeiro acesso mais rapido", e o que faz existir um segundo acesso barato.
- Nada a mudar no nginx da VPS: `proxy_http_version 1.1` no `location /` seria equivalente e vale
  pelo keepalive, mas o conserto no container cobre qualquer proxy — inclusive um que o projeto
  nao controla.

## 2026-07-30 (5) · T-070 — O mesmo WASM baixado duas vezes (regressão da T-069)

Waterfall do primeiro acesso trazido pelo Daniel:

```
vision_wasm_internal.wasm   11.532 kB   33,25 s
vision_wasm_internal.wasm   11.532 kB   40,07 s
```

- **Regressão minha, na T-069.** O MediaPipe baixa o WASM DENTRO de `createFromOptions`. Como
  `createEdgePoseLandmarker` tenta GPU e depois CPU, e o prazo de 12s corta a primeira tentativa
  enquanto o download dela ainda está no ar, a segunda tentativa começava um SEGUNDO download do
  mesmo arquivo de 11,5 MB. Os dois dividiam a banda — daí 33s e 40s — e um deles ia para o lixo
  (`aoChegarTarde` fecha o landmarker que chega tarde, mas os bytes já foram gastos).
- **Conserto**: `pose/assetWarmup.ts` tira o download de dentro da tentativa. Baixa uma vez, em
  sequência, para o cache HTTP; só então as tentativas de delegate acontecem — e passam a custar
  compilação, não rede. O `fileset` é resolvido UMA vez e reaproveitado nas duas tentativas: é
  dele que sai `wasmBinaryPath`, o caminho exato do binário, sem adivinhar qual dos três `.wasm`
  do diretório o navegador vai querer (confirmado na `vision.d.ts` do pacote).
- **O prazo continua**, e agora é seguro: com os bytes em cache, tentar CPU depois da GPU não
  custa outro download. Era o aquecimento que faltava para o prazo da T-069 não ter efeito
  colateral.
- **Progresso na tela**: com o download nas nossas mãos, a tela passou a dizer quanto falta
  ("43% · 7,4 de 17,3 MB"). São 17 MB no primeiro acesso; a diferença entre isso e uma tela muda
  é a diferença entre esperar e achar que travou.
- Cuidado que evitou um bug futuro: `Content-Length` é o tamanho NA REDE e os bytes contados
  saem do stream já descomprimido. No dia em que o gzip do `.wasm` for ligado, comparar os dois
  daria "340%" — 11,0 MB lidos contra 3,2 MB anunciados. `totalBytes` devolve `null` quando vê
  `Content-Encoding`, e `warmupLabel` mostra só os MB recebidos quando o total não descreve o
  que está sendo lido.
- Falha de aquecimento nunca sobe: se a rede oscilar ou o `fetch` for bloqueado, o MediaPipe
  baixa por conta própria como sempre fez. Este módulo é otimização e informação, não um novo
  ponto de falha no caminho de treinar.
- Gates: `tsc -b`, `eslint`, `vitest` 323/323 (9 novos em `assetWarmup`), build.
- Confirmado no waterfall do Daniel: a compressão do `.wasm` **não** estava ativa (11.532 kB
  transferidos = tamanho cru).
- **Compressão aplicada em seguida, a pedido dele**, no `docker/web-nginx.conf`: `gzip_static on`
  (serve `.gz` pronto quando existir) + `application/wasm` no `gzip_types` (rede de segurança que
  comprime na hora). Verificado NA IMAGEM `nginx:1.27-alpine`, não no papel: `nginx -V` tem
  `--with-http_gzip_static_module` (sem isso a diretiva derrubaria o container), `nginx -t` passa
  sem avisos, o `dist` real servido devolve `Content-Encoding: gzip` com **3,2 MB** contra 11,0,
  o descomprimido é byte a byte idêntico ao original, o `.task` continua sem comprimir e o
  fallback de rota do `/app/` segue respondendo 200. O bloco `types` próprio saiu: o mime.types
  do nginx 1.27 já traz `application/wasm` (linha 55), e declarar de novo só geraria aviso de
  extensão duplicada.

## 2026-07-30 (4) · T-069 — "Paramos de te ver na câmera" não era a câmera

O Daniel trouxe o teste que fechou o diagnóstico: **em aba anônima nunca conseguia treinar; em
aba normal funcionava, na mesma posição e no mesmo aparelho.** Trocar de aba consertava.

- **O que a aba anônima elimina**: pose-worker morto ou modo cloud quebrado derrubariam as duas
  abas (mesmo servidor). Trial/conta daria erro explícito e abriria a folha de conta.
  Enquadramento não se conserta trocando de aba. Sobra cold start — e aba anônima é cold start
  permanente: cache HTTP vazio **e** sem cache de shader da GPU em disco.
- **Causa raiz**: a sessão era pedida em `cameraStatus === 'ready'`, o MESMO sinal que dispara o
  carregamento do pipeline. O servidor conta os 10s de `no_data` desde a admissão (SPEC-009),
  e entre a câmera abrir e o primeiro `pose.frame` sair o cliente ainda precisa baixar 11,5 MB
  de WASM + 5,8 MB de modelo, compilar, inicializar a GPU e gastar 2s no probe. Com cache
  frio o prazo estourava antes do primeiro frame — e a mensagem culpava a câmera por não ver
  ninguém que estava ali, parado, no lugar certo.
- **Conserto (o estrutural)**: `session/pipelineGate.ts` — `podeAlimentarSessao()` exige
  landmarker de pé e probe decidido, e é ele que liga o `useSession`. Quem pede a sessão declara
  que pode alimentá-la; registrado como contrato na SPEC-009 §critério 4 e na SPEC-001.
- **Segundo buraco, achado no caminho**: `createEdgePoseLandmarker` caía para CPU só quando a
  GPU **rejeitava**. Inicialização de GPU que trava não rejeita — ficava pendente para sempre,
  sem fallback e sem erro. Agora toda criação tem prazo de 12s (`lib/deadline.ts`), e o valor
  que chega tarde é fechado (dois contextos de GPU vivos seria pior que nenhum). Prazo
  deliberadamente generoso: depois do portão, lentidão não é mais fatal — o prazo existe para
  pegar "travado", não "devagar". Cortar em 4s empurraria para CPU um aparelho que ia funcionar,
  e CPU costuma medir < 12fps no probe, o que jogaria a sessão para CLOUD sem necessidade.
- **Terceiro**: a tela ficava MUDA durante o aquecimento — justamente a janela de vários
  segundos do primeiro acesso. Agora diz "Preparando a análise neste aparelho…" com a nota de
  que o modelo é baixado uma vez, "Calibrando o dispositivo…" no probe, e a falha aparece em vez
  de virar espera infinita.
- Medições que sustentam o diagnóstico (não estimativas): 11.532.084 bytes de WASM +
  5.777.746 do modelo = **17,3 MB** no primeiro acesso, sem gzip em produção. O `.wasm`
  comprime para **3,2 MB** (o `.task`, 5,5 → 4,7 MB) — o comentário do `web-nginx.conf` que diz
  que os dois já são comprimidos é falso para o `.wasm`. O gzip ficou fora desta task a pedido
  do Daniel (ele aplica no nginx); anotado no BACKLOG com os números.
- **Honestidade sobre uma medição minha**: tentei cronometrar a criação do landmarker pelo
  browser e vi passar de 40s. Era artefato da ferramenta de automação, não do app — o console
  mostrou o grafo subindo e fechando normalmente. O diagnóstico se sustenta pelos bytes medidos
  e pela ordem no código, não por aquele número.
- Gates: `tsc -b`, `eslint`, `vitest` 314/314 (12 novos: `pipelineGate`, `deadline`).
- Pendências geradas: pré-carregar WASM/modelo antes de a câmera abrir (o portão tirou a falha,
  não a espera) e o gzip do `.wasm`.

## 2026-07-30 (3) · T-067/T-068 — Fronteira SITE|APP, tab bar nova e o rodapé do treino (de verdade)

Segundo teste do Daniel em aparelho real. O relato: "na parte de baixo onde tem o botão ainda
está ficando algo por cima". A queixa de detecção do mesmo relato era conexão de internet —
confirmado por ele, nada a corrigir no pipeline.

- **O rodapé tinha DUAS causas, e a primeira revisão só pegou uma.**
  1. *Posição*: os avisos da CameraView (`.stage__banner`, `bottom: 46px`) e o chip de
     diagnóstico (`bottom: 12px`) moram no palco da câmera — que no treino é a tela inteira.
     "Conectando ao servidor…" pousava exatamente sobre o botão de play. O CSS culpado não
     está na tela de treino, e foi por isso que sobreviveu ao conserto anterior.
  2. *Ordem de pintura*: `.live__fade-bottom` — o gradiente de legibilidade, quase opaco —
     tinha `z-index: 2` dentro de `.live__chrome` e pintava **por cima** do player e da barra.
     É a explicação do "parece ter se misturado com outro componente": o botão estava lá,
     coberto por preto a 96%. Corrigido tirando o `z-index` (os gradientes são os primeiros no
     DOM, logo ficam atrás por ordem natural).
- **Rodapé virou uma pilha única, medida no browser** com todos os elementos presentes ao
  mesmo tempo e no pior caso de texto (aviso de duas linhas + dica de três): barra+FAB (0) ·
  pill (100px) · toast (176px) · avisos (260px) · chip de dev (348px), folgas de 12 a 17px.
  Verificado também que o toque no centro do FAB chega ao botão (`elementFromPoint`).
- **T-068 — tab bar nova**: Início · Progresso · Analytics · Perfil, com "Início" = a
  pré-configuração. No treino a MESMA barra ganha o play/stop no meio (FAB), e o player
  flutuante de 4 botões saiu: ⏮/⏭/música eram placeholders desabilitados, e era o
  posicionamento absoluto deles que gerava a colisão. Progresso e Analytics ganharam tela em
  vez de toast "em breve" — Progresso mostra o último treino persistido (validado no browser
  com o relatório real da sessão anterior: 26 reps, 52 rep/min, 30s), Analytics reabre a
  análise da sessão (`reopenReport`) e declara o que falta.
- **T-067 — SITE e APP são dois bundles** (ADR-010): `web/index.html` (landing + Sobre) e
  `web/app/index.html` (funil de treino), um build só. Medido: site 8,8 kB × app 239 kB — quem
  abre a landing parou de baixar MediaPipe e a máquina de sessão para ler um texto.
- Decisões da fronteira:
  - **`localStorage` é por origem, e isso manda no desenho.** Conta, preferência de exercício
    e `guide_seen` pertencem ao APP. Então o site não decide nada: aponta a intenção por duas
    pontes — `#/ex/:slug` (o app aplica a regra da SPEC-015 e escolhe Guia ou Pré-config) e
    `#/entrar` (o app abre a AccountSheet) — e as duas trocam a rota com `replace`, para o
    histórico não guardar um passo que só sabe redirecionar. "Entrar" no site é um link para o
    app, não um formulário: login no host errado não valeria no outro.
  - **Links que atravessam a fronteira são `<a href>`**, montados por `shell/origins.ts` a
    partir de `VITE_SITE_URL`/`VITE_APP_URL` (default `/` e `/app/`). São `VITE_*` porque a
    decisão é de build: o bundle do site não tem como descobrir em runtime onde o app foi
    servido.
  - **Deploy pronto para subdomínio sem exigi-lo hoje**: `SITE_DOMAIN`/`APP_DOMAIN` no
    `.env.prod` ligam o modo `site.dominio` | `app.dominio` — o `prod.sh` grava as origens no
    bundle, põe os dois hosts no `ALLOWED_HOSTS`/CORS (senão a API recusa o `Host` e o celular
    só mostra "sem conexão") e imprime os server blocks. No nginx só a **raiz** do host do app
    é reescrita para `/app/index.html`: mapear o host inteiro faria o navegador pedir
    `/app/assets/…` e tomar 404, porque o HTML referencia `/assets/…` absoluto.
  - Roteadores separados de propósito (`shell/nav.ts` × `site/nav.ts`): compartilhar o union
    de rotas obrigaria cada bundle a conhecer as telas do outro, e a fronteira vazaria pelo tipo.
- Verificado no browser: pilha do rodapé medida, funil site→app ponta a ponta
  (card do site → `#/ex/squat` → preferência gravada → `#/preparar`, e o back volta ao site em
  um passo), `#/entrar` abrindo a folha de conta, e as quatro telas do app.
- Gates: `tsc -b`, `eslint`, `vitest` 302/302 (14 novos: `shell/nav`, `shell/origins`,
  `site/nav`), `npm run build` com os dois entry points.
- Pendências geradas (no BACKLOG): a capa da câmera desligada repete ExercisePicker/
  CountdownSetting dentro do `#/treino` (ruído herdado da SPEC-013), e o chip de dev pode
  encostar nos cards do meio em telas mais baixas que ~740px.

## 2026-07-30 · SPEC-014…017 + T-056…T-062 — Plano de evolução e UI v2 completa

- **Planejamento documentado primeiro** (pedido do Daniel): SPEC-014 (Interface v2 —
  vinculante, réplica do protótipo Claude Design "Evolução UI v2" + `app-completo-mobile.png`
  + `index.png`), SPEC-015 (Primeiro Acesso Guiado: Index → Escolha → Guia → Treino),
  SPEC-016 (Free × Assinatura — *futura*), SPEC-017 (Perfil físico & progresso realista —
  *futura*). Plano-mestre em `docs/PLANO-UI-V2.md`; Fase 4 no BACKLOG (T-056…T-066).
- **Imagens geradas no Kairogen** (seedream-v4, 8 créditos; ~35 restantes): hero do index e
  passos do guia (polichinelo ×2, agachamento ×2), personagem consistente via reference
  image, comprimidas para ~80KB em `web/public/img/`.
- **UI v2 implementada** (T-056…T-062): tokens novos (Manrope/Space Grotesk, #05070d,
  azul/roxo/ciano, animações `df*`), roteador por hash (`shell/nav.ts`, sem dependência),
  tab bar flutuante de 4 itens (sem FAB), Index responsivo (mobile = tela 1; ≥900px =
  `index.png` com mini-HUD estático e footer), Escolha (cards com demo/badge/dot), Guia
  (SPEC-015, "visto" por exercício no localStorage), Pré-configuração (steppers funcionais de
  série/reps persistidos; duração TRAVADA nos 30s — autoridade do servidor; espelhar; grade +
  scan + silhueta ciano sobre a câmera ao vivo), Treino ao Vivo (HUD flutuante com anel de
  reps real, ângulo T-044, TimerRing, pill do exercício, player) e Sobre.
- Decisões:
  - **Pré-config e treino são UM componente** (`SessionScreen`) com a CameraView num slot
    estável (`.sess__cam`) e cromo absoluto por cima — trocar de tela não pode desmontar a
    câmera. A sessão só abre no `#/treino` (`useSession(camera && rota)`); a pré-config é
    espelho puro.
  - **Honestidade > fidelidade** (tabela de desvios na SPEC-014): FC e kcal mostram `--`
    (sem sensor/sem MET), player mostra **stop** e não pause (sessão de 30s é atômica),
    música desabilitada. Série/reps são metas cosméticas do HUD até a T-045.
  - Design system "Nocturne" do Claude Design **não** adotado (estética diverge do
    protótipo); os tokens vêm do próprio protótipo v2.
  - Google Fonts no `index.html`: offline degrada para system-ui — anotado na spec.
- Bug pego na verificação em browser: dois toques rápidos no stepper perdiam um incremento
  (closure velha) — corrigido com updater funcional + persistência em `useEffect`.
- Removidos os rascunhos `Index.tsx`, `ExecuteExercicies.tsx` e `hud/CardSelector.tsx`
  (substituídos pelas telas de `screens/`).
- Gates: `tsc` limpo, `eslint` limpo, `vitest` 288/288. Funil inteiro verificado no browser
  (mobile 375px e desktop 1280px), inclusive back do navegador e persistência do guia.
- Pendências: T-063…T-066 (Free/Assinatura, perfil físico, GIFs) ficam como specs futuras;
  duração configurável depende da SPEC-009 evolução; testar blur do HUD em aparelho real
  (degradar para fundo sólido se houver jank — SPEC-014 §Materiais).

**Mesma data, segunda rodada — ajustes do teste em aparelho real (SPEC-014 §Revisão):**

- Demo dos cards de exercício inteira (`contain` sobre `--bg`), sem corte.
- FC removida das duas telas (sem sensor = ruído); anel de reps maior (76px) e TEMPO
  RESTANTE promovido ao topo-direito — reps e tempo legíveis a ~2 metros.
- Card SÉRIE flutuante removido (info já está no subtítulo; colidia com o pill) e rodapé
  reespaçado com `env(safe-area-inset-bottom)` — o player ficava sob a barra do navegador.
- **Relatório sobrevive ao F5**: `report/lastReport.ts` persiste o último relatório
  (`digitalfit.last_report`); o store rehidrata no boot e reabre a folha se estava aberta;
  "Fechar" persiste fechado sem apagar os dados. Verificado no browser: reload com folha
  aberta reabre com os mesmos números; reload após fechar não reabre e mantém o dado.
- Gates: `tsc` + `eslint` limpos, `vitest` 288/288.

---

## 2026-07-29 · T-032 — Exercício 2: o agachamento

- Entregue: `exercises/squat.py` + 33 testes, `Code.SQUAT_TOO_SHALLOW` no contrato, mensagem
  no catálogo de feedback, entrada no catálogo do cliente (e portanto **selecionável** — o
  seletor da T-051 passou a desenhar de verdade).
- **A decisão que define o módulo: a feature não é o ângulo do joelho, e a SPEC-007 estava
  errada ao sugerir que fosse** ("agachamento: ângulo do joelho + profundidade do quadril").
  O joelho viaja para a frente e a câmera frontal — o enquadramento que a SPEC-003 pede em
  todo o produto — quase não vê esse eixo: 80° reais leem 133° no plano da imagem. Um limiar
  de `knee_angle < 90°` **nunca dispararia**. A spec foi corrigida.
  - O que se usa é a **altura do quadril** (quadril→tornozelo em torsos): 1,02 em pé → 0,64
    no fundo, monotônica, e sobrevive à normalização — a origem no quadril médio apaga a
    descida absoluta, mas não a perna encolhendo em relação ao próprio torso.
  - Divisor por frame, não da calibração. A lição da T-019 aplicada de novo.
  - `knee_angle_view` existe como feature, com `view` no nome de propósito: serve ao relatório
    e à bancada, e o nome grita que não é o ângulo do corpo. Tem teste travando que ele **não**
    serve de critério — para um "conserto" bem-intencionado falhar alto em vez de silenciar a
    contagem.
- Achado durante os testes: **o One Euro corta o fundo do agachamento acima de ~90 rpm**.
  Exato até 90, zero em 120 — e não é a FSM: o filtro entrega 0,727 contra o limiar de 0,72 e
  todo agachamento vira "raso". A 30 fps o mesmo ritmo volta a contar, o que fecha o
  diagnóstico. Os parâmetros do filtro foram medidos para o polichinelo, cujo pulso anda ~3
  torsos/s; o quadril anda bem menos. Não mexi no limiar de profundidade, que tem
  justificativa anatômica (coxa paralela ao chão) — o caminho certo é parâmetro por exercício
  na SPEC-006, e está nas Descobertas.
- No cliente, `main_angle: 'none'` para o agachamento e a célula "Ângulo" passa a mostrar
  `--`. Exibir o ângulo do braço durante um agachamento seria um número parado em ~12° o
  treino inteiro — e número imóvel enquanto a pessoa se esforça lê como "não está me vendo",
  que é a ansiedade que o esqueleto sobre a imagem existe para evitar (SPEC-013).
- **Limitação declarada, não escondida**: os limiares saem da geometria do gerador, não de
  vídeo de gente agachando (o corpus só tem polichinelo). São conservadores — o gerador não
  inclina o tronco e vídeo real inclina, o que aumenta o sinal. Virou **T-053**.
- Gates: `ruff` limpo, `pytest` **569**; web `lint`/`typecheck`/`test` (288) limpos; **e2e
  5/5**. Verificado ao vivo: `POST /api/sessions` com `"exercise":"squat"` devolve ticket, e
  slug inválido responde `disponiveis: jumping_jack, squat`.
- Pendências geradas: T-053 (corpus de agachamento) e T-054 (`KNEES_INWARD` — o valgo é a
  falha que a câmera frontal vê melhor que qualquer outra, e precisa de parâmetro novo no
  gerador de poses).

---

## 2026-07-29 · T-052 — O gerador de fixtures aprende a dobrar o joelho

- Por quê antes da T-032: todos os critérios de aceite da SPEC-007 são baseados em fixture.
  Sem gerador, a FSM 2 não teria como ser aceita — e essa metade do trabalho estava invisível
  no título da T-032.
- Feito: `Pose` ganhou `knee_angle`, `stick_figure` passou a montar a perna como cadeia de
  dois segmentos, e nasceram `squat_poses()`/`standing_pose()`, espelhando a forma do gerador
  do polichinelo.
- Decisões:
  - **Default `KNEE_STRAIGHT` = perna reta = a geometria que já existia.** A suíte inteira
    (535 testes) passa sem um número se mexer, e há teste explícito para isso. Um deslocamento
    de milésimos aqui reescreveria em silêncio o significado de todos os limiares medidos até
    hoje — inclusive os do corpus.
  - **Ao agachar, quem desce é o quadril; o chão fica.** Ancorar no quadril e deixar o
    tornozelo subir daria a mesma geometria relativa, mas a altura do corpo no quadro não
    mudaria — e a validação de cena veria um agachamento como alguém parado, enquanto em vídeo
    o corpo encolhe visivelmente.
- **A medição que muda a T-032**: de frente, 80° reais de joelho leem **133°**. O joelho viaja
  para a frente e a câmera frontal não vê esse eixo. Uma FSM com limiar de 90° lido do plano
  da imagem **nunca dispararia** no enquadramento que o produto pede. O que se vê bem é a
  altura ombro→tornozelo (0,607 → 0,468). O gerador reproduz essa perda de propósito: uma
  fixture que entregasse o ângulo verdadeiro de frente produziria uma FSM aprovada em teste e
  reprovada em vídeo — o pior resultado possível para uma bancada. Tabela nas Descobertas.
- Um teste meu falhou e o certo era corrigir o teste: eu tinha afirmado encolhimento de 25%
  sem medir; o real é 19%. Trocado pelo número medido, com o porquê de ele ser conservador
  (o gerador não inclina o tronco, e vídeo real inclina).
- Gates: `ruff` limpo, `pytest` **535** (era 521, +14).

---

## 2026-07-29 · T-051 — O cliente passa a escolher o exercício

- O buraco: `useSession.ts` mandava `DEFAULT_EXERCISE` fixo. Um exercício podia estar pronto,
  testado e medido no worker e ainda assim ser inalcançável pelo produto — só por `curl`. A
  SPEC-007 diz "usuário **seleciona** o exercício" desde o dia 1 e isso nunca foi construído.
- Decisões:
  - **O seletor não desenha nada enquanto houver um exercício só.** Um controle de uma opção
    não é escolha, é ruído em cima da câmera. O que a task entrega é o caminho da escolha até
    o `POST /sessions`; a superfície aparece sozinha quando o catálogo crescer. Virou regra
    nomeada (`offersChoice()`) com teste que se inverte sozinho no dia da T-032, em vez de um
    `&&` solto dentro do componente.
  - Mora na capa da câmera, ao lado da preparação, pelo mesmo motivo dela: é o instante em
    que a escolha importa, e é antes de a sessão abrir. A aba Exercícios (T-046) será a
    superfície de navegar; esta é a escolha rápida de quem já sabe o que veio fazer.
  - Persistida em `localStorage` como o countdown — treinar não exige conta (SPEC-011).
  - **Validada na leitura, não só na escrita.** Um slug guardado hoje pode sumir do catálogo
    amanhã; um aparelho parado há meses voltaria pedindo um exercício que não existe e levaria
    recusa do servidor a cada tentativa, sem caminho de volta pela interface.
  - Chips e não `<select>`: são nomes, e a roleta nativa abriria por cima da câmera.
- **Um defeito real, achado por um teste que eu escrevi esperando ver passar**: `'toString' in
  EXERCISE_CATALOG` é `true`. `in` percorre o protótipo, então `toString` passava por
  exercício válido, ia para o `POST /sessions`, e `getExercise` devolvia uma função no lugar
  do card — `.display_name` viraria `undefined` no meio da tela. `Object.hasOwn` nos dois
  pontos. Registrado como regra geral do web nas Descobertas.
- Gates: `lint`/`typecheck` limpos, vitest **287** (era 278); **e2e 5/5** com a stack subida.
- Pendências geradas: divergência possível entre o catálogo do web e o registro do worker —
  hoje falha alto na admissão, então não bloqueia; o fim da classe seria o servidor publicar
  o catálogo. Decidir junto com a T-046, que é quem precisa da lista completa.

---

## 2026-07-29 · T-050 — `Phase` vira par neutro (`rest`/`peak`)

- Por quê agora: mudança de contrato, e o AGENTS.md manda contrato primeiro. Escrever a FSM 2
  antes disso significaria escrevê-la duas vezes.
- Raio de alcance **medido antes de mexer**, não estimado: `phase` não vai para o Parquet nem
  para o Postgres, e nenhum componente do web a renderiza. Só existe em `events.py`,
  `jumping_jack.py`, `lib/events.ts` e testes. Por isso a troca foi limpa, sem camada de
  compatibilidade — que teria sido pura dívida para zero dado antigo.
- Decisões:
  - **`REST`/`PEAK`, não `UP`/`DOWN`.** Toda contagem por repetição tem os mesmos dois
    extremos: a posição de partida e o extremo da amplitude. Somar um par por exercício
    (`closed/open`, `up/down`, …) obrigaria HUD, relatório e dataset a virarem um `switch`
    sobre `exercise` para saber o que a palavra quer dizer — o oposto de um contrato.
  - **Nada de rótulo de exibição ainda.** A task previa isso, e eu tirei: nenhuma tela desenha
    a fase hoje. Construir o catálogo de tradução agora seria inventar requisito. A SPEC-007
    registra onde ele nasce quando nascer (catálogo do cliente).
  - `closed`/`open` passam a ser **rejeitados alto** na desserialização, com teste próprio. O
    risco real não é dado velho em disco — é um worker desatualizado publicando no stream; um
    `closed` aceito em silêncio viraria fase errada no HUD sem ninguém perceber.
  - No `jumping_jack.py` o texto continua dizendo FECHADO ⇄ ABERTO, porque é o nome do
    movimento. `REST`/`PEAK` é o nome do dado. Os dois convivem, e o docstring diz isso.
- Gates: `ruff` limpo, `pytest` **521**; web `lint`/`typecheck`/`test` (278) limpos; **e2e com
  a stack de verdade subida: 5/5** — que é o teste que importa aqui, já que a mudança cruza a
  rede entre o enum Python e o TS.
- Docs: SPEC-002 (tabela de eventos), SPEC-007 (fases + de quem é a palavra de tela),
  ARCHITECTURE §7.3.

---

## 2026-07-29 · T-047 — A FSM lê a fase inicial em vez de assumi-la

- Contexto: o Daniel perguntou se dá para começar o exercício 2. Auditei o código e a resposta
  foi "a espinha aguenta, mas não comece pela T-032". A T-047 entrou primeiro porque o bug não
  é do polichinelo — é do **padrão** que a segunda FSM vai copiar.
- Feito: `initial_phase(feats) -> Phase` entrou no **contrato** (`exercises/base.py`), não
  escondido dentro do polichinelo. `step()` chama no primeiro frame utilizável; se a leitura
  der `OPEN`, a FSM nasce aberta, anuncia `exercise.phase` (o HUD desenha a fase — adotar em
  silêncio o deixaria mentindo) e marca o início da rep.
- Decisões:
  - **A fase adotada exige os DOIS limiares de abertura**, não um. É o que separa "está no
    topo de um polichinelo" de "está parado com os braços erguidos": de pé com os pés juntos,
    `ankle_spread` reprova e baixar os braços não vira repetição. Pagar uma rep inventada para
    recuperar uma rep perdida seria um péssimo negócio — e a rep fantasma é a mais visível das
    duas para quem está treinando.
  - Frame intermediário ou `degraded` ⇒ `CLOSED`. Sem afirmação, vale o repouso.
  - O método foi para o Protocol de propósito: todo exercício novo é **obrigado** a responder
    onde começa. Era exatamente a pergunta que ninguém tinha feito.
- Medições (antes → depois):
  - `polichinelo-02.mp4 --no-calibrate`: **14/15 → 15/15**. É a rep diagnosticada na T-038.
  - `evalctl run eval/corpus/` (com calibração): **20/13/19 nos dois casos — não mudou**.
    Rodei o corpus com o código antigo via `git stash` para ter certeza em vez de supor. O
    motivo é a guarda dos dois limiares: no frame em que a contagem começa, depois da
    calibração, a pessoa está em posição intermediária. O "não mudou" é a prova de que a
    guarda existe de verdade, e não só no comentário.
  - `test_rep_feita_durante_a_preparacao_NAO_conta`: `rodar(3)` foi de 2 para 3. Não é
    regressão — é o conserto aparecendo no cenário do produto (quem exercita durante a
    preparação está em movimento quando o "VAI!" chega). Atualizei o número e o porquê.
  - Sobra no `02`: −2, e agora está inteiramente explicado — é a janela de calibração caindo
    em cima de exercício de verdade num vídeo a 73 rpm. Não é contagem. O produto não paga
    esse preço porque tem o countdown (T-049). Manifest atualizado.
- Auditoria da regra "um exercício novo não muda nada fora de `exercises/`" (nota técnica da
  SPEC-007): **falsa como está escrita**, e a spec foi corrigida para dizer isso. Agnósticos de
  fato: registro por slug, validação no `POST /sessions`, roteamento, relatório, Parquet e o
  catálogo de feedback. Ainda exigem mudança fora: `Phase` (T-050), seleção de exercício no
  cliente (T-051) e o gerador de fixtures (T-052).
- Gates: `ruff check` limpo; `pytest` **520** (era 514, +6).
- Pendências geradas: T-050, T-051, T-052 no backlog, nesta ordem, antes da T-032.

---

## 2026-07-29 · T-049 — Preparação "3, 2, 1" configurável antes de a contagem valer

- Pedido do Daniel: um timer de 3 s depois da preparação e antes de contar, extensível ou
  desligável, com UX que ajude sem virar atrito.
- **A SPEC-004 já pedia isso e a implementação tinha colapsado o passo.** A Fase Inicial diz
  "countdown fixo 3-2-1", mas desde a T-019 o `session.calibrated` era emitido e a contagem
  começava no MESMO frame: media o corpo e já valia, sem aviso para quem estava do outro lado.
  O que a task acrescenta de novo é a configuração.
- **A decisão que define a entrega: quem segura a contagem é o servidor.** Se fosse animação
  no cliente, o polichinelo feito durante o "3, 2, 1" entraria no total — e o recurso estaria
  enganando quem confia nele. Entrou uma fase no analysis-worker em que os frames continuam
  sendo normalizados (o One Euro precisa chegar quente ao primeiro movimento que vale) e a
  cena continua avisando (é quando "entre no quadro" mais ajuda), mas a FSM não os vê.
- Contrato primeiro, como manda o AGENTS.md: `SessionStarted.countdown_s` e
  `SessionCalibrated.countdown_ms`. O evento de calibração **mudou de significado** — era
  "contagem começou", agora é "corpo medido".
- Decisões:
  - **Os 30 s começam no "JÁ", não na medição.** `exercise_started_wall_ms` passa a ser um
    instante no futuro; `expiry_reason` já comparava contra ele e não precisou mudar. Cobrar a
    preparação do treino encurtaria a sessão de quem escolheu 10 s.
  - **Sem um `session.counting`.** Foi considerado e descartado: o cliente já ancorava o anel
    no relógio dele ao receber o `session.calibrated`, então o evento novo custaria uma ida ao
    servidor sem comprar autoridade. A autoridade está em o worker não alimentar a FSM.
  - **`clamp` em vez de recusa** no `countdown_s` (0–10 s): é conforto, não parâmetro de
    medição. Derrubar a sessão porque veio `-1` trocaria um treino por uma mensagem de erro. O
    teto de 10 s não é técnico — é para o campo não virar forma de segurar vaga sem treinar.
  - **A preferência mora no aparelho, não na conta.** A SPEC-011 é explícita em que treinar não
    exige conta; uma preferência que só funciona depois de cadastrar seria uma punição por não
    se cadastrar, no produto que se define por não precisar disso.
  - **UX em três níveis, do mais rápido de ler para o mais lento** (revisto depois de o Daniel
    pedir mais clareza): o anel que se esvazia dá o "está acabando" no periférico, sem leitura
    nenhuma; o número gigante dá o quanto falta; e a linha de apoio — "Fique parado. Comece o
    polichinelo quando aparecer **VAI!**" — resolve a única dúvida que custa caro, "já é pra
    começar?". A linha some no VAI!, porque aí a resposta é óbvia e texto sobrando durante o
    exercício é ruído. O anel reusa o gradiente e a técnica do `TimerRing` dos 30 s: é a mesma
    ideia visual (um tempo que corre), e duas linguagens para dois relógios no mesmo produto
    seria custo sem retorno. Fundo escurece só o bastante para destacar sem esconder a pessoa
    que está se posicionando, e há `prefers-reduced-motion`.
  - **A primeira versão dizia só "preparando…"**, e era insuficiente pelo motivo certo: quem vê
    a tela pela primeira vez não pode ficar em dúvida se já devia estar pulando — errar isso
    custa as primeiras repetições, que é exatamente o que a task existe para proteger.
  - **O controle fica na capa da câmera**, não em tela de ajustes: ela não existe (Perfil é
    conta e histórico), e este é o único instante em que a escolha importa. Ciclo por toque
    (3 → 5 → 10 → desligado) em vez de `<select>`, que abriria roleta nativa sobre a câmera.
- Erro que peguei na revisão: o `.stage` inteiro é espelhado (`scaleX(-1)`, visão de espelho) e
  o "3" sairia invertido. As outras camadas já desfaziam o espelho; a nova não. Corrigido.
- **Sete testes quebraram ao mudar o default, e isso foi informação.** Cada um era um teste de
  CONTAGEM herdando em silêncio uma decisão de produto. Agora declaram `countdown_s=0` no
  próprio corpo — quando o default mudar de novo, eles não se mexem.
- Gates: `pytest` 514 verde (era 507), `ruff` limpo, `npm run typecheck`/`eslint` limpos,
  vitest 278 (era 254). E-2-e 5/5 contra a stack real, com um caso novo que prova a corrente
  inteira: a preferência sai do cliente, atravessa a admissão, vira `session.started` no
  barramento e chega ao worker — que emite `countdown_ms: 10000` e **não conta** nenhuma das 5
  repetições feitas durante a preparação.
- Pendências geradas (4 em "Descobertas"): a mudança de significado do `session.calibrated`, a
  ausência deliberada do `session.counting`, o default 0 no caminho sem admissão, e a lição
  dos testes que herdavam o default.

---

## 2026-07-29 · T-040 — Fonte de vídeo no navegador e a terceira perna da paridade

- Entregue: `web/src/dev/videoSource.ts` (dirige o `<video>` a partir de um arquivo),
  `startFile` no `useCamera`, `VideoSourceControl` no painel de dev, `parityExport.ts` (o JSON
  no formato do `VideoResult`), e `evalctl parity --browser <json>` como terceira perna.
- **A task foi pequena porque o desenho já estava certo.** `useEdgePipeline` nunca soube de
  onde vinha a imagem — ele lê do elemento `<video>`. Trocar `srcObject` (MediaStream) por
  `src` (blob) não mudou uma linha dele. É o dividendo do "keypoint-first": a origem é
  detalhe.
- **O achado que quase estragou a medição: o capability probe come o começo do vídeo.** Ele
  roda 2 s de detecção antes de o loop começar. Com câmera é inofensivo; com arquivo são 2 s
  de conteúdo — e logo os primeiros, que a SPEC-004 usa para medir o corpo parado. Se eu
  tivesse dado `play()` ao carregar, o navegador leria um trecho diferente do que o harness lê,
  e a diferença apareceria como "divergência JS × Python" quando seria erro meu de montagem.
  Resolvido carregando **pausado no frame 0** e rebobinando depois do probe. Tem teste cujo
  único propósito é falhar se alguém puser um `play()` no carregamento.
- Decisões:
  - **O JSON do navegador sai no formato `VideoResult.to_dict()`**, que já existe e já é lido.
    Inventar um segundo formato só criaria tradução na fronteira — mesma razão do contrato de
    eventos.
  - **`load_browser_result` recusa arquivo sem `source: "browser-edge"`.** Passar um relatório
    do próprio harness por engano faria a comparação medir Python contra Python e responder
    "paridade perfeita" — o resultado mais tranquilizador e mais inútil possível.
  - **A perna do navegador entra no veredito com a mesma tolerância.** Se ela existe é porque
    alguém quis medi-la; reportar OK ignorando-a seria pior do que não ter a perna.
  - **O `delegate` (`gpu`/`cpu`) viaja no JSON.** Os dois dão resultados diferentes, e
    relatório que não diz qual rodou não é reproduzível.
  - Fim do arquivo encerra a captura pelo mesmo caminho de sempre (sem frames → `no_data`,
    T-011). Nada de rota nova para o modo dev.
- Gates: `pytest` 507 verde (era 500), `ruff` limpo, `npm run typecheck` limpo, `eslint` limpo,
  vitest 254 (era 238). CLI verificada contra o corpus real:
  `edge=20 cloud=20 browser=20 (delta +0, browser +0, tolerancia 1)`, com os dois caminhos de
  recusa saindo com código 2 **antes** de gastar a passada do MediaPipe.
- **O que NÃO está verificado, e é o principal:** o número do navegador naquela linha veio de
  um JSON que eu escrevi à mão para exercitar o encanamento. A medição de verdade — abrir o
  `polichinelo-01.mp4` no painel e ver quanto o MediaPipe WASM conta — depende de alguém
  clicar. É a passada que fecha a task, e é justamente a que ninguém pode fazer por automação
  barata (ver Descobertas).
- Pendências geradas (3 em "Descobertas"): o probe consumindo tempo do arquivo, a perna do
  navegador ser manual, e vídeo > 30 s ser cortado pelo timer autoritativo.

---

## 2026-07-29 · T-048 — Gate das ferramentas de dev (e dois gates que não existiam)

- Nasceu de uma pergunta do Daniel sobre a T-040: "quando você diz *eu*? porque um usuário
  comum não deveria estar upando vídeos". Eu tinha descrito a fonte de vídeo da bancada como
  se fosse fluxo de produto. Fui verificar como as superfícies de dev eram separadas hoje e a
  resposta era: **não eram**.
- **O chip de dev estava em produção desde a T-007.** `CameraView.tsx` renderizava o chip de
  diagnóstico e o `FixtureControls` atrás de `{isReady && ...}` — nenhuma flag. Quem abrisse o
  domínio público e ligasse a câmera via `pose gpu`, `seq 412 · 14.9fps` e botões de gravar
  fixture. O `FixtureControls.tsx` até declara no topo "não faz parte da UI de produto"; o
  código nunca fez valer. **Comentário não é gate.**
- Entregue: `web/src/dev/gate.ts` como único lugar que decide, `User.is_admin` (+ migration
  0003) exposto no `GET /api/me`, e `manage.py admin_tools` como única porta de concessão.
- Decisões:
  - **Duas fontes de direito: build de dev, ou conta com `is_admin`.** A segunda é o que o
    Daniel pediu — inspecionar o servidor de produção com o que está de pé lá, sem precisar
    de um build especial. Local continua sem login, porque exigir "crie conta e se promova"
    seria atrito diário para resolver um problema que só existe em produção.
  - **O `?dev=` modifica, nunca concede.** `?dev=0` desliga (o admin vê a tela como o usuário
    comum a vê, sem deslogar); `?dev=1` sozinho não faz nada para quem não é admin. Se
    concedesse, o gate seria decoração — tem teste para os dois lados.
  - **`is_admin` não entra por nenhuma rota.** Só pelo comando, que exige shell na máquina.
    Tem teste que manda `is_admin: true` no corpo do cadastro e exige `False` na resposta.
  - **A flag é lida do banco a cada `/api/me`, não posta no JWT.** Revogar tem efeito
    imediato, verificado ao vivo: promovi e revoguei com o MESMO access token na mão.
  - **`is_admin` e não `is_staff`**: `is_staff` é o campo que o admin do Django consulta, e
    não há admin aqui — reusar o nome prometeria semântica que o projeto não tem.
  - Aproveitei para tirar `docker compose up` da mensagem de erro que o usuário final vê
    quando o gateway cai. Instrução de subir a stack é diagnóstico, não produto.
- **Achado grave no caminho: o `tsc --noEmit` não checava um único arquivo.** O `tsconfig.json`
  da raiz tem `"files": []` + project references, e nessa forma o `tsc` sem `-b` sai 0 sem
  verificar nada. Eu rodei esse comando como gate várias vezes, inclusive fechando a T-022.
  Com `tsc -b --force` apareceram 10 erros reais — dois meus da T-022 (`accountSummary.ts`,
  `noUncheckedIndexedAccess` em `split()[0]`) e dois de `reportSummary.test.ts` que vinham da
  T-020. Ou seja, `npm run build` estava quebrado havia dias. Corrigidos todos e criado
  `npm run typecheck`, que agora é o gate de verdade.
- **Segundo erro meu, e o pior:** rodei `npx prettier --write` para formatar. O projeto **não
  tem Prettier** — o npx baixou a versão 3.9.6 na hora e reformatou seis arquivos para o
  estilo padrão dele (ponto-e-vírgula, aspas duplas), contra a convenção do repositório. O
  `eslint` passou nos dois estados, porque não checa estilo. Revertido pelo git nos arquivos
  versionados e reescrito à mão nos novos. Virou descoberta: enquanto não houver formatador
  configurado, não rodar formatador no `web/`.
- Gates: `pytest` 500 verde (era 492), `ruff` limpo, `npm run typecheck` limpo **de verdade**,
  `npm run build` voltou a funcionar, `eslint` limpo, vitest 238 (era 229). Ciclo verificado
  contra a stack real: cadastro tentando se promover pelo corpo → `is_admin: False`; comando
  `--on` → `/api/me` responde `True` com o mesmo token; `--list`; `--off`.
- Pendências geradas (3 em "Descobertas"): a superfície de dev exposta desde a T-007, o
  typecheck vazio (a T-027 tem de incluir `npm run typecheck`), e a falta de formatador no
  `web/`.

---

## 2026-07-29 · T-022 — Auth JWT + trial anônimo + histórico do usuário

- Entregue (servidor): `server/api/auth.py` (register/login/refresh/me com rate limit por IP),
  `server/api/trial.py` (quota de 3 sessões/dia por aparelho, em Redis), modelos `User` e
  `SessionClaim` + migration `0002`, `GET /api/sessions?mine` como histórico, e a admissão
  passando a gravar a dona da sessão. `tests/test_auth.py` (26 testes) organizado pelos três
  critérios da SPEC-011.
- Entregue (cliente): `web/src/auth/` (`storage.ts`, `api.ts`, `accountSummary.ts`,
  `AccountSheet.tsx`), `web/src/store/account.ts`, aba Perfil funcional, e a identidade
  passando a acompanhar admissão e busca de relatório. 5 arquivos de teste novos; a suíte web
  foi de 172 para 229.
- **O treino continua funcionando sem conta, e isso é a arquitetura, não uma gentileza.** O
  WebSocket da sessão autentica pelo token HMAC de 45 s do ticket (SPEC-009), não pelo JWT.
  Consequência direta: renovar o access no meio de um treino não derruba nada, porque o treino
  nunca dependeu dele — o critério 3 da spec sai de graça. Tem teste cujo único propósito é
  falhar se alguém acoplar o WS ao JWT no futuro.
- **A admissão NÃO passa pelo `authedFetch`.** Se o access venceu, `POST /api/sessions` cai no
  trial anônimo em vez de falhar. Negar o treino de quem tem conta por causa de um token velho
  seria pior do que contar a sessão como visitante.
- Decisões:
  - **`SessionClaim` em vez de `user_id` no `SessionResult`.** A spec pede `user_id` na
    sessão, mas o `SessionResult` é gravado pelo report-builder e a SPEC-010 promete que ele é
    derivável 100% por replay dos eventos. Dono é fato da admissão, não do treino: ficou em
    tabela própria, escrita pela API, e o histórico é a junção pelo `session_id`. O corpus da
    T-021 segue sem qualquer dado de pessoa.
  - **`X-Device-Id` em header, não cookie httpOnly.** Cookie cross-origin exigiria
    `SameSite=None; Secure`, que o navegador descarta em http — ou seja, todo o ambiente de
    dev. E httpOnly protegeria de XSS um dado que a própria spec assume ser burlável.
  - **Rate limit só nas rotas de auth** (`AUTH_THROTTLE_RATE`, 10/min por IP). Limitar
    `POST /sessions` seria mexer na quota do trial, que é decisão de produto e vive em
    `trial.py`. O contador vai no cache Redis para valer no serviço inteiro: com locmem, 3
    workers gunicorn dariam 3× o limite.
  - **Senha errada e e-mail inexistente devolvem a mesma mensagem**, para o login não virar
    oráculo de quem tem conta.
  - **`JWT_SIGNING_KEY` separado do `DJANGO_SECRET_KEY`**, para girar um não deslogar o mundo
    pelo outro. O `prod.sh secrets` agora gera a chave e a acrescenta em `.env.prod` quando ela
    não existe — quem já tem o arquivo de antes não precisa editar nada à mão.
- Gates: `pytest` 492 verde (era 466), `ruff check`/`format` limpos, `tsc --noEmit` e
  `eslint` limpos, vitest 229 verde. `npm run e2e` 4/4 contra o stack real, incluindo um caso
  novo que faz a jornada inteira — cadastro, sessão com conta, relatório, histórico — e prova
  que `session_claim` e `session_result`, duas tabelas sem chave estrangeira entre elas, se
  encontram no `GET /api/sessions?mine`.
- Pendências geradas (5 em "Descobertas"): device em header em vez de cookie; o dia do trial
  virando às 21 h no Brasil; ausência de logout no servidor (sem blacklist de refresh); as
  tabelas mortas que o `contrib.auth` trouxe; e o motivo do `SessionClaim`.

---

## 2026-07-28 · T-021 — dataset-writer (Parquet por sessão + schema documentado)

- Entregue: `workers/dataset_writer/` (`collector.py` puro, `parquet.py` com o schema,
  `main.py` com o loop); extra `dataset` (pyarrow) e imagem própria
  (`docker/dataset-writer.Dockerfile`); serviço no compose de dev e de prod;
  `docs/DATASET.md` (o "schema documentado" do critério 3); `tests/test_dataset_writer.py`
  (21 testes).
- **Lê dois streams, e não dá para escolher um.** Os frames vivem em `pose.frames`, mas o
  `session.completed` autoritativo é emitido pelo analysis-worker em `events.analysis` — ler
  só o primeiro perderia toda sessão encerrada pelo timer dos 30 s, que é o caso normal. Como
  os dois são independentes, o encerramento pode ultrapassar os últimos frames: daí a
  **carência de 1,5 s** antes de fechar o arquivo. Sem ela a cauda de cada série sumiria em
  silêncio, e um corpus com o fim de todo exercício faltando é pior que um corpus menor.
- **Ack imediato, ao contrário do report-builder.** Lá as mensagens ficam pendentes até o
  relatório estar no banco. Aqui isso seria teatro: `pose.frames` é aparado por `MAXLEN ~5000`
  (~11 sessões) e entrada aparada some do stream mesmo continuando no PEL — o restart
  reencontraria pendências vazias e acharia que se protegeu. O dataset é best-effort por
  construção, e a spec pede dele só que o arquivo seja legível.
- Decisões:
  - **O dataset guarda o dado de entrada, não keypoints canônicos.** A spec diz "sequências
    normalizadas" e era tentador aplicar a SPEC-006 aqui. Mas assar a canonicalização de hoje
    no arquivo congelaria `mincutoff`/`beta` dentro do corpus: mexer nos filtros amanhã
    invalidaria tudo que já foi gravado. Landmarks 0–1 no frame são reversíveis; normalização
    é reproduzível a partir deles, e continua sendo decisão revisável.
  - **Formato longo, 138 colunas** (`nose_x`… `right_foot_index_v`), `float32`, zstd, uma
    linha por frame. `df[COORD_COLUMNS].to_numpy()` já é a matriz `(n_frames, 132)` que um
    modelo temporal consome; uma coluna de listas custaria um `explode` em todo notebook.
  - **`session_id` entra como coluna**, além do nome do arquivo — não está na lista da spec e
    entra de propósito: um treino concatena centenas de arquivos e sem isso não há como dizer
    onde uma sequência termina.
  - **Sessão abandonada é gravada, não descartada** — o oposto do report-builder. Um relatório
    de sessão que não terminou seria errado; keypoints continuam sendo keypoints. Pelo mesmo
    motivo o SIGTERM faz `drain()`: deploy no meio da captura não pode virar sessão perdida.
  - **Escrita atômica** (`.tmp` + `os.replace`): crash no meio da escrita deixa o arquivo
    anterior intacto em vez de um Parquet truncado que só explodiria meses depois, dentro de
    um treino.
  - `RedisBus.consume` ganhou `block_ms=0` = **não bloquear** (no Redis, `BLOCK 0` bloqueia
    para sempre). É o que permite ler dois streams na mesma volta sem dobrar a latência
    ociosa. Tem teste com fakeredis: se a tradução se perder, o teste trava — melhor que o
    processo travar em produção.
- Gates: ruff + format limpos, pytest **466** verde (+21), `npm run e2e` 3/3 contra a stack
  real. No disco, sessões de verdade: 320 frames × 138 colunas lidas com `pandas.read_parquet`,
  `seq` contíguo de 0 a 141 nas três sessões do E2E (nenhum frame perdido), metadados
  `schema_version=1` no arquivo, ~725 B/frame.
- Pendências geradas: 3 itens em "Descobertas" (`degraded` sempre `false` porque nenhum
  produtor o preenche; duas réplicas partiriam a sessão ao meio; o corpus não carrega o
  desfecho da sessão, que vive no Postgres).

---

## 2026-07-28 · T-020 — relatório da sessão (consolidação + Postgres + tela)

- Entregue: `session.report.ready` no contrato; `workers/report_builder/builder.py` (puro);
  `SessionResult` + migration inicial; comando `manage.py report_builder`;
  `GET /api/sessions/{id}/report`; tela de relatório no cliente (`web/src/report/`); serviço
  `report-builder` no compose de dev e de prod; `tests/test_report_builder.py` (17 testes) e
  dois arquivos de teste no cliente.
- **O payload de `session.report.ready` é vazio de propósito.** A tentação era mandar reps e
  cadência junto, já que o builder acabou de calculá-los — e aí existiriam dois lugares
  dizendo quantas repetições a sessão teve, o evento e o `GET .../report`. Quando divergissem
  (replay, reprocessamento, mudança de fórmula), ninguém saberia qual está certo. O evento é
  um sino: diz "agora existe", e o conteúdo tem uma fonte só.
- **Ack só depois de gravar.** A SPEC-010 promete que um crash não deixa sessão sem relatório.
  Isso não sai de graça do loop: o builder acumula eventos e só confirma as mensagens da
  sessão quando o relatório está no banco. Se o processo morre no meio, nada foi confirmado e
  tudo é reentregue — o `RedisBus` ganhou `consume_pending()` (XREADGROUP id `0`) e o
  `InMemoryBus` ganhou o PEL correspondente, sem o qual todo teste de reinício passaria por
  não haver o que reentregar. Requisito colado nisso: **nome de consumidor estável**, porque o
  PEL é indexado por nome — um nome com PID dentro tornaria o critério falso na prática, sem
  erro nenhum aparecendo.
- **Um erro meu que o teste pegou**: a evacuação de sessões abandonadas comparava o `ts` do
  evento (relógio do **cliente**) com o agora do servidor. Isso descartaria na hora qualquer
  sessão de celular com a hora torta e todo replay da bancada. Separei `last_seen_ms`
  (servidor) de `last_ts` (cliente) — a mesma lição da T-016 no descarte por idade.
- Decisões:
  - **`session.started` passou a ser publicado nos dois streams** (`pose.frames` para a
    análise, `events.analysis` para o relatório). Sem isso o relatório não saberia o exercício
    e teria de consultar o Redis, quebrando a propriedade da spec — relatório derivável 100%
    por replay dos eventos. O contrato já previa publicar para outra audiência.
  - **ADR-008**: o report-builder roda dentro do Django, não em `workers/`. É o único
    consumidor que escreve no Postgres; um worker separado teria de importar `server/`,
    invertendo a única direção de dependência do repositório. A consolidação em si continua
    pura, sem Django, e é onde estão os testes de cadência.
  - **O total de reps vem do `session.completed`**, não da contagem de `rep.detected` vistos.
    Um builder que subiu no meio da sessão reporta o número certo; só o gráfico sai
    incompleto — e isso é visível, ao contrário de um total silenciosamente menor.
  - A tela mostra `repCount` ao vivo enquanto o relatório não chega: a pessoa acabou de treinar
    e não pode olhar para uma tela vazia por causa de um detalhe de consolidação.
- Gates: ruff + format limpos, pytest 445 verde, tsc e eslint limpos, vitest 165 verde. E2E
  contra a stack real com **3 testes** (um novo, cobrindo a cadeia inteira: worker →
  report-builder → Postgres → API → cliente). No banco, uma sessão real do E2E: 8 reps em
  8 377 ms, cadência 57,3 rpm, janelas `[4, 4]`, calibração com 16 amostras.
- Pendências geradas: 3 itens em "Descobertas" (publicação dupla de `session.started`; o
  report-builder não escala sem trocar a recuperação para `XAUTOCLAIM`; testes de banco em
  SQLite não cobrem nada específico de Postgres).

---

## 2026-07-28 · Produção na VPS — dois bugs que só existem fora da máquina de dev

Reportados pelo Daniel a partir do `docker ps` da VPS: `pose-worker` em `Restarting (1)` e
`api` em `Up (unhealthy)`. Causas distintas, ambas invisíveis em dev.

- **`pose-worker` em crash loop: o modelo não existe na VPS.** `eval/models/*.task` é
  gitignorado (5,5 MB de binário) e o compose de prod monta `./eval/models` por bind mount —
  num clone novo o Docker cria o diretório vazio e `resolve_model_path` estoura.
  - O sintoma engana: o `up` termina verde, api/gateway/web sobem, o modo **edge funciona
    inteiro**. Só o celular que cai em cloud fica sem contagem, e a causa está num container
    que reinicia calado, fora do caminho de quem está testando.
  - Corrigido em `scripts/prod.sh`: `garante_modelo()` roda como preflight do `up` (junto de
    `verifica_portas`) e baixa o `.task` quando falta ou está truncado. Reusa o
    `download_model` do contrato de propósito — a URL do modelo tem UMA fonte de verdade, e
    edge/cloud/bancada dependem de ser o mesmo arquivo. Só stdlib lá dentro, então o
    `python3` do sistema basta: sem `uv`, sem venv na VPS.
  - Novo comando `./scripts/prod.sh modelo`: baixa e religa só o `pose-worker`, para
    consertar uma stack já no ar sem rebuild de tudo.
  - Verificado no caminho real: modelo removido → baixado, `cmp` byte a byte igual ao da
    bancada; modelo truncado → detectado e rebaixado.
- **`api` unhealthy com a api perfeitamente viva: o healthcheck não mandava `Host`.** Em prod
  `ALLOWED_HOSTS` é só o `DOMAIN`; o healthcheck fazia `GET http://127.0.0.1:8000/healthz`,
  que chega com `Host: 127.0.0.1` e leva 400 (DisallowedHost).
  - Medido antes de mexer: `127.0.0.1 -> 400`, `fit.exemplo.com -> 200`.
  - Escolhi mandar o `Host` certo em vez de afrouxar `ALLOWED_HOSTS`. Acrescentar `127.0.0.1`
    resolveria o sintoma e desfaria a propriedade que a T-023 verificou de propósito (Host
    estranho recusado) — barato de fazer, caro de perceber depois.
  - Verificado no container real (projeto `digital-fit-hc`, porta alternativa): `healthy`,
    `exit=0`; e o comando antigo, rodado dentro do mesmo container, continua dando
    `HTTP Error 400`.
- Pendência gerada: 1 item em "Descobertas" (nenhum outro bind mount de prod depende de
  arquivo gitignorado — `./eval/models` era o único).

---

## 2026-07-28 · T-019 — calibração no countdown (e um critério de spec derrubado por medição)

- Entregue: `workers/analysis_worker/calibration.py`, `session.calibrated` no contrato,
  `Baseline` com `shoulder_span`/`wrist_rest_y`, `Normalizer.set_baseline()`, orquestração no
  router, calibração também na bancada, `tests/test_calibration.py` (12 testes),
  `session_poses()` nas fixtures.
- **O critério 3 da SPEC-004 estava errado, e o corpus provou.** A spec pedia `ankle_spread`
  relativo à largura de ombros medida na calibração. Implementei e a acurácia PIOROU: MAE de
  0,67 para 2,00, com o vídeo frontal caindo de 20/20 para 18/20.
  - Diagnóstico: a escala de `ankle_spread` subiu ~1,37× (p50 de 1,60 para 2,19) e a fração de
    frames abaixo do limiar de fechar caiu de 36% para 24% — as reps deixavam de FECHAR.
  - Tentei reexpressar os limiares por esse fator. A varredura mostrou que **não existe fator
    global**: o que levava o vídeo frontal a 20/20 derrubava o oblíquo de 19/21 para 3/21.
  - A razão é conceitual, e é o que fecha o caso: o divisor por frame **se autocorrige**. Com
    a pessoa em ângulo, abertura dos pés e largura de ombros encurtam JUNTAS em perspectiva, e
    a razão se mantém. Fixar o divisor numa medida única destrói exatamente essa invariância —
    e o vídeo oblíquo é quem paga.
  - Revertido; SPEC-004 corrigida com a medição registrada. A baseline segue valendo para a
    escala da normalização e para o relatório/T-030.
- Decisões:
  - **Os 30 s correm do fim da calibração**, não do primeiro frame: o countdown é preparação.
    Efeito colateral bom — o motivo `timeout`, que era inalcançável, virou o teto de vida da
    sessão e cobre a calibração que nunca fecha (com frames chegando, `no_data` não salvaria).
  - **Nada de contagem antes da medida** (SPEC-004, critério 2). Um "1" no placar durante o
    countdown seria uma repetição que a pessoa não fez.
  - **Frame degradado é recusado pela calibração**: landmark adivinhado pelo modelo viraria
    proporção inventada. Mediana, nunca média, pelo mesmo motivo.
  - **A bancada calibra também.** Se `evalctl` pulasse a calibração, mediria um pipeline que
    não existe — e diria uma acurácia que nenhum usuário experimenta.
- Consequência no corpus: MAE 1,333. O vídeo `01` (2 s parados no início) volta a **20/20**;
  `02` e `03` perdem 2 cada porque **não têm countdown** e a medição come exercício real. O
  guia de gravação passou a exigir 2–3 s parado, e `--no-calibrate` existe para comparação.
- **Cliente (mesma task)**: `sessionStatus` ganhou `calibrating`, o anel do HUD passou a
  ancorar em `session.calibrated` (e não no primeiro frame — senão o HUD mostraria menos
  tempo do que o servidor concede), e a tela ganhou a instrução "Fique em pé, parado" no
  centro do palco, onde é vista antes de a pessoa começar a pular.
- **O E2E ao vivo ficou mais rígido, e isso revelou um erro real**: a fixture sintética não
  tinha countdown, então a calibração comia a primeira repetição — 7 de 8 — e a asserção de
  `±1` engolia isso em silêncio. Com o countdown na fixture, a contagem é **exata** (8/8
  confirmado no log do worker) e a tolerância virou igualdade. O teste também passou a exigir
  que `session.calibrated` tenha chegado: sem ele, o servidor teria contado durante a
  preparação.
- Gates: ruff + format limpos, pytest 425 verde, tsc limpo, eslint limpo, vitest 144 verde,
  `npm run e2e` verde contra a stack real.
- Pendências geradas (3 em "Descobertas").

---

## 2026-07-28 · Corpus com 3 vídeos: paridade confirmada, dois erros de contagem diagnosticados

- Daniel gravou mais dois vídeos, ambos em retrato 576×1024 (o primeiro era paisagem):
  `02` com 15 reps começando imediatamente, cadência rápida (~73 rpm); `03` com 21 reps em
  ângulo oblíquo de 20–30°.
- **Paridade edge × cloud: perfeita nos três** — 20/20, 14/14, 20/20, delta 0 em todos. Isso é
  o resultado mais importante da rodada: os dois erros de contagem são **idênticos nos dois
  caminhos**, logo não vêm da degradação cloud (320px, JPEG, 10fps, IMAGE), e sim do pipeline.
  A T-018 sai mais forte do que entrou.
- Bancada no corpus: MAE 0,667, 33% exatos, 54 de 56 reps. Os dois erros são de −1.
- **Erro do vídeo 02, diagnosticado**: no `ts=0` a pessoa **já está aberta** (arm 143°, spread
  3.19). A FSM nasce em `Phase.CLOSED` e o debounce de 250 ms exige estabilidade antes de
  aceitar a abertura; aos 167 ms ela já está fechando. A primeira rep é estruturalmente
  impossível de contar. Virou a **T-047**.
  - Antes disso levantei a hipótese "erra quando não há tempo parado no início" e a **refutei
    por experimento**: cortando 0,5 / 1 / 1,5 / 2 / 2,5 / 3 s do começo do vídeo 01, a
    contagem continua 20/20 em todos os cortes. Não é o tempo parado, é a **fase** em que a
    captura começa. Registrar a hipótese errada importa: ela era plausível e teria virado
    "conhecimento" se eu tivesse parado na correlação.
- **Erro do vídeo 03, diagnosticado**: detecção perfeita nos primeiros 20 s e **zero pose** do
  segundo 21 ao 25 (mapa por segundo). A pessoa sai do quadro e a 21ª rep acontece onde o
  modelo não a vê. O ângulo oblíquo, que era a suspeita natural, **não atrapalhou**.
  - Descoberta de produto que veio junto: falha TOTAL de detecção é **silenciosa**. A validação
    de cena (SPEC-003) opera sobre landmarks; sem landmarks não há evento e não há
    `OUT_OF_FRAME`. Quem treina fica sem "volte para o quadro" justamente quando mais precisa,
    até o `no_data` de 10 s.
- Banda cloud medida nos três: 3,1 / 7,9 / 3,9 KB por frame (31–79 KB/s por sessão).
- Manifest atualizado com as condições de cada vídeo e com o que já se sabe que cada um
  expõe — `conhecido:` deixa explícito que aqueles −1 têm causa conhecida, para não serem
  lidos como ruído em toda rodada futura.

---

## 2026-07-28 · T-018 fechada com vídeo real + início do corpus (T-038)

- Daniel forneceu o primeiro vídeo rotulado: 20 polichinelos, 854×480 @30fps, 28,9s, com ~2s
  parados no início.
- **Paridade edge × cloud: `edge=20  cloud=20`, delta 0.** E as duas contagens batem com o
  rótulo humano — ou seja, o resultado valida três coisas de uma vez: o caminho cloud não
  perde repetição, a FSM acerta em vídeo real, e a bancada mede o que diz medir.
  - frames: edge 374 (15fps), cloud 248 (10fps); sem pose: 59 e 41
  - cadência 55,1 e 55,6 rpm; duração mediana da rep 1001 ms nos dois
  - zero sinais de qualidade, zero frames degradados
  - a rep mais longa (3,8 s) é a primeira, porque engloba os 2 s parados do começo
- **Banda cloud medida em vídeo real: 3,1 KB/frame (~31 KB/s por sessão)** — três vezes menor
  que a medição anterior sobre a referência de UI (9,8 KB), que era uma imagem renderizada
  cheia de detalhe. Três sessões simultâneas ≈ 0,75 Mbit/s. Folgado no orçamento da VPS.
- `evalctl run eval/corpus/`: MAE 0.000, 100% exatos. Baseline gravado em
  `eval/out/baseline.json` para o `evalctl compare` ter contra o que comparar.
- **T-038 começou**: `eval/corpus/manifest.yaml` com o primeiro vídeo rotulado e
  `eval/corpus/README.md` com o guia de gravação — o que variar entre vídeos (distância, luz,
  ângulo, execução preguiçosa) e por que execuções imperfeitas são as mais valiosas (são elas
  que testam o feedback engine, não só a contagem). Vídeos não são versionados; o manifest e o
  guia sim.
- Gates: ruff + format limpos, pytest 413 verde.

---

## 2026-07-28 · T-018 (parcial) — arruamento da paridade edge × cloud

- Entregue: `eval/parity.py` (`CloudPathExtractor`, `compare_paths`, tolerância),
  `evalctl parity <video>`, `tests/test_parity.py` (17 testes).
- O que a comparação isola: as quatro degradações reais do caminho cloud — 320px, JPEG q60,
  10fps em vez de 15, e `RunningMode.IMAGE` em vez de `VIDEO`. Nada além disso muda: mesmo
  arquivo de modelo, mesma FSM depois da extração.
- Decisões:
  - **Compara contagem de reps, não keypoints.** Landmarks idênticos são impossíveis por
    construção (JPEG e modo IMAGE mudam os números) e não é o que o produto entrega.
  - **A tolerância sai da contagem do caminho de referência (edge), não da média.** Com a
    média, um cloud muito errado aumentaria a própria margem — o critério afrouxaria
    justamente no caso em que precisa ser rígido. Há teste para isso.
  - **O `CloudPathExtractor` usa o extractor de produção**, não uma cópia: os bytes que passam
    pelo MediaPipe no teste são os mesmos que passariam vindos de um celular.
  - **Cadência diferente por caminho faz parte da comparação** (15 vs 10fps): menos frames é
    menos chance de a FSM ver o pico do movimento, e isso é uma degradação legítima do cloud.
- Verificação do encanamento com MediaPipe real, sobre um vídeo gerado da referência de UI:
  edge leu 45 frames (3s × 15fps), cloud leu 30 (× 10fps), **os dois detectaram a pessoa em
  100% dos frames** — o JPEG de 320px não perde a pessoa —, e 0 reps dos dois lados, correto
  para imagem estática. Banda medida: 9,8 KB/frame, ~98 KB/s por sessão cloud.
- **Não fecha a task**: falta rodar em vídeo com polichinelo de verdade, e isso é a T-038, que
  depende de gravação. O comando está pronto: `evalctl parity video.mp4 --expected-reps 20`.
- Gates: ruff + format limpos, pytest 413 verde.
- Pendências geradas (2 em "Descobertas"): a paridade é Python×Python, não navegador×servidor;
  e o número de banda medido, a conferir contra o orçamento na T-028.

---

## 2026-07-28 · T-017 — semáforo de slots cloud (o modo cloud passa a existir de verdade)

- Entregue: `workers/shared/slots.py` (`CloudSlots`), admissão consultando o semáforo,
  `analysis-worker` devolvendo a vaga em todos os finais, `tests/test_slots.py` (10 testes) e
  testes de liberação no `test_analysis_worker.py`. `fakeredis[lua]` nas dev deps.
- Decisões:
  - **ZSET com expiração por membro, não `INCR`/`DECR`.** A nota técnica da SPEC-009 sugeria
    contador. Contador atende ao critério 1 (negar a 4ª sessão) mas não ao 2, que exige
    liberar a vaga inclusive em crash de worker: quem crasha não decrementa, e depois de três
    crashes o modo cloud estaria esgotado para sempre, sem nada em log dizendo por quê. Com
    score = expiração e varredura a cada operação, a vaga do morto volta sozinha.
  - **Lua porque varrer-conferir-inserir é um passo só.** Entre o `ZCARD` e o `ZADD` de dois
    processos cabem duas admissões para a mesma vaga.
  - **Idempotente por `session_id`**: retry de rede não pode virar vazamento de vaga.
  - **Quem libera é o analysis-worker**, não a API: é ele que sabe quando a sessão acabou de
    verdade, inclusive por timer e por `no_data` — caminhos que nunca passam pela API.
  - **Libera sem perguntar o modo.** Remover membro ausente é no-op, então o worker chama
    `release` para toda sessão. A alternativa — guardar o modo e checá-lo aqui — é o tipo de
    detalhe que se esquece num caminho de erro e vaza vaga para sempre.
  - **A vaga é tomada antes de a sessão existir.** Registrar primeiro deixaria uma janela com
    token válido para uma sessão que nunca foi admitida.
  - **Falha ao liberar não impede o encerramento**: o score recolhe a vaga depois, e travar o
    fim da sessão deixaria o usuário sem o resultado do treino.
- Um teste antigo caiu com razão: `test_pedido_de_cloud_e_negado_na_fase_0` afirmava que cloud
  é sempre recusado. Virou três testes — cloud com vaga é admitido, sem vaga é negado, e edge
  nunca consulta o semáforo (o modo padrão do produto não pode depender da capacidade cloud).
- Verificação ao vivo contra a stack: quatro `POST /api/sessions` seguidos com
  `requested_mode: cloud` → `cloud, cloud, cloud, denied_cloud`, com `ZCARD slots:cloud == 3`.
  Passados 10s as três fecharam por `no_data` (o caminho do **timer do servidor**, que não
  passa por `session.completed` externo), o ZSET voltou a 0 e uma nova sessão cloud entrou.
- Gates: ruff + format limpos, pytest 396 verde.
- Pendências geradas (2 em "Descobertas"): a nota técnica da SPEC-009 sobre `INCR`/`DECR` ficou
  desatualizada e vale corrigir na próxima passada; e o registro de por que a liberação mora no
  worker.

---

## 2026-07-28 · T-016 — pose-worker: `frames.raw` → MediaPipe CPU → `pose.frame`

- Entregue: `workers/pose_worker/` (extractor + router + main), `workers/shared/pose_model.py`,
  `docker/pose-worker.Dockerfile`, serviço `pose-worker` nos dois compose, extra `pose` no
  pyproject, `tests/test_pose_worker.py` (14 testes), ADR-007.
- Decisões:
  - **ADR-007: `RunningMode.IMAGE`, sem estado entre frames.** A bancada usa `VIDEO`, que
    pressupõe uma sequência contínua com timestamps crescentes por instância. O worker lê de
    consumer group: dois frames seguidos da mesma sessão podem cair em réplicas diferentes,
    então essa premissa não vale. Manter rastreamento exigiria prender sessão a réplica
    (perdendo a tolerância a falha que o grupo dá de graça) ou misturar o rastreamento de
    sessões distintas — pior, porque o estado de uma pessoa influenciaria os landmarks de
    outra. Em troca, o mesmo JPEG dá sempre o mesmo resultado, e é isso que dá sentido à
    T-018.
  - **Modelo resolvido em `workers/shared/pose_model.py`**, reusado pela bancada (direção
    eval → workers, nunca o contrário). Três pontas carregam o mesmo `.task`; se cada uma
    resolvesse à sua maneira, o sintoma de divergência seria "a contagem mudou", sem nada
    apontando para o modelo.
  - **Mesmo decoder JPEG da bancada (cv2).** Com PIL de um lado e OpenCV do outro, a T-018
    mediria a diferença dos decodificadores, não a do pipeline.
  - **`ts` e `seq` do frame original são preservados** no `pose.frame`. Carimbar a hora do
    processamento faria a cadência vista pela FSM virar a do servidor sob carga, e os
    limiares de duração de repetição passariam a medir a fila, não o exercício.
  - **Imagem própria** (MediaPipe + OpenCV ≈ 250 MB): api, gateway e analysis-worker seguem
    enxutos. Modelo entra por volume, não assado na imagem.
  - **Lote de 5, não 50.** Cada frame custa uma detecção completa; puxar 50 encheria a
    memória com trabalho que vence por idade antes de ser feito.
  - **Sem pessoa no quadro não vira evento.** Um `pose.frame` com landmarks inventados faria
    a validação de cena (SPEC-003) dizer que está tudo bem.
- Verificação ponta a ponta contra a stack real, com JPEG de verdade (a referência de UI
  reduzida a 320px, 11 KB — dentro da faixa de 10–25 KB prevista no contrato): três
  `frame.raw` pelo WebSocket saíram como três `pose.frame` com `source=cloud`, 33 landmarks,
  todos visíveis, nariz em (0.518, 0.258). Os três resultados **idênticos** entre si —
  confirmando na prática o determinismo que motivou o ADR-007. No mesmo stream, lado a lado
  com `pose.frame` `source=edge` de sessões anteriores: é o critério 4 da SPEC-005 (downstream
  sem branch por origem) verificado com os olhos.
- Gates: ruff + format limpos, pytest 374 verde, compose de dev e de produção válidos.
- Pendências geradas (3 em "Descobertas"): descarte por idade usa relógio do cliente (risco de
  skew, contraria a nota da spec corrigir — precisa de decisão); IMAGE×VIDEO significa que a
  paridade da T-018 é de contagem, não de keypoints; modelo por volume exige `fetch-model` na
  VPS antes do primeiro deploy cloud.

---

## 2026-07-28 · T-015 — envio de `frame.raw` no modo cloud (início da Fase 1)

- Contrato primeiro (`AGENTS.md`): `EventType.FRAME_RAW`, dataclass `FrameRaw` e rota
  `frame.raw → frames.raw` em `workers/shared/events.py`. Depois gateway, depois cliente.
- Entregue: `FrameRaw` com validação (assinatura JPEG, teto de 256 KB, maior lado ≤ 320px);
  `_stream_de_entrada()` no gateway; `web/src/capture/jpegEncoder.ts` (redução + JPEG q60) e
  `web/src/capture/cloudFrames.ts` (loop de 10fps com trava de envio).
- Decisões:
  - **`frame.raw` é o único tipo cuja rota padrão não é `pose.frames`.** Imagem não entra no
    fluxo da análise; quem a consome é o pose-worker (T-016). Teste trava isso: se a rota
    voltar para `pose.frames`, o analysis-worker receberia JPEG onde espera 33 landmarks.
  - **Trava de "um por vez" no envio cloud.** A codificação é assíncrona e pode passar dos
    100ms do alvo de 10fps; sem a trava os frames se empilhariam enquanto a pessoa treina.
    Frame que chega com codificação em andamento é descartado — mesma regra do backpressure
    do gateway. A trava vem **antes** do relógio: consumir o tick e depois descartar
    derrubaria o fps efetivo abaixo do alvo (há teste para os dois lados).
  - **Validação de tamanho é do servidor, redução é do cliente.** Aceitar frame maior
    empurraria o resize para o pose-worker, que roda com 1 vCPU e é o gargalo do modo cloud
    (SPEC-005, critério 2).
  - **`source: cloud` em `frame.raw`**, embora o produtor seja o navegador — o campo descreve
    o caminho de extração, não a máquina.
  - **`InMemoryBus` passou a registrar o stream de destino** (`routed`, `published_in()`).
    Antes ele fazia `del stream`, então nenhum teste de roteamento podia falhar.
- Um teste antigo caiu, e com razão: `CLIENT_INGEST_TYPES <= ANALYSIS_INPUT_TYPES` deixou de
  valer, porque `frame.raw` entra pelo cliente e **não** vai para a análise. Reescrito para o
  invariante que continua verdadeiro e é o que importa: todo tipo que o cliente pode publicar
  tem consumidor declarado.
- Verificação: `frame.raw` publicado à mão contra a stack real cai em `frames.raw` (não em
  `pose.frames`), com o JPEG intacto como `bin` do MessagePack.
- Gates: ruff + format limpos, pytest 360 verde, tsc limpo, eslint limpo, vitest 144 verde.
- Pendências geradas (3 em "Descobertas"): o caminho cloud não é exercitável até T-016+T-017;
  convenção do `source`; gateway em dev não recarrega código (`uvicorn` sem `--reload`).

---

## 2026-07-28 · T-023 — ambiente de produção (VPS + domínio) separado do de dev

- **Motivo, e ele não é infraestrutural**: `getUserMedia` só existe em contexto seguro, então
  a câmera não abre por IP de rede local. Sem HTTPS de verdade, a T-014 (30s de polichinelo
  no celular) não tem como acontecer. Produção nasceu como pré-requisito de teste, não como
  entrega de produto.
- Entregue: `docker-compose.prod.yml` (autônomo), `docker/web.Dockerfile` (build multi-stage
  do Vite → nginx), `docker/web-nginx.conf`, `scripts/prod.sh`, `.env.prod.example`,
  `docs/DEPLOY.md`. `gunicorn` entrou no extra `server`.
- Decisões:
  - **Arquivo autônomo, não override.** Um `-f base -f prod` herdaria bind mounts e
    `runserver` em silêncio; o dia em que isso for percebido já é tarde. Custa duplicação
    entre os dois compose e vale a pena.
  - **Um domínio, três portas.** `/` → web, `/api/` → api, `/ws/` → gateway. Same-origin
    zera CORS e mantém `wss://` no mesmo host do `https://` — os dois pontos onde deploy
    assim quebra. Portas em `127.0.0.1`; quem expõe é o nginx do Daniel.
  - **`DOMAIN` como fonte única.** O script deriva `VITE_API_URL`, `GATEWAY_WS_URL`,
    `DJANGO_ALLOWED_HOSTS` e `CORS_ALLOWED_ORIGINS`. Mantidas à mão, essas quatro divergem
    calado, e cliente falando com um host enquanto o WS fala com outro só aparece no celular.
  - **`replicas: 1` fixo no `analysis-worker`.** A FSM tem estado em memória por sessão e o
    consumer group dividiria frames da mesma sessão entre réplicas — quebraria só sob carga.
  - **`gunicorn` para o `api`, `uvicorn` para o `gateway`**: a divisão WSGI/ASGI da
    ARCHITECTURE vale em produção também. `GATEWAY_RELAY=0` no `api` para o relay não
    empurrar cada evento duas vezes.
  - **Segredos: gerar, nunca sobrescrever.** `prod.sh secrets` só preenche campo vazio —
    rotacionar `SESSION_TOKEN_SECRET` sem querer derrubaria toda sessão em voo.
  - **`down`/`ps`/`logs` toleram `.env.prod` quebrado.** A hora em que mais se precisa
    derrubar uma stack é justamente quando a configuração está errada.
- Bugs encontrados e corrigidos **antes** da VPS:
  - `docker compose wait` bloqueia até o container **parar**, não até ficar saudável — a
    linha teria travado o primeiro deploy para sempre. Removida: `compose run` já respeita
    `depends_on: service_healthy`.
  - `.env.prod` não estava no `.gitignore` — segredos a um `git add -A` do repositório.
  - `.dockerignore` excluía `web/` inteiro, o que impedia a imagem do cliente de existir.
    Trocado por exclusões específicas (`web/node_modules`, `web/dist`, `public/wasm`…).
  - `application/wasm` explícito no nginx do container: com o MIME errado o navegador recusa
    o módulo, a câmera abre e a pose nunca carrega.
- Verificação (stack de produção subida localmente em portas alternativas, `Host` do domínio):
  `/healthz` e `/readyz` ok; `POST /api/sessions` devolvendo `ws_url` já como
  `wss://<domínio>/ws/session/…`; wasm servido como `application/wasm`; `redis` e `postgres`
  sem porta no host; `Host` estranho recusado com 400; worker abrindo e fechando a sessão
  criada por curl.
- Gates: ruff limpo, pytest 353 verde, tsc limpo, eslint limpo, vitest 132 verde.
- Pendências geradas (3 em "Descobertas"): Caddy→nginx manual; `VITE_API_URL` é build time
  (rebuild obrigatório ao trocar de domínio); produção sem backup/quota/auth (T-022/025/026)
  e sem snapshot de estado (T-031).
- **Não fecha a T-014**: falta o deploy real e os 30s de polichinelo no celular.

---

## 2026-07-28 · [A+B] Cliente ligado à API real + CORS + E2E headless

> **Para o Daniel**: falta só você na frente da câmera. `docker compose up`, abrir
> `http://localhost:5173` (ou o IP da máquina no celular), permitir a câmera e fazer 30 s de
> polichinelo. Tudo antes disso está verificado por máquina.

- `web/src/session/admission.ts`: o cliente **pede a sessão** (`POST /api/sessions`) e abre o
  WS no `ws_url` do ticket. Antes ele inventava `session_id` e token — resto de quando a T-011
  não existia; era uma sessão que o servidor não conhecia. `VITE_WS_URL` continua como escape
  para o mock local.
- `server/core/cors.py`: **sem CORS o app nunca teria funcionado no navegador**, e nenhum
  `curl` mostraria isso — quem aplica a regra é o navegador, não o servidor. Em `DEBUG` libera
  qualquer origem (o celular entra pelo IP da LAN, que ninguém lista antes); fora de `DEBUG`,
  só `CORS_ALLOWED_ORIGINS`, que nasce vazia.
- Serviço `web` no compose — a pendência que ficou **sem dono** entre os dois agentes (o A
  atribuiu ao B, o B disse que compose é território do A). O `setup-mediapipe` agora copia o
  modelo de `eval/models/` antes de sair para a rede, então a primeira subida do container não
  depende de internet.
- `web/src/session/live.e2e.test.ts` (`npm run e2e`, fora da suíte padrão): E2E do cliente
  contra o stack real. Prova o que nada provava — que o **espelho TS do contrato**
  (`lib/events.ts`) fala com o gateway Python. O mock do Agente B foi validado contra o
  `events.py`, mas mock e servidor podem concordar entre si e estarem os dois errados.
- Decisões:
  - **`probe_result` no formato do evento** (`probe_fps`, não `fps`): o cliente manda o payload
    de `session.capability` inteiro e o servidor monta o evento a partir dele. `fps` segue
    aceito para não quebrar ticket antigo.
  - **Middleware de CORS próprio** em vez de `django-cors-headers`: são 30 linhas e a Fase 0
    tem uma regra só. Com domínio de produção e cookies, trocar é uma linha no `MIDDLEWARE`.
  - E2E em config separada (`vitest.e2e.config.ts`), serial: cada teste abre a própria sessão
    e em paralelo disputariam o mesmo worker e o mesmo relógio.
- Bug de teste encontrado de raspão: `test_endpoint_cria_sessao` só passava quando a `views.py`
  ainda não tinha sido importada no momento do monkeypatch — a view faz
  `from api.sessions import create_session`, então patchar o módulo de origem não alcança a
  referência dela. Meus testes de CORS mudaram a ordem dos arquivos e a fragilidade apareceu.
  Agora o patch é em `api.views.create_session`, onde a view de fato lê.
- Gates: `ruff` limpo, **352 testes** Python, `tsc`/`eslint` limpos, **127 testes** web, build
  OK. E2E contra o stack de pé: 8 frames-rep enviados ⇒ **8 reps contadas** pelo servidor,
  `exercise.phase` chegando, nenhum `pose.frame`/`quality.signal` vazando para o cliente; parar
  de enviar ⇒ servidor fecha sozinho com `no_data`.
- Pendências: T-014 só com a validação humana (câmera real); T-038 (corpus) depende de gravar
  os vídeos.

---

## 2026-07-28 · [A+B] Junção das duas linhas de trabalho

- Os dois agentes trabalharam em **repositórios separados** que nunca se falaram: o Agente A em
  `Digital Fit/` (branch `master`) e o Agente B em `df-agent-b/` (branch `agent-b`). A base
  comum é o commit de bootstrap — cada um implementou a **própria T-001**, o que fez toda a
  infra (compose, pyproject, `server/`, README, CI) colidir como `add/add` no merge.
- Resolução: a infra ficou com a linha do Agente A, que evoluiu com gateway, worker e sessões e
  está verificada rodando; `web/` inteiro veio do Agente B; `DEVLOG`/`BACKLOG` foram unidos
  (as duas listas de "Descobertas" valem, e a tabela de tasks agora reflete os dois lados).
- O `web/` que eu tinha começado a montar nesta sessão foi **descartado**: era duplicata de
  trabalho já commitado e mais completo do Agente B (97 testes, mock-gateway validado contra o
  `events.py`, cliente WS com backpressure).
- Estado real da Fase 0 depois da junção: só a **T-014** (E2E com câmera real) e a **T-038**
  (corpus de vídeos) continuam abertas.

---

## 2026-07-28 · [A] T-010 — Feedback engine (núcleo)

> **Agente B**: o HUD agora tem um evento só para mostrar: `feedback.issued`
> `{code, severity, message, hint}`. A `message` e o `hint` já vêm em pt-BR, prontos para a
> tela — **não** monte texto a partir do `code`. O motor garante **no máximo um feedback por
> vez** e no máximo 1 do mesmo código a cada 4 s, então o card do treinador (SPEC-013) pode
> simplesmente substituir o conteúdo quando chega um novo, sem fila própria. `quality.signal`
> não vai mais para o cliente: é insumo do motor.

- `workers/analysis_worker/feedback/`: catálogo em `catalog.pt-BR.yaml` (código → mensagem,
  dica, severidade, prioridade) + `FeedbackEngine` (prioridade, throttle, supressão por cena).
- Ligado no `AnalysisRouter` como último passo do frame: cena e FSM produzem sinais, o motor
  decide o que o HUD vê.
- `SessionState.summary()` passa a devolver `feedback_issued` ao lado de `quality_signals` —
  o relatório (T-020) precisa da diferença entre "detectei 12" e "avisei 3".
- Decisões:
  - **Texto fora do código**: um YAML por idioma (`catalog.<locale>.yaml`); ajustar palavra não
    é deploy. Código desconhecido ou entrada sem `message` é erro na carga — typo não vira
    feedback mudo.
  - **Prioridade no catálogo, não no código** (`priority`, menor vence): cena 10–11, execução
    20–21. Ordenar é dado, não `if`.
  - **Supressão por cena com janela de 3 s** (`SCENE_SUPPRESS_MS`), não flag booleana: o
    validador repete o aviso a cada 2 s, então a janela se renova sozinha enquanto o problema
    existe e expira sozinha quando ele some — sem evento de "cena resolvida", que não existe.
  - **Throttle por código, não global**: braço e perna são problemas diferentes; calar um
    porque o outro falou esconderia metade da correção. Quando um código está em throttle, o
    próximo da fila passa.
  - **`rep.detected` é ignorado** pelo motor: feedback positivo é Fase Evolução.
  - Um motor por sessão — throttle e supressão são estado de sessão.
- Gates: `ruff` limpo, **346 testes** verdes (27 novos). Critérios da SPEC-008 verificados no
  stack real (API → WS → worker → HUD, Redis e gateway de verdade): 12 reps preguiçosas em 12 s
  ⇒ **3 feedbacks** de `ARMS_TOO_LOW` com gaps de 4,1 s (nunca 12); corpo fora de quadro ⇒ só
  `OUT_OF_FRAME`, **zero** crítica de execução; amplitude cheia ⇒ 12 reps e **nenhum** feedback
  falso; latência sinal→HUD **≤ 39 ms** (orçamento: 150 ms).
- Pendências: o card "Dica do Treinador" é T-012 (Agente B); agregação por padrão, TTS e
  feedback positivo ficam na Fase Evolução da SPEC-008.

---

## 2026-07-27 · [A] T-013 — Validação de cena mínima

> **Agente B**: `scene.warning` já chega pelo WS com `{code, severity, hint}` — códigos
> `OUT_OF_FRAME`, `TOO_FAR`, `TOO_CLOSE`. O `hint` vem em pt-BR e pode ir direto para a tela
> enquanto o catálogo do feedback engine não estiver na frente dele.

- `workers/analysis_worker/scene.py`: `SceneValidator` (um por sessão) com as duas travas da
  SPEC-003 Fase Inicial — enquadramento pelas 4 âncoras (ombros e tornozelos, `visibility ≥ 0.5`)
  e distância pela altura do corpo entre 40% e 95% do frame — e o debounce de 1 s para ligar /
  2 s para repetir.
- Ligado no `AnalysisRouter`: a cena é checada **antes** da FSM, então um frame ruim ainda avisa
  o usuário mesmo com a FSM congelada. É exatamente quando o aviso importa.
- Decisões:
  - **Altura do corpo sai dos pontos normalizados × escala**: `(tornozelo_y − nariz_y)` em torsos
    × `torso` (unidades de frame) = fração da altura do frame. Sem isso, o validador precisaria
    dos landmarks crus e teria uma segunda porta de entrada.
  - **`OUT_OF_FRAME` tem prioridade e interrompe a checagem de distância**: sem âncoras
    visíveis, a altura viria de landmarks adivinhados pelo modelo — mediria ruído.
  - O validador **conta** os avisos (`counts`) porque a SPEC-003 manda anexá-los ao relatório
    (T-020).
  - Rosto/mãos invisíveis não são problema de enquadramento — só as 4 âncoras contam.
- Gates: `ruff` limpo, **319 testes** verdes (22 novos). Critérios da SPEC-003: 2 s fora do quadro
  ⇒ **exatamente 1 aviso** (6 s ⇒ 3 avisos, pelo intervalo de 2 s); **zero falso positivo** em
  cena padrão, inclusive durante 20 polichinelos (o movimento muda a altura aparente e não
  dispara distância); 0,5 s de falha ⇒ nenhum aviso.

---

## 2026-07-27 · [A] T-011 — Ciclo de sessão (`POST /api/sessions` + timer autoritativo)

> **Agente B**: o fluxo de abertura está pronto. `POST /api/sessions`
> `{exercise, requested_mode, probe_result}` → `{session_id, token, ws_url, mode, exercise,
> duration_s, expires_at}`. Use o `ws_url` como veio (já traz o token). Pedido de `cloud`
> responde `mode: "denied_cloud"` — Fase 0 é edge only. O **fim da sessão vem do servidor**
> (`session.completed` pelo WS); o timer do HUD é cosmético.

- `server/api/sessions.py`: `SessionRequest.parse` (validação), `create_session` (registro em
  Redis com TTL, publicação de `session.started` e, quando houver probe, `session.capability`).
- `server/api/views.py`: `POST /api/sessions` → 201 com o ticket, 400 para pedido inválido,
  503 quando o Redis está fora.
- `workers/analysis_worker/router.py`: `SessionState.expiry_reason` + `AnalysisRouter.tick()`,
  chamado a cada volta do loop do worker (roda mesmo sem evento chegando).
- Decisões:
  - **Timer no relógio do servidor, não no `ts` do cliente**: celular com relógio torto não pode
    encurtar nem esticar a sessão. Há teste com `ts` no futuro provando isso.
  - **Duas regras de fim**: 30 s desde o primeiro frame ⇒ `completed`; 10 s sem frame ⇒
    `no_data` (critério 4 da SPEC-009). A regra de TTL virou código morto e foi removida — uma
    das duas sempre vence antes dos 45 s; `timeout` fica no vocabulário para o caminho de
    semáforo/quotas (T-017/T-025).
  - **Sessão negada não nasce**: pedido de cloud não gera registro, evento nem slot.
  - Estado da sessão em Redis (hash com TTL), não em Postgres: Fase 0 é anônima e a sessão é
    efêmera. Persistir resultado é a SPEC-010 (T-020).
- Bug encontrado por teste: sessão fechada por `no_data` **sem nenhum frame** montava envelope
  com `ts=0`, que o contrato recusa. Agora o `ts` cai para o relógio do servidor.
- Bug encontrado só na verificação real (e é o mais importante do dia): com `redis-py` 8, o
  `channels_redis` estoura `TimeoutError` na leitura do channel layer e **mata o consumer do
  WebSocket** — o cliente recebia as reps e depois nada. `redis>=5.2,<6` resolveu. Nenhum teste
  pegaria isso: eles usam channel layer em memória.
- Verificado ponta a ponta com os 5 serviços no ar (curl + cliente WebSocket real):
  - `POST /api/sessions` devolve ticket com token válido para aquela sessão; `requested_mode:
    cloud` ⇒ `denied_cloud`; exercício inexistente ⇒ 400;
  - abrir o WS com o `ws_url` do ticket, mandar 3 polichinelos e **parar de enviar** ⇒ o servidor
    encerrou sozinho 11 s depois (`no_data`, 3 reps) e o cliente recebeu o fim;
  - mandando frames sem parar ⇒ o servidor encerrou em **30,0 s** com `completed` e 29 reps.
- Gates: `ruff` limpo, **297 testes** verdes (26 novos), compose com 5 serviços de pé.

---

## 2026-07-27 · [A] T-005 — Gateway Channels (WS ↔ streams)

> **Agente B**: o WebSocket está no ar. `ws://localhost:8001/ws/session/{session_id}?token=…`,
> binário/MessagePack nos dois sentidos. O gateway aceita do cliente **só**
> `pose.frame`, `session.capability` e `session.completed` (abort) — publicar `rep.detected`
> pelo cliente é recusado de propósito. De volta chegam fase, rep, cena, feedback e fim.
> Token inválido/expirado fecha com **4401**; envelope de outra sessão fecha com **4400**.

- `server/api/tokens.py`: token de sessão HMAC-SHA256 truncado (`{expira_em}.{assinatura}`),
  TTL de 45 s, comparação em tempo constante. Emitido pela API na T-011, verificado aqui.
- `server/gateway/consumers.py`: `SessionConsumer` — valida token, entra no grupo da sessão,
  valida envelope, confere que a sessão do envelope é a da URL e enfileira para publicação.
- `server/gateway/relay.py`: um consumidor por processo lê `events.analysis` (grupo `gateway`)
  e faz `group_send` ao grupo da sessão; quem tem a conexão empurra pelo WS.
- `core/asgi.py` virou `ProtocolTypeRouter` (HTTP + WS) e sobe o relay; serviço `gateway`
  (uvicorn, porta 8001) no compose.
- Decisões:
  - **`group_send` via channel layer** em vez de o relay falar direto com a conexão: com 2
    processos de gateway (ADR-002), o evento lido por um processo precisa alcançar a conexão que
    está no outro. Sem isso, metade dos feedbacks se perderia ao escalar.
  - **Publicação em tarefa separada com fila de 3** (`INGEST_BUFFER`): `receive` nunca bloqueia,
    e frame novo desbanca frame velho — é o backpressure da SPEC-002 aplicado onde o servidor
    pode aplicá-lo.
  - **`CLIENT_INGEST_TYPES`**: o cliente só publica frames, capability e encerramento. Sem essa
    lista, um navegador poderia injetar `rep.detected` e a contagem não valeria nada.
  - **Sem `daphne` em produção**: o gateway sobe com uvicorn; daphne ficou só no grupo `dev`
    porque `channels.testing` o importa.
  - Texto no WS é ignorado (o transporte é MessagePack) e envelope corrompido é logado sem
    derrubar a conexão — critério 3 da SPEC-002.
- Verificado com o compose no ar (gateway + worker + redis), cliente WebSocket real:
  - 62 `pose.frame` de 4 polichinelos ⇒ **4 `rep.detected` + 8 `exercise.phase` chegaram ao
    cliente**, e o `session.completed` voltou com `rep_count=4` (critério 1 do fluxo);
  - **latência frame → evento no cliente: mediana 18 ms, p95 28 ms, máx 31 ms** (orçamento da
    SPEC-002 é < 150 ms) — medido com envio em tempo real a 15 fps;
  - **matar o `analysis-worker` no meio da sessão não derrubou o WS** (critério 2): o cliente
    seguiu conectado, e ao religar o worker as repetições voltaram a chegar. Ressalva honesta:
    sem snapshot, a FSM recomeça e o `rep_count` reinicia — previsto para a Fase 0 (T-031);
  - token `lixo` não conecta (o servidor recusa o upgrade).
- Gates: `ruff` limpo, **271 testes** verdes (32 novos), compose com 5 serviços (o `api` não
  subiu por porta 8000 ocupada no host — registrado em Descobertas).

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

## 2026-07-27 · [B] Ponta cliente do WebSocket (envio + backpressure)

- Fecha a última task da minha fila. O cliente agora **envia** `pose.frame` a 15fps, além de
  receber os `CLIENT_PUSH_TYPES`.
- **Backpressure da SPEC-002**: fila de no máximo 3 frames; encheu, descarta o **mais antigo**.
  Frame novo vale mais que frame velho — entregar frame atrasado é pior que não entregar.
  O cliente também para de empurrar quando `bufferedAmount` passa de 64 KB.
- **Decisão sobre o `seq`** (pendência que eu tinha registrado na T-004): o contrato diz
  "monotônico por **sessão**", sem ressalva por tipo, então criei `clientSequencer.ts` — um
  contador único por sessão que todos os eventos do cliente consomem. O frame clock continua
  dono do `ts` e da decimação, mas o `seq` do envelope sai do sequenciador.
  **Consequência que o Agente A precisa saber**: o `seq` dos `pose.frame` que chegam ao
  gateway **não é contíguo**, porque a `session.capability` consome o 0. Atualizei a
  descoberta no BACKLOG com isso.
- `session.capability` é enviada no momento em que o socket abre (o probe já terminou, porque
  a sessão só conecta com a câmera de pé).
- Estados de conexão viraram faixa na tela: conectando, e um aviso laranja explícito quando
  cai — dizendo que a contagem não vai avançar e como subir o mock. Silêncio aqui seria pior:
  o usuário veria o esqueleto funcionando e o contador parado, sem explicação.
- `sessionId`/token: na Fase 0 o cliente inventa o id (`POST /sessions` é a T-011). Dá para
  forçar por `?session=` e `?token=` para teste manual. Quando a T-011 existir, id e token
  passam a vir **só** de lá.
- Gates: `tsc -b` limpo, `npm run lint` sem erros nem warnings, `npm run test` **118/118**,
  `npm run build` OK.
- **Não verificado**: o envio de ponta a ponta. O mock conta os frames que recebe, mas sem
  webcam não há frame para enviar — o caminho `câmera → pose → WS → mock` só fecha com o
  Daniel na frente da câmera.

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
