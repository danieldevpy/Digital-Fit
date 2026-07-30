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
| Calorias | **mede só na hora** (kcal ao vivo na sessão); acúmulo diário/histórico **bloqueado** | contagem progressiva: acumulado do dia, semana, histórico |
| Progresso/histórico | limitado (últimas N sessões, sem gráficos) | avançado (SPEC-010 evolução + SPEC-017) |
| Modo Efeito (efeitos visuais premium do esqueleto/HUD) | bloqueado | liberado |
| Perfil físico (peso/altura → kcal reais, progresso realista) | — | incluído (SPEC-017) |

"Modo Efeito" = pacote de efeitos visuais da Fase Evolução da SPEC-013/014 (esqueleto reagindo à fase, trilhas de acerto, temas de cor). É cosmético de propósito: bloquear cosmético não degrada o treino de quem é Free.

## Fase Inicial

### Escopo / Comportamento

- Campo `plan` (`free` | `subscriber`) no usuário (SPEC-011); anônimo = Free.
- Contador diário de sessões por usuário/dispositivo no Redis (`df:quota:<user>:<yyyy-mm-dd>`, TTL 48h); `POST /sessions` recusa com `429 quota_exceeded` após o limite.
- UI: chip de plano no Perfil; ao bater o limite, sheet "Você treinou muito hoje 🎉" com contagem, hora em que renova e CTA de assinatura (ainda sem checkout — lista de espera/`em breve`).
- Kcal ao vivo (a "medição na hora" do Free): cálculo MET client-side com peso default 70kg marcado "estimado" (SPEC-013 §Evolução) — aparece no card CALORIAS da sessão para todos; o **acúmulo** (dia/histórico) só para assinante.

### Fora de escopo (vai para Evolução)

- Checkout/pagamento (Stripe/Mercado Pago — T-036), trial, downgrade/upgrade automático.
- Modos de exercício alternativos (dependem da SPEC-009 evolução).
- Modo Efeito em si (depende dos efeitos existirem).

### Critérios de aceite

1. 11ª sessão do dia (Free) é recusada pelo servidor; a UI mostra o sheet de limite antes mesmo de abrir a câmera.
2. Assinante (flag manual no banco) não é recusado.
3. Kcal ao vivo aparece na sessão para todos; nenhuma tela do Free soma kcal entre sessões.
4. Forjar o client não fura a quota (a trava é a API).

## Eventos (consome / produz)

`session.completed` alimenta o contador. Recusa de admission ganha razão nova: `quota_exceeded` (adicionar ao contrato quando implementar).

## Notas técnicas

- Limite diário renova à meia-noite do fuso do usuário — na prática, usar UTC e mostrar "renova em Xh" para não abrir discussão de fuso na Fase Inicial.
- Anônimo é rastreado por device-id local; é furável trocando de navegador — aceitável na Fase Inicial, resolver junto com auth obrigatória de quem quer histórico.
