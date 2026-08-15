# SPEC-002 — Transporte & Contrato de Eventos
Status: draft | Camada: client + gateway | Depende de: SPEC-001

## Entidade e responsabilidade

Move eventos entre cliente e servidor (WebSocket binário) e dentro do servidor (Redis Streams). Dono do **envelope de eventos** e do arquivo `workers/shared/events.py` — a única fonte da verdade do contrato.

## Fase Inicial

### Escopo / Comportamento

- WS em `wss://…/ws/session/{session_id}?token=…`, autenticado pelo token da sessão (SPEC-009).
- Serialização **MessagePack**; envelope: `{v, type, session_id, ts, seq, source, data}`.
- Gateway (Django Channels) publica no stream certo: `frame.raw` → `frames.raw`; `pose.frame` → `pose.frames`.
- Gateway assina `events.analysis` (consumer group `gateway`) e empurra `rep.detected` / `feedback.issued` / `session.completed` ao cliente conectado.
- **Backpressure simples**: se buffer de envio do cliente > 3 frames, descarta o mais antigo (frame novo vale mais que frame velho).
- Streams com `MAXLEN ~ 5000` (aprox.) para nunca estourar RAM.

### Fora de escopo (vai para Evolução)

Reconexão com resume, compressão delta de keypoints, WebRTC, multi-gateway.

### Critérios de aceite

1. Round-trip `pose.frame` → análise → `rep.detected` no cliente < 150ms na rede local.
2. Matar e religar o worker de análise não derruba o WS do cliente.
3. Evento com envelope inválido é rejeitado e logado, sem quebrar o gateway.
4. Redis nunca ultrapassa o MAXLEN configurado sob carga.

## Fase Evolução

- **Reconexão com resume**: cliente guarda último `seq` confirmado; ao reconectar em ≤ 5s, sessão continua (importante em mobile).
- **Delta encoding** de keypoints (enviar diferenças) — reduz ~60% da banda edge.
- Heartbeat/latência medida por sessão exposta na telemetria.
- Extração do gateway para serviço próprio se virar gargalo (ADR-002) — o contrato não muda.

## Eventos

Dono do envelope de TODOS os eventos. Tabela completa em `ARCHITECTURE.md` §5.

### Contrato v1 publicado (T-002)

Fonte da verdade: `workers/shared/events.py`. O código manda; esta tabela é vista de leitura.

| `type` | Produtor | Stream padrão | `data` |
|---|---|---|---|
| `session.capability` | cliente | `pose.frames` | `mode, probe_fps, webgl, ua` |
| `session.started` | api | `pose.frames` | `exercise, mode, duration_s` |
| `pose.frame` | cliente (edge) / pose-worker (cloud) | `pose.frames` | `landmarks[33]`, `norm?`, `degraded?`, `width?`+`height?` |
| `exercise.phase` | analysis-worker | `events.analysis` | `phase: rest\|peak` (par neutro, T-050) |
| `rep.detected` | analysis-worker | `events.analysis` | `rep_count, phase, duration_ms` |
| `quality.signal` | analysis-worker | `events.analysis` | `code, value?, rep_index?` |
| `scene.warning` | worker de cena | `events.analysis` | `code, severity, hint?` |
| `feedback.issued` | feedback engine | `events.analysis` | `code, severity, message, hint?` |
| `session.completed` | analysis-worker / api | `events.analysis` | `reason, rep_count` |

- Envelope: `{v: 1, type, session_id, ts (epoch ms), seq (monotônico por sessão), source, data}`.
  Fora do contrato ⇒ `EventValidationError` (o gateway loga e descarta — critério 3).
- `pose.frames` é o fluxo de **entrada** da análise (frames + metadados da sessão);
  `events.analysis` é a **saída** dela (HUD, relatório, dataset).
- No stream, o envelope viaja em **um único campo** (`e`) do `XADD`, com a mesma serialização
  MessagePack do WebSocket — nunca espalhado em colunas.
- O gateway empurra ao cliente apenas `CLIENT_PUSH_TYPES` (fase, rep, cena, feedback, fim):
  `pose.frame` nunca volta e `quality.signal` é insumo interno do feedback engine.
- `width`/`height` do `pose.frame` (T-110) são as dimensões do frame de onde os landmarks
  saíram, e existem porque `x` vem dividido pela largura e `y` pela altura — sem elas o espaço
  normalizado herda o formato do vídeo (SPEC-006, item 0). São **aditivos e opcionais**: vêm os
  dois ou nenhum (um sozinho é rejeitado), e a ausência significa "trate como isotrópico", que
  é o comportamento anterior. Por isso **não** houve bump de `PROTOCOL_VERSION`: cliente antigo
  com servidor novo, e o contrário, continuam se entendendo.
- Eles viajam **por frame**, e não uma vez na abertura da sessão, porque o aparelho pode girar
  no meio do treino — carimbar a dimensão no `session.started` seria assumir que ninguém vira o
  celular.
- Medido: `pose.frame` com 33 landmarks = ~1,3 KB ⇒ ~20 KB/s a 15 fps (dentro do orçamento
  de banda edge do `ARCHITECTURE.md` §4).
- Fora da v1, por fase: `frame.raw` (T-015/SPEC-005), `session.report.ready` (T-020/SPEC-010),
  `scene.status` e `hold.progress` (Fase Evolução das SPEC-003/007).

## Notas técnicas

- `events.py` declara os eventos como dataclasses + validação leve (sem pydantic pesado nos hot paths).
- Consumer groups: `pose-workers` em `frames.raw`; `analysis` em `pose.frames`; `gateway`, `report`, `dataset` em `events.analysis`/`pose.frames`.
