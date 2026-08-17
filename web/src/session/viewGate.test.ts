import { afterEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import {
  dismissViewGate,
  restoreViewGate,
  shouldConfirmView,
  viewGateDismissed,
} from './viewGate'

afterEach(uninstallStorage)

describe('trava de confirmação da variação (T-112)', () => {
  it('exercício sem variação nunca vê a trava', () => {
    installStorage()

    // Não há duas montagens de cena para confundir: interromper aqui seria um obstáculo sem
    // conteúdo, e é assim que uma trava útil vira praga.
    expect(shouldConfirmView('jumping_jack')).toBe(false)
    expect(shouldConfirmView('squat')).toBe(false)
  })

  it('exercício com variação vê a trava na primeira vez', () => {
    installStorage()

    expect(shouldConfirmView('flexao')).toBe(true)
  })

  it('depois de confirmar, não pergunta de novo NESTA visita', () => {
    installStorage()

    // É o que separa "trava" de "interrogatório": a caixa intercepta o "Ligar câmera", e o
    // "Iniciar Exercício" que vem logo depois passa direto.
    expect(shouldConfirmView('flexao', { confirmadoPara: 'flexao' })).toBe(false)
    // Mas confirmar um exercício não confirma outro.
    expect(shouldConfirmView('flexao', { confirmadoPara: 'abdominal' })).toBe(true)
  })

  it('quem marca "não mostrar novamente" não vê mais — e só naquele exercício', () => {
    installStorage()

    dismissViewGate('flexao')

    expect(viewGateDismissed('flexao')).toBe(true)
    expect(shouldConfirmView('flexao')).toBe(false)
    // A dispensa é por exercício de propósito: no dia em que outro ganhar vistas, ele terá uma
    // decisão de cena própria para ensinar, e herdar o "já sei" da flexão devolveria a sessão
    // zerada que a trava existe para impedir.
    expect(viewGateDismissed('abdominal')).toBe(false)
  })

  it('a dispensa sobrevive à próxima visita — é a promessa do checkbox', () => {
    const fake = installStorage()

    dismissViewGate('flexao')

    expect(fake.store.get('digitalfit.view_gate_off.flexao')).toBe('1')
  })

  it('dá para desfazer a dispensa', () => {
    installStorage()
    dismissViewGate('flexao')

    restoreViewGate('flexao')

    expect(shouldConfirmView('flexao')).toBe(true)
  })

  it('sem armazenamento a trava APARECE, e é o lado certo do erro', () => {
    // O custo de perguntar de novo é um toque. O custo de não perguntar é a sessão inteira
    // zerada e a pessoa concluindo que o app não funciona.
    installStorage({ readOnly: true })

    expect(() => dismissViewGate('flexao')).not.toThrow()
    expect(shouldConfirmView('flexao')).toBe(true)
  })
})
