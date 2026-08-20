// A escolha manual de orientação, e o que ela custa (SPEC-027 §F).
//
// `orientation.ts` responde qual é a forma da viewport. Este módulo responde **qual layout
// vale**, que é outra pergunta desde que existe um botão — e ele existe por um caso concreto:
// celular com a **rotação de tela travada**. Nesse aparelho, virar o celular de lado não muda
// a viewport, não dispara a consulta de mídia, e o app segue desenhando retrato para alguém
// que está segurando deitado.
//
// O que quase ninguém percebe é que, nesse mesmo caso, **o quadro da câmera também não gira**:
// o navegador entrega os frames alinhados à orientação da TELA, que está travada. O mundo
// chega deitado — e aí para de ser assunto de layout:
//
//   · `TOO_FAR`/`TOO_CLOSE` (SPEC-003) medem a altura do corpo como fração da ALTURA do
//     quadro, e com o mundo a 90° passam a medir outra coisa;
//   · a linha ombro-ombro fica perpendicular à horizontal com que a SPEC-003 a compara;
//   · `arm_abduction` (T-044/T-052) continua EXISTINDO e passa a estar errado, que é pior do
//     que não existir.
//
// Por isso o botão tem duas responsabilidades, e a segunda é a que protege o exercício: ele
// alterna o layout **e**, quando o que ele produz é paisagem numa viewport que continuou
// retrato, a tela diz que destravar a rotação é o caminho que preserva a leitura. O produto
// não finge que os dois caminhos são equivalentes.
//
// Girar o FRAME antes da pose ficou fora da Fase Inicial (SPEC-027 §Fora de escopo): é um
// canvas a mais no caminho quente a 15fps, e a SPEC-001 decide edge×cloud por latência por
// inferência — um passo ali pode empurrar aparelho honesto para cloud.
import type { Orientation } from './orientation'

/**
 * A escolha manual, com a orientação da viewport no instante em que foi feita.
 *
 * Guardar `quandoViewportEra` é o que implementa "vale até a orientação real mudar": uma
 * escolha que sobrevivesse a um giro de VERDADE seria uma escolha que ninguém consegue
 * desfazer — a pessoa gira o aparelho, nada acontece, e não há nada na tela explicando por quê.
 */
export interface EscolhaDeOrientacao {
  quer: Orientation
  quandoViewportEra: Orientation
}

/** Qual layout vale agora. A viewport ganha de volta assim que ela mesma muda. */
export function resolveOrientation(
  viewport: Orientation,
  escolha: EscolhaDeOrientacao | null,
): Orientation {
  if (!escolha) return viewport
  if (escolha.quandoViewportEra !== viewport) return viewport
  return escolha.quer
}

/** O que o botão produz ao ser tocado, dado o que está valendo agora. */
export function escolherOutra(
  viewport: Orientation,
  escolha: EscolhaDeOrientacao | null,
): EscolhaDeOrientacao {
  const valendo = resolveOrientation(viewport, escolha)
  return {
    quer: valendo === 'landscape' ? 'portrait' : 'landscape',
    quandoViewportEra: viewport,
  }
}

/**
 * A tela precisa avisar que a rotação do aparelho está travada?
 *
 * Só no caso que machuca: **paisagem pedida numa viewport que continuou retrato**. O
 * contrário — retrato forçado numa viewport deitada — não avisa nada, e a assimetria é
 * deliberada: ali o quadro da câmera está em pé com o mundo em pé, o layout é apenas mais
 * estreito do que precisaria, e não há nada sobre o exercício a corrigir.
 */
export function rotacaoTravada(viewport: Orientation, valendo: Orientation): boolean {
  return valendo === 'landscape' && viewport === 'portrait'
}

/**
 * Como esta sessão será rotulada (SPEC-027 §Eventos). Quem leva o rótulo ao
 * `session.capability` é a T-176; aqui mora a regra, que é o que precisa ser testável.
 *
 * `landscape_forced` não é enfeite de telemetria: é o único jeito de EXCLUIR depois as
 * sessões de quadro girado de qualquer calibração — e sem ele elas viram ruído não explicado
 * no corpus, indistinguíveis de gente que se enquadrou mal.
 */
export type RotuloDeOrientacao = 'portrait' | 'landscape' | 'landscape_forced'

export function orientationLabel(
  viewport: Orientation,
  valendo: Orientation,
): RotuloDeOrientacao {
  if (rotacaoTravada(viewport, valendo)) return 'landscape_forced'
  return valendo
}
