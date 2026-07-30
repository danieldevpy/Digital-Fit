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

**São DOIS entry points** (T-067, ADR-010) — abrir a raiz não abre o app de treino:

| URL | bundle | o que é |
|---|---|---|
| `http://localhost:5173/` | site | landing e Sobre |
| `http://localhost:5173/app/` | app | escolha, guia, pré-config, treino, progresso, conta |

`npm run setup` prepara os assets do MediaPipe fora do bundle e **fora do git**:

- `public/wasm/` — runtime WASM copiado de `node_modules/@mediapipe/tasks-vision`
- `public/models/pose_landmarker_lite.task` — baixado uma vez (~5,5 MB)
- `public/pose-assets.json` — tamanhos descomprimidos dos dois acima, para a barra de progresso
  do primeiro acesso ter denominador (sob gzip o servidor não manda `Content-Length` — T-071)

`getUserMedia` só funciona em `localhost` ou HTTPS.

Outros scripts: `npm run lint`, `npm run typecheck` (`tsc -b` — o `tsc --noEmit` na raiz NÃO
checa nada, ver T-048), `npm run test` (vitest), `npm run build`.

## Estrutura

```
web/
├── index.html                    # SITE  → src/entries/site.tsx
├── app/index.html                # APP   → src/entries/app.tsx
├── scripts/setup-mediapipe.mjs   # WASM + modelo + manifesto → public/ (não versionados)
└── src/
    ├── entries/                  # os dois pontos de entrada e nada mais
    ├── site/                     # bundle do site: landing, Sobre, roteador e barra próprios
    ├── app/                      # casca do app (AppShell): rotas do funil de treino
    ├── screens/                  # telas do app + cards de exercício (compartilhado com o site)
    ├── shell/                    # navegação do app (hash), tab bar, links entre as fronteiras
    ├── capture/                  # câmera (SPEC-001), pipeline de frames e overlay do esqueleto
    ├── pose/                     # MediaPipe edge, aquecimento de assets, geometria (SPEC-005)
    ├── probe/                    # capability probe (SPEC-001)
    ├── session/                  # admissão, eventos, preferências, portão de partida
    ├── hud/                      # peças do HUD (anéis, GetReady, chips)
    ├── report/                   # relatório da sessão e último treino no aparelho
    ├── auth/                     # conta e trial anônimo (SPEC-011)
    ├── dev/                      # ferramentas de diagnóstico atrás do gate da T-048
    ├── lib/                      # contrato de eventos, gateway WS, utilidades
    ├── ui/                       # ícones SVG inline
    └── store/                    # estado da sessão (zustand)
```

A fronteira site↔app é de verdade: nenhum arquivo de `site/` importa `capture/`, `pose/` ou
`session/`, e é isso que mantém o bundle do site em ~9 kB contra ~240 kB do app. Link que
atravessa a fronteira é `<a href>` de `shell/origins.ts`, nunca `navigate()` — o outro lado pode
estar em outro host (`site.dominio.com` | `app.dominio.com`).

A geometria do esqueleto (`src/pose/skeleton.ts`) é função pura e testada sem câmera;
só `drawSkeleton` toca o canvas. Mesma regra da análise no lado Python.

⚠️ **Nenhum número na tela é inventado.** O `placeholders.ts` da T-043 morreu quando a T-012
ligou o HUD aos eventos; o que não existe aparece como `--` (kcal, FC) ou não aparece (FC saiu
das duas telas na revisão de 2026-07-30). Ver §Desvios da SPEC-014 antes de desenhar métrica
nova: mostrar valor de fachada quebra a confiança de quem treina.

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

**Trocar mock → real é uma variável**: `VITE_WS_URL` no `.env` (sem ela, aponta para o mock) —
ver `.env.example`. Cliente e mock usam a mesma implementação de `src/lib/gateway.ts`.

O cliente **envia** `pose.frame` a 15fps com o backpressure da SPEC-002: fila de no máximo
3 frames, e o mais antigo é descartado quando enche. O `seq` do envelope vem de
`src/lib/clientSequencer.ts`, compartilhado por todos os eventos que o cliente emite — o
contrato diz "monotônico por **sessão**", não por tipo.

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
