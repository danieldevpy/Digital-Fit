// Entry do SITE (T-067) — servido na raiz (ou em `site.dominio.com`).
// Só conteúdo institucional: landing, Sobre e a 404. Nada de câmera, sessão ou conta — este
// bundle não importa nada de `capture/`, e é essa a fronteira que a T-067 comprou.
//
// **Este arquivo é o único do bundle do site que conhece o navegador** (T-159). Ler a URL, ler
// o `<html lang>` e redirecionar link velho são leituras do mundo, e o mundo do build é outro:
// lá quem monta a mesma árvore é `entries/prerender.tsx`. Manter as duas pontas simétricas — um
// entry por ambiente, componentes puros no meio — é o que impede o pré-render de divergir da
// tela que a pessoa vê.
import { StrictMode } from 'react'
import { createRoot, hydrateRoot } from 'react-dom/client'
import { SiteApp } from '../site/SiteApp'
import {
  redirecionarHashLegado,
  sincronizarLocaleDoDocumento,
  telaDoDocumento,
} from '../site/nav'
import '../styles.css'

// Antes de montar, e não em `useEffect`: quem chega por um `#/sobre` salvo deve ver a página
// certa, não a landing piscando antes dela. É o "301" desta migração, e ele tem de ser do lado
// do cliente porque o fragmento nunca chega ao servidor — ver `site/nav.ts`.
redirecionarHashLegado()

// Também antes de montar, e pelo mesmo motivo de sempre: o idioma resolvido depois do primeiro
// paint é um flash de língua errada. Aqui ainda importa mais que antes — o HTML já chega
// pré-renderizado numa língua, e o primeiro render do cliente TEM de bater com ele.
sincronizarLocaleDoDocumento()

const container = document.getElementById('root')
if (!container) throw new Error('#root não encontrado no index.html')

const arvore = (
  <StrictMode>
    <SiteApp screen={telaDoDocumento()} />
  </StrictMode>
)

// `hydrateRoot` quando o HTML já veio pronto do build, `createRoot` quando não veio.
//
// As duas metades são de verdade: as rotas indexáveis são pré-renderizadas (T-159) e chegam com
// conteúdo, enquanto a 404 chega vazia de propósito — ela não tem idioma para ser renderizada
// em build (é a resposta a uma URL que não existe), então quem a monta é o cliente. Escolher
// pela presença do conteúdo, e não por uma flag no HTML, mantém as duas certas sem um terceiro
// lugar para desincronizar.
if (container.firstChild) {
  hydrateRoot(container, arvore)
} else {
  createRoot(container).render(arvore)
}
