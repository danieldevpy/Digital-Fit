// Medição do probe com uma câmera falsa (T-084).
//
// Vale a pena testar o LAÇO e não só as funções puras: o defeito que esta task corrigiu não
// estava na aritmética, estava em o que era contado. Aqui a câmera falsa entrega frames a uma
// taxa e o modelo falso custa outra — que é exatamente o caso do iPhone com pouca luz — e o
// teste exige que os dois números saiam separados e certos.
import { describe, expect, it } from 'vitest'
import type { PoseLandmarker } from '@mediapipe/tasks-vision'
import { Mode } from '../lib/events'
import { enquadramentoDe, measureProbe, toCapabilityData, type ProbeOutcome } from './runProbe'

/** Queima CPU de verdade: `performance.now()` é o relógio que o probe usa, e ele não é fake. */
function gastar(ms: number): void {
  const ate = performance.now() + ms
  while (performance.now() < ate) {
    /* intencionalmente ocupado */
  }
}

interface CameraFalsaOpts {
  /** ms entre frames apresentados pela "câmera". */
  intervaloMs: number
  /** Custo de cada inferência. */
  inferenciaMs: number
  /** Quantos frames o compositor apresenta a cada callback (simula frames pulados). */
  apresentadosPorCallback?: number
}

function cameraFalsa({ intervaloMs, inferenciaMs, apresentadosPorCallback = 1 }: CameraFalsaOpts) {
  let currentTime = 0
  let presentedFrames = 0
  let timer: ReturnType<typeof setTimeout> | undefined

  const video = {
    readyState: 2,
    HAVE_CURRENT_DATA: 2,
    get currentTime() {
      return currentTime
    },
    requestVideoFrameCallback(callback: (now: number, metadata: unknown) => void): number {
      timer = setTimeout(() => {
        currentTime += intervaloMs / 1000
        presentedFrames += apresentadosPorCallback
        callback(performance.now(), { presentedFrames })
      }, intervaloMs)
      return 1
    },
    cancelVideoFrameCallback() {
      clearTimeout(timer)
    },
  } as unknown as HTMLVideoElement

  const landmarker = {
    detectForVideo() {
      gastar(inferenciaMs)
      return { landmarks: [] }
    },
  } as unknown as PoseLandmarker

  return { video, landmarker }
}

describe('measureProbe', () => {
  /**
   * O caso do relatório: câmera devagar (pouca luz no iPhone), modelo rápido. A régua antiga
   * media ~10fps e mandava para cloud. A nova tem de dizer que o MODELO vai bem e que a
   * CÂMERA é que está lenta — dois números, duas conclusões diferentes.
   */
  it('separa câmera lenta de aparelho lento', async () => {
    const { video, landmarker } = cameraFalsa({ intervaloMs: 100, inferenciaMs: 5 })

    const medida = await measureProbe(landmarker, video, 600, 900)

    expect(medida.failed).toBe(false)
    expect(medida.samples).toBeGreaterThan(0)
    // Modelo em ~5ms/inferência: bem acima do limiar de 12fps.
    expect(medida.modelFps).toBeGreaterThan(50)
    expect(medida.inferenceMsP50).toBeLessThan(20)
    // Câmera a 10fps — e este é o número que NÃO pode decidir o modo.
    expect(medida.cameraFps).toBeLessThan(20)
    expect(medida.cameraFpsSource).toBe('apresentados')
  }, 5000)

  /** Aparelho lento de verdade: o modelo é o gargalo e a medida tem de acusar. */
  it('acusa o aparelho quando quem é lento é o modelo', async () => {
    const { video, landmarker } = cameraFalsa({ intervaloMs: 10, inferenciaMs: 40 })

    const medida = await measureProbe(landmarker, video, 600, 900)

    expect(medida.modelFps).toBeLessThan(40)
    expect(medida.inferenceMsP50).toBeGreaterThanOrEqual(30)
  }, 5000)

  /**
   * Frames que o compositor apresentou mas nós não tratamos continuam contando para a taxa da
   * câmera: é isso que `presentedFrames` compra sobre contar chamadas nossas.
   */
  it('conta frames apresentados, não frames processados', async () => {
    const { video, landmarker } = cameraFalsa({
      intervaloMs: 30,
      inferenciaMs: 1,
      apresentadosPorCallback: 3,
    })

    const medida = await measureProbe(landmarker, video, 400, 700)

    expect(medida.cameraFpsSource).toBe('apresentados')
    // ~3 frames a cada 30ms ≈ 100fps de fonte, contra ~33 callbacks/s que tratamos.
    expect(medida.cameraFps ?? 0).toBeGreaterThan(50)
  }, 5000)

  /**
   * O caso que travava o app para sempre: câmera que não entrega frame nenhum. Sem o watchdog
   * o rVFC nunca dispara, a promessa nunca resolve e a tela fica em "calibrando o dispositivo"
   * sem erro e sem saída.
   */
  it('resolve mesmo sem frame nenhum, e sem medida', async () => {
    const video = {
      readyState: 0,
      HAVE_CURRENT_DATA: 2,
      currentTime: 0,
      requestVideoFrameCallback: () => 1,
      cancelVideoFrameCallback: () => {},
    } as unknown as HTMLVideoElement
    const landmarker = { detectForVideo: () => ({ landmarks: [] }) } as unknown as PoseLandmarker

    const medida = await measureProbe(landmarker, video, 100, 200)

    expect(medida.failed).toBe(false)
    expect(medida.samples).toBe(0)
    expect(medida.modelFps).toBeNull()
  }, 5000)

  /** Exceção do modelo é falha de pipeline local — o servidor é a alternativa real. */
  it('marca falha quando a inferência lança', async () => {
    const { video } = cameraFalsa({ intervaloMs: 10, inferenciaMs: 0 })
    const landmarker = {
      detectForVideo() {
        throw new Error('contexto perdido')
      },
    } as unknown as PoseLandmarker

    const medida = await measureProbe(landmarker, video, 400, 700)

    expect(medida.failed).toBe(true)
    expect(medida.error).toContain('contexto perdido')
    expect(medida.modelFps).toBeNull()
    expect(medida.cameraFps).toBeNull()
  }, 5000)
})

// ------------------------------------------------------------------ enquadramento (T-176)

const medidaOk: ProbeOutcome = {
  modelFps: 20,
  inferenceMsP50: 50,
  cameraFps: 30,
  cameraFpsSource: 'apresentados',
  samples: 12,
  durationMs: 2000,
  failed: false,
  webgl: true,
  wasmSimd: true,
  forced: false,
  mode: Mode.EDGE,
  reason: 'probe_ok',
}

describe('o enquadramento que sobe junto com o probe (SPEC-027 §Eventos)', () => {
  it('carrega câmera e orientação para o contrato', () => {
    const data = toCapabilityData(medidaOk, {
      facing: 'environment',
      orientation: 'landscape_forced',
    })

    expect(data.facing).toBe('environment')
    expect(data.orientation).toBe('landscape_forced')
  })

  // Vazio é uma RESPOSTA — "esta origem não sabia dizer" — e é diferente de qualquer um dos
  // valores possíveis. É o que separa, no corpus, sessão antiga de sessão que escolheu frontal.
  it('sem enquadramento, os campos sobem vazios em vez de sumirem', () => {
    const data = toCapabilityData(medidaOk)

    expect(data.facing).toBe('')
    expect(data.orientation).toBe('')
  })

  it('origem em ARQUIVO não carimba procedência nenhuma', () => {
    // A superfície de dev (T-040) roda sobre vídeo gravado: não há câmera nem aparelho na mão,
    // e escrever `user`/`portrait` ali inventaria procedência para o dataset — que é
    // justamente o que este campo existe para evitar.
    expect(enquadramentoDe('file', 'user', 'portrait')).toBeUndefined()
    expect(toCapabilityData(medidaOk, enquadramentoDe('file', 'user', 'portrait')).facing).toBe('')
  })

  it('origem em câmera carimba o que os dois controles disseram', () => {
    expect(enquadramentoDe('camera', 'user', 'portrait')).toEqual({
      facing: 'user',
      orientation: 'portrait',
    })
  })
})
