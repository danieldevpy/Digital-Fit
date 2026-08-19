import { describe, expect, it } from 'vitest'

import { LOCALES } from '../i18n/locale'
import { exigirOrigem, linksDeCabecalho, urlAbsoluta } from './metatags'
import { ROTAS_INDEXAVEIS } from './routes'

const ORIGEM = 'https://exemplo.com.br'

describe('urlAbsoluta', () => {
  it('monta a URL de cada tela em cada idioma', () => {
    expect(urlAbsoluta(ORIGEM, 'index', 'pt-BR')).toBe('https://exemplo.com.br/')
    expect(urlAbsoluta(ORIGEM, 'index', 'en')).toBe('https://exemplo.com.br/en/')
    expect(urlAbsoluta(ORIGEM, 'sobre', 'pt-BR')).toBe('https://exemplo.com.br/sobre/')
    expect(urlAbsoluta(ORIGEM, 'sobre', 'en')).toBe('https://exemplo.com.br/en/about/')
  })
})

describe('linksDeCabecalho (T-160, SPEC-026 — camada "Achar")', () => {
  it('todo href é ABSOLUTO — é o bug da T-147, e é o motivo desta task existir', () => {
    // `href="/"` e `href="/en/"` são ignorados em silêncio pelo Google. Este caso é o portão:
    // qualquer href que não comece com o esquema reprova aqui, no dia em que for escrito.
    for (const rota of ROTAS_INDEXAVEIS) {
      for (const locale of LOCALES) {
        const hrefs = [...linksDeCabecalho(ORIGEM, rota.screen, locale).matchAll(/href="([^"]*)"/g)]

        expect(hrefs.length).toBeGreaterThan(0)
        for (const [, href] of hrefs) expect(href).toMatch(/^https:\/\//)
      }
    }
  })

  it('o par é recíproco, e cada idioma aponta para si mesmo também', () => {
    // Auto-referência é exigência do formato e o erro mais comum de quem escreve à mão.
    const doPt = linksDeCabecalho(ORIGEM, 'sobre', 'pt-BR')
    const doEn = linksDeCabecalho(ORIGEM, 'sobre', 'en')

    for (const bloco of [doPt, doEn]) {
      expect(bloco).toContain('hreflang="pt-BR" href="https://exemplo.com.br/sobre/"')
      expect(bloco).toContain('hreflang="en" href="https://exemplo.com.br/en/about/"')
    }
  })

  it('o `canonical` é a própria URL, e muda com o idioma da página', () => {
    expect(linksDeCabecalho(ORIGEM, 'sobre', 'pt-BR')).toContain(
      '<link rel="canonical" href="https://exemplo.com.br/sobre/" />',
    )
    expect(linksDeCabecalho(ORIGEM, 'sobre', 'en')).toContain(
      '<link rel="canonical" href="https://exemplo.com.br/en/about/" />',
    )
  })

  it('o `x-default` aponta para o inglês — a resposta para "não sei quem é você"', () => {
    // É a pergunta que motivou a frente inteira: o estrangeiro que não fala nenhuma das duas.
    // O destino é o mesmo `DEFAULT_LOCALE` de `i18n/locale.ts`, e as duas pontas têm de
    // concordar — se alguém mudar uma, este caso cai.
    for (const locale of LOCALES) {
      expect(linksDeCabecalho(ORIGEM, 'index', locale)).toContain(
        '<link rel="alternate" hreflang="x-default" href="https://exemplo.com.br/en/" />',
      )
    }
  })
})

describe('exigirOrigem — exigir, não deduzir', () => {
  it('aceita origem absoluta e tira a barra final', () => {
    expect(exigirOrigem('https://exemplo.com.br')).toBe('https://exemplo.com.br')
    expect(exigirOrigem('https://exemplo.com.br/')).toBe('https://exemplo.com.br')
    expect(exigirOrigem('  https://exemplo.com.br//  ')).toBe('https://exemplo.com.br')
  })

  it.each([undefined, '', '/', 'exemplo.com.br', 'https://exemplo.com.br/site'])(
    'recusa %o com uma frase que diz o que fazer',
    (bruta) => {
      // A T-159 omitia as anotações em silêncio quando não sabia a origem. Silêncio é como o
      // `hreflang` da T-147 sobreviveu meses; aqui o build para e explica.
      expect(() => exigirOrigem(bruta)).toThrow(/VITE_SITE_ORIGIN/)
    },
  )
})
