import { afterEach, describe, expect, it } from 'vitest'

import {
  clearTokens,
  deviceId,
  identityHeaders,
  rememberDeviceId,
  storeTokens,
  storedTokens,
} from './storage'
import { installStorage, uninstallStorage } from './testStorage'

afterEach(uninstallStorage)

describe('id do aparelho', () => {
  it('guarda o id que o servidor mandou', () => {
    installStorage()
    rememberDeviceId('dev-abc12345')
    expect(deviceId()).toBe('dev-abc12345')
  })

  it('sem id ainda, não inventa nenhum — quem gera é o servidor', () => {
    installStorage()
    expect(deviceId()).toBeNull()
  })

  it('resposta sem device_id não apaga o que já estava guardado', () => {
    installStorage()
    rememberDeviceId('dev-abc12345')
    rememberDeviceId(undefined)
    rememberDeviceId(null)
    expect(deviceId()).toBe('dev-abc12345')
  })
})

describe('tokens', () => {
  it('grava e lê o par', () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    expect(storedTokens()).toEqual({ access: 'a.1', refresh: 'r.1' })
  })

  it('renovar troca só o access — o refresh continua o mesmo', () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    storeTokens({ access: 'a.2' })
    expect(storedTokens()).toEqual({ access: 'a.2', refresh: 'r.1' })
  })

  it('sair apaga os dois', () => {
    installStorage()
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    clearTokens()
    expect(storedTokens()).toEqual({ access: undefined, refresh: undefined })
  })

  it('sair não apaga o aparelho: quem saiu volta a ser o mesmo visitante', () => {
    installStorage()
    rememberDeviceId('dev-abc12345')
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    clearTokens()
    expect(deviceId()).toBe('dev-abc12345')
  })
})

describe('identityHeaders', () => {
  it('visitante manda só o aparelho', () => {
    installStorage()
    rememberDeviceId('dev-abc12345')
    expect(identityHeaders()).toEqual({ 'X-Device-Id': 'dev-abc12345' })
  })

  it('logado manda os dois — quem decide qual vale é o servidor', () => {
    installStorage()
    rememberDeviceId('dev-abc12345')
    storeTokens({ access: 'a.1', refresh: 'r.1' })
    expect(identityHeaders()).toEqual({
      'X-Device-Id': 'dev-abc12345',
      Authorization: 'Bearer a.1',
    })
  })

  it('primeira visita não manda cabeçalho nenhum', () => {
    installStorage()
    expect(identityHeaders()).toEqual({})
  })
})

describe('armazenamento indisponível', () => {
  it('gravar em Safari privado não derruba a chamada', () => {
    installStorage({ readOnly: true })
    expect(() => rememberDeviceId('dev-abc12345')).not.toThrow()
    expect(() => storeTokens({ access: 'a.1', refresh: 'r.1' })).not.toThrow()
    // Não guardou nada, e é isso mesmo: o visitante vira um aparelho novo a cada visita e
    // nunca esbarra no trial. A spec já assume que o funil é burlável.
    expect(identityHeaders()).toEqual({})
  })

  it('sem `window` nenhum (SSR/teste) as leituras respondem vazio', () => {
    uninstallStorage()
    expect(deviceId()).toBeNull()
    expect(identityHeaders()).toEqual({})
  })
})
