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
4. **Texto novo nasce nas duas línguas** (SPEC-025). Frase que o cliente lê vira chave em
   `web/src/i18n/dict/pt-BR/<namespace>.ts` e `t('namespace:chave')` no componente — nunca
   literal solta. Texto de **conteúdo** (exercício, plano, conquista, feedback) não vai para o
   dicionário: vai para o painel ou para o YAML por idioma, e o par é cobrado por `pytest` /
   `manage.py i18n_status`. Número e data saem dos formatadores de `i18n/format.ts`, nunca de
   `toLocaleDateString('pt-BR')` ou `.replace('.', ',')` — o separador decimal escrito à mão foi
   o bug de i18n mais difícil de ver em duas tasks seguidas. Chamada nova à API leva
   `localeHeaders()` junto. Os quatro portões que cobram isto já rodam nos gates do item
   seguinte; nenhum deles depende de alguém lembrar.
5. **Rota nova do site nasce na tabela de rotas** (SPEC-026, plano §4). Página pública nova —
   inclusive a de um exercício — entra em `web/src/site/routes.ts`, e mais lugar nenhum: dela
   saem o roteador, o pré-render, o `sitemap.xml` e os `hreflang`, e nenhum dos quatro se
   escreve à mão. `title` e `description` da rota são **chaves do dicionário** (`site:meta.*`),
   nunca texto solto no HTML — é o que faz o `tsc` do item anterior cobrar a versão em inglês.
   Rota nova precisa também de um entry em `vite.config.ts` (`ENTRADAS_DO_BUILD`). Os três
   portões que cobram isto já rodam nos gates do item seguinte: `site/routes.test.ts` (tabela ↔
   entries do build), `site/descoberta.test.ts` (tabela ↔ sitemap, **nos dois sentidos**) e
   `site/paginaGerada.test.ts` (o HTML gerado, com `canonical`, `hreflang` recíproco e absoluto,
   `x-default` e metadados diferentes entre os idiomas). O motivo de serem portão e não
   parágrafo: o `hreflang` que a T-147 escreveu à mão ficou **inerte por meses** — relativo em
   vez de absoluto — sem erro, sem log e sem ninguém ver.
6. **Executar gates** antes de encerrar:
   - `ruff check .` **+ `ruff format --check .`** + `pytest` (workers/api). Os dois de `ruff`: o
     CI roda os dois, e a checklist só nomeava o primeiro — foi assim que o `master` ficou seis
     arquivos com o formatador reprovando, sem ninguém ver (Descoberta `[T-156]`).
   - `npm run lint` + `npm run typecheck` + `npm run test` (web), quando tocada
   - docker-compose sobe sem erro se infra foi tocada
7. **Registrar no DEVLOG.md**: data, task, o que foi feito, decisões tomadas, pendências geradas.
8. **Commit** com mensagem `T-XXX: descrição` (um commit lógico por task quando possível).

## Regras de arquitetura (invioláveis sem ADR novo)

- Workers comunicam-se **apenas por eventos** (Redis Streams). Nada de import cruzado entre serviços.
- O contrato de eventos vive em `workers/shared/events.py` — mudou evento, mudou lá primeiro.
- Modo CLOUD nunca vira default; sempre atrás de capability probe + slot de admission control.
- Lógica de análise = função pura, testável sem câmera (fixtures de keypoints).

## Quando em dúvida

- Conflito entre spec e código existente → a spec vence; se a spec estiver errada, propor atualização da spec antes de codar.
- Decisão arquitetural nova → escrever ADR curto em `ARCHITECTURE.md` §11 antes de implementar.
