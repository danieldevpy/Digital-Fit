# SPEC-017 — Perfil Físico & Progresso Realista
Status: draft | Camada: api + client | Depende de: SPEC-010, SPEC-011, SPEC-016 | Referência: ideia "peso e altura → progresso interessante e realista" (2026-07-30)

## Entidade e responsabilidade

Colher **peso e altura** de quem já tem conta e transformar isso em progresso interessante e **realista** — números que um profissional de educação física não desmentiria. É a ponte entre o dataset de sessões (SPEC-010) e um produto de retenção.

## Fase Inicial

### Escopo / Comportamento

- **Coleta**: no Perfil (AccountSheet), campos peso (kg) e altura (cm), opcionais, editáveis, com data da última atualização. Pedidos uma única vez após a 2ª sessão de quem tem conta ("Quer resultados em kcal reais?") — nunca no primeiro acesso (SPEC-015).
- **Uso imediato**: kcal MET com peso real em vez dos 70kg default (`kcal = MET × 3,5 × peso ÷ 200 × minutos`); IMC exibido no perfil com faixa e sem julgamento.
- **Progresso realista (assinante, SPEC-016)**: tela Progresso com — kcal acumuladas (dia/semana), reps totais por exercício, frequência (dias treinados), e estimativas honestas com margem declarada ("~120–180 kcal esta semana"). Nada de "você perdeu X kg" — não medimos peso ao longo do tempo, medimos treino.
- **Registro de peso ao longo do tempo**: o usuário pode reeditar o peso; cada edição vira ponto numa série temporal simples (gráfico de linha no Progresso).

### Fora de escopo (vai para Evolução)

- Metas (peso-alvo, kcal/semana) e planos de treino sugeridos.
- Integração com balanças/wearables/HealthKit.
- Qualquer recomendação nutricional (fora do produto).

### Critérios de aceite

1. Conta sem medidas: tudo funciona, kcal marcada "estimada (70kg)".
2. Com peso: kcal recalcula na próxima sessão; perfil mostra IMC.
3. Progresso mostra apenas agregados deriváveis dos eventos gravados (SPEC-010 — replay-derivable).
4. LGPD: peso/altura entram no export e na exclusão de dados (T-036).

## Eventos (consome / produz)

Consome `session.completed` (agregados). Peso/altura são dados de perfil (REST SPEC-011), não eventos.

## Notas técnicas

- Peso em kg com uma casa decimal; validação 30–300kg / 100–250cm — fora disso, pedir confirmação, não recusar.
- Série temporal de peso: tabela `profile_weight_log (user, kg, at)` — trivial e suficiente.
- MET por exercício vive no catálogo do servidor (polichinelo ≈ 8, agachamento ≈ 5); espelhado no client para o kcal ao vivo (SPEC-016).
