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
- **Partida do pipeline é um portão, não um sinal (T-069, vinculante)**: a sessão só é pedida ao servidor quando o cliente já tem como emitir frame — landmarker de pé E probe decidido (`session/pipelineGate.ts`). Câmera pronta **não** é essa condição.
- **Toda criação de landmarker tem prazo** (12s), com queda de GPU para CPU. A queda não pode depender de rejeição: inicialização de GPU que trava fica pendente para sempre, e sem prazo não há fallback nem erro.
- **Os assets são baixados FORA da tentativa de delegate (T-070)**, uma vez, para o cache HTTP. O MediaPipe baixa o WASM dentro de `createFromOptions`, então duas tentativas de delegate significavam dois downloads de 11,5 MB em paralelo — medido em produção: 33,25s e 40,07s para o mesmo arquivo. O `fileset` é resolvido uma vez e reaproveitado: é dele que sai o caminho exato do binário a aquecer.
- **Estado de aquecimento é visível**: entre a câmera abrir e o primeiro frame sair a tela diz o que está acontecendo (carregando modelo / calibrando dispositivo / falhou). Essa janela chega a vários segundos no primeiro acesso (~17 MB de WASM + modelo) e ficar muda nela é indistinguível de estar travado.

### Fora de escopo (vai para Evolução)

Re-probe no meio da sessão, seleção de câmera (frontal/traseira), ajuste dinâmico de fps por bateria/térmica, PWA/offline.

### Critérios de aceite

1. Em desktop moderno, probe conclui em ≤ 3s e escolhe `edge`.
2. Com WebGL desabilitado, probe escolhe `cloud` sem erro visível.
3. `seq` nunca repete/retrocede dentro de uma sessão; `ts` coerente entre frames (Δ ~66–100ms).
4. `?mode=cloud` força cloud mesmo em máquina potente.
5. **Em aba anônima (cache HTTP e cache de shader vazios), treinar funciona igual à aba normal** — só mais devagar para começar. Este critério nasceu de um teste real em que a aba anônima falhava 100% das vezes e a aba normal funcionava 100%, na mesma posição e no mesmo aparelho: o cliente pedia a sessão antes de poder alimentá-la, e o prazo de `no_data` do servidor (SPEC-009) estourava durante o download do modelo.

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
