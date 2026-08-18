import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
  // Um HTML por ROTA por IDIOMA, mais o app e a 404 (T-158, SPEC-026 §Escopo). Até aqui eram
  // três entradas e o site roteava por `#/sobre` — fragmento não viaja no pedido HTTP, então
  // `/` e `/#/sobre` eram a mesma página para o buscador e o site tinha UMA URL indexável por
  // idioma. Cada tela passa a ser um documento próprio, que é a condição para o pré-render da
  // T-159 preencher o `<body>` e para o `sitemap.xml` da T-163 ter o que listar.
  //
  // A lista espelha `src/site/routes.ts`, que é a fonte única — e o teste `routes.test.ts`
  // cobra que as duas concordem, porque duas listas que precisam concordar e não se conhecem
  // são exatamente o que produziu o `hreflang` inerte da T-147.
  //
  // Um build só, seis HTMLs: é o que permite servir `site.dominio.com` (nas duas línguas) e
  // `app.dominio.com` do mesmo artefato sem duplicar pipeline, e o code splitting do Rollup
  // mantém MediaPipe e a máquina de sessão fora dos bundles do site.
  build: {
    rollupOptions: {
      // Caminhos relativos à `root` do Vite (a pasta `web/`) — sem `node:path` para o
      // tsconfig.node não precisar de @types/node só por causa disto.
      input: {
        site: 'index.html',
        siteEn: 'en/index.html',
        siteSobre: 'sobre/index.html',
        siteAbout: 'en/about/index.html',
        siteNotFound: '404.html',
        app: 'app/index.html',
      },
    },
  },
  test: {
    environment: 'node',
    // `*.e2e.test.ts` exige stack de pé e fica fora da suíte padrão (roda por `npm run e2e`).
    include: ['src/**/*.test.ts'],
    exclude: ['**/node_modules/**', 'src/**/*.e2e.test.ts'],
  },
})
