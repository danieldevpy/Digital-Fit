# SPEC-013 — Interface Mobile (Tela de Sessão & App Shell)
Status: draft | Camada: client (web/) | Depende de: SPEC-008, SPEC-009 | Referência: `referencias/ui-sessao-mobile-v1.png`

## Entidade e responsabilidade

Define a interface visual do produto a partir da referência aprovada. **Mobile-first**: o layout de referência é celular em retrato; desktop é adaptação (câmera centralizada, cards nas laterais), nunca o contrário. Esta spec é vinculante para toda task de UI.

## Anatomia da tela de sessão (da referência)

De cima para baixo, sobre a câmera em tela cheia:

**1. Barra de métricas (topo, glass card com 4 células)**

| Célula | Exemplo | Fonte do dado | Fase |
|---|---|---|---|
| SÉRIE | `2` | config da sessão (circuitos) | Evolução — inicial exibe `1` |
| REPETIÇÕES | `11/20` | `rep.detected` (contador) / meta da sessão | Contador: Inicial · Meta `/20`: Evolução |
| ÂNGULO | `128°` | ângulo articular principal do exercício, ao vivo | Inicial (edge, client-side) |
| KCAL | `420` | estimativa MET | Evolução (ver §Métricas) |

**2. Câmera + esqueleto (centro, tela cheia)**
Keypoints como pontos brancos com glow; conexões em linhas claras ~2px. Esqueleto SEMPRE visível durante a sessão (é a confiança do usuário de que "está me vendo"). Cor do esqueleto pode reagir à fase (aberto/fechado) na evolução.

**3. Card do exercício (glass card)**
Nome em itálico bold caps ("POLICHINELO"), subtítulo categoria • grupo ("CARDIO • CORPO INTEIRO" — novos campos do catálogo de exercícios), e à direita o **anel de countdown** (gradiente roxo) com `00:24` + "TEMPO RESTANTE" — este é o timer cosmético dos 30s (autoridade continua no servidor, SPEC-009).

**4. Card "Dica do Treinador" (glass card)**
É a materialização do feedback engine (SPEC-008): avatar do treinador + label "DICA DO TREINADOR" (roxo, caps) + mensagem do `feedback.issued` + botão outline "VER DETALHES" (abre o `hint` estendido do catálogo). Quando não há feedback ativo, exibe dica genérica do exercício (campo `default_tip` do catálogo) — o card nunca fica vazio.

**5. Bottom nav (5 itens)**
`Início` (ativo) · `Exercícios` · **FAB central** (waveform, gradiente roxo, elevado — inicia sessão) · `Progresso` · `Perfil`.

## Design tokens

```css
--bg: #0B0B10;                 /* fundo geral quase preto */
--surface: rgba(20,20,28,.72); /* glass cards + backdrop-blur(16px) */
--surface-border: rgba(255,255,255,.08);
--accent: #7C5CFF;             /* roxo primário */
--accent-2: #A78BFA;           /* gradiente: accent → accent-2 */
--hot: #FF8A3D;                /* laranja (kcal/energia) */
--text: #FFFFFF;  --text-dim: rgba(255,255,255,.6);
--radius: 18px;                /* cantos dos cards */
--skeleton: #EAF2FF;           /* pontos/linhas do esqueleto, com glow */
```

Tipografia: sans geométrica (Inter/Manrope); nome do exercício em itálico black caps; números de métrica grandes e tabulares (`font-variant-numeric: tabular-nums` — o contador não pode "dançar").

## Fase Inicial (redefine a T-012)

### Escopo / Comportamento

- Tela de sessão completa conforme anatomia acima, com: barra de métricas (SÉRIE fixo `1`, REPETIÇÕES sem meta, ÂNGULO ao vivo, KCAL oculto ou `--`), esqueleto sobre câmera, card do exercício + anel de 30s, card do treinador ligado ao `feedback.issued` (com `default_tip` como estado vazio), warnings de cena como estado do card do treinador com prioridade máxima.
- **Ângulo ao vivo (edge)**: calculado no cliente a partir dos landmarks (mesma fórmula de `arm_angle` da FSM, replicada em TS) — puramente cosmético/informativo; autoridade de contagem continua no worker. Atualiza no máximo a 10Hz para não piscar.
- App shell: bottom nav com as 4 telas (Exercícios/Progresso/Perfil como placeholders "em breve") + FAB iniciando o fluxo de sessão.
- Escolha do exercício na capa da câmera, junto com a preparação (T-051): é o instante em que importa — logo antes de treinar e antes de a sessão abrir. **Não desenha nada enquanto o catálogo tiver um item só**; a aba Exercícios (Fase Evolução) é a superfície de navegar e conhecer, esta é a escolha rápida de quem já sabe o que veio fazer.
- Mobile-first: layout de referência em ≤ 480px; desktop adapta com a mesma hierarquia.

### Fora de escopo (vai para Evolução)

Séries/circuitos, meta de reps, kcal, cor do esqueleto por fase, telas reais de Exercícios/Progresso/Perfil, animações elaboradas.

### Critérios de aceite

1. Em um celular real (Chrome Android), a tela de sessão reproduz a referência: 4 zonas na ordem correta, glass cards, esqueleto visível sobre a câmera.
2. Contador de reps e anel de countdown atualizam sem layout shift (números tabulares).
3. Card do treinador: mostra `default_tip` sem feedback ativo; troca para `feedback.issued` em < 150ms; warnings de cena têm prioridade sobre dicas de execução (herda regras da SPEC-008).
4. Ângulo exibido difere < 5° do calculado pelo worker para a mesma sequência (fixture de teste).

## Fase Evolução

- **Meta de repetições** (`11/20`): `target_reps` opcional na config da sessão (SPEC-009); ao atingir a meta antes dos 30s → celebração + sessão completa com `reason: "target_reached"`.
- **Séries/circuitos**: treino = N séries de 30s com descanso configurável; célula SÉRIE ativa; tela de descanso com countdown e próximo exercício (SPEC-009 evolução).
- **KCAL**: estimativa MET — `kcal = MET × 3,5 × peso ÷ 200 × minutos` (polichinelo ≈ 8 MET). Peso do perfil do usuário (SPEC-011); sem perfil, default 70kg com indicação de "estimado". Valor acumulado do dia (como na referência) exige histórico (SPEC-010).
- **Modo cloud**: ângulo ao vivo vem do servidor (evento `metrics.update` a ~5Hz — adicionar ao contrato quando chegar aqui) para o cliente fraco não calcular nada.
- Esqueleto reage à fase (`exercise.phase`): cor/glow muda em aberto/fechado; trilha de acerto na rep válida.
- Telas reais: Exercícios (catálogo com categoria/grupo muscular — campos já no card), Progresso (SPEC-010 histórico), Perfil (SPEC-011).
- Coach por voz (SPEC-008 evolução) sincronizado com o card do treinador.

## Eventos consumidos

`rep.detected`, `feedback.issued`, `scene.warning`, `exercise.phase`, `session.started/completed` — exatamente os `CLIENT_PUSH_TYPES` do contrato v1. A UI **não exige nenhum evento novo** na fase inicial (ângulo é client-side). `metrics.update` só na evolução (modo cloud).

## Notas técnicas

- Catálogo de exercícios (client) ganha campos: `display_name`, `category` ("Cardio"), `muscle_group` ("Corpo inteiro"), `default_tip`, `main_angle` (qual ângulo exibir: polichinelo = abdução do braço).
- Glass effect: `backdrop-filter` tem custo em mobile — máximo 3 superfícies com blur simultâneas (topo, card exercício, card treinador); bottom nav pode ser sólido.
- Esqueleto em `<canvas>` sobreposto ao `<video>`; desenhar no mesmo rAF do frame clock (SPEC-001) para não duplicar loops.
- A imagem de referência é a fonte visual; divergências intencionais devem ser anotadas nesta spec (seção futura "Desvios da referência").
