---
name: df-spec
description: Escreve e revisa specs do Digital Fit no padrão da casa. Use quando o usuário pedir "criar uma spec", "revisar a SPEC-XXX", "especificar <feature>", "aprovar spec", ou quando uma ideia de produto precisar virar comportamento antes de virar código. Também cobre o desdobramento da spec em tasks T-XXX no BACKLOG.md. Toda mudança de comportamento nasce de spec — se o pedido é implementar uma task já existente, a skill certa é df-executor.
---

# Specs — Digital Fit

Neste projeto, comportamento nasce de spec, implementação nasce de task, e a spec é dona da
verdade (conflito spec × código → a spec vence). Uma spec boa aqui não é um wireframe nem um
PRD genérico: é uma **entidade com responsabilidade, decisões justificadas e critérios
mensuráveis**.

## Estrutura (template de `specs/README.md`, vinculante)

```markdown
# SPEC-XXX — <Entidade>
Status: draft | approved | implemented(initial) | implemented(evolution)
Camada: ... | Depende de: SPEC-YYY | Referência: <ideia/data, quando houver>

## Entidade e responsabilidade
## Fase Inicial
### Escopo / Comportamento
### Fora de escopo (vai para Evolução)
### Critérios de aceite
## Fase Evolução
## Eventos (consome / produz)
## Notas técnicas
```

Ciclo de vida: `draft` → revisão pelo Daniel (uma a uma) → `approved` → tasks no BACKLOG →
`implemented(initial)`. Spec nova entra no índice de `specs/README.md` na hora.

## O estilo da casa (o que separa spec boa de spec genérica)

1. **Fase Inicial mínima e completa** — o menor recorte que funciona de ponta a ponta. Tudo
   que dá para adiar vai explicitamente para "Fora de escopo", com o motivo.
2. **Decisões com dono e com porquê.** Quando a spec escolhe entre caminhos (UTC × fuso SP,
   tabela × derivação, evento novo × evento existente), o texto registra a alternativa
   rejeitada e o motivo. Divergência intencional de outra spec é declarada ("diverge de
   propósito"). Frases como "esta linha existe para dizer que é de propósito" são o padrão.
3. **Critérios de aceite mensuráveis** — cada um verificável por teste, comando ou consulta.
   "Funciona bem" não é critério; "11ª sessão recusada pelo servidor mesmo forjando o client"
   é.
4. **Honestidade de UI**: nenhuma tela mostra número que o sistema não mediu (`--` até
   existir). Toda trava de plano/quota é **no servidor**; a UI reflete e vende, nunca é a
   única barreira.
5. **Anti-fragilidade por derivação**: feature de produto sobre dados de treino
   (gamificação, progresso, trilha, seleção diária) deve ser **derivação pura** de
   `SessionClaim`/`SessionResult` sempre que possível — recomputável do zero, sem contador
   que dessincroniza. Estado novo persistido exige justificativa (fato não-derivável, ex.:
   perdão comprado).
6. **As três naturezas de configuração** (SPEC-018): negócio/conteúdo → Postgres/admin;
   infra → env; **medição (limiares calibrados) → código + bancada**. Nada atravessa sem ADR.
7. **Eventos**: novo evento só se for fato do domínio de treino; mudança de contrato é
   aditiva e começa por `workers/shared/events.py`. "Nenhum evento novo" é uma resposta
   legítima e frequente.
8. **Contexto de VPS**: 4 vCPU/6 GB. Solução que pede infra nova precisa se pagar.

## Revisão de uma spec existente

Apresente: (a) resumo da entidade em 3 linhas; (b) os maiores riscos/incertezas da Fase
Inicial; (c) o que mudaria e por quê. Aprovada → `Status: approved` + ajustar tasks no
BACKLOG se o escopo mudou.

## Desdobrar em tasks

- Task = recorte executável em uma sessão, com fronteira clara ("Fase Inicial nunca inclui
  itens de Evolução").
- Formato no BACKLOG: `| T-XXX | descrição que cabe numa linha e diz o QUÊ e a fronteira |
  specs | todo |` — numeração sequencial global.
- Declare dependências entre tasks na própria descrição ("depende de T-YYY") e o que pode
  andar em paralelo (raia api/client × raia workers/eval × raia contrato).
- Trabalho de natureza diferente = task separada (criar exercício ≠ gravar corpus ≠ promover
  maturidade — precedente T-032/T-053).
- Marcos devem terminar em produto **funcional**, nunca em meia-mecânica no ar (Fase 5 é o
  modelo).
- **Superfície nova = texto novo, e ele nasce nas duas línguas** (SPEC-025, AGENTS §Fluxo 4).
  Ao escrever o §Escopo, diga de qual das cinco fontes de texto a frase vem — bundle do cliente
  (dicionário), catálogo de feedback (YAML do worker), banco (painel), código do servidor (YAML
  da API) ou HTML de shell. A pergunta não é decorativa: ela decide se a task é "acrescentar
  chave" ou "acrescentar coluna de tradução", e responder tarde é o que produz metade da tela
  numa língua. Idioma **não** é Fase Evolução de nada — é Fase Inicial de tudo desde a T-141.

- **Página pública nova = rota nova, e rota nova nasce na tabela** (SPEC-026, plano §4). Se a
  spec cria uma superfície que o buscador deve encontrar, o §Escopo declara: o caminho em cada
  idioma (o **slug é traduzido** — `/sobre/` × `/en/about/`, porque a palavra na URL é sinal de
  busca), as chaves de `title`/`description` no namespace `site`, e se ela é estática ou vem do
  banco. Nada de "e o SEO a gente vê depois": as quatro saídas — roteador, pré-render,
  `sitemap.xml` e `hreflang` — são geradas de `web/src/site/routes.ts`, então uma rota declarada
  na spec e esquecida na tabela não existe pela metade, ela não existe. E vale a invariante
  dura da SPEC-026: **nenhuma camada de idioma é redirecionamento** — o Googlebot rastreia dos
  EUA, e redirecionar por IP ou `Accept-Language` apaga a versão pt do índice.

## Encerramento

Igual a qualquer sessão: entrada no DEVLOG (decisões e alternativas rejeitadas), commit
`docs: SPEC-XXX ...`. Spec é documentação executável do futuro — o DEVLOG é a memória de por
que ela é assim.
