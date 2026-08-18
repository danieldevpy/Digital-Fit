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
)
