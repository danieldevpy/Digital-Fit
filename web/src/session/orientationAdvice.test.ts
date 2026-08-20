import { describe, expect, it } from 'vitest'

import { isOrientacaoRecomendada, orientationAdvice, recomendacaoDe } from './orientationAdvice'

describe('quando o app sugere virar o celular (SPEC-027 §E)', () => {
  it('exercício de chão com o aparelho em pé: sugere deitar', () => {
    expect(orientationAdvice('paisagem', 'portrait')).toBe('paisagem')
  })

  it('exercício em pé com o aparelho deitado: sugere levantar', () => {
    expect(orientationAdvice('retrato', 'landscape')).toBe('retrato')
  })

  // Os dois silêncios importam tanto quanto os dois conselhos: conselho que aparece quando não
  // há o que mudar é exatamente o que ensina alguém a ignorar conselho.
  it('cala quando o aparelho já está como o exercício pede', () => {
    expect(orientationAdvice('paisagem', 'landscape')).toBeNull()
    expect(orientationAdvice('retrato', 'portrait')).toBeNull()
  })

  it('cala quando o exercício não tem preferência', () => {
    expect(orientationAdvice('qualquer', 'portrait')).toBeNull()
    expect(orientationAdvice('qualquer', 'landscape')).toBeNull()
  })
})

describe('o vocabulário vindo do servidor', () => {
  it('aceita os três valores do contrato', () => {
    expect(recomendacaoDe('retrato')).toBe('retrato')
    expect(recomendacaoDe('paisagem')).toBe('paisagem')
    expect(recomendacaoDe('qualquer')).toBe('qualquer')
  })

  // Mesmo tratamento de `main_angle`: contrato fechado no cliente, `CharField` aberto no
  // servidor. Um cliente antigo não pode dar conselho sobre vocabulário que não conhece — e
  // `qualquer` é o único default que produz silêncio em vez de palpite.
  it('valor que este bundle não conhece vira `qualquer`, não vira conselho', () => {
    expect(recomendacaoDe('diagonal')).toBe('qualquer')
    expect(recomendacaoDe(undefined)).toBe('qualquer')
    expect(recomendacaoDe(null)).toBe('qualquer')
    expect(orientationAdvice(recomendacaoDe('diagonal'), 'portrait')).toBeNull()
  })

  it('a guarda de tipo não deixa passar o que não é do vocabulário', () => {
    expect(isOrientacaoRecomendada('retrato')).toBe(true)
    expect(isOrientacaoRecomendada('landscape')).toBe(false)
  })
})
