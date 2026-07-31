# AGENTS.md — Regras de trabalho (Digital Fit)

Regras para qualquer sessão de desenvolvimento (humano ou agente).

## Skills (o fluxo abaixo, operacionalizado)

Agentes devem usar as skills do projeto em `.claude/skills/` — elas transformam estas regras
em passo a passo com gates:

- **`df-executor`** — executar uma task `T-XXX` (contexto mínimo, escopo travado, testes a
  partir dos critérios de aceite, gates, DEVLOG, commit).
- **`df-exercise`** — criar, calibrar ou promover um exercício (checklist da SPEC-020,
  `evalctl`, escada de maturidade). Usa-se **junto** com a df-executor.
- **`df-spec`** — escrever/revisar uma spec e desdobrá-la em tasks.

Pedido que não caiba em nenhuma → seguir o fluxo manual abaixo, que continua sendo a fonte.

## Fluxo de uma sessão

1. **Carregar contexto mínimo**: ler `context/project.md` → spec da task → só então abrir código relacionado. Não ler arquivos fora do escopo da task.
2. **Escopo rigoroso**: implementar somente o que a task T-XXX descreve. Descobriu algo fora do escopo? Registre como nova task no `BACKLOG.md`, não implemente.
3. **Fase Inicial ≠ Fase Evolução**: nunca antecipar itens da Fase Evolução de uma spec dentro de uma task de Fase Inicial, mesmo que "seja rápido".
4. **Executar gates** antes de encerrar:
   - `ruff check` + `pytest` (workers/api)
   - `npm run lint` + `npm run typecheck` + `npm run test` (web), quando tocada
   - docker-compose sobe sem erro se infra foi tocada
5. **Registrar no DEVLOG.md**: data, task, o que foi feito, decisões tomadas, pendências geradas.
6. **Commit** com mensagem `T-XXX: descrição` (um commit lógico por task quando possível).

## Regras de arquitetura (invioláveis sem ADR novo)

- Workers comunicam-se **apenas por eventos** (Redis Streams). Nada de import cruzado entre serviços.
- O contrato de eventos vive em `workers/shared/events.py` — mudou evento, mudou lá primeiro.
- Modo CLOUD nunca vira default; sempre atrás de capability probe + slot de admission control.
- Lógica de análise = função pura, testável sem câmera (fixtures de keypoints).

## Quando em dúvida

- Conflito entre spec e código existente → a spec vence; se a spec estiver errada, propor atualização da spec antes de codar.
- Decisão arquitetural nova → escrever ADR curto em `ARCHITECTURE.md` §11 antes de implementar.
