import { afterEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import { facingPreference, setFacingPreference } from './cameraPrefs'
import {
  FACING_DEFAULT,
  facingConstraint,
  facingFromSettings,
  hasCameraChoice,
  isFacing,
  mirrorDefaultFor,
  otherFacing,
} from './facing'

afterEach(uninstallStorage)

describe('espelho é consequência da câmera (SPEC-027 §B)', () => {
  it('frontal abre espelhada; traseira abre sem espelho', () => {
    expect(mirrorDefaultFor('user')).toBe(true)
    expect(mirrorDefaultFor('environment')).toBe(false)
  })
})

describe('a restrição pedida (SPEC-027 §A)', () => {
  // O núcleo do critério 3: com `ideal`, o aparelho sem traseira devolve a frontal em
  // SILÊNCIO — não há erro para capturar e o botão passaria a mentir. É `exact` que produz o
  // `OverconstrainedError` do qual o fallback honesto depende.
  it('trocar pede `exact` — é o único jeito de descobrir que a câmera não existe', () => {
    expect(facingConstraint('environment', 'exact')).toEqual({
      facingMode: { exact: 'environment' },
    })
  })

  it('abrir pede `ideal` — aqui não há nada a descobrir, e falhar seria tela preta', () => {
    expect(facingConstraint('user', 'ideal')).toEqual({ facingMode: { ideal: 'user' } })
  })
})

describe('quem manda no rótulo é o track, não o pedido (SPEC-027 §A)', () => {
  it('o valor relatado vence o pedido', () => {
    expect(facingFromSettings({ facingMode: 'environment' }, 'user')).toBe('environment')
  })

  // Aparelho que aceita a restrição e entrega outra coisa existe. Sem esta linha o botão
  // diria "traseira" sobre imagem frontal — exatamente o que a regra de honestidade proíbe.
  it('aparelho que ignorou a restrição não deixa o rótulo errado na tela', () => {
    expect(facingFromSettings({ facingMode: 'user' }, 'environment')).toBe('user')
  })

  it('navegador que não relata `facingMode` cai no pedido, que é o melhor que se sabe', () => {
    expect(facingFromSettings({}, 'environment')).toBe('environment')
    expect(facingFromSettings(undefined, 'user')).toBe('user')
  })

  it('valor estranho não vira `Facing` por descuido', () => {
    expect(facingFromSettings({ facingMode: 'left' }, 'user')).toBe('user')
    expect(isFacing('left')).toBe(false)
    expect(isFacing(null)).toBe(false)
  })
})

// Critério 2 da SPEC-027, nas duas contagens.
describe('o controle só existe onde há escolha (SPEC-027 §A)', () => {
  it('uma câmera só: não há escolha a oferecer', () => {
    expect(hasCameraChoice([{ kind: 'videoinput' }])).toBe(false)
  })

  it('duas câmeras: há', () => {
    expect(hasCameraChoice([{ kind: 'videoinput' }, { kind: 'videoinput' }])).toBe(true)
  })

  it('microfone não é câmera — só `videoinput` conta', () => {
    expect(
      hasCameraChoice([
        { kind: 'videoinput' },
        { kind: 'audioinput' },
        { kind: 'audiooutput' },
      ]),
    ).toBe(false)
  })

  // iPhone lista as lentes da traseira como entradas separadas. A pergunta do controle é
  // "há mais de uma?", e a resposta continua sendo sim — qual delas ninguém escolhe.
  it('lista longa de lentes continua sendo "há escolha"', () => {
    expect(
      hasCameraChoice([
        { kind: 'videoinput' },
        { kind: 'videoinput' },
        { kind: 'videoinput' },
        { kind: 'videoinput' },
      ]),
    ).toBe(true)
  })

  it('lista vazia (navegador sem suporte) esconde o controle', () => {
    expect(hasCameraChoice([])).toBe(false)
  })
})

describe('preferência lembrada (SPEC-027 §A)', () => {
  // Segunda metade do critério 1: recarregar a página abre direto na câmera escolhida.
  it('guarda a intenção e devolve na próxima carga', () => {
    installStorage()
    setFacingPreference('environment')
    expect(facingPreference()).toBe('environment')
  })

  it('quem nunca escolheu abre no default do produto', () => {
    installStorage()
    expect(facingPreference()).toBe(FACING_DEFAULT)
    expect(FACING_DEFAULT).toBe('user')
  })

  it('lixo no armazenamento não vira câmera', () => {
    const fake = installStorage()
    fake.store.set('digitalfit.camera_facing', 'traseira')
    expect(facingPreference()).toBe(FACING_DEFAULT)
  })

  it('sem `window` (SSR/pré-render) não explode', () => {
    expect(facingPreference()).toBe(FACING_DEFAULT)
    expect(setFacingPreference('environment')).toBe('environment')
  })

  it('armazenamento recusado (Safari privado) vale pela sessão atual', () => {
    installStorage({ readOnly: true })
    expect(setFacingPreference('environment')).toBe('environment')
    expect(facingPreference()).toBe(FACING_DEFAULT)
  })
})

describe('otherFacing', () => {
  it('alterna nos dois sentidos', () => {
    expect(otherFacing('user')).toBe('environment')
    expect(otherFacing('environment')).toBe('user')
  })
})
