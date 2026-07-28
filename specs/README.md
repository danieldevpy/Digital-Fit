# Specs — Digital Fit

Cada etapa do pipeline é uma **entidade** com duas fases:

- **Fase Inicial**: o mínimo funcional, com poucas travas de segurança. É o que entra no MVP.
- **Fase Evolução**: validações e refinamentos completos (luz, ângulo, distância, calibração, ML…), já projetados agora, implementados depois como tasks próprias.

## Índice

| SPEC | Entidade | Fase Inicial entra em |
|---|---|---|
| [SPEC-001](SPEC-001-captura-e-probe.md) | Captura & Capability Probe | Fase 0 |
| [SPEC-002](SPEC-002-transporte-e-eventos.md) | Transporte & Contrato de Eventos | Fase 0 |
| [SPEC-003](SPEC-003-validacao-de-cena.md) | Validação de Cena | Fase 1 (mínimo na 0) |
| [SPEC-004](SPEC-004-posicao-inicial.md) | Posição Inicial & Calibração | Fase 1 |
| [SPEC-005](SPEC-005-extracao-de-pose.md) | Extração de Pose (edge + cloud) | Fase 0 (edge) / 1 (cloud) |
| [SPEC-006](SPEC-006-normalizacao-e-filtragem.md) | Normalização & Filtragem | Fase 0 |
| [SPEC-007](SPEC-007-analise-de-exercicio.md) | Análise de Exercício (FSM) | Fase 0 |
| [SPEC-008](SPEC-008-feedback-engine.md) | Feedback Engine | Fase 0 |
| [SPEC-009](SPEC-009-sessao-e-admission.md) | Sessão & Admission Control | Fase 0 (mínimo) / 2 |
| [SPEC-010](SPEC-010-relatorio-e-dataset.md) | Relatório, Persistência & Dataset | Fase 1 |
| [SPEC-011](SPEC-011-api-saas.md) | API SaaS | Fase 1 (auth) / 2 |
| [SPEC-012](SPEC-012-entrada-e-avaliacao.md) | Fontes de Entrada & Bancada de Avaliação | Fase 0 (harness CLI) |

## Template

```markdown
# SPEC-XXX — <Entidade>
Status: draft | approved | implemented(initial) | implemented(evolution)
Camada: ... | Depende de: SPEC-YYY

## Entidade e responsabilidade
## Fase Inicial
### Escopo / Comportamento
### Fora de escopo (vai para Evolução)
### Critérios de aceite
## Fase Evolução
## Eventos (consome / produz)
## Notas técnicas
```

## Ciclo de vida

`draft` → revisão (você analisa uma a uma) → `approved` → tasks no BACKLOG → `implemented(initial)` → futuramente `implemented(evolution)`.
