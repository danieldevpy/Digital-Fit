# SPEC-003 — Validação de Cena
Status: draft | Camada: client (edge) / worker (cloud) | Depende de: SPEC-005, SPEC-006

## Entidade e responsabilidade

Garante que a cena permite análise confiável **antes e durante** a sessão: luz, distância, enquadramento e ângulo da câmera. É a entidade que "padroniza" o exercício — condição de qualidade dos dados de todo o resto.

## Fase Inicial

### Escopo / Comportamento (travas mínimas)

- **Enquadramento**: corpo inteiro visível = os 4 landmarks-âncora (ombros e tornozelos) com `visibility ≥ 0.5`. Falhou por > 1s → `scene.warning {code: OUT_OF_FRAME}` e HUD mostra silhueta-guia.
- **Distância (proxy grosseiro)**: altura do corpo (cabeça→tornozelo) entre 40% e 95% da altura do frame. Fora disso → `TOO_FAR` / `TOO_CLOSE`.
- Warnings **não bloqueiam** a sessão na fase inicial — apenas orientam e são anexados ao relatório.

### Fora de escopo (vai para Evolução)

Análise de luz, ângulo/tilt da câmera, fundo, oclusões, bloqueio de início por cena ruim.

### Critérios de aceite

1. Sair do quadro por 2s gera exatamente um warning (com debounce), não spam.
2. Warnings aparecem no HUD em < 300ms e constam no relatório final.
3. Zero falso-positivo de `TOO_FAR` em cena padrão (pessoa a 2–3m, câmera na cintura/peito).

## Fase Evolução

- **Luz**: histograma de luminância do frame (só cloud, ou amostrado 1×/s no edge via canvas): média < 60 → `LOW_LIGHT`; estouro > 15% de pixels saturados → `BACKLIT`. Sugestões acionáveis ("acenda a luz / vire de frente para a janela").
- **Ângulo da câmera**: inclinação da linha ombro-ombro e quadril-quadril vs. horizontal + razão torso aparente → detecta câmera muito baixa/alta ou pessoa não-frontal → `CAMERA_TILT`, `NOT_FACING`.
- **Distância ótima por exercício**: cada `ExerciseAnalyzer` declara faixa ideal (polichinelo: corpo a 60–85% do frame).
- **Gate de início**: sessão só inicia com cena `OK` por 1s contínuo (integra com SPEC-004); durante a sessão, cena ruim por > 3s pausa a contagem (não conta rep com dado ruim).
- **Score de qualidade da cena** (0–100) anexado à sessão — vira filtro de qualidade do dataset (SPEC-010).

## Eventos

Produz: `scene.warning {code, severity, hint}` · `scene.status {ok|degraded, score}` (evolução).
Consome: `pose.frame` (+ amostras de frame no modo cloud para análise de luz).

## Notas técnicas

- Toda checagem baseada em keypoints roda nas duas modalidades (edge/cloud) com o MESMO código Python no worker; no edge, réplica TS mínima apenas para feedback instantâneo de enquadramento.
- Debounce padrão de warnings: 1s para ligar, 2s para repetir o mesmo código.
