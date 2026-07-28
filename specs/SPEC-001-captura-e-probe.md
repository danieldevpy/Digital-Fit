# SPEC-001 — Captura & Capability Probe
Status: draft | Camada: client | Depende de: —

## Entidade e responsabilidade

Gerencia câmera, relógio de frames e a decisão EDGE vs CLOUD. É a porta de entrada de todo dado do sistema: entrega frames com timestamp/seq corretos para a extração de pose (SPEC-005) ou para o transporte (SPEC-002).

## Fase Inicial

### Escopo / Comportamento

- `getUserMedia` com resolução preferida 640×480 @30fps; fallback para o que o device der.
- **Frame clock próprio**: loop via `requestVideoFrameCallback` (fallback `requestAnimationFrame`), decimando para o alvo de processamento: 15 fps (edge) / 10 fps (cloud). Cada frame ganha `ts` (epoch ms) e `seq` monotônico.
- **Capability Probe**: ao preparar a sessão, roda o modelo de pose local por 2s em frames reais e mede fps efetivo.
  - fps ≥ 12 → modo `edge`
  - fps < 12, sem WebGL/WASM-SIMD, ou exceção → solicita modo `cloud` à API
- Modo **forçável** via configuração/query param (`?mode=edge|cloud`) para debug.
- UI de estado da câmera: sem permissão / carregando / pronta.

### Fora de escopo (vai para Evolução)

Re-probe no meio da sessão, seleção de câmera (frontal/traseira), ajuste dinâmico de fps por bateria/térmica, PWA/offline.

### Critérios de aceite

1. Em desktop moderno, probe conclui em ≤ 3s e escolhe `edge`.
2. Com WebGL desabilitado, probe escolhe `cloud` sem erro visível.
3. `seq` nunca repete/retrocede dentro de uma sessão; `ts` coerente entre frames (Δ ~66–100ms).
4. `?mode=cloud` força cloud mesmo em máquina potente.

## Fase Evolução

- **Re-probe adaptativo**: se fps do edge degradar >30% durante a sessão (térmica), pausar e oferecer troca para cloud na próxima sessão.
- Seleção de câmera + espelhamento correto; preferência lembrada por usuário.
- Ajuste dinâmico de fps de envio conforme RTT/backpressure do WS (integra com SPEC-002).
- Telemetria de devices (modelo de GPU, fps médio) para calibrar o limiar do probe com dados reais.

## Eventos

Produz: `session.capability` `{mode, probe_fps, webgl, ua}` · encaminha frames ao módulo de pose (edge) ou `frame.raw` (cloud).

## Notas técnicas

- O probe usa o MESMO modelo/config da sessão real (senão a medida mente).
- Decimação por tempo, não por contagem (garante fps alvo estável com câmeras de 24–60fps).
