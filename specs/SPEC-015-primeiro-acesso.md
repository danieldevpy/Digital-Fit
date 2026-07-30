# SPEC-015 — Primeiro Acesso Guiado (Exemplo antes do treino)
Status: implemented(initial) | Camada: client (web/) | Depende de: SPEC-014 | Referência: ideia "PRIMEIRO ACESSO" (2026-07-30)

## Entidade e responsabilidade

O primeiro contato do cliente com o produto tem de ser **suave e fácil de prosseguir**: ele nunca deve cair na câmera sem saber o que vai acontecer. Esta spec define o funil de primeiro acesso e a tela de Guia (exemplo passo a passo) que se encaixa entre a escolha do exercício e a pré-configuração.

```
INDEX → ESCOLHA DO EXERCÍCIO → EXEMPLO GUIADO → COMEÇO DO EXERCÍCIO
```

Cada seta é um toque único, sem formulário, sem login, sem decisão difícil. Login/conta só aparecem quando agregam (histórico, progresso — SPEC-011/017), nunca como barreira do primeiro treino.

## Fase Inicial

### Escopo / Comportamento

- **Gatilho**: primeiro toque num card de exercício que o usuário nunca treinou (`localStorage` `df.guide.seen.<exercise_key>`). Nas vezes seguintes o card leva direto à Pré-configuração; o Guia continua acessível por um link "ver exemplo" no card EXERCÍCIO da pré-config.
- **Tela de Guia** (`#/guia/:exercise`): mesma pele da SPEC-014 —
  1. Header: nome do exercício + categoria/grupo (catálogo).
  2. Imagem de demonstração grande (Kairogen; GIF/vídeo curto é Evolução).
  3. Passos numerados (2–4 por exercício, campo `guide_steps` no catálogo): tile numerado roxo + frase curta e imperativa ("Fique de frente para a câmera, corpo inteiro visível", "Braços descem e sobem junto com o salto"…).
  4. Dica de cena (luz, distância ~2m, celular apoiado) — texto fixo, mesma para todos os exercícios.
  5. CTA "Entendi, vamos lá →" (pill glow) → Pré-configuração. Link discreto "Pular" com o mesmo destino (pular também marca como visto).
- **Todo exercício tem demo visual**: campo `demo_img` obrigatório no catálogo; sem asset, cai na silhueta SVG ciano (nunca card vazio).
- Transições entre as telas do funil: fade/slide de ~200ms, sem bloqueio (animação é decoração, o toque seguinte não espera).

### Fora de escopo (vai para Evolução)

- GIF/vídeo de demonstração em loop (T-066) — inclusive no card da Escolha.
- Guia interativo "faça junto" (esqueleto do usuário sobreposto ao exemplo, validação de posição — SPEC-004 evolução).
- Onboarding de conta/medidas no primeiro acesso (SPEC-017 — só para quem já tem conta).
- Tour do app (coach marks) nas outras telas.

### Critérios de aceite

1. Usuário novo: Index → toque em "Começar Treino" → Escolha → toque no card → Guia → CTA → Pré-config → "Iniciar Exercício" → treinando. Nenhum passo pede login ou dado pessoal.
2. Usuário que já viu o guia daquele exercício vai da Escolha direto à Pré-config.
3. "Pular" e "Entendi" marcam o guia como visto; limpar o storage volta o comportamento de novato.
4. Exercício sem `guide_steps` não quebra: mostra demo + dica de cena + CTA.

## Eventos (consome / produz)

Nenhum evento de servidor. Telemetria de funil (quantos pulam o guia) é Evolução, junto com a SPEC-011.

## Notas técnicas

- Marcar "visto" por exercício (não global): um usuário que sabe polichinelo ainda não viu agachamento.
- Imagens dos passos em `web/public/img/guia/<exercise>-<n>.png` (Kairogen). Prompt de geração deve manter a mesma identidade do hero (pessoa em roupa escura, fundo de academia escuro, traços neon ciano/roxo).
- O Guia é tela estática: não montar câmera nem sessão ali.
