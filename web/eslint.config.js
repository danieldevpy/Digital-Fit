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
  // `no-literal-string` GLOBAL (T-154, PLANO-I18N.md §4 — o portão que vale para sempre).
  //
  // Até aqui a regra entrava por diretório: cada task da Onda 2 ligava-a só para a pasta que
  // acabara de migrar (T-142 `shell`, T-147 `site`, T-148 `funnel`, T-149 `session`, T-150
  // `report`/`progress`, T-151 `account`/`errors`, T-153 o próprio runtime). Era o desenho certo
  // enquanto a migração corria — ligar tudo de uma vez teria produzido ~280 erros e travado as
  // seis raias atrás de telas que ainda não tinham dicionário. Com a Onda 2 fechada, os
  // overrides viraram exatamente o oposto do que o portão promete: uma lista de exceções que
  // cresce sozinha quando alguém cria um arquivo fora dela.
  //
  // Agora vale para `src/**`, e o que sobra de fora está nos `files` de exclusão abaixo, com
  // motivo escrito. `mode: 'jsx-only'` (não o padrão `jsx-text-only`) para também pegar string
  // solta em atributo — `aria-label`, `alt`, `title`, `placeholder` são os ~30 rótulos de
  // acessibilidade que a SPEC-025 §Entidade conta como texto de cliente.
  //
  // **O que esta regra NÃO pega, e está registrado**: string fora de JSX (Descoberta `[T-149]`
  // do BACKLOG). O `mode: 'jsx-only'` olha JSXText e JSXAttribute e nada mais, então uma frase
  // nascida num módulo `.ts` passa batido. Quem cobre esse flanco é
  // `src/i18n/textoNovo.test.ts`, que varre o código-fonte atrás de literal acentuada.
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: [
      // O dicionário É o texto — cobrar `t()` dentro dele seria recursão.
      'src/i18n/dict/**',
      // Testes falam de texto o tempo todo (fixtures, asserts nas duas línguas). O que protege
      // o teste de mentir é ele rodar, não o lint.
      'src/**/*.test.{ts,tsx}',
      // Ferramenta de operação, não superfície de quem treina — a mesma exclusão que a
      // SPEC-025 §Escopo dá ao painel admin do Django. Só aparece com build de dev ou conta
      // `is_admin` (`dev/gate.ts`).
      'src/dev/**',
    ],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-only',
          'jsx-attributes': {
            // A lista PADRÃO precisa ser repetida — `context.options[0]` substitui o default
            // inteiro, não faz merge. Depois dela, três famílias de nome, todas com o mesmo
            // critério: é vocabulário de contrato (do navegador, do leitor de tela, do SVG) ou
            // é frase que alguém lê?
            exclude: [
              // padrão do plugin
              'className',
              'styleName',
              'style',
              'type',
              'key',
              'id',
              'width',
              'height',
              // `className` com outro nome, e slugs de tela/variante (dado, não frase)
              'figuraClassName',
              'active',
              'variant',
              // vocabulário da ARIA: contrato do leitor de tela. `aria-label` fica de FORA de
              // propósito — é justamente o texto que a spec conta.
              'role',
              'aria-hidden',
              'aria-live',
              'aria-modal',
              'aria-labelledby',
              'aria-current',
              'autoComplete',
              // geometria e pintura de SVG
              'viewBox',
              'preserveAspectRatio',
              'points',
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
)
