---
name: df-executor
description: Executa tasks T-XXX do Digital Fit com entrega confiável e testável. Use quando o usuário disser "Executar T-XXX", "rodar a task", "implementar T-XXX" ou pedir qualquer implementação que corresponda a uma task do BACKLOG.md. Carrega contexto mínimo na ordem certa, trava o escopo antes de codar, escreve os testes a partir dos critérios de aceite, roda os gates obrigatórios, registra no DEVLOG e commita. Para task de exercício novo (FSM/hold), use também a skill df-exercise.
---

# Executor de Task — Digital Fit

Você vai executar UMA task `T-XXX` do `BACKLOG.md`. O objetivo não é só "funcionar": é a
entrega ser **confiável** (escopo exato, gates verdes, honestidade sobre o que não foi
verificado) e **testável** (cada critério de aceite vira teste ou verificação medida).

## 1. Carregar contexto mínimo (nesta ordem, nada além)

1. `context/project.md` — visão e decisões-chave
2. `context/conventions.md` — convenções de código, eventos e derivação
3. A linha da task no `BACKLOG.md` (e as specs que ela referencia em `specs/`)
4. `AGENTS.md` — regras da sessão
5. Só então abrir o código relacionado. **Não ler arquivos fora do escopo da task.**

Marque a task como `doing` no BACKLOG antes de começar.

## 2. Travar o escopo ANTES de codar

Escreva (para si e para o DEVLOG) três listas curtas:

- **Entra**: exatamente o que a task descreve.
- **Não entra**: itens de "Fase Evolução" da spec são **proibidos** nesta task, mesmo que
  triviais ("é rápido" não é argumento — é o mecanismo de scope creep deste projeto).
- **Descobertas**: qualquer coisa fora do escopo encontrada no caminho vai para a seção
  "Descobertas" do `BACKLOG.md` (formato `[T-XXX] título em negrito + parágrafo`), nunca
  para o código desta sessão.

Conflito entre spec e código existente → **a spec vence**; se a spec estiver errada, proponha
a correção da spec antes de codar (não conserte em silêncio).

## 3. Testes nascem dos critérios de aceite

Antes de implementar, mapeie **cada critério de aceite** da spec para:

- um teste automatizado (preferido): pytest com fixtures de keypoints/datas, ou vitest no web; ou
- uma verificação **medida** (número, saída de comando, screenshot) quando teste automatizado
  não alcança — e registre a medição no DEVLOG, nunca a alegação.

Regras de teste da casa:

- Lógica de análise/derivação = **função pura** testável sem câmera, sem banco e sem mock de
  relógio (data/tempo entram como parâmetro). Fixtures em `tests/fixtures/`.
- Novo evento ⇒ `workers/shared/events.py` **primeiro**, com teste de serialização.
- Mudança de contrato/coluna deve ser **aditiva** (default que não quebra consumidor atual).
- UI nunca mostra número inventado: sem dado real, mostra `--` (princípio "honestidade >
  fidelidade" da SPEC-014).

## 4. Implementar

- Workers não importam Django; dependência corre server → workers, nunca o inverso (ADR-008).
- Comunicação entre serviços somente por eventos (Redis Streams).
- Configuração de negócio é resolvida na API e carimbada no evento; worker nunca lê banco
  (ADR-011, SPEC-018 P1). Todo valor tem default em código como piso (P2).
- Gamificação/progresso/trilha = **derivação pura** de `SessionClaim`/`SessionResult` — sem
  contador persistido novo sem justificativa na spec (SPEC-019 é o precedente).

## 5. Gates (obrigatórios, nunca encerrar com gate vermelho)

```bash
uv run ruff check .
uv run pytest
# se web/ foi tocado:
cd web && npm run lint && npm run typecheck && npm run test
# se infra foi tocada:
docker compose up --build  # sobe sem erro
```

Depois dos gates, confira os critérios de aceite da spec **um a um**, anotando como cada um
foi verificado (teste X, comando Y, medição Z). Critério não verificável nesta sessão (ex.:
exige aparelho real) → declarar como **pendência**, nunca como feito.

## 6. Encerramento

1. `BACKLOG.md`: status da task (`done`, ou `doing`/`blocked` com o motivo na própria linha).
2. `DEVLOG.md`: entrada no topo — `## AAAA-MM-DD (n) · T-XXX — título`, com: o que foi feito,
   **decisões tomadas e por quê**, medições, pendências geradas. O DEVLOG deste projeto conta
   a história do raciocínio, não só o diff — siga o tom das entradas existentes.
3. Commit: `T-XXX: descrição curta` (um commit lógico por task quando possível).

## O que NUNCA fazer

- Antecipar Fase Evolução dentro de task de Fase Inicial.
- Marcar `done` com gate vermelho, critério não conferido ou "deve funcionar".
- Editar `SessionResult` à mão ou criar segundo escritor do Postgres via stream (ADR-008).
- Mexer em limiar calibrado (FSM/cena/filtros) fora de uma task de calibração com bancada
  (SPEC-018 P3).
- Inventar número em tela (kcal, BPM, XP) que o servidor não forneceu.
