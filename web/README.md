# web/ — cliente React + Vite

**Território do Agente B.** O Agente A (núcleo Python) não cria nem edita arquivos aqui.

## O que mora aqui

Cliente React + Vite + TypeScript: captura de câmera, capability probe, MediaPipe no
navegador (modo edge), HUD de sessão e relatório. Ver `specs/SPEC-001`, `SPEC-005`,
`SPEC-008` e as tasks T-003, T-004, T-007, T-010 (HUD), T-012 no `BACKLOG.md`.

Estrutura sugerida (ARCHITECTURE.md §10):

```
web/
├── package.json
├── vite.config.ts
└── src/{capture,probe,hud,report}/
```

## Interface com o servidor

A **única** interface entre os dois territórios é o contrato de eventos:

- Fonte da verdade: [`workers/shared/events.py`](../workers/shared/events.py)
- Envelope: `{v, type, session_id, ts, seq, source, data}` — MessagePack no WebSocket
- Mudanças de contrato são anunciadas no [`DEVLOG.md`](../DEVLOG.md) com prefixo `[A]`

## docker-compose

O serviço `web` ainda não está no `docker-compose.yml` — o Agente B adiciona quando
o Vite existir (dev server na porta 5173, `VITE_API_URL` / `VITE_WS_URL` apontando
para o `api`).
