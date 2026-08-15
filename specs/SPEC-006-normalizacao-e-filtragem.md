# SPEC-006 — Normalização & Filtragem
Status: draft | Camada: worker | Depende de: SPEC-005

## Entidade e responsabilidade

Converte `pose.frame` cru em keypoints **canônicos**: invariantes a posição da câmera, tamanho do corpo e jitter. É a fronteira entre "dados de visão" e "dados de movimento" — tudo depois daqui raciocina em unidades corporais.

## Fase Inicial

### Escopo / Comportamento

0. **Isotropia** (T-110): `x` chega dividido pela **largura** do frame e `y` pela **altura**,
   então os dois eixos não são comparáveis. Multiplicar `x` por `largura ÷ altura` põe ambos em
   unidades de **altura de frame**. As dimensões viajam no `pose.frame` (SPEC-002); ausentes, o
   espaço é tratado como isotrópico — que é o comportamento anterior a esta task e o que mantém
   fixture e cliente antigos válidos.

   Converte-se `x` para a moeda de `y`, e não o contrário, porque `torso` sai daqui em unidades
   de frame e é a régua de distância da SPEC-003: um tronco de pessoa em pé é quase todo `y`, e
   nessa direção a régua praticamente não se move (medido no corpus: ≤ 1,9%, com os avisos de
   cena idênticos nos seis vídeos).

   **Por que corrigir o espaço e não apenas exigir features de eixo único**: a alternativa
   considerada era declarar que toda feature é razão no mesmo eixo. Ela não fecha — ângulo é
   `atan2(dx, dy)` por definição, e `arm_angle` (polichinelo), `knee_angle` (agachamento) e
   `elbow_angle` (flexão) misturam os eixos por construção. Nenhuma regra de redação salva um
   ângulo; só a correção do espaço salva.
1. **Recentragem**: origem no ponto médio dos quadris (landmarks 23/24).
2. **Escala**: dividir pela distância ombro-médio→quadril-médio (torso = 1.0). Usa baseline da SPEC-004 quando disponível; senão, valor instantâneo.
3. **Suavização**: One Euro Filter por coordenada (β e mincutoff únicos globais na fase inicial).
4. **Qualidade**: frame com `visibility` média dos âncoras < 0.5 é marcado `degraded: true` (a FSM decide ignorar).
5. Saída: `pose.frame` enriquecido (`data.norm`) no mesmo evento — não cria novo tipo.

### Fora de escopo (vai para Evolução)

Interpolação de frames perdidos, rotação para alinhar eixo do corpo, filtros por exercício, outlier rejection.

### Critérios de aceite

1. Mesma sequência com pessoa a 2m e a 4m → features (SPEC-007) diferem < 5%.
2. Jitter (desvio-padrão de landmark parado) reduz ≥ 60% após filtro, sem atraso perceptível (> 1 frame) em movimento rápido.
3. Função pura: `normalize(frames_in) -> frames_out` coberta por testes com fixtures.
4. **O mesmo corpo filmado em paisagem e em retrato normaliza igual** (T-110): keypoints
   idênticos e features idênticas, incluindo as que misturam eixos. Medido antes da correção: a
   mesma largura de ombros lia 0,348 torsos em 854×480 e 1,168 em 576×1024 (razão 3,4×).

## Fase Evolução

- **Interpolação** de gaps ≤ 2 frames (linear) para estabilizar cadência com perda de pacote.
- **Alinhamento rotacional**: rotacionar para deixar a linha dos quadris horizontal — tolera câmera torta (par com SPEC-003 evolução).
- **Outlier rejection**: descartar salto de landmark > 0.5 torso entre frames consecutivos (teleporte = erro do modelo).
- Parâmetros do One Euro **por exercício** (exercício rápido tolera mais lag ≠ prancha).
- Confiança composta por membro (braço esq. ruim ≠ frame todo ruim) — feedback mais preciso.

## Eventos

Consome: `pose.frame` cru. Produz: `pose.frame` com `data.norm` (mesmo stream, campo adicional).

## Notas técnicas

- One Euro: implementação própria (~40 linhas, numpy), estado por sessão+landmark.
- Nunca filtrar `visibility` — só coordenadas.
- Este módulo é o lugar MAIS crítico para testes de regressão: qualquer mudança altera todos os exercícios.
