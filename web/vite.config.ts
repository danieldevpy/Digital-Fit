import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

/**
 * Os HTML do build, por rota e por idioma. Exportado para o `site/routes.test.ts` confrontar
 * esta lista com a tabela de rotas — duas listas que precisam concordar e não se conhecem são
 * exatamente o que deixou o `hreflang` da T-147 inerte (SPEC-026 §Notas técnicas).
 */
export const ENTRADAS_DO_BUILD = {
  site: 'index.html',
  siteEn: 'en/index.html',
  siteSobre: 'sobre/index.html',
  siteAbout: 'en/about/index.html',
  siteNotFound: '404.html',
  app: 'app/index.html',
}

// A passada de SSR do build (que compila `entries/prerender.tsx` para o `scripts/prerender.mjs`
// consumir) mora em `vite.ssr.config.ts`, e não num ramo aqui dentro: o `isSsrBuild` do callback
// de config não chega populado quando a entrada vem pela linha de comando, e um config que se
// bifurca por detecção de flag é o tipo de coisa que quebra em silêncio numa atualização.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
  // Um HTML por ROTA por IDIOMA, mais o app e a 404 (T-158, SPEC-026 §Escopo). Até aqui eram
  // três entradas e o site roteava por `#/sobre` — fragmento não viaja no pedido HTTP, então
  // `/` e `/#/sobre` eram a mesma página para o buscador e o site tinha UMA URL indexável por
  // idioma. Cada tela é um documento próprio, e é isso que o pré-render preenche e o
  // `sitemap.xml` da T-163 vai listar.
  //
  // Um build só: é o que permite servir `site.dominio.com` (nas duas línguas) e
  // `app.dominio.com` do mesmo artefato sem duplicar pipeline, e o code splitting do Rollup
  // mantém MediaPipe e a máquina de sessão fora dos bundles do site.
  build: {
    rollupOptions: {
      // Caminhos relativos à `root` do Vite (a pasta `web/`) — sem `node:path` para o
      // tsconfig.node não precisar de @types/node só por causa disto.
      input: ENTRADAS_DO_BUILD,
    },
  },
  test: {
    environment: 'node',
    // `*.e2e.test.ts` exige stack de pé e fica fora da suíte padrão (roda por `npm run e2e`).
    include: ['src/**/*.test.ts'],
    exclude: ['**/node_modules/**', 'src/**/*.e2e.test.ts'],
  },
})
