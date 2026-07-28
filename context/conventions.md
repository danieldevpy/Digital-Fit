# Digital Fit — Convenções

## Eventos

- Envelope obrigatório: `{v, type, session_id, ts, seq, source, data}`
- `type` em dot.case: `pose.frame`, `rep.detected`, `scene.warning`, `session.completed`
- `source`: `edge` | `cloud` | `system`
- Transporte cliente↔gateway: WebSocket binário (MessagePack). Interno: Redis Streams.
- Streams nomeados no plural do fluxo: `frames.raw`, `pose.frames`, `events.analysis`
- Novo evento ⇒ atualizar `workers/shared/events.py` (única fonte da verdade) e a spec correspondente.

## Código

- Python: 3.12+, type hints obrigatórios, `ruff` + `pytest`. Workers não importam Django.
- Lógica de análise = funções puras testáveis com fixtures de keypoints (`tests/fixtures/keypoints/`).
- Cada exercício implementa a interface `ExerciseAnalyzer` em `workers/analysis_worker/exercises/`.
- React: componentes funcionais, TypeScript, estado de sessão em um único store (zustand).
- Nomes de branch: `spec-XXX/t-YYY-descricao-curta`.

## Specs & tasks

- Toda mudança de comportamento nasce de uma SPEC; toda implementação nasce de uma task T-XXX no `BACKLOG.md`.
- Task só é `done` com: critérios de aceite atendidos + testes verdes + DEVLOG atualizado.
- Fase Evolução de uma entidade **não** entra junto com a Fase Inicial — é task separada, priorizada depois.

## Unidades e medidas

- Keypoints normalizados 0–1 relativos ao frame; após normalização corporal, unidades em "torsos" (distância ombro-médio→quadril-médio = 1.0).
- Ângulos em graus. Timestamps em ms epoch (cliente) + `seq` monotônico por sessão.
- Confiança/visibilidade: 0–1; limiar padrão 0.5.
