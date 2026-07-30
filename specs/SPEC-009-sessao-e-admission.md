# SPEC-009 — Sessão & Admission Control
Status: draft | Camada: api + workers | Depende de: SPEC-002

## Entidade e responsabilidade

Dona do ciclo de vida da sessão de 30s e da capacidade do sistema: decide se uma sessão pode começar (e em que modo), controla timeout, encerramento e recuperação. Transforma a sessão de 30s na **unidade de carga** do produto.

## Fase Inicial

### Escopo / Comportamento

- `POST /api/sessions` `{exercise, requested_mode, probe_result}` → `{session_id, ws_url, token, mode}`.
- Ciclo: `created → active → completed | aborted | expired`.
- TTL de 45s (30s + margem) via chave Redis com expiração; expirou → `session.completed {reason: "timeout"}`.
- **Admission mínimo**: semáforo só para modo cloud (`slots:cloud = 3`, INCR/DECR atômico). Sem slot → resposta `mode: "denied_cloud"` e o cliente informa indisponibilidade momentânea. Edge: sem limite na fase inicial.
- Token de sessão simples (HMAC assinado, expira com o TTL) — autentica o WS sem depender de auth de usuário (Fase 0 é anônima).
- Timer dos 30s é **autoridade do servidor** (analysis-worker emite `session.completed`); o timer do HUD é cosmético.

### Fora de escopo (vai para Evolução)

Fila de espera, quotas por usuário/plano, retomada de sessão, limite edge.

### Critérios de aceite

1. 4ª sessão cloud simultânea é negada; libera vaga quando qualquer uma termina.
2. Slot cloud é liberado em TODOS os finais (completa, aborta, TTL, crash de worker) — teste de cada caminho.
3. Cliente com token expirado/errado não conecta ao WS.
4. Sessão sem nenhum frame por 10s → `aborted {reason: "no_data"}`.

O prazo do critério 4 conta desde a ADMISSÃO, e isso é um contrato com o cliente: **quem pede a sessão declara que já pode alimentá-la**. Não é o servidor que espera o cliente aquecer — é o cliente que só pede quando estiver pronto (SPEC-001, portão de partida). Pedir antes gasta o prazo carregando modelo, e o sintoma é um `no_data` que acusa a câmera de não ver ninguém quando o problema era a partida do pipeline (T-069).

## Fase Evolução

- **Fila de espera cloud** com posição visível e estimativa (30s/slot); promoção automática ao vagar.
- **Limite edge** (ex.: 50) para proteger gateway/Redis — barato, evita abuso.
- **Quotas por plano** (integra SPEC-011): sessões/dia, prioridade de fila para pagantes.
- **Retomada**: reconexão em ≤ 5s continua a sessão (par com SPEC-002 evolução); estado da FSM restaurado do snapshot Redis.
- Sessões de duração configurável (45s/60s premium) — o admission control já é parametrizado por duração.
- **Meta de reps e séries** (SPEC-013): `target_reps` opcional na config (fim antecipado com `reason: "target_reached"`); treino em N séries de 30s com descanso — cada série é uma sessão do ponto de vista do admission control (a unidade de carga não muda).
- Autoscaling manual documentado: 2ª máquina rodando só pose-workers apontando pro mesmo Redis.

## Eventos

Produz: `session.started`, `session.completed {reason}`. Consome: heartbeats do gateway, `session.completed` do analysis (fim por timer).

## Notas técnicas

- Semáforo: `INCR` + verificação + `DECR` em Lua script (atômico) com TTL de segurança no contador.
- Toda transição de estado é evento no stream — o histórico de uma sessão é reconstruível por replay.
