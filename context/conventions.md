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

## Derivação (gamificação, progresso, trilhas — SPEC-019/020/022)

- Feature de produto sobre dados de treino é **derivação pura** de `SessionClaim`+`SessionResult`:
  função sem I/O, recomputável do zero, data/"hoje" como parâmetro (sem mock de relógio).
  Estado persistido novo só para fato não-derivável, justificado na spec.
- Fuso da virada de dia do engajamento: **America/Sao_Paulo fixo** (a quota da SPEC-016 usa
  UTC — divergência intencional). Conversão na derivação, armazenamento sempre em UTC.
- Fórmulas com efeito acumulado (XP) são **versionadas em código** (`XP_FORMULA_V`); mudou a
  fórmula, incrementa e recalcula tudo.
- Cache de derivação em Redis é otimização, nunca fonte: recalcular do zero reproduz o cache,
  e Redis fora degrada para consulta direta (P2 da SPEC-018).

## Exercícios & maturidade (SPEC-020/021)

- Exercício novo segue a checklist da SPEC-020 (skill `df-exercise`): módulo em
  `exercises/`, gerador sintético, 4 fixtures canônicas, sinais de qualidade, figura
  (teste da T-082 cobra), guia, catálogo com categoria+MET, nasce `beta`.
- Maturidade: `beta` (gerador) → `calibrado` (corpus real ≥8 vídeos no `evalctl`, erro ≤ ±1/20)
  → `validado` (paridade edge×cloud×browser + 1 semana de produção sem anomalia). Promoção é
  task separada. Free só vê `validado`; `calibrado` é o Laboratório 🧪 do assinante.
- Feature compartilhada entre exercícios é **importada**, nunca copiada.
- Câmera é frontal: features vivem no plano X/Y (o eixo Z mente — lição medida do agachamento).

## Specs & tasks

- Toda mudança de comportamento nasce de uma SPEC; toda implementação nasce de uma task T-XXX no `BACKLOG.md`.
- Task só é `done` com: critérios de aceite atendidos + testes verdes + DEVLOG atualizado.
- Fase Evolução de uma entidade **não** entra junto com a Fase Inicial — é task separada, priorizada depois.

## Unidades e medidas

- Keypoints normalizados 0–1 relativos ao frame; após normalização corporal, unidades em "torsos" (distância ombro-médio→quadril-médio = 1.0).
- Ângulos em graus. Timestamps em ms epoch (cliente) + `seq` monotônico por sessão.
- Confiança/visibilidade: 0–1; limiar padrão 0.5.
