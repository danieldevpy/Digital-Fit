# SPEC-021 — Exercícios Isométricos (modalidade *hold*)
Status: approved (revisão 2026-07-31) | Camada: contrato + worker + api + client | Depende de: SPEC-002, SPEC-007, SPEC-010, SPEC-014 | Habilita: Tier B da SPEC-020, "dia leve" da SPEC-019

## Entidade e responsabilidade

Segunda modalidade de análise: exercícios que **não têm repetição** — a pessoa entra numa
posição e o valor é *quanto tempo ela sustenta a forma correta*. Wall sit, prancha, e depois
toda a família de alongamento/mobilidade ("segure X por Y segundos").

É uma capacidade do motor, não um exercício: construída uma vez, destrava o Tier B inteiro da
SPEC-020 e dá à SPEC-019 o "dia leve" que protege o fogo sem exigir treino intenso diário. A
SPEC-007 já a previa ("prancha — modalidade *tempo*, não *reps*; a interface já suporta via
eventos `hold.progress`"); esta spec paga essa promessa.

## Modelo da modalidade

Cada exercício declara `scoring: "reps" | "hold"` no registro (`EXERCISES`) e no catálogo. O
`ExerciseAnalyzer` é o mesmo protocolo — muda o que `step()` emite:

- **Em posição** (features dentro da janela de sustentação): o relógio de tempo válido corre.
- **Fora de posição**: o relógio para; não zera. Sair e voltar soma trechos — punir com zerar
  transformaria um tremor de keypoint em rage quit.
- **Histerese como nas FSMs cíclicas**: limiar de *entrar* mais exigente que o de *permanecer*
  (entrou com quadril < 0,74, permanece até 0,80) — sem isso a fronteira vira metralhadora de
  entra/sai.
- **Frames `degraded` congelam o relógio** (não somam, não zeram) — mesma regra que congela a
  FSM cíclica na SPEC-007.
- Qualidade: sustentar em posição rasa emite o sinal do exercício (`HIPS_TOO_HIGH` no wall
  sit), roteado pela SPEC-008 como qualquer outro.

## Contrato de eventos (mexer em `workers/shared/events.py` PRIMEIRO — AGENTS.md)

| Evento | Produtor | Consumidores | data |
|---|---|---|---|
| `hold.progress` | analysis-worker | gateway→HUD, report-builder | `valid_ms` (acumulado), `in_position: bool` — emitido a ~1 Hz e na transição |
| — | | | |

Sem evento novo de "quebrou": a transição `in_position: true → false` **é** a informação, e um
`hold.broken` separado seria o mesmo fato dito duas vezes. `rep.detected` não é emitido por
exercício hold. `session.completed` e o fluxo de fim não mudam — o timer autoritativo de 30 s
(SPEC-009) continua mandando.

`SessionResult` ganha colunas **aditivas** (default 0, nenhum consumidor atual quebra):
`hold_valid_ms` (total sustentado) e `hold_best_ms` (maior trecho contínuo). O relatório de um
exercício hold mostra tempo, não reps.

## Primeiro exercício: wall sit (`wall_sit`)

Escolhido porque é o isométrico **mais barato do mundo real**: em pé, câmera frontal (o
enquadramento que tudo já valida), e a feature é a **altura do quadril que o `squat` já
calcula** — quadril→tornozelo em torsos. Em posição: < 0,78 na entrada, permanece até 0,84
(números iniciais para o gerador sintético; calibração real segue a escada de maturidade da
SPEC-020). Raso demais (0,84–0,90 sustentado) → `HIPS_TOO_HIGH`.

Prancha fica explicitamente para depois: é hold **+** chão (Tier C — guia de posicionamento de
câmera e validação de cena deitada, evolução da SPEC-003). Misturar as duas novidades numa
task só é o jeito de não entregar nenhuma.

## HUD e relatório (SPEC-014)

- Tela de treino: o anel de REPETIÇÕES vira anel de **TEMPO EM POSIÇÃO** (conta para cima,
  mm:ss, mesma posição e tamanho — legível a 2 m, regra da Revisão 1). Fora de posição o anel
  esmaece e o toast do coach diz o porquê (sinal de qualidade da SPEC-008).
- O anel de TEMPO RESTANTE (sessão) não muda — são dois relógios com papéis diferentes e
  rótulos distintos.
- Relatório: "Tempo em posição 22 s · melhor sequência 15 s" no lugar do bloco de reps;
  cadência/rep_durations ficam vazios e as telas não os desenham para hold.
- Figura própria em `EXERCISE_FIGURES` (teste da T-082 cobra) + guia SPEC-015.

## Sessão válida e XP (amarra com a SPEC-019)

Exercício hold é **sessão válida** com `hold_valid_ms ≥ 10_000` (10 s sustentados em 30 s de
sessão — piso generoso de propósito: o dia leve existe para manter o fogo acessível, não para
ser mais uma prova). A regra vive no `engagement.py` da SPEC-019, que recebe o `scoring` do
exercício por parâmetro justamente para isto — o módulo continua puro e a fixture não precisa
de banco.

**Hold precisa de linha própria na fórmula de XP, senão o dia leve paga um terço.** A tabela da
SPEC-019 é toda rep-based: sem componente de tempo, um wall sit sustentado 25 s rende +10
(sessão) +10 (limpa) = **20 XP**, contra os 60 de um polichinelo. O "dia leve" existe para
proteger o fogo em dia de corpo cansado; fazer dele um dia de XP ruim é ensinar que ele é uma
escolha inferior — e a pessoa que precisava dele treina errado ou não treina. Componente novo,
espelhando as reps para que as duas modalidades tenham o mesmo teto:

| Componente (hold) | Valor |
|---|---|
| Tempo sustentado | +1 XP a cada 2 s de `hold_valid_ms`, teto +40 |

Isso incrementa `XP_FORMULA_V` (§XP da SPEC-019) e, como a fórmula é derivada, o histórico
inteiro é recalculado — que é exatamente o motivo de ela ser versionada. Sessões `reps` não
mudam de valor: o componente só é lido quando `scoring == "hold"`.

## Fase Inicial

### Escopo / Comportamento

- `scoring` no registro/catálogo; `hold.progress` no contrato; colunas aditivas no
  `SessionResult` + consolidação no report-builder.
- Modalidade hold no analysis-worker (relógio válido, histerese, degraded congela) como código
  compartilhado em `exercises/` — o wall sit é uma parametrização, não dono da lógica.
- `wall_sit` completo pela checklist da SPEC-020 (gerador, fixtures, figura, guia, feedback,
  `maturity: beta`).
- HUD de hold + relatório de hold.
- Regra de sessão válida no engajamento.

### Fora de escopo (vai para Evolução)

Prancha e qualquer exercício de chão (Tier C); metas de hold ("segure 60 s"); séries de hold
com descanso (SPEC-009 evolução); sons/heartbeat de sustentação (Modo Efeito, SPEC-016).

### Critérios de aceite

1. Fixture sustentando 20 s limpos → `hold_valid_ms ≈ 20_000` (tolerância 1 frame).
2. Fixture que sai 2× da posição → soma dos trechos, `hold_best_ms` = maior trecho; nunca zera.
3. Fixture com frames `degraded` no meio → relógio congela (não soma, não zera).
4. Fixture tremendo na fronteira do limiar → sem flip-flop (histerese comprovada).
5. Sessão de wall sit não emite `rep.detected`; relatório mostra tempos e nenhuma tela mostra
   reps/cadência para hold.
6. Wall sit com 12 s sustentados acende o fogo; com 8 s, não.
7. Replay do stream reproduz o mesmo `SessionResult` (promessa da SPEC-010 intacta).
8. Wall sit de 25 s limpo e polichinelo de 25 reps limpo rendem XP da mesma ordem (teto igual);
   sessão `reps` não muda de XP com o bump de `XP_FORMULA_V`.
9. Um consumidor que não conhece `hold.progress` (report-builder da versão anterior, em teste)
   processa a sessão sem erro — a prova de que o contrato é aditivo e o bump é desnecessário.

## Fase Evolução

Prancha (junto do Tier C); família alongamento/mobilidade parametrizada (posição-alvo por
ângulos + janela); meta de hold por sessão; feedback progressivo ("15 s! aguenta mais 5");
detecção de compensação (quadril caindo lentamente — derivada no tempo, não limiar).

## Eventos (consome / produz)

Consome: `pose.frame`. Produz: `hold.progress` (novo), `feedback.issued` (existente).

**`PROTOCOL_VERSION` não sobe** — e esta linha decide, em vez de deixar a dúvida para a task. A
mudança é inteiramente aditiva em ambos os lados: um evento novo que consumidor antigo ignora
(o gateway repassa o que não conhece, o report-builder faz `match` por tipo) e colunas com
default 0 num modelo que ninguém lê por posição. Nenhum produtor ou consumidor existente precisa
mudar para continuar correto, que é o teste do bump. Subir a versão por mudança aditiva treina o
projeto a ignorar o número — e o dia em que ele significar algo (mudança de formato de
`pose.frame`, por exemplo) é o dia em que precisamos que ele seja levado a sério.

## Notas técnicas

- O relógio válido conta por timestamps dos frames (`ts`), nunca por contagem de frames — fps
  varia por aparelho (lição do T-084).
- `hold.progress` a 1 Hz + transições: ~30 eventos por sessão, ruído desprezível no stream.
- Reusar a feature de altura do quadril importando o módulo do `squat`, não copiando — mesma
  regra de feature compartilhada da SPEC-020 (§Notas).
