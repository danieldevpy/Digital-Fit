import { describe, expect, it } from 'vitest'
import { pipelinePhase, podeAlimentarSessao } from './pipelineGate'
import type { PoseStatus, ProbeStatus } from '../store/session'

describe('podeAlimentarSessao', () => {
  it('não abre sessão enquanto o landmarker não está de pé', () => {
    // Este é O caso do bug de 2026-07-30: a câmera pronta não significa pipeline pronto, e
    // abrir a sessão aqui gastava o prazo de 10s do servidor baixando modelo.
    const carregando: PoseStatus[] = ['idle', 'loading']
    for (const poseStatus of carregando) {
      expect(podeAlimentarSessao({ poseStatus, probeStatus: 'idle' })).toBe(false)
      expect(podeAlimentarSessao({ poseStatus, probeStatus: 'done' })).toBe(false)
    }
  })

  it('não abre sessão enquanto o probe está medindo', () => {
    expect(podeAlimentarSessao({ poseStatus: 'ready', probeStatus: 'idle' })).toBe(false)
    expect(podeAlimentarSessao({ poseStatus: 'ready', probeStatus: 'running' })).toBe(false)
  })

  it('abre quando o probe decidiu', () => {
    expect(podeAlimentarSessao({ poseStatus: 'ready', probeStatus: 'done' })).toBe(true)
  })

  it('probe que falhou também é decisão: vira CLOUD e o laço sobe igual (SPEC-001)', () => {
    expect(podeAlimentarSessao({ poseStatus: 'ready', probeStatus: 'error' })).toBe(true)
  })

  it('pose que falhou nunca abre: sem landmarker não há frame para enviar', () => {
    const todos: ProbeStatus[] = ['idle', 'running', 'done', 'error']
    for (const probeStatus of todos) {
      expect(podeAlimentarSessao({ poseStatus: 'error', probeStatus })).toBe(false)
    }
  })
})

describe('pipelinePhase', () => {
  it('conta a história do aquecimento para a tela', () => {
    expect(pipelinePhase({ poseStatus: 'idle', probeStatus: 'idle' })).toBe('parado')
    expect(pipelinePhase({ poseStatus: 'loading', probeStatus: 'idle' })).toBe('carregando')
    expect(pipelinePhase({ poseStatus: 'ready', probeStatus: 'idle' })).toBe('carregando')
    expect(pipelinePhase({ poseStatus: 'ready', probeStatus: 'running' })).toBe('medindo')
    expect(pipelinePhase({ poseStatus: 'ready', probeStatus: 'done' })).toBe('pronto')
    expect(pipelinePhase({ poseStatus: 'ready', probeStatus: 'error' })).toBe('pronto')
    expect(pipelinePhase({ poseStatus: 'error', probeStatus: 'idle' })).toBe('falhou')
  })

  it('a falha da pose vence qualquer estado do probe — é ela que impede treinar', () => {
    expect(pipelinePhase({ poseStatus: 'error', probeStatus: 'done' })).toBe('falhou')
  })
})
