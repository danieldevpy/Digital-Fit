# SPEC-003 — Validação de Cena
Status: draft | Camada: client (edge) / worker (cloud) | Depende de: SPEC-005, SPEC-006

## Entidade e responsabilidade

Garante que a cena permite análise confiável **antes e durante** a sessão: luz, distância, enquadramento e ângulo da câmera. É a entidade que "padroniza" o exercício — condição de qualidade dos dados de todo o resto.

## Fase Inicial

### Escopo / Comportamento (travas mínimas)

- **Enquadramento**: corpo inteiro visível = os 4 landmarks-âncora (ombros e tornozelos) com `visibility ≥ 0.5`. Falhou por > 1s → `scene.warning {code: OUT_OF_FRAME}` e HUD mostra silhueta-guia.
- **Distância (proxy grosseiro)**: altura do corpo (cabeça→tornozelo) entre 40% e 95% da altura do frame. Fora disso → `TOO_FAR` / `TOO_CLOSE`.
- Warnings **não bloqueiam** a sessão na fase inicial — apenas orientam e são anexados ao relatório.

### Fora de escopo (vai para Evolução)

Análise de luz, ângulo/tilt da câmera, fundo, oclusões, bloqueio de início por cena ruim.

### Critérios de aceite

1. Sair do quadro por 2s gera exatamente um warning (com debounce), não spam.
2. Warnings aparecem no HUD em < 300ms e constam no relatório final.
3. Zero falso-positivo de `TOO_FAR` em cena padrão (pessoa a 2–3m, câmera na cintura/peito).

## Fase Evolução

- **Luz**: histograma de luminância do frame (só cloud, ou amostrado 1×/s no edge via canvas): média < 60 → `LOW_LIGHT`; estouro > 15% de pixels saturados → `BACKLIT`. Sugestões acionáveis ("acenda a luz / vire de frente para a janela"). **Entregue na T-085 — ver §Aviso de cena na pré-configuração.**
- **Nitidez / lente suja** (item novo, T-085): energia de alta frequência do frame (variância do laplaciano) abaixo do limiar com luz boa → `SEM_NITIDEZ`. Não afirma a causa: lente suja, foco errado e pouca luz produzem o mesmo sintoma, e a mensagem pede a ação que resolve os três.
- **Ângulo da câmera**: inclinação da linha ombro-ombro e quadril-quadril vs. horizontal + razão torso aparente → detecta câmera muito baixa/alta ou pessoa não-frontal → `CAMERA_TILT`, `NOT_FACING`.
- **Distância ótima por exercício**: cada `ExerciseAnalyzer` declara faixa ideal (polichinelo: corpo a 60–85% do frame).
- **Gate de início**: sessão só inicia com cena `OK` por 1s contínuo (integra com SPEC-004); durante a sessão, cena ruim por > 3s pausa a contagem (não conta rep com dado ruim).
- **Score de qualidade da cena** (0–100) anexado à sessão — vira filtro de qualidade do dataset (SPEC-010).

## Aviso de cena na pré-configuração (T-085 — implementado)

Primeiro pedaço da Fase Evolução a entrar, e com escopo deliberadamente estreito. Decisões do Daniel, vinculantes:

1. **Orienta, nunca bloqueia.** Nenhum aviso impede treinar, nem desabilita o CTA. Travar por um limiar não calibrado é o caminho curto para o app parecer quebrado numa sala que funcionava.
2. **Só na tela de Início** (pré-configuração), que é onde a câmera abre para teste e onde ainda dá para limpar a lente e acender a luz. No treino a instrução de medição manda na tela (SPEC-014, T-071) e um aviso a mais disputaria espaço com o que importa.
3. **Um canal só**: o pill que já existe dentro da janela da câmera. O conselho toma o lugar da dica de enquadramento enquanto vale — enquadramento a silhueta-guia já ensina sozinha, luz e lente suja são invisíveis para quem está do outro lado do celular.
4. **Não afirma a causa** de imagem sem detalhe (lente suja × foco × luz): pede a ação que resolve os três.
5. **Roda no cliente, e só pode rodar lá**: no modo edge nenhum pixel sobe (keypoint-first). Amostra de 160×120 a 1×/s num canvas fora do DOM; a imagem não sai do aparelho.
6. **Debounce de 2 amostras** para acender **e** para apagar: alguém passando na frente da luz não dispara nada, e uma amostra boa solta não apaga um aviso que continua valendo.

Códigos: `LUZ_FRACA` · `CONTRALUZ` · `SEM_NITIDEZ`. Prioridade nessa ordem, e **nitidez só é julgada com luz boa** — no escuro o detalhe cai por outro motivo e o aviso mentiria a causa.

**Limiares são provisórios e vieram de medição, não de gosto.** Não existe corpus de cena ruim (o `eval/corpus` tem 3 vídeos, todos de boa luz). Foram medidos esses três como estão e em variantes sintéticas — escurecidos (×0,25) e borrados (boxblur 6) — com as mesmas contas do cliente. Duas conclusões mudaram o desenho:

- **Normalizar o laplaciano pelo contraste não serve para comparar cenas.** A razão `varLap/contraste²` é imune à luz e inútil entre cenas: o vídeo 03 **nítido** dá 0,15 e o vídeo 01 **borrado** dá 0,16 — um limiar sobre ela reprovaria a cena boa. Por isso a nitidez usa o laplaciano cru, com a luz como pré-condição.
- **Estouro alto não é contraluz.** O vídeo 01 tem 92,8% de pixels saturados e é cena boa (fundo claro, pessoa bem iluminada, centro em 244). Contraluz é fundo claro com sujeito **escuro** — a regra olha o centro do quadro, onde a silhueta-guia põe o corpo.

Recalibrar quando existir corpus de cena ruim (cozinha à noite, contraluz de janela, lente com digital); enquanto não existir, os limiares erram para o lado de **não** avisar. O custo de um falso positivo é uma frase a mais na tela — nunca um treino impedido.

## Eventos

Produz: `scene.warning {code, severity, hint}` · `scene.status {ok|degraded, score}` (evolução).
Consome: `pose.frame` (+ amostras de frame no modo cloud para análise de luz).

## Notas técnicas

- Toda checagem baseada em keypoints roda nas duas modalidades (edge/cloud) com o MESMO código Python no worker; no edge, réplica TS mínima apenas para feedback instantâneo de enquadramento.
- Debounce padrão de warnings: 1s para ligar, 2s para repetir o mesmo código.
