// A sequência da troca de câmera (SPEC-027 §A), separada do hook de propósito.
//
// `useCamera.ts` tem `getUserMedia`, `<video>`, permissão e React — nada disso roda no
// `environment: 'node'` dos testes, e a troca é justamente a parte cuja falha é invisível:
// ela só acontece em aparelho que NÃO tem a câmera pedida, que é o aparelho que ninguém tem
// na mesa na hora de escrever o código. Por isso a política mora aqui, com as dependências
// injetadas, e o hook fica sendo fiação.
import type { Facing } from './facing'
import { otherFacing } from './facing'

export interface SwapDeps {
  /** Abre um stream na câmera pedida. `exact` é o que levanta `OverconstrainedError`. */
  abrir: (facing: Facing, precisao: 'ideal' | 'exact') => Promise<MediaStream>
  /** Pendura o stream no vídeo e resolve rótulo, espelho e zoom. */
  adotar: (stream: MediaStream, pedido: Facing) => Promise<void>
  /** Para os tracks do stream atual. */
  soltar: () => void
  /** `OverconstrainedError`? Injetado para o teste não precisar forjar `DOMException`. */
  ehRestricaoImpossivel: (erro: unknown) => boolean
}

export type SwapResult =
  /** Trocou de verdade. */
  | { estado: 'trocou'; facing: Facing }
  /**
   * Não trocou e voltou para a câmera anterior. `notice: 'single_camera'` quando o motivo foi
   * o aparelho não ter a câmera pedida — o único caso que a tela explica hoje.
   */
  | { estado: 'voltou'; facing: Facing; notice: 'single_camera' | null }
  /** Perdeu a câmera de ida E a de volta: não há imagem nenhuma. */
  | { estado: 'sem_camera'; erro: unknown }

/**
 * Solta a câmera atual ANTES de pedir a outra, e não depois: parte dos aparelhos — iPhone em
 * especial — não entrega duas câmeras ao mesmo tempo, e pedir a segunda com a primeira viva
 * falha ou congela as duas. O preço dessa ordem é não haver para onde voltar sem reabrir, e é
 * exatamente isso que o segundo `try` faz.
 */
export async function swapCamera(anterior: Facing, deps: SwapDeps): Promise<SwapResult> {
  const alvo = otherFacing(anterior)
  deps.soltar()

  try {
    const stream = await deps.abrir(alvo, 'exact')
    await deps.adotar(stream, alvo)
    return { estado: 'trocou', facing: alvo }
  } catch (erro) {
    // `exact` recusado = este aparelho não tem a câmera pedida. Com `ideal` não haveria erro
    // nenhum aqui: viria a mesma câmera de volta e a tela diria que trocou.
    const notice = deps.ehRestricaoImpossivel(erro) ? 'single_camera' : null
    try {
      const volta = await deps.abrir(anterior, 'ideal')
      await deps.adotar(volta, anterior)
      return { estado: 'voltou', facing: anterior, notice }
    } catch (falhaAoVoltar) {
      return { estado: 'sem_camera', erro: falhaAoVoltar }
    }
  }
}
