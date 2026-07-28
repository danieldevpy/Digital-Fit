# SPEC-005 — Extração de Pose (EDGE + CLOUD)
Status: draft | Camada: client (edge) / worker (cloud) | Depende de: SPEC-001, SPEC-002

## Entidade e responsabilidade

Transforma frames em `pose.frame` (33 landmarks MediaPipe, `[x, y, z, visibility]`). Dois provedores, **um único contrato de saída** — downstream nunca sabe a origem.

## Fase Inicial

### Escopo / Comportamento

**EDGE (padrão)**
- MediaPipe Pose Landmarker (Tasks API) em WASM+SIMD, delegate GPU quando disponível; modelo `lite`.
- 15 fps alvo; emite `pose.frame` com `source: "edge"` direto no WS.

**CLOUD (opt-in, controlado)**
- Cliente envia `frame.raw` (JPEG, maior lado 320px, qualidade ~60, 10 fps) somente com slot cloud concedido (SPEC-009).
- `pose-worker` (Python + MediaPipe, modelo `lite`, CPU) consome `frames.raw` via consumer group, emite `pose.frame` com `source: "cloud"`.
- 2 réplicas de pose-worker, cada uma limitada a 1 vCPU (cgroup do compose).
- Frame que esperar > 500ms na fila é descartado (análise em tempo real não quer frame velho).

### Fora de escopo (vai para Evolução)

Troca dinâmica de modelo, ONNX Runtime, GPU no servidor, segmentação/máscara, múltiplas pessoas no quadro.

### Critérios de aceite

1. Mesmo vídeo processado por edge e por cloud → contagem de reps idêntica (tolerância ±1 em 20).
2. `pose-worker` processa frame 320px em ≤ 80ms (p95) em 1 vCPU da VPS.
3. Latência fila+extração cloud ≤ 200ms (p95) com 3 sessões cloud simultâneas.
4. Downstream (SPEC-006/007) roda sem nenhum branch por `source`.

## Fase Evolução

- **Seleção de modelo por carga**: `lite` ↔ `full` conforme slots livres (qualidade extra quando sobra CPU).
- Migração do pose-worker para **ONNX Runtime** (MoveNet/RTMPose) se benchmark mostrar >30% de ganho em CPU.
- **Detecção de múltiplas pessoas**: escolher a pessoa dominante (maior bbox central) e avisar `MULTIPLE_PEOPLE`.
- Vídeo cloud com qualidade adaptativa por RTT; avaliar WebRTC apenas se JPEG/WS provar-se insuficiente (ADR-003).
- z-coordinate: hoje ignorado; avaliar uso para exercícios com profundidade (flexão).

## Eventos

Consome: `frame.raw` (cloud). Produz: `pose.frame {landmarks[33], source}`.

## Notas técnicas

- Ordem/índices de landmarks seguem o padrão MediaPipe Pose (0=nariz … 32=pé esq.). Documentar no `events.py`.
- O probe do SPEC-001 usa exatamente esta config edge.
- Descarte por idade mede a **espera na fila** com o relógio do servidor: idade = agora − hora
  de entrada no stream (o ID da entrada do Redis é `<ms-do-servidor>-<n>`). A versão anterior
  desta nota mandava usar o `ts` do envelope; foi corrigida na T-016 porque `ts` é carimbado
  pelo **navegador**, e um celular com relógio atrasado faria todo frame parecer velho — o
  worker descartaria a sessão inteira em silêncio. O texto do comportamento sempre disse
  "esperar na fila", que é justamente o que a hora de entrada mede.
- O `ts` do cliente continua sendo o que vai no `pose.frame` emitido: para a FSM, o tempo que
  importa é o da captura, não o do processamento.
