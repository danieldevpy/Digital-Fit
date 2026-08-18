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
