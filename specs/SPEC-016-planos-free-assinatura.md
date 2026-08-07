# SPEC-016 — Planos: Modo Free × Modo Assinatura
Status: draft | Camada: api + client | Depende de: SPEC-009, SPEC-011, SPEC-014 | Referência: ideias "MODO FREE" / "MODO ASSINATURA" (2026-07-30)

## Entidade e responsabilidade

Define o que cada plano pode fazer e onde o produto mostra o limite. Princípio: o Free é um produto **bom e completo em sessão única** — o que ele não tem é acúmulo, volume e efeitos. A trava é sempre **no servidor** (quota/admission, SPEC-009/011); a UI apenas reflete e vende o upgrade, nunca é a única barreira.

## Matriz de capacidades

| Capacidade | Free | Assinatura |
|---|---|---|
| Sessões de exercício | boa quantidade, **limite diário** (proposta inicial: 10/dia, contado por `session.completed`) | sessões muito maiores (duração configurável, séries/circuitos — SPEC-009 evolução) e limite diário generoso |
| Duração da sessão | 30s fixa | configurável (30s–5min, steppers da pré-config passam a valer) |
| Modos de exercício | modo padrão | modos diferentes (meta de reps, circuito, desafio) |
| Calorias | **mede só na hora** (kcal ao vivo na sessão, por repetição); acúmulo diário/histórico **bloqueado** | contagem progressiva: acumulado do dia, semana, histórico |
| Progresso/histórico | limitado (últimas N sessões, sem gráficos) | avançado (SPEC-010 evolução + SPEC-017) |
| Modo Efeito (efeitos visuais premium do esqueleto/HUD) | bloqueado | liberado |
| Perfil físico (peso/altura → kcal reais, progresso realista) | — | incluído (SPEC-017) |

"Modo Efeito" = pacote de efeitos visuais da Fase Evolução da SPEC-013/014 (esqueleto reagindo à fase, trilhas de acerto, temas de cor). É cosmético de propósito: bloquear cosmético não degrada o treino de quem é Free.

## Fase Inicial

### Escopo / Comportamento

- Campo `plan` (`free` | `subscriber`) no usuário (SPEC-011); anônimo = Free.
- Contador diário de sessões por usuário/dispositivo no Redis (`df:quota:<user>:<yyyy-mm-dd>`, TTL 48h); `POST /sessions` recusa com `429 quota_exceeded` após o limite.
- UI: chip de plano no Perfil; ao bater o limite, sheet "Você treinou muito hoje 🎉" com contagem, hora em que renova e CTA de assinatura (ainda sem checkout — lista de espera/`em breve`).
- Kcal ao vivo (a "medição na hora" do Free): cálculo client-side **por repetição**, com peso default 70kg marcado "estimado" (SPEC-013 §Evolução) — aparece no card CALORIAS da sessão para todos; o **acúmulo** (dia/histórico) só para assinante.

  **Por repetição, e não por tempo decorrido** (correção de 2026-08-01, T-128). A primeira versão desta linha dizia "cálculo MET client-side" e foi implementada como `MET × 3,5 × peso / 200 × minutos` (T-063). A fórmula está certa e o insumo estava errado: ela cobra a mesma caloria de quem faz 40 polichinelos em 30s e de quem fica parado olhando a câmera — o número sobe com o **relógio**, não com o esforço. Num app que conta repetição por visão computacional, gastar o dado que ele existe para produzir e faturar tempo de tela é a mentira mais fácil de não perceber.

  O que vale:

  ```
  kcal_por_rep = (MET × 3,5 × peso_kg / 200) / cadência_referência_rpm
  kcal         = reps × kcal_por_rep × m(cadência_medida)
  ```

  - **`cadência_referência_rpm` é dado do catálogo** (`Exercise.ref_cadence_rpm`, SPEC-018 §B), ao lado do `met` e pelo mesmo motivo: o MET de tabela vale a um ritmo, e o ritmo é propriedade do movimento — 20 rpm é rápido para agachamento e lento para polichinelo. Constante no cliente seria o `[A/T-051]` recomeçando.
  - **`m()` é o multiplicador de ritmo**: quem acelera perde economia de movimento (mais aceleração e frenagem por rep, menos aproveitamento elástico). É modesto e **travado** — `m = 1 + K·(c/c_ref − 1)`, limitado a uma faixa estreita, porque um pico de detecção não pode virar um número absurdo na tela. Cadência só é considerada depois de uma janela mínima de sessão; antes disso `m = 1`.
  - **Propriedade que amarra as duas versões**: no ritmo de referência a fórmula nova dá exatamente o mesmo número da antiga. A mudança não reescala o produto — ela faz o número responder a quem está treinando.
  - **Sem MET ou sem cadência de referência, o card mostra `--`.** Cair de volta no cálculo por tempo seria reintroduzir o defeito em silêncio, justamente no caminho degradado onde ninguém olha.
  - **Reps são as do servidor** (`rep.detected`, SPEC-007), não uma contagem do cliente. O kcal passa a ser derivado de dado que o servidor produziu — mais perto da regra da SPEC-014, não mais longe.

### Fora de escopo (vai para Evolução)

- Checkout/pagamento (Stripe/Mercado Pago — T-036), trial, downgrade/upgrade automático.
- Modos de exercício alternativos (dependem da SPEC-009 evolução).
- Modo Efeito em si (depende dos efeitos existirem).

### Critérios de aceite

1. 11ª sessão do dia (Free) é recusada pelo servidor; a UI mostra o sheet de limite antes mesmo de abrir a câmera.
2. Assinante (flag manual no banco) não é recusado.
3. Kcal ao vivo aparece na sessão para todos; nenhuma tela do Free soma kcal entre sessões.
   3.1. O número **não anda sem repetição**: sessão parada mantém o card em zero, e duas
   sessões de mesma duração com contagens diferentes dão calorias diferentes.
   3.2. Ritmo acima da referência rende mais por repetição, dentro de uma faixa travada; um
   pico de cadência não produz número absurdo.
4. Forjar o client não fura a quota (a trava é a API).

## Eventos (consome / produz)

`session.completed` alimenta o contador. Recusa de admission ganha razão nova: `quota_exceeded` (adicionar ao contrato quando implementar).

## Notas técnicas

- Limite diário renova à meia-noite do fuso do usuário — na prática, usar UTC e mostrar "renova em Xh" para não abrir discussão de fuso na Fase Inicial.
- Anônimo é rastreado por device-id local; é furável trocando de navegador — aceitável na Fase Inicial, resolver junto com auth obrigatória de quem quer histórico.
