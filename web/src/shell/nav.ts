// Navegação por hash DO APP (SPEC-014 §Mapa de navegação).
//
// `location.hash` e não um router de pacote: são poucas telas, o back do navegador e o
// refresh precisam funcionar, e uma dependência nova não paga o próprio custo aqui.
//
// O index saiu daqui na T-067: a landing virou bundle próprio (`src/site/`), e o app começa
// na pré-configuração — é ela a tela "Início" da tab bar. Hash desconhecido cai em
// `preparar` porque abrir o app sem rota é abrir o app para treinar.
import { useSyncExternalStore } from 'react'
import { isExerciseKey } from '../session/catalog'

export type Route =
  | { screen: 'exercicios' }
  | { screen: 'guia'; exercise: string }
  | { screen: 'preparar' }
  | { screen: 'treino' }
  | { screen: 'progresso' }
  | { screen: 'analytics' }
  /**
   * Ponte do site para o app: `#/ex/<slug>` não é tela, é a decisão do funil (SPEC-015)
   * pedida de fora. O site não pode tomá-la — `guide_seen` mora no localStorage do APP, e
   * localStorage não atravessa host. Então o site aponta o exercício e o app decide entre
   * Guia e Pré-config, trocando a rota por cima (sem deixar entrada no histórico).
   */
  | { screen: 'abrirExercicio'; exercise: string }
  /**
   * Outra ponte do site: `#/entrar` abre a folha de conta. Existe porque a conta é do app
   * (o token fica no localStorage desta origem) e o site precisa de um link para ela —
   * "Entrar" não pode ser um botão que loga no host errado.
   */
  | { screen: 'entrar' }

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#\/?/, '').replace(/\/$/, '')
  if (path === 'exercicios') return { screen: 'exercicios' }
  if (path === 'preparar') return { screen: 'preparar' }
  if (path === 'treino') return { screen: 'treino' }
  if (path === 'progresso') return { screen: 'progresso' }
  if (path === 'analytics') return { screen: 'analytics' }
  if (path === 'entrar') return { screen: 'entrar' }

  const guia = /^guia\/(.+)$/.exec(path)
  // Slug desconhecido no guia não é erro de rota: cai na escolha, onde dá para se orientar.
  if (guia) {
    return isExerciseKey(guia[1]) ? { screen: 'guia', exercise: guia[1] } : { screen: 'exercicios' }
  }

  const abrir = /^ex\/(.+)$/.exec(path)
  if (abrir) {
    return isExerciseKey(abrir[1])
      ? { screen: 'abrirExercicio', exercise: abrir[1] }
      : { screen: 'exercicios' }
  }

  return { screen: 'preparar' }
}

export function routeHash(route: Route): string {
  switch (route.screen) {
    case 'guia':
      return `#/guia/${route.exercise}`
    case 'abrirExercicio':
      return `#/ex/${route.exercise}`
    default:
      return `#/${route.screen}`
  }
}

/**
 * `replace` existe para a ponte `#/ex/<slug>`: ela é um passo interno do funil, e deixá-la
 * no histórico faria o back do navegador voltar para a ponte — que redirecionaria de novo,
 * prendendo quem só quis voltar uma tela.
 */
export function navigate(route: Route, { replace = false }: { replace?: boolean } = {}): void {
  const hash = routeHash(route)
  if (replace) window.location.replace(`${window.location.pathname}${window.location.search}${hash}`)
  else window.location.hash = hash
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

function snapshot(): string {
  return window.location.hash
}

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, snapshot, () => '')
  return parseHash(hash)
}
