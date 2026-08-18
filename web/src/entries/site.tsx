// Entry do SITE (T-067) — servido na raiz (ou em `site.dominio.com`).
// Só conteúdo institucional: landing e Sobre. Nada de câmera, sessão ou conta — este bundle
// não importa nada de `capture/`, e é essa a fronteira que a T-067 comprou.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { SiteApp } from '../site/SiteApp'
import { redirecionarHashLegado } from '../site/nav'
import '../styles.css'

// Antes de montar, e não em `useEffect` (T-158): quem chega por um `#/sobre` salvo deve ver a
// página certa, não a landing piscando antes dela. É o "301" desta migração, e ele tem de ser
// do lado do cliente porque o fragmento nunca chega ao servidor — ver `site/nav.ts`.
redirecionarHashLegado()

const container = document.getElementById('root')
if (!container) throw new Error('#root não encontrado no index.html')

createRoot(container).render(
  <StrictMode>
    <SiteApp />
  </StrictMode>,
)
