# SPEC-019 — Engajamento & Gamificação (fogo, meta diária, XP)
Status: draft | Camada: api + client | Depende de: SPEC-010, SPEC-011, SPEC-016, SPEC-018 | Referência: ideia "foguinho do Duolingo" (2026-07-30)

## Entidade e responsabilidade

Transforma sessões concluídas em motivo de voltar amanhã: **fogo** (dias seguidos ativos),
**meta diária**, **XP** com bônus de execução limpa, e **conquistas**. É a camada que faz o
produto ser usado todo dia — o resto do sistema mede o treino; esta spec mede a constância.

Princípio central: **tudo é derivável dos fatos já gravados** (`SessionClaim` +
`SessionResult`). A gamificação é uma *leitura agregada* do banco, nunca uma segunda fonte da
verdade: nenhum worker novo, nenhuma escrita no hot path, ADR-008 intacto (o report-builder
segue sendo o único consumidor que escreve no Postgres). Se o cálculo de streak mudar amanhã,
recalcular do zero dá o mesmo resultado ou um resultado melhor — nunca um estado órfão que
ninguém sabe de onde veio.

O que isso compra, na prática:

- **Sem migração de dados**: o fogo de quem treinou este mês já existe, só não era mostrado.
- **Sem bug de contador**: não há contador para dessincronizar; há uma função pura sobre datas.
- **Testável como a FSM**: fixtures de listas de datas, sem banco, sem relógio de verdade.

## Vocabulário (vinculante)

| Termo | Definição |
|---|---|
| **Sessão válida** | `SessionResult` com `rep_count ≥ 1`. Sessão com zero reps não conta para nada desta spec — senão abrir a câmera por 30 s vira fazenda de fogo. (Quando a SPEC-021 existir: exercício de modalidade *hold* é válido com `hold_valid_ms ≥ 10_000`.) |
| **Dia ativo** | dia-calendário com ≥ 1 sessão válida. |
| **Fogo (streak)** | número de dias ativos consecutivos terminando hoje ou ontem. Terminou anteontem = fogo apagado (0). |
| **Proteção** | dia falho "perdoado" no meio de uma sequência. Direito **derivado por regra**, não item de inventário: até N dias falhos perdoados por mês-calendário (N vem do plano; ver §Planos). Dois dias falhos seguidos consomem duas proteções — se houver. |
| **Meta diária** | alvo pessoal de sessões válidas por dia: casual = 1, regular = 2, intenso = 4. Escolha do usuário, gratuita. |
| **XP** | pontos por sessão válida, fórmula versionada em código (§XP). |

**Meta ≠ fogo, de propósito.** No Duolingo a ofensiva exige a meta batida; aqui o fogo acende
com **uma** sessão válida, qualquer que seja a meta. Motivo: exercício físico tem dia de corpo
cansado, e uma meta ambiciosa não pode queimar a constância — o fogo mede *voltar*, a meta mede
*quanto*. Quem pôs meta "intenso" e fez uma sessão mantém o fogo e vê a meta incompleta; as
duas informações ficam legíveis separadas.

## Fuso horário (decisão explícita)

A virada do dia do fogo é **meia-noite de America/Sao_Paulo, fixo**, para todo mundo, na Fase
Inicial. A SPEC-016 escolheu UTC para a *quota* — e lá está certo, porque quota é proteção de
capacidade e "renova em Xh" resolve a comunicação. Fogo é outra coisa: meia-noite UTC é 21h no
Brasil, e "treinei às 22h e o app disse que foi amanhã" mata a mecânica no primeiro contato. O
produto é pt-BR; fuso por usuário é Evolução. As duas escolhas divergem e esta linha existe
para dizer que é de propósito.

## Derivação (como se calcula)

Módulo puro em `server/api/engagement.py` (mesma filosofia da FSM: função sem I/O, fixtures):

```
dias_ativos(sessions)              -> set[date]     # sessões válidas do usuário, no fuso SP
streak(dias, hoje, protecoes_mes)  -> StreakInfo    # corrente, melhor, proteções usadas no mês
xp_da_sessao(result)               -> int           # §XP — recebe um SessionResult
xp_total(results)                  -> int
nivel(xp_total)                    -> Level         # tabela de faixas em código
conquistas(agregados)              -> list[str]     # §Conquistas — predicados puros
```

A API monta os agregados com uma consulta por usuário (join `SessionClaim` → `SessionResult`
por `session_id`, que já é como o histórico funciona) e cacheia o resultado pronto em Redis
(`df:eng:{user_id}`), invalidado por `post_save` de `SessionResult` — o report-builder roda
como comando do Django, então o signal dispara no processo certo. Cache frio = uma consulta;
Redis fora = consulta direto (P2 da SPEC-018: degradar, nunca falhar).

## XP (fórmula versionada)

Constante `XP_FORMULA_V = 1` em código, gravada junto de qualquer lugar que exiba XP "histórico".
Mudou a fórmula, incrementa a versão e **recalcula tudo** — é barato, é derivável, e evita o
museu de pontos incomparáveis.

| Componente | Valor | Fonte no `SessionResult` |
|---|---|---|
| Sessão válida | +10 | `rep_count ≥ 1` |
| Repetições | +1 por rep, teto +40 | `rep_count` |
| **Execução limpa** | +10 | `feedback_counts == {}` e `scene_warning_counts == {}` |
| Meta diária batida | +15 (1×/dia) | derivado dos dias ativos + meta do perfil |

O bônus de execução limpa é o que o Duolingo não tem e nós temos de graça: o feedback engine
já mede a *forma*. XP premia treinar **bem**, não só treinar — e usa dados que já estão na linha
do relatório, sem tocar no pipeline.

Níveis: tabela de faixas em código (`LEVELS = [0, 100, 300, 700, 1500, …]`, nomes de nível
definidos com o produto). Nível é apresentação sobre XP total; não tem persistência própria.

## Planos (o que cada role tem)

| Capacidade | Anônimo | Free | Assinatura |
|---|---|---|---|
| Fogo | **fantasma** (local, §Anônimo) | servidor | servidor |
| Proteções/mês | 0 | 1 | 2 (colunas novas no `Plan` da SPEC-018; defaults em código como piso) |
| Meta diária | — | sim | sim |
| XP e nível | — | sim | sim |
| Conquistas | — | básicas | todas |
| Recuperar fogo apagado ("reacender") | — | — | Evolução (é escrita, não derivação — ver lá) |

A escada segue o princípio da SPEC-016: o Free tem a mecânica **completa** no dia a dia — o
que a assinatura compra é folga (mais proteção) e resgate. Gamificação capada no Free não
converte, irrita.

## Anônimo: o fogo fantasma

O visitante vê um fogo **local** (client-side, derivado de um diário de dias com sessão válida
em `localStorage`, alimentado no fim de cada sessão) com rótulo honesto: *"seu fogo vive só
neste aparelho — crie uma conta para não perdê-lo"*. A dor de perder uma sequência de 4 dias é
um CTA de cadastro melhor que o `429` do trial.

**Na criação da conta, o fogo sobrevive de verdade**: o cadastro passa a enviar o `device_id`
(o mesmo do trial), e a API **adota** as `SessionClaim` anônimas daquele aparelho
(`user IS NULL AND device_id = X` → `user`). Como o fogo do servidor é derivado das claims, a
sequência feita antes da conta vira sequência da conta — e o histórico vem junto, o que torna
literal a promessa "a conta serve para guardar o histórico" (README). Adoção é uma escrita da
API em tabela que a API já escreve na admissão; ADR-008 segue falando de consumidores de
stream. Limitação aceita e documentada: aparelho compartilhado adota sessões de outra pessoa —
mesmo furo, e mesma aceitação, do trial por device-id (SPEC-011).

## Conquistas

Catálogo **em código** (`ACHIEVEMENTS`: slug, nome, descrição, predicado puro sobre os
agregados). Deriváveis, sem tabela: a lista de conquistas de um usuário é `conquistas(agregados)`.
O toast "nova conquista!" é responsabilidade do cliente — diff entre a lista do servidor e a
última vista (`localStorage`), mesma técnica do `guide_seen`. Sem tabela de "notificado em".

v1 (predicados que os agregados de hoje já sustentam):

| Slug | Critério |
|---|---|
| `primeira-sessao` | 1 sessão válida |
| `fogo-7` / `fogo-30` | melhor sequência ≥ 7 / ≥ 30 |
| `centena` | ≥ 100 reps acumuladas num mesmo exercício |
| `milheiro` | ≥ 1000 reps totais |
| `sem-reparo` | 10 sessões limpas (sem feedback nem warning) |
| `semana-cheia` | meta batida 7 dias seguidos |

Conquistas por categoria de exercício ("3 categorias na mesma semana") entram quando a
SPEC-020 der categoria ao catálogo — o predicado já nasce escrito, desabilitado por dependência.

## Superfícies de UI

- **Início (pré-config)**: chip do fogo (🔥 + número) ao lado do cabeçalho + anel fino da meta
  do dia (0/N sessões). Toque abre o painel de engajamento (sheet): fogo, calendário do mês com
  dias ativos e proteções usadas, XP, nível, meta editável.
- **Perfil**: fogo, melhor sequência, XP/nível, galeria de conquistas (apagadas = bloqueadas).
- **Relatório (fim da sessão)**: linha "+XP" com a decomposição (sessão +10 · reps +18 ·
  limpa +10) — é onde o bônus de forma *ensina* que forma vale ponto.
- **Anônimo**: chip fantasma com o rótulo honesto; painel mostra só o local e o CTA de conta.

Nenhum número da UI nasce no cliente para usuário logado — chip e painel leem
`GET /api/engagement`. O fantasma do anônimo é explicitamente rotulado como local.

## Fase Inicial

### Escopo / Comportamento

- Módulo `engagement.py` puro (streak com proteções por mês, XP v1, níveis, conquistas v1) +
  fixtures de datas cobrindo: sequência simples, dia falho protegido, dois falhos seguidos,
  virada de mês (proteções renovam), fogo apagado, sessão de zero reps ignorada.
- `GET /api/engagement` (autenticado): `{streak, best_streak, protections_used_month,
  protections_month, today_active, goal, goal_done_today, xp, level, achievements[]}` — com
  cache Redis invalidado por `post_save` de `SessionResult`.
- Campo `daily_goal` no perfil (`casual|regular|intenso`, default casual), editável por REST.
- Adoção de sessões do aparelho no cadastro (device_id no `POST /api/auth/register`).
- Fogo fantasma local do anônimo + CTA.
- UI: chip + anel na Início, painel de engajamento, seção no Perfil, "+XP" no relatório.
- Colunas `streak_protections_month` no `Plan` (SPEC-018/T-073), defaults em código (anon 0,
  free 1, subscriber 2).

### Fora de escopo (vai para Evolução)

- **Missões diárias/semanais** ("hoje: 2 categorias diferentes") — dependem da SPEC-020.
- **Ligas semanais** (ranking por XP em coortes) — sem massa de usuários é pódio de 3 pessoas.
- **Notificações push / e-mail de lembrete** — exige PWA + permissão; é projeto próprio.
- **Reacender o fogo** (resgate pago de sequência apagada): é a primeira mecânica **não
  derivável** (um perdão comprado é um fato novo, tabela própria `streak_amnesty(user, date)`),
  e por isso fica de fora até a base derivável estar estável.
- Fuso por usuário; XP ao vivo durante a sessão (consumer de `rep.detected` no HUD); widget.

### Critérios de aceite

1. Fixtures do módulo puro passam sem banco e sem mock de relógio (data "hoje" é parâmetro).
2. Sessão com `rep_count = 0` não acende fogo, não dá XP, não bate meta.
3. Treinou 22h30 em São Paulo → conta no dia de São Paulo (teste com timestamp UTC do banco).
4. Dia falho com proteção disponível não apaga o fogo; sem proteção, apaga; proteções renovam
   na virada do mês-calendário.
5. Cadastro com device_id que tem sessões anônimas: `GET /api/engagement` já nasce com o fogo
   e `GET /api/sessions?mine` com o histórico do aparelho.
6. Recalcular do zero (cache limpo) reproduz exatamente o que estava no cache.
7. `GET /api/engagement` responde com Redis fora do ar (degrada para consulta direta).
8. Anônimo nunca vê número do servidor; logado nunca vê número calculado no cliente.

## Fase Evolução

Missões (catálogo em dado, admin da SPEC-018); ligas por coorte de XP semanal; push/e-mail com
opt-in explícito; reacender pago (`streak_amnesty`, com carimbo no painel de quem usou);
fuso por usuário (campo no perfil, default SP); XP ao vivo no HUD via `rep.detected`;
conquistas por categoria/trilha (SPEC-020); "modo férias" (pausa declarada que não queima
proteção — honestidade > punição).

## Eventos (consome / produz)

**Nenhum evento novo.** Consome apenas o que o report-builder já materializou em
`SessionResult`. Esta spec é o teste de estresse da promessa da SPEC-010 (replay-derivable) —
e ela passa: engajamento inteiro é uma vista sobre o dataset.

## Notas técnicas

- A consulta agregada é por usuário e sob demanda; com `HISTORY_LIMIT`-alike não serve — streak
  precisa de **todas** as datas, mas só das datas: `values_list` de `created_at` + `rep_count`
  é barata mesmo com milhares de sessões. Índice existente por `session_id` cobre o join.
- `created_at` do `SessionResult` é o relógio do servidor (UTC); conversão para SP na derivação,
  nunca no armazenamento.
- O painel de engajamento é sheet, não rota — segue o padrão da AccountSheet.
- Nada desta spec entra no bundle do SITE (ADR-010): fogo é do app.
