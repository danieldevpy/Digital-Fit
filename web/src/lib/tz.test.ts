// O fuso do aparelho no cliente (T-156).
import { describe, expect, it } from 'vitest'

import { deviceTimeZone, timezoneHeaders } from './tz'

describe('deviceTimeZone', () => {
  it('devolve o nome IANA do aparelho — a mesma fonte que o fogo fantasma usa', () => {
    // Não dá para afirmar QUAL é (depende da máquina que roda a suíte), e afirmar seria repetir
    // o erro que a T-156 conserta: um teste que só passa em quem mora no Brasil. O que se cobra
    // é a forma — `Região/Cidade` — e a coerência com o `Intl`, que é de onde o servidor vai
    // receber a resposta.
    const fuso = deviceTimeZone()
    expect(fuso).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone)
    expect(fuso).toMatch(/^[A-Za-z]+\/[A-Za-z_+\-/0-9]+$|^UTC$/)
  })
})

describe('timezoneHeaders', () => {
  it('manda o fuso no cabeçalho que o servidor lê', () => {
    expect(timezoneHeaders()).toEqual({ 'X-Timezone': deviceTimeZone() })
  })

  it('sem fuso conhecido não manda cabeçalho nenhum', () => {
    // Ambiente sem `Intl` capaz. Vazio é ausência, e ausência é o que faz o servidor cair no
    // padrão — mandar `X-Timezone: ` vazio só o faria gastar uma normalização para o mesmo fim.
    const original = Intl.DateTimeFormat
    try {
      // @ts-expect-error — substituindo o global de propósito, para simular o ambiente capado.
      Intl.DateTimeFormat = () => {
        throw new Error('sem Intl')
      }
      expect(timezoneHeaders()).toEqual({})
    } finally {
      Intl.DateTimeFormat = original
    }
  })
})
