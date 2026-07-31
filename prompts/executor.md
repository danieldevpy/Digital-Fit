# Prompt — Executor de Task (Digital Fit)

> **Superseded para agentes Claude Code**: use as skills do repo (`.claude/skills/df-executor`,
> `df-exercise`, `df-spec`) — versões mais completas e mantidas destes prompts. Este arquivo
> permanece como checklist para uso manual ou para agentes sem suporte a skills.

```
Você vai executar a task {T-XXX} do projeto Digital Fit.

CONTEXTO (leia nesta ordem, nada além disso):
1. context/project.md — visão e decisões-chave
2. context/conventions.md — convenções
3. A spec referenciada pela task em specs/
4. AGENTS.md — regras da sessão

REGRAS:
- Escopo rigoroso: implemente somente o que a task descreve. Itens de "Fase
  Evolução" da spec são PROIBIDOS nesta task, mesmo que triviais.
- Descobertas fora do escopo → registrar na seção "Descobertas" do BACKLOG.md.
- Lógica de análise deve ser função pura testável com fixtures (sem câmera).
- Comunicação entre serviços somente por eventos (workers/shared/events.py).

GATES (obrigatórios antes de encerrar):
- ruff check + pytest verdes (python) / lint + test verdes (web, se tocada)
- docker-compose sobe sem erro, se infra foi tocada
- Critérios de aceite da spec correspondente verificados um a um

ENCERRAMENTO:
1. Atualizar status da task no BACKLOG.md
2. Registrar entrada no DEVLOG.md (data, task, feito, decisões, pendências)
3. Commit: "T-XXX: descrição curta"
```

## Prompt — Revisão de Spec

```
Vamos revisar a {SPEC-XXX} do Digital Fit. Me apresente:
1. Um resumo da entidade em 3 linhas
2. Os pontos de maior risco/incerteza técnica da Fase Inicial
3. O que você mudaria e por quê
Depois discutimos e, aprovada, mude Status para "approved" e ajuste
as tasks correspondentes no BACKLOG se o escopo mudou.
```
