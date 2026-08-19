// A passada de SSR do build (T-159, SPEC-026 §Escopo · ADR-012).
//
// Compila `src/entries/prerender.tsx` para `dist-ssr/`, que o `scripts/prerender.mjs` executa em
// Node para gerar o HTML que vai dentro de cada entry do `dist/`. Nada daqui é servido: é
// ferramenta de build, e some do artefato final.
//
// **Config próprio, e não um ramo dentro do `vite.config.ts`.** O callback de config recebe um
// `isSsrBuild`, mas ele não chega populado quando a entrada de SSR vem pela linha de comando —
// o build falhava com "input should not be an html file when building for SSR", porque o config
// devolvia a lista de HTML do navegador. Um arquivo separado torna a intenção explícita e não
// depende de detecção de flag, que é o tipo de coisa que volta a quebrar numa atualização.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    ssr: 'src/entries/prerender.tsx',
    outDir: 'dist-ssr',
    emptyOutDir: true,
  },
})
