// Entry do APP (T-067) — servido em `/app/` (ou em `app.dominio.com`).
// Só o funil de treino mora aqui: câmera, sessão, relatório e conta.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { AppShell } from '../app/AppShell'
import '../styles.css'

const container = document.getElementById('root')
if (!container) throw new Error('#root não encontrado no app/index.html')

createRoot(container).render(
  <StrictMode>
    <AppShell />
  </StrictMode>,
)
