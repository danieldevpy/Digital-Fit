import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
  test: {
    environment: 'node',
    // `*.e2e.test.ts` exige stack de pé e fica fora da suíte padrão (roda por `npm run e2e`).
    include: ['src/**/*.test.ts'],
    exclude: ['**/node_modules/**', 'src/**/*.e2e.test.ts'],
  },
})
