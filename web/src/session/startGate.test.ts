import { describe, expect, it } from 'vitest'
import { ctaDeInicio } from './startGate'
import type { CameraStatus } from '../store/session'

describe('ctaDeInicio', () => {
  it('só deixa iniciar o exercício com a câmera ligada', () => {
    // O critério inteiro desta regra: `iniciar` — a ação que navega para o treino — existe
    // num estado só. Nos outros o CTA é o interruptor da câmera, nunca a porta do treino.
    const semCamera: CameraStatus[] = ['idle', 'requesting', 'denied', 'error']
    for (const cameraStatus of semCamera) {
      expect(ctaDeInicio(cameraStatus).action).not.toBe('iniciar')
    }
    expect(ctaDeInicio('ready').action).toBe('iniciar')
  })

  it('com a câmera desligada o CTA é o de ligar, e diz isso', () => {
    expect(ctaDeInicio('idle')).toEqual({ action: 'ligar', label: 'Ligar câmera', disabled: false })
  })

  it('trava só enquanto o navegador decide a permissão', () => {
    expect(ctaDeInicio('requesting')).toEqual({
      action: 'aguardar',
      label: 'Abrindo câmera…',
      disabled: true,
    })
    const clicaveis: CameraStatus[] = ['idle', 'ready', 'denied', 'error']
    for (const cameraStatus of clicaveis) {
      expect(ctaDeInicio(cameraStatus).disabled).toBe(false)
    }
  })

  it('permissão negada e erro seguem clicáveis: o motivo está na capa, a saída é tentar de novo', () => {
    for (const cameraStatus of ['denied', 'error'] as CameraStatus[]) {
      expect(ctaDeInicio(cameraStatus)).toEqual(ctaDeInicio('idle'))
    }
  })
})
