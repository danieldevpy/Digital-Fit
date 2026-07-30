// Qualidade de cena na pré-configuração (SPEC-003 Fase Evolução, T-085).
//
// Função pura: entra um frame pequeno, sai um conselho em português. O `useSceneCheck` só
// amostra a câmera e chama isto — a regra se testa com um buffer, sem câmera e sem React.
//
// Três decisões de produto que estão no código de propósito:
//
// 1. **Orienta, não bloqueia.** Nada aqui impede treinar. A Fase Inicial da SPEC-003 já diz
//    que warning de cena orienta e não trava, e travar por um limiar não calibrado é o
//    caminho curto para o app parecer quebrado numa sala que funcionava.
// 2. **Não afirma a causa.** Imagem sem detalhe pode ser lente suja, foco errado ou pouca
//    luz. A mensagem pede a ação que resolve os três e custa 5 segundos ("limpe a lente"),
//    em vez de fingir um diagnóstico que não temos como fazer.
// 3. **Só na pré-configuração.** Durante o treino a instrução de medição manda na tela
//    (SPEC-014, T-071) e um aviso a mais ali disputaria espaço com o que importa.
//
// ---------------------------------------------------------------------------------------
// Sobre os limiares: são PROVISÓRIOS e vieram de medição, não de gosto.
//
// Não existe corpus de cena ruim (o `eval/corpus` tem 3 vídeos, todos de boa luz). O que deu
// para fazer foi medir esses três como estão e em variantes sintéticas — escurecidos (x0,25)
// e borrados (boxblur 6) — com exatamente as contas abaixo:
//
//   vídeo            luz    estourado  varLaplaciano
//   01 como está    244,6      92,8%          1792
//   01 escurecido    60,9       0,0%           119
//   01 borrado      244,7      89,2%           173
//   02 como está    136,7       0,0%          2627
//   02 escurecido    34,0       0,0%           160
//   02 borrado      136,7       0,0%           373
//   03 como está    124,4       0,6%          2003
//   03 escurecido    30,9       0,0%           125
//   03 borrado      124,2       0,6%           559
//
// Duas conclusões que MUDARAM o desenho:
//
// - **Normalizar o laplaciano pelo contraste não serve para comparar cenas.** A razão
//   `varLap / contraste²` é linda contra variação de luz (o vídeo 01 vai de 1,32 para 1,40 ao
//   ser escurecido) e inútil entre cenas: o vídeo 03 NÍTIDO dá 0,15 e o vídeo 01 BORRADO dá
//   0,16. Um limiar sobre ela reprovaria a cena boa. Por isso a nitidez é julgada pelo
//   laplaciano CRU e só quando a luz está boa — que é o que impede confundir escuro com
//   borrado, já que escurecer também derruba o laplaciano (1792 → 119).
// - **Estouro alto não é contraluz.** O vídeo 01 tem 92,8% de pixels saturados e é uma cena
//   boa: fundo claro com a pessoa bem iluminada (o centro também mede 244). Contraluz é fundo
//   claro com sujeito ESCURO — por isso a regra olha o centro do quadro, onde a silhueta-guia
//   põe o corpo, e não só o total.
//
// Recalibrar quando existir corpus de cena ruim (gravações de propósito: cozinha à noite,
// contraluz de janela, lente com digital). Enquanto não existir, os limiares ficam
// conservadores: erram para o lado de não avisar, e o custo de um falso positivo é uma frase
// a mais na tela — nunca um treino impedido.

/** Tamanho da amostra. 160×120 é ~19k pixels: alguns décimos de ms, uma vez por segundo. */
export const AMOSTRA_LARGURA = 160
export const AMOSTRA_ALTURA = 120

/** Abaixo disto a cena está escura (corpus bom: 124–245; escurecido x0,25: 31–61). */
export const LUZ_MINIMA = 60

/** Fração de pixels saturados que levanta suspeita de contraluz. */
export const ESTOURO_MAXIMO = 0.15

/** …mas só é contraluz se o CENTRO (onde o corpo fica) estiver escuro. */
export const LUZ_CENTRO_MINIMA = 90

/**
 * Energia de alta frequência abaixo da qual a imagem está sem detalhe (corpus bom: 1792–2627;
 * com borrão forte: 173–559). Só vale com luz boa — no escuro este número cai por outro motivo.
 */
export const DETALHE_MINIMO = 600

/** Contraste mínimo para a nitidez ser julgável: parede lisa não tem o que borrar. */
export const CONTRASTE_MINIMO = 12

export interface SceneMetrics {
  /** Luminância média do frame inteiro, 0–255. */
  luz: number
  /** Luminância média da faixa central — onde a silhueta-guia põe o corpo. */
  luzCentro: number
  /** Fração de pixels saturados (0–1). */
  estourado: number
  /** Desvio-padrão da luminância: o "quanto há para ver" na cena. */
  contraste: number
  /** Variância do laplaciano: energia de alta frequência (detalhe). */
  detalhe: number
}

export type SceneCode = 'LUZ_FRACA' | 'CONTRALUZ' | 'SEM_NITIDEZ'

export interface SceneAdvice {
  code: SceneCode
  /** O que a pessoa lê. Uma frase, com a ação junto. */
  text: string
}

/**
 * Uma frase curta com a ação junto. O tamanho não é estética: o pill vive dentro da janela
 * nítida, que tem 202px — a dica que já mora ali tem 38 caracteres, e estas ficam na mesma
 * ordem para não virarem um parágrafo em cima da câmera.
 */
const CONSELHOS: Record<SceneCode, string> = {
  LUZ_FRACA: 'Está escuro · acenda uma luz',
  CONTRALUZ: 'A luz está atrás de você · vire-se',
  SEM_NITIDEZ: 'Imagem sem nitidez · limpe a lente',
}

/** Recorte central: 30–70% da largura, 15–85% da altura (a faixa da silhueta-guia). */
const CENTRO_X0 = 0.3
const CENTRO_X1 = 0.7
const CENTRO_Y0 = 0.15
const CENTRO_Y1 = 0.85

/**
 * Métricas de um frame RGBA (o que sai de `getImageData().data`).
 *
 * Uma passada só pelo buffer para luz/estouro/centro, e uma segunda pelo interior para o
 * laplaciano — a 19k pixels isso é ruído de CPU perto de uma inferência de pose.
 */
export function measureScene(
  pixels: Uint8ClampedArray,
  largura: number,
  altura: number,
): SceneMetrics {
  const total = largura * altura
  if (total === 0 || pixels.length < total * 4) {
    return { luz: 0, luzCentro: 0, estourado: 0, contraste: 0, detalhe: 0 }
  }

  const luma = new Float64Array(total)
  let soma = 0
  let somaQuadrados = 0
  let saturados = 0
  let somaCentro = 0
  let pixelsCentro = 0

  const x0 = Math.floor(largura * CENTRO_X0)
  const x1 = Math.floor(largura * CENTRO_X1)
  const y0 = Math.floor(altura * CENTRO_Y0)
  const y1 = Math.floor(altura * CENTRO_Y1)

  for (let y = 0; y < altura; y += 1) {
    for (let x = 0; x < largura; x += 1) {
      const i = y * largura + x
      const p = i * 4
      // Coeficientes de luminância do Rec. 709 — os mesmos que a bancada usou para medir.
      const valor =
        0.2126 * (pixels[p] ?? 0) + 0.7152 * (pixels[p + 1] ?? 0) + 0.0722 * (pixels[p + 2] ?? 0)
      luma[i] = valor
      soma += valor
      somaQuadrados += valor * valor
      if (valor >= 250) saturados += 1
      if (x >= x0 && x < x1 && y >= y0 && y < y1) {
        somaCentro += valor
        pixelsCentro += 1
      }
    }
  }

  const media = soma / total
  const variancia = Math.max(0, somaQuadrados / total - media * media)

  // Laplaciano de 4 vizinhos no interior. A média dele é ~0 numa imagem qualquer, mas não
  // exatamente — a variância é calculada de verdade, não assumida.
  let somaLap = 0
  let somaLapQuadrado = 0
  let contagemLap = 0
  for (let y = 1; y < altura - 1; y += 1) {
    for (let x = 1; x < largura - 1; x += 1) {
      const i = y * largura + x
      const lap =
        4 * (luma[i] ?? 0) -
        (luma[i - largura] ?? 0) -
        (luma[i + largura] ?? 0) -
        (luma[i - 1] ?? 0) -
        (luma[i + 1] ?? 0)
      somaLap += lap
      somaLapQuadrado += lap * lap
      contagemLap += 1
    }
  }

  const mediaLap = contagemLap > 0 ? somaLap / contagemLap : 0
  const varianciaLap =
    contagemLap > 0 ? Math.max(0, somaLapQuadrado / contagemLap - mediaLap * mediaLap) : 0

  return {
    luz: media,
    luzCentro: pixelsCentro > 0 ? somaCentro / pixelsCentro : media,
    estourado: saturados / total,
    contraste: Math.sqrt(variancia),
    detalhe: varianciaLap,
  }
}

/**
 * O conselho a dar, ou `null` quando a cena está boa o bastante.
 *
 * A ordem é de prioridade e não é arbitrária: escuro primeiro porque é a causa que estraga
 * tudo o mais (inclusive a leitura de nitidez); contraluz depois; nitidez por último e SÓ com
 * luz boa, porque no escuro o detalhe cai por outro motivo e o aviso mentiria a causa.
 */
export function avaliarCena(m: SceneMetrics): SceneAdvice | null {
  if (m.luz < LUZ_MINIMA) return { code: 'LUZ_FRACA', text: CONSELHOS.LUZ_FRACA }
  if (m.estourado >= ESTOURO_MAXIMO && m.luzCentro < LUZ_CENTRO_MINIMA) {
    return { code: 'CONTRALUZ', text: CONSELHOS.CONTRALUZ }
  }
  if (m.contraste >= CONTRASTE_MINIMO && m.detalhe < DETALHE_MINIMO) {
    return { code: 'SEM_NITIDEZ', text: CONSELHOS.SEM_NITIDEZ }
  }
  return null
}

/**
 * Quantas amostras seguidas com o mesmo veredito antes de mexer na tela.
 *
 * Amostramos 1×/s, então isto é o "debounce de 1s para ligar" que a SPEC-003 pede — e vale
 * para os dois lados: alguém passando na frente da luz não acende o aviso, e uma amostra boa
 * solta não apaga um aviso que é real.
 */
export const CONFIRMACOES = 2

export interface SceneStreak {
  code: SceneCode | null
  vezes: number
}

export const STREAK_INICIAL: SceneStreak = { code: null, vezes: 0 }

/** Acumula o veredito da amostra; zera a contagem quando ele muda. */
export function acumular(anterior: SceneStreak, novo: SceneCode | null): SceneStreak {
  if (anterior.code === novo) return { code: novo, vezes: anterior.vezes + 1 }
  return { code: novo, vezes: 1 }
}

/** Já dá para mostrar (ou tirar) o aviso? */
export function confirmado(streak: SceneStreak): boolean {
  return streak.vezes >= CONFIRMACOES
}
