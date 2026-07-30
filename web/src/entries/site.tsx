// Entry do SITE (T-067) — servido na raiz (ou em `site.dominio.com`).
// Só conteúdo institucional: landing e Sobre. Nada de câmera, sessão ou conta — este bundle
// não importa nada de `capture/`, e é essa a fronteira que a T-067 comprou.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { SiteApp } from '../site/SiteApp'
import '../styles.css'

const container = document.getElementById('root')
if (!container) throw new Error('#root não encontrado no index.html')

createRoot(container).render(
  <StrictMode>
    <SiteApp />
  </StrictMode>,
)
