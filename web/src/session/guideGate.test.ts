// A regra de quando o exemplo abre sozinho e quando o link se destaca (`guideGate.ts`).
import { afterEach, describe, expect, it } from 'vitest'
import { installStorage, uninstallStorage } from '../auth/testStorage'
import { estadoDoExemplo, temConta } from './guideGate'

afterEach(uninstallStorage)

describe('estadoDoExemplo', () => {
  it('sem conta o exemplo abre — mesmo que a pessoa já o tenha visto', () => {
    // O coração da mudança: "já viu uma vez" deixou de ser a pergunta. Enquadramento é
    // instrução, e quem não tem conta recebe a instrução toda vez que troca de exercício.
    expect(estadoDoExemplo({ temConta: false, jaViu: true }).abrirAgora).toBe(true)
    expect(estadoDoExemplo({ temConta: false, jaViu: false }).abrirAgora).toBe(true)
  })

  it('com conta o exemplo NUNCA abre sozinho', () => {
    expect(estadoDoExemplo({ temConta: true, jaViu: false }).abrirAgora).toBe(false)
    expect(estadoDoExemplo({ temConta: true, jaViu: true }).abrirAgora).toBe(false)
  })

  it('o link se destaca só para quem tem conta e ainda não viu aquele exercício', () => {
    expect(estadoDoExemplo({ temConta: true, jaViu: false }).destacarLink).toBe(true)
    expect(estadoDoExemplo({ temConta: true, jaViu: true }).destacarLink).toBe(false)
  })

  it('quem não tem conta nunca recebe o destaque — acabou de ver o exemplo inteiro', () => {
    expect(estadoDoExemplo({ temConta: false, jaViu: false }).destacarLink).toBe(false)
    expect(estadoDoExemplo({ temConta: false, jaViu: true }).destacarLink).toBe(false)
  })

  it('o absurdo não é representável: abrir sozinho E pedir que abram, nunca juntos', () => {
    for (const temConta of [true, false]) {
      for (const jaViu of [true, false]) {
        const estado = estadoDoExemplo({ temConta, jaViu })
        expect(estado.abrirAgora && estado.destacarLink).toBe(false)
      }
    }
  })
})

describe('temConta', () => {
  it('status resolvido manda, e não olha o armazenamento', () => {
    installStorage()
    expect(temConta('authenticated')).toBe(true)
    expect(temConta('anonymous')).toBe(false)
  })

  it('status resolvido como anônimo vence um refresh esquecido no aparelho', () => {
    // O `logout` limpa os tokens, mas a ordem importa: quem já sabe que é anônimo não pode
    // ser "promovido" por um resto de armazenamento.
    const fake = installStorage()
    fake.store.set('digitalfit.refresh', 'sobra')
    expect(temConta('anonymous')).toBe(false)
  })

  it('antes do fetchMe, o refresh guardado responde a tempo', () => {
    // O caso apertado: a ponte `#/ex/<slug>` do site chama o funil num efeito de boot, com o
    // status ainda `unknown`. Sem este atalho, quem tem conta levaria o exemplo na cara.
    const fake = installStorage()
    fake.store.set('digitalfit.refresh', 'um-refresh')
    expect(temConta('unknown')).toBe(true)
  })

  it('sem refresh guardado, `unknown` é tratado como sem conta', () => {
    installStorage()
    expect(temConta('unknown')).toBe(false)
  })

  it('sem armazenamento nenhum (Safari privado) não explode e trata como sem conta', () => {
    // Sem `window` instalado — o `ler` do storage.ts cai no catch.
    expect(() => temConta('unknown')).not.toThrow()
    expect(temConta('unknown')).toBe(false)
  })
})
