import js from '@eslint/js'
import globals from 'globals'
import i18next from 'eslint-plugin-i18next'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'public/wasm', 'public/models'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
  {
    files: ['scripts/**/*.mjs'],
    extends: [js.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.node,
    },
  },
  // `no-literal-string` por diretório (T-142, PLANO-I18N.md §4): ligar a regra no repositório
  // inteiro de uma vez travaria a Onda 2 inteira atrás de telas que ainda não migraram. Em vez
  // disso, cada task de migração liga a regra só para a pasta que ela acabou de migrar — esta
  // task migrou `shell` (TabBar, nav — SPEC-014 §Mapa de navegação) e o efeito de `<html lang>`
  // em `AppShell.tsx`. A T-154 remove estes overrides e liga a regra global depois que a Onda 2
  // terminar. `mode: 'jsx-only'` (não o padrão `jsx-text-only`) para também pegar string solta
  // em atributo (`aria-label`, `alt`, `title`, `placeholder`), não só texto de nó JSX.
  {
    files: ['src/shell/**/*.{ts,tsx}', 'src/app/AppShell.tsx'],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': ['error', { mode: 'jsx-only' }],
    },
  },
  // T-147 (namespace `site`): `site/IndexScreen`, `AboutScreen`, `SiteBar`, `SiteApp`, `nav` —
  // migrados para `t()`. Mesmo `mode: 'jsx-only'` do override acima, mesma doutrina. `active`
  // acrescentado ao `jsx-attributes.exclude` (a lista PADRÃO — `context.options[0]` substitui o
  // default inteiro, não faz merge, então a exclusão de `className`/`style`/... precisa ser
  // repetida aqui): é o slug da tela em `SiteBar` (`'index' | 'sobre'`), o mesmo
  // vocabulário-de-contrato que já vale para `Category`/`Code` no resto do projeto — dado, não
  // frase.
  {
    files: ['src/site/**/*.{ts,tsx}'],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-only',
          'jsx-attributes': {
            exclude: [
              'className',
              'styleName',
              'style',
              'type',
              'key',
              'id',
              'width',
              'height',
              'active',
            ],
          },
        },
      ],
    },
  },
  // T-151, namespaces `account` + `errors` (SPEC-025 Onda 2 — a última raia): a conta
  // (`auth/AccountSheet`, `accountSummary`, `auth/api`) e o engajamento (`engagement/*`).
  // `engagement/calendar.ts` entra sem ter mais texto: as iniciais da semana saíram dele para o
  // `Intl` nesta task, e a regra passa a valer para que não voltem.
  //
  // É a raia com mais plural do app (dias de sequência, treinos guardados, sessões da meta,
  // dias treinados no mês) — todos por `.one`/`.other` e `Intl.PluralRules`, plano §2.7.
  {
    files: [
      'src/auth/AccountSheet.tsx',
      'src/auth/accountSummary.ts',
      'src/auth/api.ts',
      'src/engagement/AchievementGallery.tsx',
      'src/engagement/AchievementToast.tsx',
      'src/engagement/EngagementSection.tsx',
      'src/engagement/EngagementSheet.tsx',
      'src/engagement/FireChip.tsx',
      'src/engagement/XpLine.tsx',
      'src/engagement/format.ts',
      'src/engagement/calendar.ts',
    ],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-only',
          'jsx-attributes': {
            exclude: [
              'className',
              'styleName',
              'style',
              'type',
              'key',
              'id',
              'width',
              'height',
              'role',
              'aria-hidden',
              'aria-live',
              'autoComplete',
              'viewBox',
              'cx',
              'cy',
              'r',
            ],
          },
        },
      ],
    },
  },
  // T-150, namespaces `report` + `progress` (SPEC-025 Onda 2): a leitura do que já foi treinado
  // — o relatório do fim (`report/*`) e as duas telas de histórico (`ProgressScreen`,
  // `AnalyticsScreen`). `history/aggregates.ts` e `session/kcal.ts` entram junto: o primeiro não
  // tem texto nenhum (só `Rumo`, que é contrato) e o segundo perdeu o `ESTIMATED_LABEL` para o
  // dicionário nesta task.
  //
  // Além do `t()`, esta raia trocou os `toLocaleDateString('pt-BR')` e os
  // `.toFixed(1).replace('.', ',')` pelos formatadores de `i18n/format.ts` (plano §2.6) — o que
  // nenhuma regra de lint pega, porque data e número não parecem texto.
  {
    files: [
      'src/report/ReportSheet.tsx',
      'src/report/reportSummary.ts',
      'src/report/sessionReport.ts',
      'src/screens/ProgressScreen.tsx',
      'src/screens/AnalyticsScreen.tsx',
      'src/history/aggregates.ts',
      'src/session/kcal.ts',
    ],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-only',
          'jsx-attributes': {
            exclude: [
              'className',
              'styleName',
              'style',
              'type',
              'key',
              'id',
              'width',
              'height',
              'role',
              'aria-hidden',
              'viewBox',
              'preserveAspectRatio',
              'points',
            ],
          },
        },
      ],
    },
  },
  // T-149, namespace `session` (SPEC-025 Onda 2): o treino em si — a capa e os avisos da
  // câmera, o aquecimento do pipeline, a medição do corpo, os conselhos de cena, as recusas da
  // admissão, o CTA de dois degraus, o HUD e as duas telas do `SessionScreen`.
  // `session/preferences.ts` entra fora da lista original da task porque o `countdownLabel` dele
  // é o texto que o `aria-label` do `CountdownSetting` interpola (ver o docstring lá).
  //
  // O chip de diagnóstico do `CameraView` e o conselho de "suba a stack" continuam em português
  // cru, com `eslint-disable` e justificativa no ponto: são ferramenta de operação, a mesma
  // exclusão que a SPEC-025 §Escopo dá ao painel admin. Note que `mode: 'jsx-only'` não alcança
  // string fora de JSX — o que cobre os módulos `.ts` desta raia (`admission`, `sceneQuality`,
  // `assetWarmup`, …) é o teste de paridade e a revisão, não esta regra.
  //
  // `aria-modal`/`aria-labelledby` não aparecem aqui (nenhum arquivo desta lista os usa);
  // `role`, `aria-hidden`, `aria-live`, `stroke*`, `fill`, `transform` e afins são vocabulário
  // de SVG/ARIA — contrato de desenho e de leitor de tela, nunca frase que alguém lê.
  {
    files: [
      'src/screens/SessionScreen.tsx',
      'src/capture/CameraView.tsx',
      'src/capture/useCamera.ts',
      'src/capture/useEdgePipeline.ts',
      'src/hud/CoachTip.tsx',
      'src/hud/StatsBar.tsx',
      'src/hud/GetReady.tsx',
      'src/hud/TimerRing.tsx',
      'src/hud/CountdownSetting.tsx',
      'src/hud/ZoomControl.tsx',
      'src/session/startGate.ts',
      'src/session/pipelineGate.ts',
      'src/session/admission.ts',
      'src/session/useSession.ts',
      'src/session/preferences.ts',
      'src/scene/sceneQuality.ts',
      'src/pose/assetWarmup.ts',
      'src/probe/runProbe.ts',
    ],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-only',
          'jsx-attributes': {
            exclude: [
              'className',
              'styleName',
              'style',
              'type',
              'key',
              'id',
              'width',
              'height',
              'role',
              'aria-hidden',
              'aria-live',
              'variant',
              'viewBox',
              'fill',
              'stroke',
              'strokeWidth',
              'strokeLinecap',
              'strokeDasharray',
              'transform',
              'x1',
              'y1',
              'x2',
              'y2',
              'offset',
              'stopColor',
              'cx',
              'cy',
              'r',
              'd',
            ],
          },
        },
      ],
    },
  },
  // T-148, namespace `funnel` (SPEC-025 Onda 2): o caminho da SPEC-015 do lado do app —
  // Escolha (`screens/ChooseScreen`, `ExerciseRails`), Guia (`screens/GuideScreen`), a escolha
  // de variação de câmera (`ui/ViewPicker`, `hud/ViewConfirm`), os dois seletores herdados do
  // funil antigo (`hud/ExercisePicker`, `ui/ExerciseDemo`) e o card da vitrine do site
  // (`screens/ExerciseCards`, que mora em `screens/` mas só o site desenha). `screens/funnel.ts`,
  // `session/guideGate.ts` e `session/viewGate.ts` entram sem ter nada a pegar hoje — é a mesma
  // doutrina de "pasta migrada" do `ui/exerciseFigures.ts` na T-152: a regra passa a valer ANTES
  // de a primeira frase aparecer ali, que é o único momento em que ela custa zero.
  //
  // Arquivos explícitos, e não `src/screens/**`: `ProgressScreen`/`AnalyticsScreen` são da T-150
  // e `SessionScreen` é da T-149 — as raias da Onda 2 dividem estas pastas.
  //
  // Cinco nomes acrescentados ao `jsx-attributes.exclude` (a lista PADRÃO precisa ser repetida —
  // `context.options[0]` substitui o default inteiro, não faz merge). `role="radio"`,
  // `role="dialog"`, `aria-modal="true"`, `aria-labelledby="vgate-titulo"` e `aria-hidden="true"`
  // são vocabulário da ARIA: contrato do navegador e do leitor de tela, nunca frase que alguém
  // lê. `figuraClassName` é `className` com outro nome (o ramo-figura do `ExerciseDemo`), e
  // `className` já está no default pelo mesmo motivo. `aria-label` e `alt` ficam de FORA da
  // exclusão de propósito — são exatamente o texto que a SPEC-025 §Entidade conta entre os ~30
  // rótulos de acessibilidade, e é por eles que esta regra existe em `mode: 'jsx-only'`.
  {
    files: [
      'src/screens/ChooseScreen.tsx',
      'src/screens/GuideScreen.tsx',
      'src/screens/ExerciseCards.tsx',
      'src/screens/ExerciseRails.tsx',
      'src/screens/funnel.ts',
      'src/ui/ViewPicker.tsx',
      'src/ui/ExerciseDemo.tsx',
      'src/hud/ViewConfirm.tsx',
      'src/hud/ExercisePicker.tsx',
      'src/session/guideGate.ts',
      'src/session/viewGate.ts',
    ],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-only',
          'jsx-attributes': {
            exclude: [
              'className',
              'styleName',
              'style',
              'type',
              'key',
              'id',
              'width',
              'height',
              'figuraClassName',
              'role',
              'aria-modal',
              'aria-labelledby',
              'aria-hidden',
            ],
          },
        },
      ],
    },
  },
  // T-152, namespace `catalog` (SPEC-025 Onda 2): o catálogo embutido de exercícios
  // (`session/catalog.ts`), as variações de câmera (`session/exerciseViews.ts`), o embutido de
  // `CODE_MESSAGES` do card do treinador (`session/coachCard.ts`, herança da T-144) e o registro
  // de figuras (`ui/exerciseFigures.ts`, sem texto — entra pela mesma doutrina de "pasta
  // migrada", não por ter algo a pegar). Arquivos explícitos, e não uma pasta inteira: o resto
  // de `session/` (`admission.ts`, `useSession.ts`, ...) pertence a outras raias da Onda 2
  // (T-149) e ainda não migrou.
  {
    files: [
      'src/session/catalog.ts',
      'src/session/exerciseViews.ts',
      'src/session/coachCard.ts',
      'src/ui/exerciseFigures.ts',
    ],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': ['error', { mode: 'jsx-only' }],
    },
  },
)
