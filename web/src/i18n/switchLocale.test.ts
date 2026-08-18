// A troca de idioma em runtime (T-153, SPEC-025 critério de aceite 2).
//
// O critério é explícito sobre o que é fácil errar: "trocar o idioma nas configurações muda a
// tela **e** o que vem do servidor na mesma ação, sem recarregar e sem esperar cache expirar".
// A metade "muda a tela" é o store, e ela é trivial. A metade cara é a segunda — e é ela que
// estes testes protegem, porque falha em silêncio: a tela troca, a pessoa vê inglês, e o
// catálogo continua em português por horas sem ninguém entender por quê.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import { useAccountStore } from '../store/account'
import { useConfigStore } from '../store/config'
import { useI18nStore } from './store'
import { switchLocale } from './switchLocale'

/** Uma conta qualquer: sem usuário o `refreshEngagement` sai antes de tocar a rede. */
function entrar(): void {
  useAccountStore.getState().setUser({
    id: 1,
    email: 'a@b.com',
    name: 'Ana',
    is_admin: false,
    daily_goal: 'casual',
    date_joined: '2026-01-01T00:00:00Z',
  })
}

interface Chamada {
  url: string
  aceita: string | null
}

function espiarFetch(): Chamada[] {
  const chamadas: Chamada[] = []
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (entrada, init) => {
    const headers = new Headers(init?.headers)
    chamadas.push({ url: String(entrada), aceita: headers.get('Accept-Language') })
    // 500 de propósito: a troca de idioma NÃO pode depender de a rede responder bem.
    return new Response('', { status: 500 })
  })
  return chamadas
}

beforeEach(() => {
  installStorage()
  useI18nStore.getState().setLocale('pt-BR')
  useConfigStore.getState().reset()
})

afterEach(() => {
  useAccountStore.getState().reset()
  useI18nStore.getState().setLocale('pt-BR')
  uninstallStorage()
  vi.restoreAllMocks()
})

describe('switchLocale', () => {
  it('troca o store e persiste no aparelho, sem recarregar nada', () => {
    espiarFetch()
    switchLocale('en')

    expect(useI18nStore.getState().locale).toBe('en')
    expect(window.localStorage.getItem('digitalfit.locale')).toBe('en')
  })

  it('revalida as DUAS rotas que guardam texto do servidor, com o idioma novo no header', async () => {
    // As duas da SPEC-025 §Notas técnicas: o `config` porque o ETag inclui o locale (e o
    // `If-None-Match` guardado é o da língua velha), e o `engagement` porque o cache é por
    // `(usuário, dia, locale)` e traz nome de conquista já renderizado.
    entrar()
    const chamadas = espiarFetch()

    switchLocale('en')
    // As duas chamadas são disparadas sem `await` de propósito (a tela não espera a rede) —
    // um tick basta para elas saírem.
    await Promise.resolve()
    await Promise.resolve()

    const urls = chamadas.map((c) => c.url)
    expect(urls.some((u) => u.includes('/api/config'))).toBe(true)
    expect(urls.some((u) => u.includes('/api/engagement'))).toBe(true)
    // O header é o coração da T-153: sem ele o servidor responderia na língua do NAVEGADOR,
    // e revalidar não adiantaria nada.
    expect(chamadas.every((c) => c.aceita === 'en')).toBe(true)
  })

  it('rede fora não desfaz a troca — idioma não é operação que possa falhar na cara de quem trocou', async () => {
    entrar()
    espiarFetch() // devolve 500 nas duas
    switchLocale('en')
    await Promise.resolve()
    await Promise.resolve()

    expect(useI18nStore.getState().locale).toBe('en')
  })

  it('escolher o idioma que já está ativo não gasta rede', async () => {
    entrar()
    const chamadas = espiarFetch()

    switchLocale('pt-BR')
    await Promise.resolve()

    expect(chamadas).toEqual([])
  })
})
