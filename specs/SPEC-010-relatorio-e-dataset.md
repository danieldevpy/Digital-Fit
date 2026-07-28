# SPEC-010 — Relatório, Persistência & Dataset
Status: draft | Camada: worker (consumers) | Depende de: SPEC-007, SPEC-008, SPEC-009

## Entidade e responsabilidade

Consumers do fim da cadeia: consolidam a sessão em relatório para o usuário, persistem resultados no Postgres e acumulam o dataset de keypoints que financia o ML futuro. **Nunca no hot path** — tudo assíncrono pós-eventos.

## Fase Inicial

### Escopo / Comportamento

**report-builder** (consumer de `events.analysis`):
- Ao receber `session.completed`, consolida: total de reps, cadência média e por janela de 5s, duração efetiva, feedbacks emitidos (código + contagem), warnings de cena.
- Persiste `SessionResult` no Postgres; emite `session.report.ready {session_id}`.
- Cliente busca `GET /api/sessions/{id}/report` → tela de relatório (reps, gráfico de cadência, dicas do que melhorar).

**dataset-writer** (consumer de `pose.frames`):
- Grava sequências normalizadas por sessão em Parquet: `dataset/{date}/{session_id}.parquet` (colunas: seq, ts, 33×4 floats, degraded, exercise, source).
- ~30s @15fps ≈ 450 frames ≈ 250KB — custo desprezível, valor enorme.

### Fora de escopo (vai para Evolução)

Histórico/progresso entre sessões, exportação, anonimização formal, pipeline de treino.

### Critérios de aceite

1. Relatório disponível ≤ 2s após o fim da sessão.
2. Crash do report-builder → evento fica pendente no consumer group e é processado ao reiniciar (nenhuma sessão sem relatório).
3. Parquet legível por pandas com schema documentado; sessões `aborted` sem frames não geram arquivo.

## Fase Evolução

- **Histórico e progresso**: evolução de reps/cadência/form score por semana; recordes pessoais; streaks.
- **Filtro de qualidade do dataset**: só sessões com scene score ≥ X (SPEC-003 evolução) entram no conjunto de treino.
- **Rotulagem**: ferramenta interna simples para marcar sessões (exercício correto? reps corretas?) → ground truth do classificador (SPEC-007 evolução).
- **Pipeline de treino**: notebook/script versionado que lê os Parquet e treina o classificador temporal; modelo versionado em `models/`.
- Retenção e anonimização: keypoints não identificam rosto, mas definir política de retenção e opt-out (pré-requisito de SaaS sério, par com SPEC-011).

## Eventos

Consome: `pose.frames`, `events.analysis`. Produz: `session.report.ready`.

## Notas técnicas

- Escrita Parquet com pyarrow, buffer em memória por sessão, flush no `session.completed`.
- Relatório é derivável 100% por replay dos eventos — o builder não guarda estado próprio além do buffer da sessão.
