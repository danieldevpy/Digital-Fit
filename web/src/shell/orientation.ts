// Orientação da tela (SPEC-027 §C).
//
// **A fonte da verdade é a FORMA DA VIEWPORT, não o ângulo do aparelho.** `matchMedia
// ('(orientation: landscape)')` responde "a caixa em que eu desenho é mais larga que alta?",
// que é exatamente a pergunta do layout. `screen.orientation.angle` e o `window.orientation`
// obsoleto respondem outra coisa — em celular com a rotação de tela travada os dois discordam,
// e seguir o ângulo desenharia um layout largo dentro de uma caixa estreita.
//
// **Media query e não `resize`.** `resize` também dispara quando a barra do navegador do
// celular entra e sai — a cada rolagem — e cada disparo reavaliaria o layout inteiro. A
// consulta só acorda quando a resposta muda.
//
// Isto é um sinal, não uma decisão: quem decide qual layout vale é quem consome, e é lá que a
// T-175 vai enfiar a escolha manual. Por isso o resultado vira CLASSE no DOM e não `@media`
// no CSS — uma `@media (orientation: landscape)` não tem como ser sobreposta por um botão, e
// duas fontes da verdade para a mesma pergunta é o que a casa não faz.
import { useSyncExternalStore } from 'react'

export type Orientation = 'portrait' | 'landscape'

export const CONSULTA_PAISAGEM = '(orientation: landscape)'

export function orientationFrom(paisagem: boolean): Orientation {
  return paisagem ? 'landscape' : 'portrait'
}

/** `matchMedia` do navegador, com a forma mínima que este módulo usa. */
export interface ConsultaMidia {
  matches: boolean
  addEventListener: (tipo: 'change', ouvinte: () => void) => void
  removeEventListener: (tipo: 'change', ouvinte: () => void) => void
}

export type AbrirConsulta = (consulta: string) => ConsultaMidia

function consultaPadrao(): AbrirConsulta | null {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return null
  return (consulta) => window.matchMedia(consulta)
}

/**
 * Lê a orientação agora. Sem `matchMedia` (pré-render, navegador antigo) responde `portrait`,
 * que é o layout de sempre — o produto nasceu retrato e é ele que não pode depender de
 * detecção para funcionar.
 */
export function currentOrientation(abrir: AbrirConsulta | null = consultaPadrao()): Orientation {
  if (!abrir) return 'portrait'
  return orientationFrom(abrir(CONSULTA_PAISAGEM).matches)
}

/**
 * Avisa quando a orientação muda; devolve a função de cancelar.
 *
 * `abrir` é injetável para o teste poder provar o que importa aqui: que a assinatura é na
 * consulta de mídia, que ela é cancelada, e que ninguém pendurou nada em `resize`.
 */
export function subscribeOrientation(
  avisar: () => void,
  abrir: AbrirConsulta | null = consultaPadrao(),
): () => void {
  if (!abrir) return () => {}
  const consulta = abrir(CONSULTA_PAISAGEM)
  consulta.addEventListener('change', avisar)
  return () => consulta.removeEventListener('change', avisar)
}

/**
 * `useSyncExternalStore` e não `useState` + `useEffect`: o valor é externo ao React, e este é
 * o gancho que não perde uma mudança acontecida entre o render e o efeito. O terceiro
 * argumento é o instantâneo do servidor — o pré-render (T-159) roda sem `window`, e sem ele a
 * hidratação quebraria em vez de simplesmente começar em retrato.
 *
 * As três funções são estáveis de propósito, no módulo e não no corpo do componente: o gancho
 * re-assina toda vez que a identidade de `subscribe` muda, e com uma arrow criada a cada
 * render isso viraria um `removeEventListener` seguido de um `addEventListener` — a janela
 * entre os dois é onde uma mudança de orientação se perde sem deixar rastro.
 */
const assinar = (avisar: () => void) => subscribeOrientation(avisar)
const agora = () => currentOrientation()
const noServidor = (): Orientation => 'portrait'

export function useOrientation(): Orientation {
  return useSyncExternalStore(assinar, agora, noServidor)
}
