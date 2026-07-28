// Config só do E2E contra o stack real (T-014). Separada da suíte padrão de propósito:
// estes testes precisam de `docker compose up` e levam ~30s, então não podem entrar no
// `npm run test` que roda a cada salvamento e na CI.
//
//     docker compose up -d
//     VITE_API_URL=http://localhost:8000 npm run e2e
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.e2e.test.ts'],
    // Sessão de 30s + timer de no_data de 10s: pressa aqui vira falso vermelho.
    testTimeout: 90_000,
    hookTimeout: 30_000,
    // Cada teste abre a própria sessão no servidor; em paralelo eles disputariam o mesmo
    // worker e o mesmo relógio.
    fileParallelism: false,
    sequence: { concurrent: false },
  },
})
