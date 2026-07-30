# SPEC-014 — Interface v2 (Evolução UI: réplica do protótipo)
Status: implemented(initial) | Camada: client (web/) | Depende de: SPEC-008, SPEC-009, SPEC-013 | Substitui: camada visual da SPEC-013 (os contratos de eventos e regras de dados da 013 continuam valendo)

Referências visuais (vinculantes, nesta ordem de autoridade):

1. `referencias/app-completo-mobile.png` — as 5 telas do app mobile (Landing/Index, Seleção, Pré-configuração, Executando, Sobre/Footer).
2. `referencias/index.png` — Index em versão desktop. **Só o Index é responsivo pc/mobile; todas as telas do app de exercício mantêm aspecto mobile (coluna central ≤ 430px) mesmo no desktop.**
3. Protótipo Claude Design "Digital Fit - Evolução UI v2" (projeto `a437c4d7-121a-4f31-ae33-581ae0c90f93`, arquivo `Digital Fit - Evolução UI v2.dc.html`) — comportamento funcional das telas Pré-configuração e Treino ao Vivo (steppers, troca de exercício, play/pause, anéis com contagem real).
4. `referencias/ui-generative-ia-v3.png` — cores, materiais e animações das telas 3 e 4.

O design system "Nocturne" gerado no Claude Design **não** é a fonte visual (Inter/#161826/botões outline divergem do protótipo). Dele aproveita-se apenas o método: tokens centralizados em `:root`, estados de foco/hover temáticos, e nada de valor hard-coded fora dos tokens.

## Entidade e responsabilidade

Define a nova casca visual completa do produto: landing (Index), fluxo de primeiro acesso (SPEC-015), seleção de exercício, pré-configuração, treino ao vivo, sobre, e a navegação entre elas. É vinculante para toda task de UI a partir da Fase 4. A lógica de sessão (captura, pose, eventos, admission) não muda — esta spec é uma troca de pele + novas telas de navegação.

## Design tokens v2 (vinculantes)

Extraídos do protótipo v2 e da referência v3. Substituem os tokens da SPEC-013 em `web/src/styles.css`.

```css
--bg: #05070d;                    /* fundo geral (quase preto azulado) */
--bg-glow: #0b101e;               /* topo do gradiente radial do fundo */
--surface: rgba(13, 18, 32, .8);  /* cards de configuração */
--surface-hud: rgba(8, 12, 22, .72); /* cards flutuantes sobre a câmera + blur(14px) */
--surface-border: rgba(255, 255, 255, .08);
--blue: #4d8cff;                  /* azul primário: reps, FC, ícones vitais */
--cyan: #4dd2ff;                  /* ciano: esqueleto-guia, scan, silhuetas */
--accent: #8b5cf6;                /* roxo primário: anéis, bordas ativas, glow */
--accent-2: #a78bfa;              /* roxo claro (gradientes) */
--accent-deep: #7c4dff;           /* roxo profundo (botão do player) */
--hot: #f5a83d;                   /* laranja: calorias */
--live: #34d399;                  /* verde: indicador "ao vivo" */
--text: #ffffff;
--text-dim: rgba(255, 255, 255, .55);
--text-faint: rgba(255, 255, 255, .45);
--radius: 16px;                   /* cards */
--radius-cam: 18px;               /* moldura da câmera na pré-configuração */
--skeleton: #eef2ff;              /* esqueleto ao vivo, glow roxo+ciano */
```

Tipografia: **Manrope** (UI, títulos, botões) + **Space Grotesk** (números de métrica, tabular). Labels de célula: 8–10px, caps, `letter-spacing .10–.12em`, `--text-dim`. Números grandes: Space Grotesk 700, `tabular-nums`.

Animações canônicas (nomes e timings do protótipo): `dfScan` (varredura ciano 3.4s), `dfGlow` (pulso de opacidade 2.2–2.6s), `dfPulse` (halo do botão do player 2.2s), `dfWave` (traço de ECG 2.4–3s), `dfSpin` (aro orbital 14s), `dfChev` (chevrons de transição 1.5s). Respeitar `prefers-reduced-motion` (remover animação, nunca a informação).

Materiais: glass = fundo `--surface-hud` + `backdrop-filter: blur(14px)` + borda `--surface-border`. Limite de blur simultâneo herdado da SPEC-013 sobe para **6 superfícies pequenas** na tela de treino (os cards HUD são pequenos; medir em aparelho real — se houver jank, degradar para fundo sólido `rgba(8,12,22,.9)` sem blur, começando pelos cards menores).

CTA primário ("Iniciar Exercício", "Começar Treino"): pill 999px, fundo `linear-gradient(90deg, rgba(77,140,255,.14), rgba(139,92,246,.18))`, borda 1.5px `rgba(139,92,246,.75)`, glow externo `0 0 24px rgba(139,92,246,.35)`, texto Manrope 700.

## Mapa de navegação

Desde a T-067 há **duas fronteiras**, não uma árvore só (ADR-010): o SITE é um bundle (`/`) e o APP é outro (`/app/`, ou `app.dominio.com`). Links que atravessam a fronteira são `<a href>` montados por `shell/origins.ts`, nunca `navigate()`.

```
╔═ SITE (bundle web/index.html) ═════════════════════════════════════════════╗
║  Index (#/)   ── "Começar Treino" ──▶  APP #/exercicios                    ║
║    │             ── "Entrar" ──────▶  APP #/entrar                         ║
║    │             ── card do exercício ▶ APP #/ex/:slug                     ║
║    └─ Sobre (#/sobre) — footer do Index e barra do site                    ║
║  Barra do site: Início · Sobre · Abrir o app                               ║
╚════════════════════════════════════════════════════════════════════════════╝
                                     │
╔═ APP (bundle web/app/index.html) ══▼═══════════════════════════════════════╗
║  #/ex/:slug (ponte, sem tela)                                              ║
║      [1º acesso àquele exercício?]                                         ║
║        sim ▼                  não ▼                                        ║
║  Guia (#/guia/:ex) ─────▶  Pré-config (#/preparar)  ◀── abrir o app        ║
║                                    │ "Iniciar Exercício"                   ║
║                                    ▼                                       ║
║                            Treino ao Vivo (#/treino)                       ║
║                                    │ fim da sessão                         ║
║                                    ▼                                       ║
║                            Relatório (sheet existente)                     ║
║  Escolha (#/exercicios) · Progresso (#/progresso) · Analytics (#/analytics) ║
║  #/entrar (ponte, sem tela) → abre a AccountSheet                          ║
║  Tab bar: Início · Progresso · Analytics · Perfil                          ║
║           (Início = Pré-config; Perfil abre AccountSheet;                  ║
║            no Treino a barra ganha o play/stop no meio)                     ║
╚════════════════════════════════════════════════════════════════════════════╝
```

As duas **pontes** (`#/ex/:slug` e `#/entrar`) existem porque `localStorage` é por origem: `guide_seen` e o token de conta moram no app, então o site aponta a intenção e o app decide. Elas trocam a rota com `replace` — no histórico não fica um passo que só sabe redirecionar.

Roteamento por `location.hash` (sem dependência nova): back do navegador/Android funciona, refresh cai na tela certa. Telas do app renderizam dentro da coluna `.app__phone` (≤ 430px); só o Index escapa dela em ≥ 900px. Abrir o app sem rota cai em `#/preparar` — abrir o app é abrir para treinar.

## Anatomia das telas

### 1. Index — landing (responsivo)

Mobile (tela 1 da referência): logo + wordmark "DIGITAL FIT / SEU TREINO. SUA EVOLUÇÃO."; badge pill "✦ INTELIGÊNCIA QUE TE MOVE"; headline "Treine melhor. / **Evolua** sempre." (Evolua em roxo `--accent-2`); parágrafo sobre visão computacional; imagem hero (pessoa com esqueleto neon — Kairogen); 3 linhas de feature com ícone em tile 40px (`Análise em Tempo Real`, `Conte Repetições`, `Corrija sua Execução`); CTA "Começar Treino →"; tab bar.

Desktop ≥ 900px (`referencias/index.png`): nav topo (logo à esquerda, botão outline "Entrar" à direita); hero em 2 colunas — esquerda com badge/headline/copy/features/CTA + link "▶ Ver como funciona"; direita um device-card com a imagem hero e mini-HUD por cima (barra SÉRIE/REPETIÇÕES/ÂNGULO/KCAL no topo, cards REPETIÇÕES 12/15, FC 124, ÂNGULO 176°, CALORIAS 87, pill "POLICHINELO · CARDIO • CORPO INTEIRO", anel TEMPO RESTANTE 00:20) — o mini-HUD é decorativo (markup estático), não uma sessão real. Abaixo: seção "ESCOLHA SEU EXERCÍCIO / Treinos rápidos, **resultados reais**" com os cards de exercício (mesmo componente da tela Escolha); footer 4 colunas (marca+sociais, Recursos, Sobre, Suporte) + copyright.

### 2. Escolha de exercício

Título central "Escolha seu exercício"; subtítulo "Treinos rápidos, / **resultados reais**" (segunda linha roxa). Cards empilhados (mobile) / 3 colunas (desktop no Index): categoria em caps pequeno (`CARDIO`/`FORÇA`/`ALONGAMENTO`), nome 700, mini-waveform decorativo, badge "30s" no canto, ilustração/demo do exercício (imagem Kairogen; GIF é evolução — SPEC-015), rodapé com dot colorido (verde=Ativo, azul=Inferiores, roxo=Mobilidade) + grupo muscular, chevron circular à direita. Card do exercício selecionado ganha borda `--accent` com glow. Fonte dos dados: `session/catalog.ts` (ganha campos `demo_img`, `dot_color`, `guide_steps`). Toque no card → SPEC-015 decide Guia ou Pré-config.

### 3. Pré-configuração (protótipo v2, tela 1 — funcional)

Header: "Pré-configuração" + "Vamos preparar seu treino". Corpo em 3 colunas sobre a câmera:

- Coluna esquerda (92px): card EXERCÍCIO (ícone ciano + nome; toque troca/volta à Escolha), card SÉRIE (valor + steppers − / + , 1–9), card REPETIÇÕES (5–30), card DURAÇÃO (mm:ss, passos de 10s, 10–300s). Steppers funcionais; valores persistem em `session/preferences`.
- Centro: câmera ao vivo (CameraView) em moldura `--radius-cam` com borda azulada e glow; overlay de grade 28px, varredura `dfScan`, silhueta-guia ciano tracejada (`dfGlow`), pill inferior "Você já está visível · alinhe-se à guia".
- Coluna direita (96px): botão Espelhar (liga/desliga o espelhamento do palco), card FREQUÊNCIA CARDÍACA (`--` BPM + onda `dfWave` — sem sensor, placeholder honesto), card ÂNGULO (ao vivo, T-044), card CALORIAS ESTIMADAS (`--` kcal, anel pontilhado).

CTA "Iniciar Exercício ▶" (pill glow) → inicia câmera+sessão (GetReady 3-2-1 existente) e navega para Treino ao Vivo. Tab bar embaixo.

DURAÇÃO na Fase Inicial: exibida e persistida, mas a autoridade continua no servidor (30s, SPEC-009); valores ≠ 30s ficam desabilitados com tooltip "em breve" até a SPEC-009 evolução aceitar `duration` na config. Nunca fingir que o servidor obedeceu.

### 4. Treino ao Vivo (protótipo v2, tela 2 — imersiva)

Câmera em tela cheia com esqueleto branco-glow (canvas existente); gradientes de legibilidade no topo (140px) e na base (270px). Elementos flutuantes:

- Topo centro: dot verde pulsante + "Treino ao Vivo"; abaixo "Polichinelo • Série 1/1".
- Aro orbital decorativo (`dfSpin`) atrás do esqueleto.
- Card REPETIÇÕES (topo-esq): anel azul com progresso `reps/meta` real (`rep.detected`); sem meta, anel cheio e contador simples.
- Card FREQUÊNCIA CARDÍACA (topo-dir): `--` BPM + onda (placeholder honesto até existir sensor).
- Card ÂNGULO e card CALORIAS: logo abaixo dos dois de cima, em posição FIXA em px (T-071 — a referência os punha a meia altura, e `top: 46%` colidia com a faixa dos avisos em telas altas; misturar % com a pilha do rodapé em px é o que embaralhou a tela no teste real). Ângulo ao vivo (T-044); calorias `--` na Fase Inicial, ao vivo na SPEC-016.
- Card SÉRIE (baixo-esq): `1/1` na Fase Inicial.
- Pill central: nome do exercício em caps 800 + "CARDIO • CORPO INTEIRO".
- Anel TEMPO RESTANTE (baixo-dir): countdown real da sessão (TimerRing, roxo, autoridade no servidor).
- Rodapé (revisto na T-068): a **tab bar do app com o botão da sessão no meio** — 66px roxo radial com `dfPulse`, ícone de stop enquanto a sessão roda (pause real não existe no servidor; fingir pause é mentir) e de play antes dela. O player flutuante de 4 botões da referência saiu: ⏮/⏭/música eram placeholders desabilitados, e era o posicionamento absoluto deles que produzia as colisões do rodapé. Trocar de exercício continua sendo papel da pré-configuração. Música é Evolução (SPEC-009).

Warnings de cena e dica do treinador (SPEC-008): entram como toast/pill glass acima do player, mesma regra de prioridade da SPEC-013 §4.

**Instrução modal manda na tela (T-071, vinculante).** Enquanto o servidor mede o corpo (SPEC-004, "Fique em pé, parado"), o cromo flutuante sai: cards, pill do exercício e aro orbital somem, e avisos de status não-acionáveis (como o de modo cloud) também. Todos mostram `0`, `--` ou o tempo cheio naquele instante — nada conta ainda, e juntos tornam a instrução ilegível. Ficam o cabeçalho, o toast do coach (que é o que explica por que a medição não fecha) e a barra com o stop.

### 5. Sobre / Footer (tela 5)

Logo neon central; "Sobre o Digital Fit" + subtítulo; 3 cards de valor (Privacidade em primeiro lugar, Para todos os níveis, Evolução constante) com ícone em tile roxo; lista "Recursos" (Como funciona, Exercícios, Benefícios, Planos — âncoras/`em breve`); ícones sociais; copyright. No desktop este conteúdo é o footer do Index; no mobile é tela própria (#/sobre).

## Fase Inicial (o que entra agora — tasks T-056…T-062)

1. Tokens v2 + fontes + animações canônicas em `styles.css` (T-056).
2. Roteador por hash + shell `.phone`/desktop + tab bar nova (T-056).
3. Index responsivo com hero Kairogen (T-057).
4. Escolha de exercício com cards da referência (T-058).
5. Guia passo a passo — SPEC-015 (T-059).
6. Pré-configuração funcional ligada à câmera/preferences (T-060).
7. Treino ao Vivo com HUD flutuante ligado aos eventos reais (T-061).
8. Sobre (T-062).

### Fora de escopo (Evolução)

FC real, kcal ao vivo (SPEC-016), pause real, música, duração configurável no servidor, GIFs de demonstração (T-066), telas Progresso/Exercícios completas (T-046), efeitos de esqueleto por fase.

### Critérios de aceite

1. Colocada lado a lado com `app-completo-mobile.png`, cada tela é reconhecível de imediato como a mesma tela (estrutura, cores, materiais, tipografia). Divergências intencionais listadas em §Desvios.
2. `index.png` reproduzido em ≥ 900px; abaixo disso o Index vira a tela 1 mobile. As demais telas ficam ≤ 430px centralizadas em qualquer viewport.
3. Steppers da pré-configuração funcionam e persistem; "Iniciar Exercício" chega ao Treino ao Vivo com câmera aberta e GetReady rodando.
4. No Treino ao Vivo, reps/ângulo/tempo vêm dos dados reais da sessão; nenhum número simulado.
5. Navegação por hash: back do navegador volta uma tela; refresh mantém a tela.
6. Gates verdes: lint, typecheck, testes (os testes de `hud/` e `session/` existentes continuam passando ou são atualizados junto).

## Revisão 2026-07-30 — pós-teste em aparelho real

Ajustes decididos pelo Daniel depois do primeiro treino de verdade na interface nova:

1. **Cards de frequência cardíaca removidos das duas telas** (pré-config e treino): sem sensor, o `--` era só ruído. Voltam quando existir dado real.
2. **Treino legível a ~2 metros**: anel de repetições maior (76px, número 1.5rem) no topo-esquerdo e o anel de TEMPO RESTANTE promovido ao topo-direito (onde a referência punha a FC) — os dois números que importam ficam na linha dos olhos.
3. **Card SÉRIE flutuante removido** do rodapé do treino: a informação já vive no subtítulo do topo ("Polichinelo • Série 1/1") e o card colidia com o pill do exercício.
4. **Rodapé sem colisões + safe area**: pill, toast e player espaçados e com `env(safe-area-inset-bottom)` — o botão do player ficava sob a barra do navegador do celular.
5. **Demo dos cards de exercício aparece inteira** (`object-fit: contain` sobre `--bg`), sem corte.
6. **Último relatório persiste no aparelho** (`digitalfit.last_report`): F5 depois do treino reabre a folha se estava aberta; fechar mantém os dados guardados sem reabrir. A autoridade continua no servidor (SPEC-010) — isto é carbono local.

## Revisão 2026-07-30 (2) — fronteira SITE|APP e rodapé único (T-067/T-068)

Segundo teste em aparelho real: o rodapé do treino continuava com "algo por cima do botão". A primeira revisão tratou só metade da causa.

1. **Duas causas, não uma.** (a) *Posição*: os avisos da CameraView (`.stage__banner`, `bottom: 46px`) e o chip de diagnóstico (`bottom: 12px`) vivem no palco da câmera, que no treino é a tela inteira — o "Conectando ao servidor…" pousava sobre o botão de play, e o CSS culpado não estava na tela de treino. (b) *Ordem de pintura*: `.live__fade-bottom`, o gradiente quase opaco de legibilidade, tinha `z-index: 2` dentro de `.live__chrome` e pintava POR CIMA do player e da barra — o botão aparecia apagado, "misturado com outro componente". A segunda causa é a que sobreviveu ao primeiro conserto.
2. **Rodapé virou uma pilha medida no browser**, com todos os elementos presentes ao mesmo tempo e no pior caso de texto: barra+FAB (0) · pill do exercício (100px) · toast (176px) · avisos (260px) · chip de dev (348px). Folgas de 12 a 17px.
3. **Player flutuante → FAB na tab bar.** Um rodapé só, empilhado pelo fluxo. ⏮/⏭/música saíram (placeholders desabilitados).
4. **Tab bar do app: Início · Progresso · Analytics · Perfil.** "Início" é a **pré-configuração** — a landing saiu do app. "Exercícios" deixou a barra: a porta é o card EXERCÍCIO da pré-config, que já existia e é melhor.
5. **Progresso e Analytics ganharam tela** (`#/progresso`, `#/analytics`) em vez do toast "em breve". Progresso mostra o último treino persistido; Analytics reabre a análise da sessão e declara o que falta (comparação entre sessões, SPEC-016/017). Nenhum número inventado.
6. **SITE e APP viraram bundles separados** (ADR-010): landing e Sobre em `/`, funil de treino em `/app/`, prontos para `site.dominio.com` | `app.dominio.com`. Conta e preferências ficam no app, porque `localStorage` é por origem — ver §Mapa de navegação (pontes `#/ex/:slug` e `#/entrar`) e `docs/DEPLOY.md`.

## Desvios da referência (honestidade > fidelidade)

| Referência mostra | Produto faz | Por quê |
|---|---|---|
| FC 124 BPM | `--` BPM | não há sensor; número inventado quebra confiança |
| Calorias 87 kcal | `--` kcal | MET exige peso (SPEC-017) e acúmulo (SPEC-016) |
| Pause no player | Stop (encerrar) | sessão de 30s é atômica no servidor (SPEC-009) |
| Botão música e ⏮/⏭ | removidos do rodapé | eram placeholders desabilitados, e o posicionamento absoluto deles colidia com pill e barra do navegador em aparelho real (T-068) |
| Player flutuante | FAB no meio da tab bar | um rodapé só; empilhamento pelo fluxo não colide por construção |
| Status bar iOS (10:32, 5G) | nada | é browser, não app nativo |
| Tab bar: Início · Exercícios · Progresso · Perfil | Início · Progresso · Analytics · Perfil | decisão do Daniel no teste de 2026-07-30: "Início" é a pré-configuração (a landing virou site, T-067) e a escolha de exercício já tem porta melhor no card EXERCÍCIO. Progresso e Analytics são abas distintas — evolução ao longo do tempo × leitura fina do treino |

## Eventos (consome / produz)

Os mesmos da SPEC-013: `rep.detected`, `feedback.issued`, `scene.warning`, `exercise.phase`, `session.started/completed`. Nenhum evento novo na Fase Inicial.

## Notas técnicas

- Fontes via Google Fonts no `index.html` com `preconnect`; `font-display: swap`.
- O palco da câmera já é espelhado (`scaleX(-1)`); o botão Espelhar da pré-config alterna essa transformação — cuidado com os overlays que já se desespelham (`.stage__cover`, `.getready`).
- Anéis de progresso: SVG `stroke-dasharray` como no protótipo (C = 2πr), transição de .6s.
- Imagens Kairogen em `web/public/img/` (hero, demos, passos do guia); `loading="lazy"` fora da primeira dobra; se os créditos acabarem, placeholder com a silhueta SVG ciano do protótipo.
- O mini-HUD do Index desktop é markup estático — não montar CameraView/useSession fora do fluxo de treino.
