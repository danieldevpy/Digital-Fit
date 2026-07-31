# SPEC-020 — Catálogo Expandido: categorias, trilhas e maturidade de exercícios
Status: draft | Camada: api + client + workers(exercises) + eval | Depende de: SPEC-007, SPEC-012, SPEC-015, SPEC-016, SPEC-018 | Referência: ideia "seções e exercícios por categoria, do fácil ao difícil" (2026-07-30)

## Entidade e responsabilidade

Organiza o catálogo para crescer: **categorias** (o eixo de navegação), **maturidade** (o quão
provado cada exercício está, amarrado à bancada da SPEC-012) e **trilhas** (a sequência que dá
sensação de progresso, à la Duolingo). Também é o **roadmap vinculante de exercícios** — a
ordem de implementação não é por dificuldade física, é por dificuldade de *detecção*, e esta
spec fixa os lotes.

A tese de produto: o que vocês construíram não é um app de polichinelo, é uma **fábrica de
exercícios** (spec → módulo FSM → gerador → corpus → evalctl → produção). Esta spec é a esteira
de saída da fábrica: como um exercício novo entra no produto, com que selo de qualidade, em que
prateleira, e para quem.

## Os dois eixos (por que a ordem é esta)

**Dificuldade física ≠ dificuldade de detecção.** Prancha é fisicamente acessível e
tecnicamente difícil (estática + chão); polichinelo é o inverso do senso comum — cansativo e
trivial de detectar. O roadmap ordena pelo eixo **técnico**, porque é ele que dita risco, teste
e custo. Quatro fatores decidem o tier de um exercício:

1. **Posição da câmera**: em pé frontal (o enquadramento que a SPEC-003 valida hoje) é barato;
   chão/ângulo baixo exige evolução da validação de cena e guia de posicionamento.
2. **Amplitude**: movimento grande sobrevive a ruído de keypoint; amplitude pequena
   (panturrilha) disputa com o jitter.
3. **Periodicidade**: ciclo claro `rest ⇄ peak` reusa a FSM existente; isométrico exige a
   modalidade *hold* (SPEC-021); multi-fase exige FSMs compostas.
4. **Oclusão/eixo**: movimento no eixo Z (profundidade) some na câmera frontal — a lição
   medida do agachamento (SPEC-007: joelho a 80° lia 133°).

**Regra que organiza tudo: cada tier novo é uma capacidade do motor, e cada capacidade
destrava um LOTE de exercícios.** Não se planeja "exercício 3, exercício 4"; planeja-se
"capacidade isométrica", "capacidade chão", e os exercícios caem em grupos.

## Roadmap de exercícios (vinculante)

### Tier A — em pé, frontal, cíclico, amplitude grande (motor de hoje; custo = calibrar + corpus)

| Slug | Nome | Categoria | Físico | Detecção — esboço da feature | MET |
|---|---|---|---|---|---|
| `jumping_jack` ✅ | Polichinelo | cardio | fácil | `arm_angle` + `ankle_spread` (feito) | 8 |
| `squat` ✅ | Agachamento | forca | fácil | altura do quadril (feito; corpus T-053) | 5 |
| `marcha` | Marcha estacionária | mobilidade | muito fácil | alternância da altura dos joelhos vs quadril; rep = ciclo E+D | 3.8 |
| `elevacao_bracos` | Elevação lateral de braços | mobilidade | muito fácil | `arm_angle` sozinho (feature já existe): sobe > 100°, desce < 30° | 2.8 |
| `high_knees` | Elevação de joelhos | cardio | médio | marcha com limiar de altura maior (joelho acima do quadril) + cadência | 8 |
| `sumo_squat` | Agachamento sumô | forca | fácil | altura do quadril do `squat` + `ankle_spread` largo exigido na baseline | 5 |

**Lote 1 = marcha, elevação de braços, high knees, sumô** — quatro exercícios pelo preço de
calibração, dois deles reusando features que já existem. `marcha` e `elevacao_bracos` têm um
papel de produto específico: são os **guardiões do fogo** (SPEC-019) — o "dia leve" honesto
para o dia em que o corpo não aguenta polichinelo.

### Tier A2 — em pé, frontal, mas com fase aérea ou assimetria (motor de hoje + cuidado extra)

| Slug | Nome | Categoria | Risco |
|---|---|---|---|
| `jump_squat` | Agachamento com salto | forca | fase aérea encurta o ciclo; debounce a recalibrar |
| `afundo` | Afundo alternado | forca | perna recua no eixo Z; feature provável: queda do joelho de trás + altura do quadril |
| `polichinelo_x` | Polichinelo cruzado | cardio | cruzamento no eixo X com oclusão momentânea de tornozelo |

### Tier B — isométricos (exige a modalidade *hold* — SPEC-021)

| Slug | Nome | Categoria | Nota |
|---|---|---|---|
| `wall_sit` | Agachamento isométrico | forca | o isométrico mais barato: em pé, frontal, reusa a altura do quadril do `squat` |
| `prancha` | Prancha | core | hold **+** chão → precisa do Tier C também |

O Tier B compensa cedo: construída a modalidade hold, toda a categoria mobilidade/alongamento
(segurar posição X por Y segundos) entra quase de graça — e é o conteúdo natural do dia leve.

### Tier C — chão / ângulo de câmera baixo (exige evolução da SPEC-003: guia de posicionamento, validação de cena deitada)

| Slug | Nome | Categoria | Risco |
|---|---|---|---|
| `flexao` | Flexão de braço | forca | visão lateral é muito melhor que frontal; guiar o usuário a deitar o celular |
| `abdominal` | Abdominal (crunch) | core | oclusão de pernas, amplitude pequena |
| `mountain_climber` | Mountain climber | cardio | rápido + chão + oclusão — o mais arriscado do tier |
| `ponte` | Elevação de quadril | forca | médio |

### Tier D — compostos multi-fase (FSMs encadeadas)

| Slug | Nome | Nota |
|---|---|---|
| `burpee` | Burpee | squat + prancha + salto; só depois de B e C existirem |

## Maturidade (o selo de qualidade, amarrado à bancada)

Campo `maturity` no catálogo, com critérios **mensuráveis** — formaliza o "os difíceis
precisam de mais teste" usando o que a SPEC-012 já construiu:

| Nível | Critério | Quem vê |
|---|---|---|
| `beta` | limiares calibrados no gerador sintético (T-052); fixtures verdes | só contas com ferramentas de dev (`is_admin`) |
| `calibrado` | corpus real ≥ 8 vídeos rotulados no `evalctl`, erro ≤ ±1 rep/20; varredura de limiares registrada no DEVLOG | assinante, com selo **Laboratório 🧪** |
| `validado` | calibrado **+** paridade edge×cloud×browser (fluxo T-040) **+** ≥ 1 semana em produção sem anomalia (taxa de sessões zero-rep do exercício < 20% — o sintoma medido em `[A/T-032]` de exercício errado/quebrado) | todo mundo; único nível que entra em trilha |

O **Laboratório** transforma o assinante em beta tester voluntário — e em fonte de corpus: o
dataset-writer já grava keypoints de toda sessão (SPEC-010), então cada sessão de Laboratório é
material de calibração. O selo diz a verdade ("em validação: a contagem pode errar") e o
assinante ganha acesso antecipado como benefício real. Rebaixar maturidade (regressão medida)
tira o exercício do ar para Free sem deploy — é exatamente o `enabled` da SPEC-018 com nuance.

### Definition of done de um exercício novo (checklist vinculante de toda task de exercício)

1. Módulo em `workers/analysis_worker/exercises/` (FSM pura ou hold, SPEC-007/021), sem tocar
   fora de `exercises/` — a meta auditada da SPEC-007 vale como gate.
2. Gerador sintético estendido (T-052) com o parâmetro do movimento + fixtures (limpas,
   preguiçosas, jitter, começa-no-meio).
3. Sinais de qualidade definidos (o `*_TOO_*` do exercício) + textos no catálogo de feedback.
4. Figura própria em `EXERCISE_FIGURES` (o teste da T-082 já cobra) + demo image + passos do
   Guia (SPEC-015).
5. Entrada no catálogo com categoria, MET, `maturity: beta`.
6. Promoções de maturidade são **tasks separadas** (gravar corpus é trabalho de outra
   natureza — o T-053 do agachamento é o precedente).

## Categorias

Vocabulário **em código** (choices, não tabela): `cardio`, `forca`, `core`, `mobilidade` —
categoria é contrato do produto (conquistas da SPEC-019 e seleção da SPEC-022 dependem dos
slugs), não conteúdo editável. Nome de exibição e cor do dot ficam onde já estão
(catálogo/`Exercise` da SPEC-018). Criar categoria nova = commit, e está certo assim: uma
categoria órfã criada por formulário quebraria os consumidores em silêncio.

## Trilhas

**Trilha** = sequência ordenada de passos; **passo** = exercício + meta cumulativa. A
progressão é **derivável** (mesmo princípio da SPEC-019): passo concluído = N sessões válidas
daquele exercício (default 3) na conta, contadas de `SessionResult` — sem tabela de progresso,
sem estado que dessincroniza. Destrave sequencial: o passo n abre quando o n−1 conclui.

Modelo (dado, admin da SPEC-018): `Trilha(slug, nome, ordem, min_plan)` e
`TrilhaItem(trilha FK, ordem, exercise FK, sessoes_para_concluir)`. Trava: item só aceita
exercício `validado` — trilha é a prateleira premium da confiança; Laboratório nunca entra.

Fase Inicial: **uma** trilha, *Fundamentos* — marcha → polichinelo → elevação de braços →
agachamento → sumô → high knees (do mais fácil ao mais difícil **físico**, já que o técnico é
todo Tier A). Renderiza como seção no topo da tela Escolha: passos com anel de progresso
(2/3), cadeado nos ainda fechados. UI de caminho completa (unidades, checkpoints, mapa) é
Evolução — primeiro validar que trilha muda retenção, depois embelezar.

## Onde cada plano toca o catálogo

| | Anônimo | Free | Assinatura |
|---|---|---|---|
| Exercícios `validado` | todos | todos | todos |
| Laboratório (`calibrado`) | — | vê com cadeado "assinante" | treina, com selo honesto |
| Trilhas | vê com cadeado "conta" | Fundamentos | todas (quando houver mais) |
| Cadeado sempre diz o **motivo** | "crie conta" | "assinante" / "em validação" | — |

Exercício `validado` não é moeda de plano na Fase Inicial — a variedade base é o produto bom
do Free (SPEC-016); o que a assinatura compra aqui é *antecipação* (Laboratório) e, adiante,
trilhas temáticas. Exclusividade de exercício validado fica possível pelo `min_plan` da
SPEC-018, decisão comercial futura.

## Fase Inicial

### Escopo / Comportamento

- Campos `maturity` e `met` no catálogo (`Exercise` da SPEC-018 + espelho no cliente), com as
  regras de visibilidade por plano/maturidade resolvidas no `GET /api/config` e **na admissão**
  (`POST /sessions` recusa exercício que o plano não pode — a UI nunca é a única trava).
- Tela Escolha agrupada por categoria, cadeados com motivo.
- Lote 1: `marcha`, `elevacao_bracos`, `high_knees`, `sumo_squat` — cada um pela checklist,
  nascendo `beta`; promoção a `calibrado` via corpus em tasks próprias.
- Trilha Fundamentos (modelo + derivação de progresso + seção na Escolha).
- Selo Laboratório na UI (badge 🧪 + frase honesta na pré-config do exercício).

### Fora de escopo (vai para Evolução)

Tiers A2/C/D (cada um vira tasks quando seu pré-requisito existir); UI de caminho completa;
múltiplas trilhas; GIFs de demonstração (T-066); detecção automática de exercício (SPEC-007
Evolução); programa formal de coleta do Laboratório com consentimento explícito para pesquisa.

### Critérios de aceite

1. Free não vê nem consegue abrir sessão de exercício `calibrado`/`beta` (recusa na admissão
   com mensagem clara, mesmo forjando o client).
2. Assinante abre `calibrado` e a pré-config mostra o selo Laboratório.
3. Rebaixar `validado → calibrado` no admin some o exercício do Free **sem deploy** e sem
   quebrar sessão em andamento.
4. Trilha: concluir 3 sessões válidas do passo 1 destrava o passo 2; progresso sobrevive a
   recálculo do zero.
5. Cada exercício do Lote 1 passa a checklist (fixtures + figura + guia + feedback) e o teste
   da T-082 cobra a figura.
6. `evalctl run` roda os 4 novos contra o gerador; o corpus real de cada um tem task própria
   aberta.

## Fase Evolução

Tier A2 (jump squat, afundo, polichinelo cruzado); trilhas por categoria e por objetivo
(alimentam a SPEC-022); checkpoints com critério agregado ("50 reps combinadas"); mapa visual
da trilha; corpus colaborativo do Laboratório com consentimento e recompensa (XP/conquista);
promoção/rebaixamento de maturidade semi-automático a partir da taxa de zero-rep em produção.

## Eventos (consome / produz)

Nenhum evento novo. Consome `SessionResult` (progresso de trilha) e o catálogo via
`GET /api/config` (SPEC-018). A admissão continua sendo o único juiz do que pode abrir.

## Notas técnicas

- MET no catálogo é o insumo do kcal (SPEC-016/017) — valores de tabela (Compendium), uma casa
  decimal, sem promessa de precisão individual.
- O espelho client (`web/src/session/catalog.ts`) continua sendo default de primeiro paint e
  fallback offline (SPEC-018 §Como cada consumidor lê); servidor vence quando chega.
- `marcha` e `high_knees` compartilham a feature de altura de joelho — implementar como feature
  única parametrizada, dois módulos finos por cima (mesma relação `squat`/`sumo_squat`).
- Trilha deriva de consulta já paga pelo engajamento (SPEC-019 agrega por exercício) — uma
  passada, dois consumidores.
