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
    └── store/                    # estado da sessão (zustand)
```

A geometria do esqueleto (`src/pose/skeleton.ts`) é função pura e testada sem câmera;
só `drawSkeleton` toca o canvas. Mesma regra da análise no lado Python.

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
