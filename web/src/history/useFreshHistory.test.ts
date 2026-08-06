import { describe, expect, it } from 'vitest'

import { deveRevalidarAoMudarVisibilidade } from './useFreshHistory'

describe('gatilho de visibilidade', () => {
  it('a página voltando a ficar visível vale uma revalidação', () => {
    expect(deveRevalidarAoMudarVisibilidade(false)).toBe(true)
  })

  it('esconder não vale: seria rede gasta para atualizar o que ninguém está vendo', () => {
    expect(deveRevalidarAoMudarVisibilidade(true)).toBe(false)
  })
})
