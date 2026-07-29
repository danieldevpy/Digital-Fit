# SPEC-007 — Análise de Exercício (FSM & Reps)
Status: draft | Camada: worker | Depende de: SPEC-006, SPEC-004

## Entidade e responsabilidade

O cérebro: recebe keypoints canônicos e produz repetições, fases do movimento e sinais de qualidade. Cada exercício é um módulo plugável implementando `ExerciseAnalyzer`.

## Interface (contrato desde o dia 1)

```python
class ExerciseAnalyzer(Protocol):
    slug: str  # "jumping_jack"

    def features(self, frame: NormFrame) -> dict: ...
    def step(self, feats: dict, ts: int) -> list[AnalysisEvent]: ...  # FSM stateful
    def initial_phase(self, feats: dict) -> Phase: ...  # fase LIDA do 1º frame (T-047)
    def ready_pose(self, feats: dict) -> bool: ...  # usado na evolução da SPEC-004
    def scene_hints(self) -> SceneHints: ...  # distância ideal etc. (SPEC-003 evolução)
    def summary(self) -> dict: ...  # p/ relatório (SPEC-010)
```

## Fase Inicial — polichinelo (`jumping_jack`)

### Escopo / Comportamento

- Features: `arm_angle` (média da abdução dos 2 braços), `wrist_above_shoulder`, `ankle_spread` (÷ largura de ombros da baseline), `cadence_10s`.
- FSM `FECHADO ⇄ ABERTO`:
  - abre: `arm_angle > 110°` E `ankle_spread > 1.4`
  - fecha: `arm_angle < 40°` E `ankle_spread < 0.9` → **1 rep** (`rep.detected`)
  - Histerese (limiares assimétricos) + debounce (fase mínima 250ms).
  - **Fase inicial lida, não assumida** (T-047): o primeiro frame utilizável decide onde a FSM
    começa, pelos mesmos limiares de abertura e exigindo os **dois**. Nascer sempre em
    `FECHADO` perdia o ciclo quando a captura já abria com a pessoa aberta; aceitar a fase com
    um limiar só criaria repetição fantasma para quem se posiciona com o braço erguido. Frame
    intermediário ou `degraded` ⇒ `FECHADO`.
- Frames `degraded` são ignorados pela FSM (estado congela; não conta nem penaliza).
- Reps parciais geram sinais de qualidade: pico de `arm_angle` entre 70–110° → `ARMS_TOO_LOW`; pico de `ankle_spread` entre 1.1–1.4 → `LEGS_TOO_CLOSED` (roteados via SPEC-008).
- Usuário **seleciona** o exercício — nada de detecção automática ainda.

### Fora de escopo (vai para Evolução)

Outros exercícios, detecção automática do exercício, score de forma por rep, thresholds personalizados.

### Critérios de aceite

1. Fixture de 20 polichinelos limpos → exatamente 20 reps.
2. Fixture com 3 reps "preguiçosas" → reps não contadas + sinais de qualidade corretos.
3. Fixture com jitter/tremor parado → 0 reps (nenhum falso positivo).
4. `step()` processa 1 frame em < 1ms (garante ~2% CPU/sessão da estimativa de capacidade).
5. Fixture que **começa no meio de uma repetição** (pessoa já aberta) conta essa repetição; e
   pessoa parada com os braços erguidos e os pés juntos conta **zero** ao baixar os braços.

## Fase Evolução

- **Novos exercícios**: agachamento (ângulo do joelho + profundidade do quadril), flexão (ângulo do cotovelo + alinhamento do corpo), prancha (hold time + ângulo quadril — modalidade *tempo*, não *reps*; a interface já suporta via eventos `hold.progress`).
- **Form score por rep** (0–100): amplitude, simetria esq/dir, estabilidade do tronco.
- **Detecção automática do exercício**: classificador temporal (janela 2–3s, 1D-CNN/ST-GCN leve em ONNX) treinado com o dataset da SPEC-010; a FSM continua validando a execução (ML identifica, regras julgam).
- **Thresholds adaptativos** por perfil do usuário (mobilidade reduzida ≠ atleta) — par com perfil corporal da SPEC-004.
- Cadência-alvo e zonas (aquecimento/intenso) configuráveis por plano de treino.

## Eventos

Consome: `pose.frame` (norm). Produz: `rep.detected`, `quality.signal`, `exercise.phase` — habilita animações no HUD.

O contrato carrega o par **neutro** `rest`/`peak` (T-050), não o vocabulário de um exercício. No polichinelo `rest` é fechado e `peak` é aberto; no agachamento, em pé e embaixo. `closed`/`open` no envelope obrigaria todo consumidor a saber de que exercício se trata para entender a palavra. **A palavra de tela é do cliente**: o catálogo de exercícios do web é quem traduz a fase, quando alguma tela precisar mostrá-la — hoje nenhuma mostra.

## Notas técnicas

- FSM = classe pura sem I/O; o worker apenas alimenta e publica. Testes 100% via fixtures.
- Estado por sessão: snapshot em Redis hash a cada 2s (retomada pós-crash, SPEC-009).
- Um novo exercício NÃO pode exigir mudanças fora de `exercises/` — se exigir, a interface está errada (revisar esta spec).
  - **Auditado antes da T-032 e a regra NÃO se sustenta como escrita.** O que de fato é
    agnóstico: registro por slug, validação do slug no `POST /sessions`, roteamento por sessão,
    relatório, Parquet e o feedback engine (mensagem é dado, não código). O que ainda exige
    mudança fora: `Phase` é `CLOSED/OPEN`, vocabulário de polichinelo, e está no envelope, no
    Postgres e no Parquet (**T-050**); o cliente não tem como escolher o exercício (**T-051**);
    e o gerador de fixtures só sabe montar polichinelos, o que deixaria a FSM 2 sem critério de
    aceite (**T-052**). A regra vale como meta e as três tasks existem para torná-la verdadeira
    — ela não deve ser lida como descrição do estado atual.
