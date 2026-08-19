import { describe, expect, it } from 'vitest'

import { LOCALES } from '../i18n/locale'
import { robotsTxt, sitemapXml } from './descoberta'
import { urlAbsoluta } from './metatags'
import { parseSitePath, ROTAS, ROTAS_INDEXAVEIS } from './routes'

const ORIGEM = 'https://exemplo.com.br'

describe('sitemapXml (T-163, SPEC-026 — a quarta saída da fonte única)', () => {
  const xml = sitemapXml(ORIGEM)

  it('tem uma entrada por rota indexável POR idioma — nem uma a mais, nem a menos', () => {
    const locs = [...xml.matchAll(/<loc>([^<]*)<\/loc>/g)].map(([, url]) => url)

    expect(locs).toHaveLength(ROTAS_INDEXAVEIS.length * LOCALES.length)
    expect(new Set(locs).size).toBe(locs.length)
  })

  it('lista exatamente as URLs que a tabela de rotas declara', () => {
    // O portão: rota nova aparece aqui sozinha, e rota removida some sozinha.
    for (const rota of ROTAS_INDEXAVEIS) {
      for (const locale of LOCALES) {
        expect(xml).toContain(`<loc>${urlAbsoluta(ORIGEM, rota.screen, locale)}</loc>`)
      }
    }
  })

  it('a 404 fica de fora — não é uma página, é a resposta para uma que não existe', () => {
    const naoIndexaveis = ROTAS.filter((rota) => !rota.indexavel)

    expect(naoIndexaveis.length).toBeGreaterThan(0)
    expect(xml).not.toContain('404')
  })

  it('cada URL carrega as alternativas de idioma e o x-default', () => {
    // A mesma informação do `hreflang` do `<head>` (T-160). O Google pede que as duas fontes
    // concordem — como as duas saem de `urlAbsoluta()`, não têm como divergir.
    const blocos = xml.split('<url>').slice(1)

    expect(blocos).toHaveLength(ROTAS_INDEXAVEIS.length * LOCALES.length)
    for (const bloco of blocos) {
      for (const locale of LOCALES) expect(bloco).toContain(`hreflang="${locale}"`)
      expect(bloco).toContain('hreflang="x-default"')
    }
  })

  it('todo href e todo loc são absolutos — o bug da T-147 não volta por esta porta', () => {
    for (const [, url] of xml.matchAll(/(?:<loc>|href=")([^<"]+)/g)) {
      expect(url).toMatch(/^https:\/\//)
    }
  })

  it('toda URL do mapa volta pelo ROTEADOR para a mesma tela e o mesmo idioma', () => {
    // O sentido que faltava (T-166). O caso acima cobra roteador → sitemap: toda rota da tabela
    // aparece no mapa. Este cobra a volta: toda URL do mapa é uma que o roteador sabe abrir.
    //
    // Um mapa e um roteador que discordam produzem o pior resultado possível da frente inteira —
    // o robô é convidado a entrar numa URL que o site responde com a 404 do `NotFoundScreen`, e
    // o Google trata URL prometida em sitemap que não existe como sinal de site abandonado. Não
    // é hipótese: o slug é traduzido por idioma (`sobre/` × `en/about/`), então renomear em um
    // lado só é uma edição de uma palavra.
    for (const [, achado] of xml.matchAll(/<loc>([^<]*)<\/loc>/g)) {
      const loc = achado!

      expect(loc.startsWith(`${ORIGEM}/`)).toBe(true)

      const { screen, locale } = parseSitePath(loc.slice(ORIGEM.length))

      expect(screen, `${loc} não é uma rota que o roteador conhece`).not.toBe('nao_encontrada')
      expect(urlAbsoluta(ORIGEM, screen, locale)).toBe(loc)
    }
  })

  it('não carimba `lastmod` — data que mente é pior que data ausente', () => {
    // Carimbar a data do build faria toda página parecer atualizada a cada deploy, inclusive
    // as que não mudaram; o Google trata `lastmod` não confiável como ruído e o ignora.
    expect(xml).not.toContain('lastmod')
  })
})

describe('robotsTxt', () => {
  const txt = robotsTxt(ORIGEM)

  it('libera o rastreamento e aponta o sitemap absoluto', () => {
    expect(txt).toContain('User-agent: *')
    expect(txt).toContain('Allow: /')
    expect(txt).toContain('Sitemap: https://exemplo.com.br/sitemap.xml')
  })

  it('NÃO bloqueia o /app/ — o `noindex` da página é quem o mantém fora do índice', () => {
    // Bloquear aqui impediria o rastreamento, o robô nunca leria o `noindex`, e a URL poderia
    // acabar listada assim mesmo por ser linkada do site. Este caso existe para impedir a
    // "correção" bem-intencionada de amanhã.
    //
    // Olha só as linhas de DIRETIVA: a palavra `Disallow` aparece no comentário do arquivo,
    // explicando por que ela não está lá — e um teste que não sabe distinguir diretiva de
    // comentário proibiria justamente a documentação da decisão.
    const diretivas = txt.split('\n').filter((linha) => linha.trim() && !linha.startsWith('#'))

    expect(diretivas.some((linha) => linha.startsWith('Disallow'))).toBe(false)
    expect(diretivas).toContain('User-agent: *')
  })
})
