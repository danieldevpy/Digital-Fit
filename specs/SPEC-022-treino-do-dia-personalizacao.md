# SPEC-022 — Treino do Dia & Personalização
Status: approved (revisão 2026-07-31) | Camada: api + client | Depende de: SPEC-016, SPEC-017, SPEC-018, SPEC-019, SPEC-020 | Referência: ideia "adaptar para assinantes por idade, IMC, objetivo" (2026-07-30)

## Entidade e responsabilidade

O conteúdo que muda todo dia e foi montado "para mim": o **Treino do Dia** — uma seleção
diária de 3–5 exercícios calibrada pelo perfil (objetivo, idade, IMC) — e os campos de perfil
que a alimentam. É a "lição do dia" do Duolingo e o principal benefício de retenção da
assinatura depois do fogo: o fogo dá o *porquê voltar*; o Treino do Dia dá o *o que fazer ao
voltar*, eliminando a paralisia de escolha.

Fronteira dura, herdada da SPEC-017 e reafirmada: **personalização de treino, nunca prescrição
de saúde.** Ajustamos impacto e volume por dados declarados; não prometemos resultado clínico,
não recomendamos nutrição, não interpretamos condição médica. Números que um profissional de
educação física não desmentiria.

## Perfil (aditivo à SPEC-017)

- `birth_year` (int, opcional) — ano, não data completa: é o que a seleção precisa e é o mínimo
  de dado pessoal (LGPD: entra no export/exclusão como peso/altura).
- `goal` (`emagrecer | condicionar | fortalecer`, opcional) — pergunta única, editável no
  Perfil, pedida no mesmo momento suave em que a SPEC-017 pede peso ("depois da 2ª sessão"),
  nunca no primeiro acesso (SPEC-015).
- IMC já deriva da SPEC-017 (peso/altura). **Perfil incompleto nunca bloqueia**: sem objetivo,
  a seleção usa `condicionar`; sem idade/IMC, não aplica ajuste de impacto. Menos dado = treino
  mais genérico, nunca treino nenhum.

## O motor de seleção (determinístico e derivável)

Função **pura** em `server/api/daily_workout.py`:

```
treino_do_dia(perfil, data, catalogo_validado, historico_agregado) -> [TreinoItem]
```

- **Determinística por (usuário, data)**: seed = hash(user_id, data-SP). Recarregar a tela dá
  o mesmo treino; dois usuários iguais em dias diferentes variam. Sem estado persistido — o
  treino de qualquer dia é recomputável (mesma filosofia da SPEC-019).
- **Composição**: 3–5 itens, só exercícios `validado` (SPEC-020); sempre ≥ 1 de `mobilidade`
  (o dia leve embutido); nunca o mesmo exercício 2× no dia; variedade contra os últimos 3 dias
  (o histórico agregado que a SPEC-019 já consulta).
- **Objetivo pesa categorias**: emagrecer → cardio-pesado (3 cardio, 1 força, 1 mobilidade);
  fortalecer → força-pesado; condicionar → balanceado.
- **Ajuste de impacto** (idade ≥ 60 **ou** IMC ≥ 30, quando declarados): substitui saltos por
  equivalentes de baixo impacto da mesma categoria (polichinelo → marcha; jump squat → squat).
  Framing na UI: "treino de baixo impacto", tom neutro, sem julgamento — mesma regra do IMC na
  SPEC-017. Não é conselho médico e a tela não finge que é.
- A intensidade dentro do item (duração/meta) segue as capacidades do plano (SPEC-016) — o
  motor escolhe *o quê*, não desrespeita *o quanto* o plano permite.

## Quem vê o quê (SPEC-016 estendida)

| | Anônimo | Free | Assinatura |
|---|---|---|---|
| Card Treino do Dia na Início | bloqueado, CTA conta | bloqueado, CTA assinatura — mostra as **categorias** do dia ("Cardio · Força · Mobilidade"), não os itens | completo: itens, progresso do dia, iniciar em sequência |
| Perfil (objetivo/idade) | — | pode preencher (já melhora kcal/UX e fica pronto para o upgrade) | usado pelo motor |

O teaser do Free mostra a *forma* do benefício sem entregá-lo — honesto (não finge conteúdo) e
vendedor (o cadeado tem conteúdo real atrás).

**O gate é `Plan.daily_workout`, não comparação de slug.** A coluna vem da SPEC-018/T-073
(`false` para anon e Free, `true` para assinante). Escrever `plan.slug == "subscriber"` numa view
seria a decisão comercial voltando para dentro do código — o oposto do que a SPEC-018 inteira
existe para conseguir, e o motivo pelo qual mudar de ideia sobre isto precisaria de deploy.

E uma honestidade sobre o cadeado: a seleção é **determinística e o algoritmo é público**, então
quem quiser recomputa o próprio treino do dia com o catálogo aberto e o `user_id`. Isso não é uma
falha — não há segredo aqui, só um produto. O que a trava faz, e é o que ela deve prometer, é a
API **não entregar** os itens ao Free; qualquer critério que diga "o Free não consegue obter" é
inverificável e seria um teste mentindo.

## Conclusão e recompensa (amarra com a SPEC-019)

Item concluído = sessão válida daquele exercício naquele dia-SP (derivável de
`SessionResult`, como tudo). Treino do dia completo → o anel do dia fecha independentemente da
meta configurada, e a conquista `treino-do-dia-7` (7 completos seguidos) entra no catálogo.

**Sem bônus de XP, e pelo mesmo motivo que derrubou o bônus de meta na SPEC-019.** Uma versão
anterior desta spec dava +25 XP na conclusão. Não pode: a seleção do dia depende de `goal`,
`birth_year` e do IMC — campos mutáveis do perfil. Quem edita o objetivo muda, retroativamente,
*quais* exercícios cada dia passado pedia, portanto muda quais dias contam como concluídos,
portanto muda o XP histórico. É exatamente o mesmo mecanismo, com um agravante: aqui o usuário
nem sabe que mexeu no passado. A regra da SPEC-019 §XP vale sem exceção — **XP só lê
`SessionResult`**; componente que precise de outra fonte tem que virar fato gravado antes.

A conquista sobrevive porque conquista não é acumulador: ela é um predicado sobre o estado de
agora, e uma conquista que reaparece depois de uma edição de perfil é estranha, não é um saldo
errado. `XP_FORMULA_V` **não** é incrementado por esta spec.

Se o bônus for considerado necessário para a retenção, o caminho honesto é persistir a conclusão
(`daily_workout_done(user, date)`) — um fato novo, com tabela, justificado como a SPEC-019 exige
para escrita não-derivável. Fica de fora da Fase Inicial: primeiro medir se o card muda
comportamento, depois pagar por estado.

## Fase Inicial

### Escopo / Comportamento

- Campos `birth_year` e `goal` no perfil (REST, export/exclusão LGPD).
- Motor puro + fixtures (perfis × datas × catálogos) e `GET /api/daily-workout` (assinante;
  Free recebe só as categorias do dia; anônimo 401) com cache diário em Redis.
- Card na Início nas três variantes (gate por `Plan.daily_workout`, coluna pronta da
  SPEC-018/T-073); assinante navega item → pré-config com o exercício já selecionado; progresso
  do dia no card (2/4 ✓).
- Conquista `treino-do-dia-7` no catálogo da SPEC-019. Sem mexer na fórmula de XP.

### Fora de escopo (vai para Evolução)

Periodização semanal (dia pesado/leve alternados de propósito); ajuste por desempenho medido
(cadência caindo → reduzir volume); metas de médio prazo ("~X kcal/semana", SPEC-017
Evolução); iniciar os itens em sequência automática com descanso (depende de séries/circuitos,
SPEC-009 Evolução); notificação "seu treino de hoje chegou" (junto do push da SPEC-019).

### Critérios de aceite

1. Mesmo usuário, mesma data → mesma seleção em qualquer chamada; datas diferentes variam.
2. Emagrecer/fortalecer/condicionar produzem os mixes declarados; sempre há 1 mobilidade;
   nunca item repetido no dia.
3. Perfil com idade 65 **e** perfil com IMC 31: nenhum item de salto; a UI diz "baixo
   impacto" sem outra qualificação.
4. Perfil vazio recebe treino genérico válido — nenhum campo é obrigatório.
5. `GET /api/daily-workout` chamado direto por um Free devolve as categorias do dia e **nenhum
   slug de exercício** no corpo; anônimo recebe 401. O gate lê `Plan.daily_workout` — virar a
   coluna no admin libera o card sem deploy e sem restart.
6. Completar os itens do dia rende o bônus exatamente 1×, e recálculo do zero reproduz o XP.
7. Exercício rebaixado de `validado` (SPEC-020) some das seleções do dia seguinte sem deploy.

## Fase Evolução

Bônus de XP por treino do dia concluído, se o card provar que muda comportamento — via
`daily_workout_done(user, date)` persistido, nunca por derivação sobre perfil mutável;
periodização semanal; dificuldade progressiva por desempenho real (o dataset da SPEC-010 é o
insumo); trilhas por objetivo (SPEC-020 Evolução) substituindo a seleção solta; "treinos
temáticos" editoriais (data comemorativa, desafio do mês) editáveis no admin (SPEC-018);
integração com metas quando a SPEC-017 Evolução as criar.

## Eventos (consome / produz)

Nenhum evento novo. Consome catálogo (`GET /api/config`), perfil e agregados de
`SessionResult`. O treino do dia é leitura; o treino em si continua nascendo pelo
`POST /sessions` de sempre.

## Notas técnicas

- Seed: `sha256(f"{user_id}:{data_sp}")` → PRNG local; nunca `random` global (reprodutível em
  teste por construção).
- Cache `df:dw:{user}:{data}` TTL 48 h; invalidação desnecessária (determinístico) exceto por
  mudança de perfil — editar objetivo/idade invalida a chave do dia (a pessoa mudou o dado
  esperando efeito; entregá-lo amanhã pareceria bug).
- O card na Início entra na coluna de conteúdo existente da pré-config — sem tela nova; a
  Início continua sendo "abrir o app é abrir para treinar" (SPEC-014).
