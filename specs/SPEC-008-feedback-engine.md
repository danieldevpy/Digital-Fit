# SPEC-008 — Feedback Engine
Status: draft | Camada: worker + client (HUD) | Depende de: SPEC-007, SPEC-003

## Entidade e responsabilidade

Converte sinais brutos da análise (`quality.signal`, `scene.warning`) em **feedback humano, priorizado e não-irritante**, entregue pelo event loop ao HUD em tempo real e consolidado no relatório.

## Fase Inicial

### Escopo / Comportamento

- Catálogo de mensagens por código: `ARMS_TOO_LOW` → "Estenda mais os braços acima da cabeça", `LEGS_TOO_CLOSED`, `OUT_OF_FRAME`, `TOO_FAR`, `TOO_CLOSE` (pt-BR, i18n-ready por estrutura de catálogo).
- **Rate limit por código**: mesmo código no máximo 1×/4s; máximo 1 feedback simultâneo no HUD.
- **Prioridade**: cena (`OUT_OF_FRAME`) > execução (`ARMS_TOO_LOW`) > ritmo.
- Superfície visual: card "Dica do Treinador" da SPEC-013 (layout, estados e prioridades definidos lá; esta spec define O QUE é dito e quando, a 013 define COMO aparece).
- Todos os feedbacks emitidos são acumulados no estado da sessão → relatório (SPEC-010).

### Fora de escopo (vai para Evolução)

Áudio/TTS, feedback positivo/motivacional, agregação inteligente, personalização de tom.

### Critérios de aceite

1. Rep preguiçosa contínua gera feedback a cada ~4s, nunca a cada rep.
2. `OUT_OF_FRAME` suprime feedbacks de execução enquanto ativo.
3. Latência sinal→HUD < 150ms (herda o orçamento da SPEC-002).

## Fase Evolução

- **Coach por voz**: TTS dos feedbacks (Web Speech API primeiro; áudio pré-gravado para os códigos comuns depois) — treinar sem olhar a tela.
- **Feedback positivo**: marcos ("10 reps!", melhor cadência) com throttle próprio.
- **Agregação por padrão**: 3× o mesmo código na sessão → mensagem única mais rica ("seus braços não estão passando da linha do ombro — tente…") em vez de repetição.
- Tom configurável (direto / motivacional / silencioso).
- A/B de eficácia de mensagem via telemetria (correção observada nas reps seguintes).

## Eventos

Consome: `quality.signal`, `scene.warning`, `rep.detected`. Produz: `feedback.issued {code, severity, message, hint}`.

## Notas técnicas

- Motor = fila priorizada + tabela de throttle por código; puro e testável.
- Catálogo de mensagens em YAML (`feedback/catalog.pt-BR.yaml`) — permite ajustar texto sem deploy de código.
