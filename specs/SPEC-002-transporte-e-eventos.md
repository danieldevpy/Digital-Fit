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

## Notas técnicas

- `events.py` declara os eventos como dataclasses + validação leve (sem pydantic pesado nos hot paths).
- Consumer groups: `pose-workers` em `frames.raw`; `analysis` em `pose.frames`; `gateway`, `report`, `dataset` em `events.analysis`/`pose.frames`.
