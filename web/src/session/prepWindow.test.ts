import { describe, expect, it } from 'vitest'
import { ALTURA_MINIMA_PX, FOLGA_PX, PADRAO, prepWindowInsets } from './prepWindow'

describe('prepWindowInsets', () => {
  it('a janela é o que sobra entre o cabeçalho e o rodapé medidos', () => {
    expect(prepWindowInsets({ stageH: 844, headH: 62, bottomH: 139 })).toEqual({
      top: 62 + FOLGA_PX,
      bottom: 139 + FOLGA_PX,
    })
  })

  it('rodapé com área segura empurra a borda de baixo — o bug do entalhe (T-167)', () => {
    // O mesmo aparelho, agora com `env(safe-area-inset-bottom)` de 34px dentro do rodapé. Com
    // a constante de 150px da T-080 a borda de baixo da janela caía DENTRO da tab bar; medindo,
    // ela sobe sozinha e os pés voltam a caber na parte nítida.
    const comEntalhe = prepWindowInsets({ stageH: 844, headH: 62, bottomH: 173 })
    expect(comEntalhe.bottom).toBe(173 + FOLGA_PX)
    expect(comEntalhe.bottom).toBeGreaterThan(PADRAO.bottom)
  })

  it('medição ainda não chegou: mantém os valores da T-080 em vez de colapsar a janela', () => {
    // `ResizeObserver` dispara antes de a fonte carregar, e altura `0` ali quer dizer "ainda
    // não sei". Zerar a borda faria a janela piscar de tamanho no primeiro quadro.
    expect(prepWindowInsets({ stageH: 844, headH: 0, bottomH: 0 })).toEqual(PADRAO)
    expect(prepWindowInsets({ stageH: 844, headH: 62, bottomH: 0 })).toEqual({
      top: 62 + FOLGA_PX,
      bottom: PADRAO.bottom,
    })
  })

  it('palco não medido não é palco de zero altura', () => {
    expect(prepWindowInsets({ stageH: 0, headH: 62, bottomH: 139 })).toEqual(PADRAO)
    expect(prepWindowInsets({ stageH: Number.NaN, headH: 62, bottomH: 139 })).toEqual(PADRAO)
  })

  it('cromo alto demais: os dois lados encolhem juntos e a janela guarda o piso', () => {
    // Palco baixinho (aparelho pequeno, barra do navegador aberta): 62+8 e 173+8 somam 251, e
    // só sobrariam 149px de janela. O cromo é que invade — ele tem fundo próprio.
    const apertado = prepWindowInsets({ stageH: 400, headH: 62, bottomH: 173 })
    expect(apertado.top + apertado.bottom).toBeLessThanOrEqual(400 - ALTURA_MINIMA_PX)
    expect(400 - apertado.top - apertado.bottom).toBeGreaterThanOrEqual(ALTURA_MINIMA_PX)
    // Proporcional, e não um comendo o outro: a janela continua no eixo da tela.
    expect(apertado.top).toBeGreaterThan(0)
    expect(apertado.bottom).toBeGreaterThan(apertado.top)
  })

  it('palco menor que o piso: a janela vira a tela inteira em vez de virar nada', () => {
    expect(prepWindowInsets({ stageH: 240, headH: 62, bottomH: 173 })).toEqual({ top: 0, bottom: 0 })
  })

  // ------------------------------------------------------------------ paisagem (T-172)
  //
  // A máquina de medir da T-167 não precisou aprender nada sobre orientação: ela lê a altura
  // REAL do cabeçalho e do rodapé, e em paisagem o CSS encolhe os dois (cabeçalho vira uma
  // linha, CTA e tab bar deixam de empilhar).
  //
  // O ganho do layout deitado **não está no tamanho da janela** — em 390px de altura o piso de
  // 280px manda nos dois casos, e o retângulo é o mesmo. Está em quanto dele fica COBERTO: o
  // cromo empilhado de retrato é 201px de altura ocupando 110px de borda, ou seja, 91px de
  // painel opaco por cima da imagem que a pessoa está tentando ler. Esta é a medida que os
  // casos abaixo travam.
  describe('celular deitado (~390px de altura)', () => {
    /** Quanto do cromo sobra POR CIMA da janela nítida. Zero = ele cabe na própria borda. */
    function invasao(stageH: number, headH: number, bottomH: number): number {
      const { top, bottom } = prepWindowInsets({ stageH, headH, bottomH })
      return Math.max(0, headH - top) + Math.max(0, bottomH - bottom)
    }

    it('com o cromo de paisagem, nada do cromo cobre a janela', () => {
      // Cabeçalho em uma linha (~30px) e rodapé em uma faixa só (~70px) — o que o CSS de
      // paisagem produz.
      expect(invasao(390, 30, 70)).toBe(0)
    })

    it('com o cromo empilhado de retrato, 91px de painel caem sobre a imagem', () => {
      expect(invasao(390, 62, 139)).toBe(91)
    })

    it('a janela guarda o piso nos dois casos — o piso é de retrato e deitado ele sempre morde', () => {
      for (const [headH, bottomH] of [
        [30, 70],
        [62, 139],
      ]) {
        const { top, bottom } = prepWindowInsets({ stageH: 390, headH: headH!, bottomH: bottomH! })
        expect(390 - top - bottom).toBe(ALTURA_MINIMA_PX)
      }
    })
  })
})
