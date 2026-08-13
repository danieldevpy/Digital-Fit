import { describe, expect, it } from 'vitest'

import { devToolsAllowed, recordModeAllowed } from './gate'

const VISITANTE = { isDevBuild: false, isAdmin: false, search: '' }

describe('quem vê as ferramentas de dev', () => {
  it('o usuário comum não vê — nem em produção, nem nunca', () => {
    expect(devToolsAllowed(VISITANTE)).toBe(false)
  })

  it('build de desenvolvimento vê sem precisar de conta', () => {
    expect(devToolsAllowed({ ...VISITANTE, isDevBuild: true })).toBe(true)
  })

  it('conta com is_admin vê em produção — é para isso que a flag existe', () => {
    expect(devToolsAllowed({ ...VISITANTE, isAdmin: true })).toBe(true)
  })
})

describe('o ?dev= modifica, nunca concede', () => {
  it('`?dev=1` não promove ninguém — senão o gate seria decoração', () => {
    expect(devToolsAllowed({ ...VISITANTE, search: '?dev=1' })).toBe(false)
  })

  it('nem combinado com outros parâmetros', () => {
    expect(devToolsAllowed({ ...VISITANTE, search: '?mode=cloud&dev=true' })).toBe(false)
  })

  it('`?dev=0` deixa o admin ver a tela como o usuário comum a vê', () => {
    expect(devToolsAllowed({ isDevBuild: false, isAdmin: true, search: '?dev=0' })).toBe(false)
  })

  it('e desliga até no build de dev', () => {
    expect(devToolsAllowed({ isDevBuild: true, isAdmin: false, search: '?dev=0' })).toBe(false)
  })

  it('`?dev=1` do admin é redundante, mas não atrapalha', () => {
    expect(devToolsAllowed({ isDevBuild: false, isAdmin: true, search: '?dev=1' })).toBe(true)
  })

  it('sem o parâmetro, quem decide são as duas fontes de direito', () => {
    expect(devToolsAllowed({ isDevBuild: false, isAdmin: true, search: '?mode=edge' })).toBe(true)
    expect(devToolsAllowed({ ...VISITANTE, search: '?mode=edge' })).toBe(false)
  })
})

describe('modo gravação (?record=1)', () => {
  const ADMIN = { isDevBuild: false, isAdmin: true, search: '' }

  it('o admin ganha a origem em arquivo', () => {
    expect(recordModeAllowed({ ...ADMIN, search: '?record=1' })).toBe(true)
  })

  it('e perde o diagnóstico junto — é o ponto do modo', () => {
    expect(devToolsAllowed({ ...ADMIN, search: '?record=1' })).toBe(false)
  })

  it('o build de dev também grava, sem precisar de conta', () => {
    expect(recordModeAllowed({ isDevBuild: true, isAdmin: false, search: '?record=1' })).toBe(true)
    expect(devToolsAllowed({ isDevBuild: true, isAdmin: false, search: '?record=1' })).toBe(false)
  })

  it('não promove ninguém: `?record=1` sem direito é inerte', () => {
    expect(recordModeAllowed({ ...VISITANTE, search: '?record=1' })).toBe(false)
    expect(devToolsAllowed({ ...VISITANTE, search: '?record=1' })).toBe(false)
  })

  it('sem o parâmetro não liga sozinho, nem para o admin', () => {
    expect(recordModeAllowed(ADMIN)).toBe(false)
    expect(recordModeAllowed({ ...ADMIN, search: '?mode=edge' })).toBe(false)
  })

  it('`?record=0` é a ausência do modo', () => {
    expect(recordModeAllowed({ ...ADMIN, search: '?record=0' })).toBe(false)
    expect(devToolsAllowed({ ...ADMIN, search: '?record=0' })).toBe(true)
  })

  it('`?dev=0` continua sendo o desligador geral — nem o botão de arquivo sobra', () => {
    expect(recordModeAllowed({ ...ADMIN, search: '?record=1&dev=0' })).toBe(false)
  })

  it('nunca os dois ao mesmo tempo: gravando, a tela é a do usuário comum', () => {
    for (const search of ['?record=1', '?record=1&dev=1', '?record=true&mode=cloud']) {
      expect(devToolsAllowed({ ...ADMIN, search })).toBe(false)
      expect(recordModeAllowed({ ...ADMIN, search })).toBe(true)
    }
  })
})
