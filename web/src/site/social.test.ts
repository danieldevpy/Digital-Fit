import { describe, expect, it } from 'vitest'

import { jsonLd, tagsSociais, type DadosDaPagina } from './social'

const BASE: DadosDaPagina = {
  origem: 'https://exemplo.com.br',
  screen: 'sobre',
  locale: 'pt-BR',
  titulo: 'Sobre o Digital Fit',
  descricao: 'O que o Digital Fit é.',
  imagemAlt: 'Marca do Digital Fit',
}

describe('tagsSociais (T-164, SPEC-026)', () => {
  it('`og:locale` usa idioma_TERRITÓRIO, não a tag do `<html lang>`', () => {
    // `pt-BR` não é `og:locale` válido — o formato quer `pt_BR`. Substituir `-` por `_` daria
    // certo aqui e erraria em `en`, que não tem território na tag e precisa de `en_US`.
    expect(tagsSociais(BASE)).toContain('property="og:locale" content="pt_BR"')
    expect(tagsSociais({ ...BASE, locale: 'en' })).toContain('property="og:locale" content="en_US"')
  })

  it('declara as outras línguas em que a página existe, e não a si mesma', () => {
    const pt = tagsSociais(BASE)

    expect(pt).toContain('property="og:locale:alternate" content="en_US"')
    expect(pt.match(/og:locale:alternate/g)).toHaveLength(1)
    expect(pt).not.toContain('property="og:locale:alternate" content="pt_BR"')
  })

  it('`og:url` e `og:image` são absolutos — preview de link não resolve relativo', () => {
    const tags = tagsSociais(BASE)

    expect(tags).toContain('property="og:url" content="https://exemplo.com.br/sobre/"')
    expect(tags).toContain('property="og:image" content="https://exemplo.com.br/img/og.jpg"')
    for (const [, url] of tags.matchAll(/content="((?:https?:)?\/\/?[^"]*)"/g)) {
      expect(url).toMatch(/^https:\/\//)
    }
  })

  it('o card é o grande — a arte é 1200×630 e o pequeno a cortaria', () => {
    expect(tagsSociais(BASE)).toContain('name="twitter:card" content="summary_large_image"')
  })

  it('escapa aspas do título — senão o atributo fecha cedo e a tag vira lixo', () => {
    const tags = tagsSociais({ ...BASE, titulo: 'A "melhor" forma' })

    expect(tags).toContain('content="A &quot;melhor&quot; forma"')
  })
})

describe('jsonLd', () => {
  const bruto = jsonLd(BASE)
  const grafo = JSON.parse(
    bruto.replace(/^\s*<script[^>]*>/, '').replace(/<\/script>\s*$/, '').replace(/\\u003c/g, '<'),
  )

  it('é JSON válido dentro de um `<script type="application/ld+json">`', () => {
    expect(bruto).toContain('application/ld+json')
    expect(grafo['@context']).toBe('https://schema.org')
    expect(grafo['@graph'].map((n: { '@type': string }) => n['@type'])).toEqual([
      'SoftwareApplication',
      'Organization',
    ])
  })

  it('NÃO inventa nota, preço nem download — a regra do `--` da SPEC-014, com agravante', () => {
    // Dado estruturado inventado não é só desonesto: é violação de política do Google e
    // derruba o rich result inteiro, não só o campo mentiroso. Este caso existe para o dia em
    // que alguém quiser "melhorar o resultado de busca".
    for (const proibido of ['aggregateRating', 'ratingValue', 'offers', 'price', 'review']) {
      expect(bruto).not.toContain(proibido)
    }
  })

  it('escapa `<` — um `</script>` no texto fecharia o bloco e o resto viraria HTML', () => {
    const comTag = jsonLd({ ...BASE, descricao: 'texto </script> perigoso' })

    expect(comTag).not.toContain('</script> perigoso')
    expect(comTag).toContain('\\u003c/script>')
  })

  it('a organização é a mesma entidade em todas as páginas, por `@id`', () => {
    // Sem `@id` estável, cada página declararia uma Organization diferente e o Google trataria
    // como entidades distintas.
    const daHome = JSON.parse(
      jsonLd({ ...BASE, screen: 'index' })
        .replace(/^\s*<script[^>]*>/, '')
        .replace(/<\/script>\s*$/, '')
        .replace(/\\u003c/g, '<'),
    )

    expect(daHome['@graph'][1]['@id']).toBe(grafo['@graph'][1]['@id'])
  })
})
