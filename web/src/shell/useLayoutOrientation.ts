// O layout que vale, com a escolha manual junto (SPEC-027 §F).
//
// Três camadas, de propósito: `orientation.ts` é o sinal do navegador, `orientationChoice.ts`
// é a regra (pura, testada sem React), e este arquivo é só a cola — o estado da escolha e o
// gancho que a tela consome. Quem quiser entender a decisão lê o do meio.
//
// A escolha **não é persistida**. Ela vale até a viewport girar de verdade, e recarregar a
// página é um começo novo: guardá-la faria alguém voltar amanhã num layout deitado escolhido
// uma vez, sem lembrar de ter escolhido.
import { create } from 'zustand'

import { currentOrientation, useOrientation, type Orientation } from './orientation'
import {
  escolherOutra,
  orientationLabel,
  resolveOrientation,
  rotacaoTravada,
  type EscolhaDeOrientacao,
  type RotuloDeOrientacao,
} from './orientationChoice'

interface OrientationChoiceState {
  escolha: EscolhaDeOrientacao | null
  alternar: (viewport: Orientation) => void
}

export const useOrientationChoiceStore = create<OrientationChoiceState>((set, get) => ({
  escolha: null,
  alternar: (viewport) => set({ escolha: escolherOutra(viewport, get().escolha) }),
}))

/**
 * O rótulo de orientação AGORA, para quem não é componente (a admissão, T-176).
 *
 * Lê as mesmas duas fontes do gancho — a viewport e a escolha manual — sem passar por React.
 * Existe porque o `POST /sessions` acontece fora de qualquer render, e carimbar a sessão com
 * um valor lido antes seria carimbar o que era verdade quando a tela desenhou, não quando o
 * treino começou.
 */
export function orientationLabelAgora(): RotuloDeOrientacao {
  const viewport = currentOrientation()
  const escolha = useOrientationChoiceStore.getState().escolha
  return orientationLabel(viewport, resolveOrientation(viewport, escolha))
}

export interface LayoutOrientation {
  /** O que o navegador diz — a forma da viewport. */
  viewport: Orientation
  /** O que a tela desenha: a viewport, ou a escolha manual enquanto ela vale. */
  valendo: Orientation
  /**
   * Paisagem pedida numa viewport que continuou retrato: a rotação do aparelho está travada,
   * e o quadro da câmera **também não girou**. É o caso em que a tela precisa dizer que
   * destravar preserva a leitura do exercício.
   */
  travada: boolean
  /** Como esta sessão seria rotulada no `session.capability` (a T-176 é quem envia). */
  rotulo: RotuloDeOrientacao
  alternar: () => void
}

export function useLayoutOrientation(): LayoutOrientation {
  const viewport = useOrientation()
  const escolha = useOrientationChoiceStore((state) => state.escolha)
  const alternarNoStore = useOrientationChoiceStore((state) => state.alternar)

  const valendo = resolveOrientation(viewport, escolha)
  return {
    viewport,
    valendo,
    travada: rotacaoTravada(viewport, valendo),
    rotulo: orientationLabel(viewport, valendo),
    alternar: () => alternarNoStore(viewport),
  }
}
