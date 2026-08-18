import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
  // Três entry points: o site em pt-BR na raiz, o site em inglês em `/en/` (T-147, SPEC-025
  // §Escopo — Site por URL), o app em `/app/`. Um build só, três HTMLs — é o que permite
  // servir `site.dominio.com` (nas duas línguas) e `app.dominio.com` do mesmo artefato sem
  // duplicar pipeline, e o code splitting do Rollup mantém MediaPipe e a máquina de sessão
  // fora dos bundles do site.
  build: {
    rollupOptions: {
      // Caminhos relativos à `root` do Vite (a pasta `web/`) — sem `node:path` para o
      // tsconfig.node não precisar de @types/node só por causa disto.
      input: {
        site: 'index.html',
        siteEn: 'en/index.html',
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
