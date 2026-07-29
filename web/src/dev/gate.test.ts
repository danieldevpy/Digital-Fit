import { describe, expect, it } from 'vitest'

import { devToolsAllowed } from './gate'

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
