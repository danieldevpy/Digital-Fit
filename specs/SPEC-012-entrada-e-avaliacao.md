# SPEC-012 — Fontes de Entrada & Bancada de Avaliação
Status: draft | Camada: cli (Python) + client | Depende de: SPEC-005, SPEC-006, SPEC-007

## Entidade e responsabilidade

Abstrai a **origem** dos dados e transforma o desenvolvimento em ciência: em vez de testar só com a câmera ao vivo, o sistema aceita múltiplas fontes de entrada e mede sua própria precisão contra um corpus de vídeos rotulados. É a entidade que permite "ir melhorando" com evidência, não com impressão.

## Os três níveis de entrada (pirâmide de teste)

| Nível | Fonte | Testa o quê | Velocidade |
|---|---|---|---|
| 1 | **Fixtures de keypoints** (JSON/Parquet gravados) | FSM, normalização, feedback — sem CV | ms (pytest) |
| 2 | **Arquivos de vídeo** (harness headless) | Pipeline completo incl. extração de pose, robustez a luz/distância/ângulo | ~1×–3× tempo real |
| 3 | **Câmera ao vivo** | UX, latência, probe, WS | manual |

Tudo converge para os mesmos eventos `pose.frame` — nenhum código downstream sabe a origem (`source: "file"` novo valor no envelope).

## Fase Inicial

### Escopo / Comportamento

**1. CLI `evalctl` (Python, roda local sem Docker):**

```
evalctl run video.mp4 --exercise jumping_jack        # 1 vídeo → resultado
evalctl run testdata/ --report out/eval.json          # corpus inteiro
evalctl compare out/eval_v1.json out/eval_v2.json     # regressão entre versões
```

- Pipeline: decode (OpenCV) → MediaPipe Python (mesmo modelo `lite` do cloud) → normalização → FSM → relatório por vídeo (reps contadas, sinais de qualidade, warnings de cena).
- Reusa os MESMOS módulos dos workers (`normalize`, `ExerciseAnalyzer`) — zero código duplicado; se o harness passa, o worker passa.
- `--save-keypoints` exporta os keypoints do vídeo como fixture de nível 1 (cada vídeo processado uma vez vira teste rápido para sempre).

**2. Corpus rotulado (`testdata/`):**

```yaml
# testdata/manifest.yaml
- file: jj_frontal_boa_luz.mp4
  exercise: jumping_jack
  expected_reps: 20
  conditions: {light: good, distance: 2.5m, angle: frontal, subject: daniel}
- file: jj_contraluz_3m.mp4
  expected_reps: 15
  conditions: {light: backlit, distance: 3m, angle: frontal}
- file: negativo_polichinelo_agachamento.mp4   # vídeo de OUTRO exercício
  exercise: jumping_jack
  expected_reps: 0                              # não deve contar nada
```

- Corpus inicial: 12–15 vídeos gravados por você (celular basta) variando: luz (boa/fraca/contraluz), distância (2m/3m/4m), ângulo (frontal/±30°), execução (limpa/preguiçosa/rápida) + 2–3 negativos (outro movimento, pessoa parada).
- Vídeos ficam FORA do git (grandes) — `testdata/` só com manifest + script de download (object storage ou pasta sincronizada).

**3. Métricas do relatório de avaliação:**

- Por vídeo: reps contadas vs. esperadas (erro absoluto), falsos positivos em negativos.
- Agregado: MAE de reps, % de vídeos exatos, taxa de FP, quebra por condição (a tabela que mostra "contraluz derruba a acurácia em X%").
- `evalctl compare` marca regressões em vermelho: mudou o filtro? roda o corpus, vê o impacto em 2 min.

### Fora de escopo (vai para Evolução)

Upload de vídeo pela UI web, replay no sistema completo via WS, eval em CI, datasets públicos.

### Critérios de aceite

1. `evalctl run` sobre o corpus roda sem sistema no ar (só Python) e gera `eval.json` com métricas agregadas e por condição.
2. Harness e analysis-worker importam o mesmo módulo de FSM/normalização (verificável por import).
3. `--save-keypoints` gera fixture que o pytest de nível 1 consome sem conversão.
4. Vídeo negativo com pessoa parada → 0 reps.

## Fase Evolução

- **Fonte de vídeo na UI web**: upload/URL tocando num `<video>` oculto processado pelo MESMO caminho edge do browser — testa o pipeline edge real (WASM) com vídeos, e valida paridade edge×cloud×harness (par com T-018).
- **Modo replay integrado**: `evalctl replay --ws` injeta keypoints gravados no gateway como se fosse um cliente — teste de integração e de carga (30 sessões sintéticas simultâneas na VPS = T-028 sem 30 voluntários).
- **Eval em CI**: subset rápido (4–5 vídeos via fixtures de keypoints) roda em todo push; corpus completo semanal ou manual. PR que degrada acurácia falha o build.
- **Corpus crescido por produção**: sessões reais com scene score alto e rotuladas (SPEC-010 evolução) entram no corpus — o produto gera seu próprio benchmark.
- **Datasets públicos** (RepCount, Countix) como complemento para diversidade de corpos/ambientes — verificar licença antes.
- Métricas de qualidade além de contagem: precisão dos sinais (`ARMS_TOO_LOW` emitido nos momentos certos, validado por rótulo temporal).

## Eventos

Produz `pose.frame` com `source: "file"` (nível 2/3 evolução). Nível inicial roda offline, sem broker.

## Notas técnicas

- Determinismo: mesmo vídeo + mesma versão → mesmo resultado (seed fixa, sem threads não-determinísticas) — senão `compare` não significa nada.
- `eval.json` versionado com hash do commit + versão do modelo MediaPipe.
- Gravação do corpus: guia de 1 página (`testdata/GUIA-GRAVACAO.md`) para padronizar como filmar cada condição.
