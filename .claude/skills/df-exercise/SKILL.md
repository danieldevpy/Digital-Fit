---
name: df-exercise
description: Fábrica de exercícios do Digital Fit. Use para criar um exercício novo (FSM cíclica ou modalidade hold), calibrar limiares, gravar/varrer corpus com evalctl, ou promover a maturidade de um exercício (beta → calibrado → validado). Trigger típico - "novo exercício", "implementar marcha/high knees/sumô/wall sit", tasks T-092 a T-096 e T-098/T-099, "promover exercício", "calibrar limiares". Complementa a df-executor (regras gerais de task) com a checklist específica de exercício da SPEC-020.
---

# Fábrica de Exercícios — Digital Fit

Um exercício novo NÃO é feature de UI: é um módulo de análise com prova de qualidade. A régua
é a SPEC-020 (roadmap por tiers + escada de maturidade) e a SPEC-007 (interface
`ExerciseAnalyzer`). Leia as duas antes de qualquer código.

## 0. Classificar antes de implementar

Confirme o **tier técnico** (SPEC-020): a câmera é frontal e a pessoa em pé? O movimento é
cíclico (FSM) ou sustentado (hold — SPEC-021)? A amplitude é grande? Há movimento no eixo Z?

Lições medidas que valem como lei:

- **A câmera frontal quase não vê o eixo Z.** O agachamento provou: 80° reais de joelho leem
  133° no plano da imagem. Feature boa é a que vive no plano X/Y (altura do quadril, abertura
  de tornozelos, ângulo de abdução) — desconfie de qualquer ângulo de articulação que dobra
  "para a frente".
- **Unidades em torsos, divisor do frame atual** (não o da calibração — lição da T-019).
- **Histerese sempre** (limiar de abrir ≠ de fechar) + debounce 250 ms; frames `degraded`
  congelam o estado (não contam, não penalizam).
- **Fase inicial é lida, não assumida** (T-047): o primeiro frame decide onde a FSM começa.

## 1. Checklist vinculante (Definition of Done da SPEC-020)

Nesta ordem — cada passo tem gate próprio:

1. **Feature compartilhada?** Se outro exercício já calcula o sinal (altura de quadril do
   `squat`, altura de joelho da `marcha`, `arm_angle` do polichinelo), **importe o módulo,
   não copie**. Parametrização > duplicação.
2. **Módulo** em `workers/analysis_worker/exercises/<slug>.py`, registrado em `EXERCISES`
   (`base.py`). Regra auditada da SPEC-007: exercício novo não pode exigir mudança fora de
   `exercises/` — se exigir, pare e registre a lacuna como Descoberta (é bug de interface).
3. **Gerador sintético** (`eval`/fixtures, precedente T-052): estenda o gerador com o
   parâmetro do movimento novo e produza as 4 fixtures canônicas — limpas (N exatas),
   preguiçosas (reps parciais → sinal de qualidade), jitter parado (0 reps), e
   começa-no-meio (conta a primeira). Para hold: sustenta-limpo, sai-e-volta (soma trechos),
   treme-na-fronteira (histerese), degraded-no-meio (relógio congela).
4. **Sinais de qualidade**: defina os códigos `*_TOO_*` do exercício + textos em
   `workers/analysis_worker/feedback/catalog.pt-BR.yaml`. Código novo entra no contrato
   (`Code`), texto é dado.
5. **Figura e apresentação**: entrada em `EXERCISE_FIGURES` (o teste da T-082 cobra figura de
   TODO exercício novo — não a contorne, obedeça-a), demo image, dot/categoria/MET no
   catálogo (client `web/src/session/catalog.ts` + `Exercise` no admin quando T-074 existir).
6. **Guia** (SPEC-015): passos de primeiro acesso (imagem + texto).
7. **Maturidade**: nasce `beta`. Promoção é TASK SEPARADA (ver §3) — nunca prometa `validado`
   na task de criação.

## 2. Calibrar limiares (sempre por medição, nunca por chute)

```bash
uv sync --extra server --extra eval
# gerador/fixtures:
uv run pytest tests/ -k <slug>
# vídeo real, quando houver:
uv run python -m eval.evalctl run video.mp4 --exercise <slug> --expected-reps N
uv run python -m eval.evalctl run eval/corpus/ --report eval/out/eval.json
```

Todo limiar escolhido entra no DEVLOG **com o número que o justificou** (tabela de varredura,
não adjetivo). Limiar é constante em código — nunca campo de admin (SPEC-018 P3).

## 3. Escada de maturidade (promoções são tasks próprias)

| Promoção | O que exige | Evidência registrada |
|---|---|---|
| `beta → calibrado` | corpus real ≥ 8 vídeos rotulados (`manifest.yaml`, guia de gravação da T-038); varredura de limiares contra ele; erro ≤ ±1 rep/20 | tabela da varredura no DEVLOG |
| `calibrado → validado` | paridade edge×cloud×browser no mesmo vídeo (fluxo T-040: `evalctl parity ... --browser <json>`) **+** ≥ 1 semana em produção com taxa de sessões zero-rep < 20% | saída do parity + consulta de produção |

Rebaixamento usa a mesma régua ao contrário: regressão medida → rebaixar no catálogo (some do
Free sem deploy) e abrir task de correção.

## 4. Gates finais

Os da df-executor (ruff, pytest, web se tocado) **mais**:

- `evalctl run` roda o exercício novo contra o gerador sem erro;
- o teste de figura (T-082) passa;
- abrir sessão do exercício pelo produto real (seleção → pré-config → treino) conta/mede na
  tela — se não der para verificar em aparelho, declare a pendência no DEVLOG.

## Anti-padrões (pare se estiver fazendo isso)

- Copiar a FSM de outro exercício e "ajustar números" sem gerador/fixtures próprios.
- Calibrar olhando o próprio corpo na webcam e chamar de calibrado (isso é `beta`).
- Colocar exercício `beta`/`calibrado` visível para Free — a prateleira do Free é `validado`.
- Prometer prancha/chão junto de hold: são DUAS capacidades (SPEC-021 §wall sit explica).
