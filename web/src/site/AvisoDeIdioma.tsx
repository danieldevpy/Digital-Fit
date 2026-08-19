// O aviso que sugere a outra versão do site (T-161, SPEC-026 §Escopo — camada "Chegar certo").
//
// **Escrito na língua de DESTINO, não na da página.** É o detalhe que quase todo mundo erra: um
// francês em `/` não lê "esta página também está disponível em inglês" escrito em português —
// para ele o aviso precisa ser `This page is also available in English.` e mais nada. Por isso
// aqui se usa `translate(sugerido, ...)`, com o locale explícito, e não o `useT()` da página.
//
// **Não existe no HTML pré-renderizado.** O snapshot de servidor de `sugestaoAtual` é `null`
// (ver `sugestaoDeIdioma.ts`), então o robô recebe a página sem o aviso e a pessoa o recebe
// depois de hidratar. As duas razões são obrigações: conteúdo diferente para robô e pessoa é
// cloaking, e o primeiro render do cliente tem de bater com o HTML da T-159.
//
// **Não redireciona nunca** (invariante da SPEC-026). É um link, e ele some quando dispensado.
import { useCallback, useSyncExternalStore } from 'react'
import { translate } from '../i18n'
import type { Locale } from '../i18n/locale'
import { siteRouteHref } from '../shell/origins'
import type { SiteScreen } from './routes'
import { assinarSugestao, dispensar, semSugestao, sugestaoAtual } from './sugestaoDeIdioma'

export function AvisoDeIdioma({ screen, locale }: { screen: SiteScreen; locale: Locale }) {
  const sugerido = useSyncExternalStore(
    assinarSugestao,
    useCallback(() => sugestaoAtual(locale), [locale]),
    semSugestao,
  )

  if (!sugerido) return null

  // Resolvidos ANTES do JSX de propósito: o `no-literal-string` roda em `jsx-only` e trata a
  // chave passada dentro de um atributo como frase solta. A lista de `callees` da regra conhece
  // `t`, não `translate` — e mexer no portão compartilhado para acomodar um componente seria
  // caro pelo motivo errado.
  const texto = translate(sugerido, 'site:hint.text')
  const cta = translate(sugerido, 'site:hint.cta')
  const fechar = translate(sugerido, 'site:hint.dismiss')

  return (
    // `lang={sugerido}`: o conteúdo deste bloco está em OUTRA língua que a da página, e é o
    // atributo que conta isso ao leitor de tela e ao tradutor do navegador (T-162).
    <aside className="langhint" lang={sugerido}>
      <p className="langhint__text">{texto}</p>
      <a className="langhint__cta" href={siteRouteHref(screen, sugerido)} hrefLang={sugerido}>
        {cta}
      </a>
      <button type="button" className="langhint__close" onClick={dispensar} aria-label={fechar}>
        ×
      </button>
    </aside>
  )
}
