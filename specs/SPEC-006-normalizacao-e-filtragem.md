# SPEC-006 — Normalização & Filtragem
Status: draft | Camada: worker | Depende de: SPEC-005

## Entidade e responsabilidade

Converte `pose.frame` cru em keypoints **canônicos**: invariantes a posição da câmera, tamanho do corpo e jitter. É a fronteira entre "dados de visão" e "dados de movimento" — tudo depois daqui raciocina em unidades corporais.

## Fase Inicial

### Escopo / Comportamento

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
