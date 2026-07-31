# Digital Fit — Memória do Projeto

> Fonte da verdade resumida. Leia este arquivo antes de qualquer sessão de trabalho.

## O que é

App web que analisa exercícios físicos por visão computacional em **sessões de 30 segundos**: conta repetições, corrige execução e classifica o exercício. MVP: polichinelo. Alvo final: SaaS multiusuário.

**Rumo atual (Fase 5, 2026-07-30):** produto de **retenção diária** à la Duolingo — fogo
(streak), meta, XP, trilhas, Treino do Dia — sobre uma **fábrica de exercícios** (spec →
FSM/hold → gerador → corpus → `evalctl` → produção, com maturidade `beta→calibrado→validado`).
Duas regras novas que valem como decisão-chave: **engajamento é derivação pura** de
`SessionClaim`+`SessionResult` (nunca contador persistido novo sem justificativa), e o roadmap
de exercícios ordena por dificuldade **de detecção** (tiers técnicos), não física. Ver
SPEC-019…022 e ARCHITECTURE §1/§9.

## Decisões-chave (não renegociar sem ADR)

1. **Keypoint-first**: o dado central do sistema são keypoints (33 landmarks), nunca vídeo. Vídeo é insumo descartável.
2. **Event-driven**: tudo flui como eventos por Redis Streams. Feedback é parte do event loop.
3. **Dois modos de extração de pose**:
   - **EDGE (padrão)**: MediaPipe no navegador; servidor recebe só keypoints.
   - **CLOUD (controlado, opt-in)**: para dispositivos incapazes; cliente envia frames JPEG reduzidos; `pose-worker` extrai no servidor. Nunca é default — exige slot liberado por admission control.
4. **Cada etapa do pipeline é uma ENTIDADE** com **Fase Inicial** (mínimo funcional, poucas travas) e **Fase Evolução** (validações completas: luz, ângulo, distância, posição inicial etc.). Ver `specs/`.
5. **Sessão de 30s = unidade de carga** (admission control por semáforos no Redis).
6. **Regras antes de ML**: FSM explicável primeiro; dataset coletado desde o dia 1 alimenta ML na Fase 3.

## Stack

React + Vite (web) · Django + DRF + Channels (api/gateway) · Python puro/numpy (workers) · Redis Streams (broker/estado) · Postgres (dados) · Docker Compose · Caddy (TLS) · VPS Debian 4vCPU/6GB.

## Entidades do pipeline (specs)

| SPEC | Entidade | Camada |
|---|---|---|
| 001 | Captura & Capability Probe | client |
| 002 | Transporte & Contrato de Eventos | client/gateway |
| 003 | Validação de Cena (luz, distância, ângulo, enquadramento) | client/worker |
| 004 | Posição Inicial & Calibração | worker |
| 005 | Extração de Pose (edge + cloud) | client/worker |
| 006 | Normalização & Filtragem | worker |
| 007 | Análise de Exercício (FSM, reps) | worker |
| 008 | Feedback Engine | worker/client |
| 009 | Sessão & Admission Control | api |
| 010 | Relatório, Persistência & Dataset | worker |
| 011 | API SaaS (auth, quotas, planos) | api |
| 012 | Fontes de Entrada & Bancada de Avaliação (`evalctl`, corpus de vídeos rotulados) | cli/client |
| 013 | Interface Mobile — contratos de dados da UI (a camada visual foi substituída pela 014) | client |
| 014 | Interface v2 — vinculante p/ UI; referências em `referencias/app-completo-mobile.png`, `referencias/index.png` e protótipo Claude Design "Evolução UI v2" | client |
| 015 | Primeiro Acesso Guiado (Index → Escolha → Guia → Treino) | client |
| 016 | Planos Free × Assinatura (quotas no servidor; UI reflete) | api/client |
| 017 | Perfil Físico & Progresso Realista (peso/altura, kcal MET) | api/client |
| 018 | Painel de Administração & Plano de Configuração (Plan, Exercise, `GET /api/config`) | api/client |
| 019 | Engajamento & Gamificação (fogo, meta, XP, conquistas — derivação pura) | api/client |
| 020 | Catálogo Expandido (categorias, trilhas, maturidade, roadmap por tiers) | api/client/workers/eval |
| 021 | Exercícios Isométricos (modalidade *hold*; wall sit primeiro) | contrato/worker/api/client |
| 022 | Treino do Dia & Personalização (objetivo, idade, IMC — assinante) | api/client |

## Documentos

- `ARCHITECTURE.md` — arquitetura completa, diagramas, ADRs, orçamento da VPS
- `specs/` — uma spec por entidade (fase inicial + evolução)
- `BACKLOG.md` — tasks T-XXX por fase
- `AGENTS.md` — regras de trabalho das sessões
- `DEVLOG.md` — histórico de sessões
- `context/conventions.md` — convenções de código e eventos
- `.claude/skills/` — skills operacionais dos agentes: `df-executor` (executar T-XXX),
  `df-exercise` (criar/calibrar/promover exercício), `df-spec` (escrever/revisar specs)
