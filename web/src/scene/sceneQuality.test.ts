import { afterEach, describe, expect, it } from 'vitest'
import { useI18nStore } from '../i18n/store'
import {
  AMOSTRA_ALTURA,
  AMOSTRA_LARGURA,
  CONFIRMACOES,
  STREAK_INICIAL,
  acumular,
  avaliarCena,
  confirmado,
  measureScene,
  type SceneMetrics,
} from './sceneQuality'

/** Frame RGBA sintético: `tom(x, y)` devolve o cinza daquele pixel. */
function frame(
  tom: (x: number, y: number) => number,
  largura = AMOSTRA_LARGURA,
  altura = AMOSTRA_ALTURA,
): Uint8ClampedArray {
  const pixels = new Uint8ClampedArray(largura * altura * 4)
  for (let y = 0; y < altura; y += 1) {
    for (let x = 0; x < largura; x += 1) {
      const p = (y * largura + x) * 4
      const valor = tom(x, y)
      pixels[p] = valor
      pixels[p + 1] = valor
      pixels[p + 2] = valor
      pixels[p + 3] = 255
    }
  }
  return pixels
}

const cenaBoa: SceneMetrics = {
  luz: 130,
  luzCentro: 140,
  estourado: 0.01,
  contraste: 50,
  detalhe: 2000,
}

describe('measureScene', () => {
  it('mede luz e contraste de um cinza chapado', () => {
    const m = measureScene(frame(() => 120), AMOSTRA_LARGURA, AMOSTRA_ALTURA)
    expect(m.luz).toBeCloseTo(120, 0)
    expect(m.luzCentro).toBeCloseTo(120, 0)
    expect(m.contraste).toBeCloseTo(0, 5)
    // Superfície lisa não tem alta frequência nenhuma.
    expect(m.detalhe).toBeCloseTo(0, 5)
    expect(m.estourado).toBe(0)
  })

  it('conta pixels saturados', () => {
    // Metade da imagem estourada.
    const m = measureScene(frame((_x, y) => (y < AMOSTRA_ALTURA / 2 ? 255 : 10)), AMOSTRA_LARGURA, AMOSTRA_ALTURA)
    expect(m.estourado).toBeCloseTo(0.5, 2)
  })

  /** Xadrez de 1px é o máximo de alta frequência possível; borrá-lo derruba o detalhe. */
  it('detalhe cai quando a imagem perde alta frequência', () => {
    const nitido = measureScene(
      frame((x, y) => ((x + y) % 2 === 0 ? 200 : 40)),
      AMOSTRA_LARGURA,
      AMOSTRA_ALTURA,
    )
    const suave = measureScene(
      frame((x) => 120 + 40 * Math.sin(x / 20)),
      AMOSTRA_LARGURA,
      AMOSTRA_ALTURA,
    )
    expect(nitido.detalhe).toBeGreaterThan(suave.detalhe * 100)
  })

  it('lê o centro separado do quadro inteiro', () => {
    // Bordas estouradas, centro escuro — a forma do contraluz.
    const m = measureScene(
      frame((x) => (x > AMOSTRA_LARGURA * 0.3 && x < AMOSTRA_LARGURA * 0.7 ? 20 : 255)),
      AMOSTRA_LARGURA,
      AMOSTRA_ALTURA,
    )
    expect(m.luzCentro).toBeLessThan(40)
    expect(m.luz).toBeGreaterThan(m.luzCentro)
    expect(m.estourado).toBeGreaterThan(0.3)
  })

  it('não estoura com buffer vazio ou curto demais', () => {
    expect(measureScene(new Uint8ClampedArray(0), 0, 0).luz).toBe(0)
    expect(measureScene(new Uint8ClampedArray(8), 160, 120).luz).toBe(0)
  })
})

describe('avaliarCena', () => {
  it('cena boa não diz nada', () => {
    expect(avaliarCena(cenaBoa)).toBeNull()
  })

  it('acusa luz fraca', () => {
    expect(avaliarCena({ ...cenaBoa, luz: 40 })?.code).toBe('LUZ_FRACA')
  })

  /**
   * O caso medido no corpus: o `polichinelo-01` tem 92,8% de pixels saturados e é cena BOA —
   * fundo claro com a pessoa bem iluminada (centro em 244). Contraluz exige o centro escuro.
   */
  it('estouro alto com centro claro não é contraluz', () => {
    expect(avaliarCena({ ...cenaBoa, estourado: 0.93, luz: 245, luzCentro: 245 })).toBeNull()
  })

  it('acusa contraluz quando o fundo estoura e o corpo fica escuro', () => {
    expect(avaliarCena({ ...cenaBoa, estourado: 0.4, luzCentro: 45 })?.code).toBe('CONTRALUZ')
  })

  it('acusa falta de nitidez com luz boa', () => {
    expect(avaliarCena({ ...cenaBoa, detalhe: 300 })?.code).toBe('SEM_NITIDEZ')
  })

  /**
   * Escurecer também derruba o laplaciano (no corpus: 1792 → 119 só apagando a luz). Se a
   * nitidez fosse julgada no escuro, o aviso mandaria limpar uma lente que está limpa.
   */
  it('no escuro a queixa é a luz, nunca a nitidez', () => {
    expect(avaliarCena({ ...cenaBoa, luz: 35, detalhe: 120 })?.code).toBe('LUZ_FRACA')
  })

  it('parede lisa não vira acusação de lente suja', () => {
    expect(avaliarCena({ ...cenaBoa, contraste: 3, detalhe: 10 })).toBeNull()
  })
})

describe('acumular / confirmado', () => {
  it('exige amostras seguidas antes de mexer na tela', () => {
    let streak = acumular(STREAK_INICIAL, 'LUZ_FRACA')
    expect(confirmado(streak)).toBe(false)
    streak = acumular(streak, 'LUZ_FRACA')
    expect(confirmado(streak)).toBe(true)
    expect(streak.vezes).toBe(CONFIRMACOES)
  })

  it('veredito diferente zera a contagem', () => {
    const streak = acumular(acumular(STREAK_INICIAL, 'LUZ_FRACA'), 'SEM_NITIDEZ')
    expect(streak).toEqual({ code: 'SEM_NITIDEZ', vezes: 1 })
    expect(confirmado(streak)).toBe(false)
  })

  it('uma amostra boa solta não apaga um aviso real', () => {
    let streak = acumular(acumular(STREAK_INICIAL, 'LUZ_FRACA'), 'LUZ_FRACA')
    expect(confirmado(streak)).toBe(true)
    streak = acumular(streak, null)
    expect(confirmado(streak)).toBe(false)
  })
})

describe('o conselho de cena existe nas duas línguas (T-149)', () => {
  afterEach(() => useI18nStore.getState().setLocale('pt-BR'))

  it('o CÓDIGO não muda de idioma; a frase muda', () => {
    // O `SceneCode` é contrato — é ele que o `acumular`/`confirmado` conta e o que os testes
    // acima cobram. Só o `text` passa pelo dicionário, e ele é resolvido na CHAMADA (getter),
    // não no import do módulo: sem isso o conselho congelaria no idioma do primeiro render.
    useI18nStore.getState().setLocale('pt-BR')
    const ptBR = avaliarCena({ ...cenaBoa, luz: 40 })
    expect(ptBR?.code).toBe('LUZ_FRACA')
    expect(ptBR?.text).toBe('Está escuro · acenda uma luz')

    useI18nStore.getState().setLocale('en')
    const en = avaliarCena({ ...cenaBoa, luz: 40 })
    expect(en?.code).toBe('LUZ_FRACA')
    expect(en?.text).toBe('It’s dark · turn on a light')
  })
})
