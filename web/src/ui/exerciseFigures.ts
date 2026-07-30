// Registro slug → figura de exercício (T-082). É AQUI que se adiciona.
//
// PARA ADICIONAR UM EXERCÍCIO, dois passos e nenhum a mais:
//   1. desenhe a pose em `icons.tsx`, seção "figuras de exercício" — copie uma das que já
//      existem e mova os pontos, para a figura nova nascer no mesmo vocabulário;
//   2. registre-a em `EXERCISE_FIGURES` abaixo, com a MESMA chave do `EXERCISE_CATALOG`.
//
// Nada de CSS, nada de tocar nas telas: o `ExerciseIcon` já lê daqui.
//
// Esquecer o passo 2 não passa em silêncio — `exerciseIcon.test.ts` compara estas chaves com
// as do catálogo e falha nomeando o slug sem figura. Foi por isso que o registro é um objeto
// exportado, e não um `switch` dentro do componente: o `switch` seria igualmente correto e
// impossível de conferir por teste, e a garantia que interessa não é "o mapa funciona", é
// "ninguém adiciona exercício e esquece a figura".
//
// Arquivo `.ts` sem JSX, separado do componente, por duas razões que se somam: a regra de
// fast refresh do ESLint reclama de módulo que exporta componente E constante, e o registro
// ser dado puro é o que deixa o teste lê-lo sem renderizar nada (a suíte roda em `node`, sem
// DOM). Fica em `ui/` e não no `session/catalog.ts` porque catálogo é conteúdo — nome, dica,
// grupo muscular — e figura é apresentação; juntá-los faria o catálogo carregar React para
// quem só quer o nome de exibição de um exercício.
import type { ReactElement } from 'react'

import { IconExJumpingJack, IconExSquat, IconExStanding } from './icons'

type Figura = (props: { className?: string }) => ReactElement

export const EXERCISE_FIGURES: Record<string, Figura> = {
  jumping_jack: IconExJumpingJack,
  squat: IconExSquat,
}

/**
 * A figura de quem ainda não tem figura.
 *
 * Não pode ser o polichinelo: um exercício sem pose própria mostraria um boneco de braços
 * pro alto no card, que é uma afirmação errada sobre o que a pessoa vai fazer — exatamente o
 * bug que esta task conserta. A neutra em pé não afirma nada além de "uma pessoa".
 */
export const FIGURA_PADRAO: Figura = IconExStanding
