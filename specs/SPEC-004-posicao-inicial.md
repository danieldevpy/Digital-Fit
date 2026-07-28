# SPEC-004 — Posição Inicial & Calibração
Status: draft | Camada: worker (+ HUD) | Depende de: SPEC-003, SPEC-006, SPEC-007

## Entidade e responsabilidade

Garante que a contagem só começa com o usuário **pronto e na postura inicial do exercício**, e calibra as medidas de referência do corpo daquele usuário naquela sessão (escala do torso, largura de ombros em repouso, alcance dos braços).

## Fase Inicial

### Escopo / Comportamento

- Countdown fixo **3-2-1** após o usuário clicar "iniciar" — sem gate por pose ainda.
- Durante o countdown, captura-se a **baseline**: mediana de 1s de `shoulder_width`, `torso_len` e posição de repouso dos pulsos. Baseline entra no estado da sessão e é usada pela normalização (SPEC-006) e pela FSM (SPEC-007).
- Se baseline não puder ser medida (corpo fora do quadro), countdown reinicia com aviso.

### Fora de escopo (vai para Evolução)

Gate por pose de prontidão, detecção de posição inicial específica por exercício, recalibração no meio da sessão.

### Critérios de aceite

1. Baseline calculada em 100% das sessões iniciadas com corpo no quadro.
2. Baseline com corpo fora do quadro → reinicia countdown, nunca inicia sessão sem baseline.
3. ~~Thresholds da FSM do polichinelo passam a usar baseline (`ankle_spread` relativo à largura de ombros MEDIDA).~~ **Corrigido na T-019 com medição.** A baseline alimenta a escala da normalização (SPEC-006) e vai no `session.calibrated` para relatório e para o gate de prontidão (T-030) — mas **não** entra no divisor de `ankle_spread`. O divisor por frame se autocorrige: com a pessoa em ângulo, abertura dos pés e largura de ombros encurtam juntas em perspectiva, e a razão se mantém. Fixá-lo destrói essa invariância. No corpus: trocar por `baseline.shoulder_span` levou o vídeo frontal de 20/20 a 18/20, e a varredura de limiares que consertava o frontal derrubava o vídeo oblíquo de 19/21 a 3/21 — não há fator global que sirva aos dois. O critério original pressupunha uma largura "assumida" no código, que nunca existiu: a FSM sempre mediu por frame.

## Fase Evolução

- **Gate de prontidão**: countdown só dispara quando a pose de prontidão do exercício for detectada e mantida por 1s (polichinelo: em pé, braços ao lado do corpo, pés juntos). HUD com silhueta-alvo e preenchimento progressivo.
- **Pose inicial por exercício** declarada na interface `ExerciseAnalyzer` (`ready_pose()` → predicado sobre features).
- **Recalibração**: se a escala do torso variar > 20% (pessoa se aproximou/afastou), recalibrar baseline em janela deslizante.
- **Perfil corporal persistente** (opt-in): médias por usuário entre sessões para acelerar prontidão e personalizar thresholds.

## Eventos

Produz: `session.calibrated {baseline}` · `ready.progress {pct}` (evolução).
Consome: `pose.frame` normalizado, `scene.status`.

## Notas técnicas

- Baseline por mediana (robusta a outliers de jitter), nunca média simples.
- A FSM (SPEC-007) recebe a baseline via estado da sessão — sem acoplamento direto entre entidades.
