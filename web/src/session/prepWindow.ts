// Geometria da janela nítida da pré-configuração (T-167).
//
// Desde a T-080 os quatro cantos da janela são quatro constantes em CSS (`--prep-win-*`), e as
// duas horizontais continuam sendo — elas dependem da largura das colunas de cards, que é uma
// decisão de layout. As duas VERTICAIS não podiam ser: `--prep-win-bottom: 150px` foi medido
// num rodapé sem `env(safe-area-inset-bottom)`, então em aparelho com entalhe o rodapé real é
// ~34px mais alto e a borda de baixo da janela cai DENTRO da tab bar. A faixa que a janela
// prometia mostrar e não mostrava é justamente onde ficam os PÉS de quem se enquadra — e o
// relato do Daniel ("não dá pra perceber o espaço ao redor da pessoa") é exatamente isso.
//
// A correção não é uma constante melhor: é parar de ter constante. O cabeçalho e o rodapé
// sabem que altura têm; a janela é o que sobra entre eles, medido no aparelho de verdade. Isso
// também cobre de graça o que iria quebrar depois: título que quebra em duas linhas noutro
// idioma (SPEC-025), CTA que muda de altura, tab bar que ganha um item.
//
// A conta mora aqui, pura, e não dentro do componente: é a mesma escolha do `startGate` — regra
// de geometria se testa com tabela de números, não montando React nem abrindo câmera.

export interface PrepChrome {
  /** Altura do palco (`.sess`) em px. */
  stageH: number
  /** Altura medida do cabeçalho (`.prep__head`) em px. */
  headH: number
  /** Altura medida do rodapé (`.prep__bottom`) em px — já com a área segura dentro. */
  bottomH: number
}

export interface PrepInsets {
  top: number
  bottom: number
}

/** Respiro entre o cromo e a borda da janela: o texto não encosta na imagem nítida. */
export const FOLGA_PX = 8

/**
 * Piso da janela. Abaixo disto ela deixa de servir para enquadrar um corpo inteiro, e aí o
 * certo é o cromo invadir a imagem (ele tem fundo próprio) em vez de a janela sumir.
 */
export const ALTURA_MINIMA_PX = 280

/**
 * Os valores da T-080. Valem até a primeira medição chegar e sempre que ela vier vazia — um
 * `ResizeObserver` dispara antes da fonte carregar, e `0` ali significa "ainda não sei", não
 * "o cabeçalho não existe".
 */
export const PADRAO: PrepInsets = { top: 64, bottom: 150 }

function medido(valor: number): boolean {
  return Number.isFinite(valor) && valor > 0
}

/**
 * Onde começam e terminam as bordas de cima e de baixo da janela nítida.
 *
 * Quando o cromo é alto demais para o palco (aparelho baixo, teclado aberto, fonte grande do
 * sistema), os dois lados encolhem PROPORCIONALMENTE em vez de um comer o outro: o cabeçalho
 * é pequeno e o rodapé é grande, e cortar só um deles deixaria a janela fora do eixo da tela.
 */
export function prepWindowInsets({ stageH, headH, bottomH }: PrepChrome): PrepInsets {
  if (!medido(stageH)) return PADRAO

  const top = medido(headH) ? Math.round(headH) + FOLGA_PX : PADRAO.top
  const bottom = medido(bottomH) ? Math.round(bottomH) + FOLGA_PX : PADRAO.bottom

  const disponivel = stageH - ALTURA_MINIMA_PX
  if (disponivel <= 0) return { top: 0, bottom: 0 }

  const somado = top + bottom
  if (somado <= disponivel) return { top, bottom }

  const fator = disponivel / somado
  return { top: Math.round(top * fator), bottom: Math.round(bottom * fator) }
}
