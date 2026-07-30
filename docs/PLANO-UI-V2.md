# Plano de Evolução — UI v2 (2026-07-30)

> Plano-mestre da evolução pós-MVP. As specs são a autoridade; este documento é o mapa.

## Objetivo

Trocar a pele do MVP pela interface do protótipo aprovado e abrir o funil de primeiro acesso, mantendo intacta a arquitetura de sessão (keypoints, eventos, admission). Depois, monetização (Free × Assinatura) e retenção (perfil físico + progresso).

## Fontes da verdade visual

| Fonte | O que manda |
|---|---|
| `referencias/app-completo-mobile.png` | as 5 telas mobile (Index, Escolha, Pré-config, Treino, Sobre) |
| `referencias/index.png` | Index desktop (única tela responsiva pc/mobile) |
| Protótipo Claude Design "Digital Fit - Evolução UI v2" (`a437c4d7-…`) | comportamento das telas Pré-config e Treino (steppers, anéis, player) |
| `referencias/ui-generative-ia-v3.png` | cores/materiais/animações das telas 3–4 |

O design system "Nocturne" do Claude Design não foi adotado (estética diverge do protótipo); dele fica só o método de tokens centralizados.

## Specs novas

- **SPEC-014** — Interface v2 (vinculante; tokens, anatomia das 6 telas, navegação, desvios honestos).
- **SPEC-015** — Primeiro Acesso Guiado (Index → Escolha → Guia → Treino; demo por exercício).
- **SPEC-016** — Planos Free × Assinatura (quota diária no servidor; kcal ao vivo vs. acúmulo; Modo Efeito). *futura*
- **SPEC-017** — Perfil Físico & Progresso Realista (peso/altura, kcal MET, IMC, série de peso). *futura*

## Ondas de execução

**Onda 1 — agora (Fase 4 do BACKLOG, T-056…T-062):** tokens + shell + as 6 telas, imagens geradas no Kairogen (hero do Index, demos e passos do guia). Critério de saída: acceptance da SPEC-014 + gates verdes.

**Onda 2 — futuras (T-063…T-066):** Free/Assinatura, perfil físico, GIFs de demonstração. Dependem de decisões de produto (preço, checkout) e da SPEC-009 evolução (duração configurável).

## Decisões registradas

1. **Só o Index é responsivo**; todo o app de exercício vive numa coluna mobile ≤ 430px, mesmo no desktop.
2. **Honestidade > fidelidade ao mock**: FC e kcal mostram `--` até existir dado real; player mostra stop (não pause) enquanto a sessão de 30s for atômica no servidor. Tabela completa de desvios na SPEC-014.
3. **Roteamento por hash**, sem dependência nova — back e refresh funcionam.
4. **Imagens**: Kairogen com identidade única (pessoa em roupa escura, academia escura, traços neon ciano/roxo). Se os créditos acabarem, silhueta SVG ciano como placeholder e as imagens entram depois.
5. Free continua bom em sessão única; toda trava de plano é no servidor.
