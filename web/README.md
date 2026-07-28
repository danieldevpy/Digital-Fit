# web/ — cliente React + Vite

**Território do Agente B.** O Agente A (núcleo Python) não cria nem edita arquivos aqui.

## O que mora aqui

Cliente React + Vite + TypeScript: captura de câmera, capability probe, MediaPipe no
navegador (modo edge), HUD de sessão e relatório. Ver `specs/SPEC-001`, `SPEC-005`,
`SPEC-008` e as tasks T-003, T-004, T-007, T-010 (HUD), T-012 no `BACKLOG.md`.

## Como rodar

```bash
npm install
npm run dev      # roda `npm run setup` antes (predev) e sobe em http://localhost:5173
```

`npm run setup` prepara os assets do MediaPipe fora do bundle e **fora do git**:

- `public/wasm/` — runtime WASM copiado de `node_modules/@mediapipe/tasks-vision`
- `public/models/pose_landmarker_lite.task` — baixado uma vez (~5,5 MB)

`getUserMedia` só funciona em `localhost` ou HTTPS.

Outros scripts: `npm run lint`, `npm run test` (vitest), `npm run build`.

## Estrutura

```
web/
├── scripts/setup-mediapipe.mjs   # WASM + modelo → public/ (não versionados)
└── src/
    ├── capture/                  # câmera (SPEC-001) e overlay do esqueleto
    ├── pose/                     # MediaPipe edge + geometria do esqueleto (SPEC-005)
    ├── hud/                      # casca visual do HUD (T-043) — dados placeholder
    ├── shell/                    # navegação (tab bar)
    ├── ui/                       # ícones SVG inline
    └── store/                    # estado da sessão (zustand)
```

A geometria do esqueleto (`src/pose/skeleton.ts`) é função pura e testada sem câmera;
só `drawSkeleton` toca o canvas. Mesma regra da análise no lado Python.

⚠️ **`src/hud/placeholders.ts` é o único lugar com números inventados.** A T-043 entregou
o layout, não o comportamento: contador, timer, ângulo e kcal são estáticos até a T-012
ligá-los aos eventos do contrato. Não espalhe valor de fachada por outros arquivos.

## Mock do gateway

O gateway real é a T-005 (Agente A). Enquanto isso:

```bash
npm run mock:gateway     # ws://localhost:8787 — contrato v1, MessagePack
npm run dev              # em outro terminal
```

`web/dev/mock-gateway.mjs` fica **fora do bundle** e emite só tipos do contrato
(`session.started` + os `CLIENT_PUSH_TYPES`): reps a cada ~1,2s, dois feedbacks, um warning
de cena e `session.completed` aos 30s. Os envelopes dele foram validados contra
`workers/shared/events.py`.

**Trocar mock → real é uma variável**: `VITE_WS_URL` no `.env` (sem ela, aponta para o mock).
Cliente e mock usam a mesma implementação de `src/lib/gateway.ts`.

## Gravador de fixtures (T-007)

Com a câmera ligada, o chip de dev tem **● gravar fixture**. Ele acumula os keypoints da
sessão e baixa um JSON para os testes do núcleo Python.

```jsonc
{
  "format": "digital-fit/pose-fixture",
  "version": 1,
  "session_id": "dev-a1b2c3d4",
  "label": "polichinelo-20-limpos",
  "capability": { "mode": "edge", "probe_fps": 28.3, "webgl": true, "ua": "..." },
  "video": { "width": 640, "height": 480 },
  "target_fps": 15,
  "events": [ /* envelopes `pose.frame` do contrato, nada além disso */ ]
}
```

`events` são envelopes do contrato **sem nenhum campo inventado** — o resto é embalagem de
fixture (rótulo, device) e fica de fora deles de propósito. Do lado Python:

```python
envelopes = [Envelope.from_dict(e) for e in fixture["events"]]
frames = [RawFrame(ts=e.ts, seq=e.seq, landmarks=e.payload().landmarks) for e in envelopes]
```

Verificado nesta forma contra `Envelope.from_dict`, `RawFrame` e `normalize()`.

## Interface com o servidor

A **única** interface entre os dois territórios é o contrato de eventos:

- Fonte da verdade: [`workers/shared/events.py`](../workers/shared/events.py)
- Envelope: `{v, type, session_id, ts, seq, source, data}` — MessagePack no WebSocket
- Mudanças de contrato são anunciadas no [`DEVLOG.md`](../DEVLOG.md) com prefixo `[A]`

Enquanto o contrato não existir, o cliente não inventa evento: o espelho TypeScript
(`src/lib/events.ts`) só nasce depois do `events.py`.

## docker-compose

O serviço `web` ainda **não** está no `docker-compose.yml`. Esse arquivo é território do
Agente A, então a T-003 não o tocou — ver a descoberta `[B/T-003]` no `BACKLOG.md`.
