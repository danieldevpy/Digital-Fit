// Navegação por hash (SPEC-014 §Mapa de navegação).
//
// `location.hash` e não um router de pacote: são seis telas, o back do navegador e o
// refresh precisam funcionar, e uma dependência nova não paga o próprio custo aqui.
import { useSyncExternalStore } from 'react'
import { isExerciseKey } from '../session/catalog'

export type Route =
  | { screen: 'index' }
  | { screen: 'exercicios' }
  | { screen: 'guia'; exercise: string }
  | { screen: 'preparar' }
  | { screen: 'treino' }
  | { screen: 'sobre' }

export function parseHash(hash: string): Route {
  const path = hash.replace(/^#\/?/, '').replace(/\/$/, '')
  if (path === 'exercicios') return { screen: 'exercicios' }
  if (path === 'preparar') return { screen: 'preparar' }
  if (path === 'treino') return { screen: 'treino' }
  if (path === 'sobre') return { screen: 'sobre' }
  const guia = /^guia\/(.+)$/.exec(path)
  // Slug desconhecido no guia não é erro de rota: cai na escolha, onde dá para se orientar.
  if (guia) return isExerciseKey(guia[1]) ? { screen: 'guia', exercise: guia[1] } : { screen: 'exercicios' }
  return { screen: 'index' }
}

export function routeHash(route: Route): string {
  switch (route.screen) {
    case 'index':
      return '#/'
    case 'guia':
      return `#/guia/${route.exercise}`
    default:
      return `#/${route.screen}`
  }
}

export function navigate(route: Route): void {
  window.location.hash = routeHash(route)
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
