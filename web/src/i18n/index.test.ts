import { describe, expect, it } from 'vitest'

import { dict as dictEn } from './dict/en'
import { dict as dictPtBR } from './dict/pt-BR'
import { useI18nStore } from './store'
import { resolveFromTable, t, tDynamic, translate } from './index'

/**
 * `tsc` cobra paridade de CHAVE (`dict/typeParity.proof.ts`), NÃO de placeholder: uma tradução
 * que esqueça o `{exercise}` compila limpa, passa no lint e só some com o nome do exercício em
 * produção, na língua que ninguém abre para conferir. Esta é a outra metade do portão.
 *
 * Desde a T-154 vale para os NOVE namespaces de uma vez, varrendo `dict/pt-BR/index.ts` — não
 * mais uma chamada por namespace escrita à mão (que era o desenho enquanto a Onda 2 corria em
 * paralelo, e que deixaria o décimo namespace de fora sem ninguém notar).
 */
function esperaMesmosPlaceholders(
  ptBR: Record<string, string>,
  en: Record<string, string>,
  namespace = '',
): void {
  const placeholders = (texto: string) => [...texto.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()

  for (const [chave, textoPtBR] of Object.entries(ptBR)) {
    const onde = namespace ? `${namespace}:${chave}` : chave
    expect({ chave: onde, ph: placeholders(en[chave] ?? '') }).toEqual({
      chave: onde,
      ph: placeholders(textoPtBR),
    })
  }
}

describe('translate — namespace real (shell), as duas línguas', () => {
  it('resolve a mesma chave nas duas línguas', () => {
    expect(translate('pt-BR', 'shell:tab.inicio')).toBe('Início')
    expect(translate('en', 'shell:tab.inicio')).toBe('Home')
  })

  it('aria-label do shell existe nas duas línguas', () => {
    expect(translate('pt-BR', 'shell:nav.aria_label')).toBe('Navegação principal')
    expect(translate('en', 'shell:nav.aria_label')).toBe('Main navigation')
  })

  it('namespace sem chave nenhuma (ainda não migrado) devolve a própria chave, não branco', () => {
    // `site` só nasce nesta task como arquivo vazio (T-147 é quem preenche) — sem fallback em
    // branco, a chave crua fica visível o bastante para ser notada em revisão (SPEC-025 §3.6).
    expect(translate('pt-BR', 'site:qualquer.coisa')).toBe('site:qualquer.coisa')
  })

  it('chave sem separador `:` devolve a própria chave', () => {
    expect(translate('pt-BR', 'chave-sem-namespace')).toBe('chave-sem-namespace')
  })
})

describe('resolveFromTable — interpolação e plural (critério 2 da T-142)', () => {
  const tabela = {
    'greeting': 'Olá, {nome}!',
    'reps.one': '{n} repetição',
    'reps.other': '{n} repetições',
    'no_plural_form': 'Sem plural nenhum',
  }

  it('interpola nomes arbitrários entre chaves', () => {
    expect(resolveFromTable(tabela, 'pt-BR', 'greeting', { nome: 'Ana' })).toBe('Olá, Ana!')
  })

  it('chave sem params devolve o texto como está', () => {
    expect(resolveFromTable(tabela, 'pt-BR', 'no_plural_form')).toBe('Sem plural nenhum')
  })

  it('plural pt-BR sem balde .zero: 1 cai em .one, 2+ cai em .other — nunca um if (n === 1)', () => {
    expect(resolveFromTable(tabela, 'pt-BR', 'reps', { n: 1 })).toBe('1 repetição')
    expect(resolveFromTable(tabela, 'pt-BR', 'reps', { n: 2 })).toBe('2 repetições')
    expect(resolveFromTable(tabela, 'pt-BR', 'reps', { n: 21 })).toBe('21 repetições')
  })

  it('plural pt-BR, n === 0, sem balde .zero: segue o CLDR ao pé da letra (cai em .one)', () => {
    // `Intl.PluralRules('pt-BR').select(0) === 'one'` — é o CLDR, não um bug: sem um balde
    // `.zero` cadastrado na tabela, `resolveFromTable` não inventa "0 repetições" sozinho.
    expect(resolveFromTable(tabela, 'pt-BR', 'reps', { n: 0 })).toBe('0 repetição')
  })

  it('balde .zero vence quando n === 0 e existe na tabela — corrige "0 repetições" apesar do CLDR', () => {
    const comZero = { ...tabela, 'reps.zero': '{n} repetições' }
    expect(resolveFromTable(comZero, 'pt-BR', 'reps', { n: 0 })).toBe('0 repetições')
    // `.zero` só entra em jogo para n === 0 — 1 e 2+ continuam pela regra normal (.one/.other).
    expect(resolveFromTable(comZero, 'pt-BR', 'reps', { n: 1 })).toBe('1 repetição')
    expect(resolveFromTable(comZero, 'pt-BR', 'reps', { n: 2 })).toBe('2 repetições')
  })

  it('plural en: mesma regra .one/.other, resolvida pelo Intl.PluralRules do locale', () => {
    expect(resolveFromTable(tabela, 'en', 'reps', { n: 1 })).toBe('1 repetição')
    expect(resolveFromTable(tabela, 'en', 'reps', { n: 2 })).toBe('2 repetições')
    // (a tabela de fixture é a mesma nos dois locales de propósito — o que muda é a CATEGORIA
    // escolhida por `Intl.PluralRules`, não o texto; ver o teste de paridade en/pt-BR abaixo
    // com uma tabela distinta por idioma.)
  })

  it('categoria plural específica ausente cai em .other', () => {
    const semUm = { 'x.other': '{n} itens' }
    expect(resolveFromTable(semUm, 'pt-BR', 'x', { n: 1 })).toBe('1 itens')
  })

  it('chave plural nenhuma cadastrada devolve undefined (quem chama decide o fallback)', () => {
    expect(resolveFromTable({}, 'pt-BR', 'inexistente', { n: 1 })).toBeUndefined()
  })

  it('duas tabelas distintas por idioma pluralizam cada uma na própria língua', () => {
    const ptBR = { 'streak.one': '{n} dia seguido', 'streak.other': '{n} dias seguidos' }
    const en = { 'streak.one': '{n} day in a row', 'streak.other': '{n} days in a row' }
    expect(resolveFromTable(ptBR, 'pt-BR', 'streak', { n: 1 })).toBe('1 dia seguido')
    expect(resolveFromTable(ptBR, 'pt-BR', 'streak', { n: 5 })).toBe('5 dias seguidos')
    expect(resolveFromTable(en, 'en', 'streak', { n: 1 })).toBe('1 day in a row')
    expect(resolveFromTable(en, 'en', 'streak', { n: 5 })).toBe('5 days in a row')
  })
})

describe('t() — lê o locale ativo no store (fora de componente)', () => {
  it('muda de resposta quando o locale do store muda', () => {
    useI18nStore.getState().setLocale('pt-BR')
    expect(t('shell:tab.perfil')).toBe('Perfil')

    useI18nStore.getState().setLocale('en')
    expect(t('shell:tab.perfil')).toBe('Profile')
  })
})

describe('tDynamic — chave montada em tempo de execução (critério da T-152)', () => {
  it('resolve uma chave existente, lendo o locale do store como o t()', () => {
    useI18nStore.getState().setLocale('pt-BR')
    expect(tDynamic('shell:tab.perfil', 'x')).toBe('Perfil')

    useI18nStore.getState().setLocale('en')
    expect(tDynamic('shell:tab.perfil', 'x')).toBe('Profile')
  })

  it('chave sem entrada no dicionário cai no fallback, não na chave namespaced', () => {
    useI18nStore.getState().setLocale('pt-BR')
    expect(tDynamic('catalog:category.hiit', 'hiit')).toBe('hiit')
  })
})

describe('namespace funnel — a moldura do funil nas duas línguas (T-148)', () => {
  it('resolve a mesma chave nas duas línguas', () => {
    expect(translate('pt-BR', 'funnel:guide.cta')).toBe('Entendi, vamos lá')
    expect(translate('en', 'funnel:guide.cta')).toBe('Got it, let\u2019s go')
  })

  it('interpola o nome do exercício, que vem do catálogo e não deste namespace', () => {
    // A moldura é do `funnel`; o nome é do `catalog`/servidor (T-146/T-152). Por isso a chave
    // guarda `{exercise}` e não a palavra.
    expect(translate('pt-BR', 'funnel:demo.alt', { exercise: 'Polichinelo' })).toBe(
      'Demonstração: Polichinelo',
    )
    expect(translate('en', 'funnel:demo.alt', { exercise: 'Jumping Jacks' })).toBe(
      'Demo: Jumping Jacks',
    )
  })

  it('a dica de "não mostrar novamente" cita o card pelo rótulo em vigor, não por um nome fixo', () => {
    const ptBR = translate('pt-BR', 'funnel:vgate.dont_show_hint', {
      card: translate('pt-BR', 'funnel:view.label_compact'),
    })
    const en = translate('en', 'funnel:vgate.dont_show_hint', {
      card: translate('en', 'funnel:view.label_compact'),
    })
    expect(ptBR).toContain('“Câmera”')
    expect(en).toContain('“Camera”')
  })

})

describe('namespace session — o treino nas duas línguas (T-149)', () => {
  it('resolve a mesma chave nas duas línguas', () => {
    expect(translate('pt-BR', 'session:cta.start_exercise')).toBe('Iniciar Exercício')
    expect(translate('en', 'session:cta.start_exercise')).toBe('Start Exercise')
  })

  it('o balde .zero da preparação vale nas duas línguas: zero tem frase própria', () => {
    // A regra que um `if (n === 0)` no componente teria escondido: "sem preparação" não é o
    // singular de nada, é outra frase — e cada língua escolhe a sua.
    expect(translate('pt-BR', 'session:countdown.value', { n: 0 })).toBe('sem preparação')
    expect(translate('pt-BR', 'session:countdown.value', { n: 5 })).toBe('5s de preparação')
    expect(translate('en', 'session:countdown.value', { n: 0 })).toBe('no countdown')
    expect(translate('en', 'session:countdown.value', { n: 5 })).toBe('5s countdown')
  })

})

describe('namespaces report + progress — a leitura do passado nas duas línguas (T-150)', () => {
  it('resolve a mesma chave nas duas línguas', () => {
    expect(translate('pt-BR', 'report:section.improve')).toBe('O que melhorar')
    expect(translate('en', 'report:section.improve')).toBe('What to improve')
    expect(translate('pt-BR', 'progress:title')).toBe('Seu treino ao longo do tempo')
    expect(translate('en', 'progress:title')).toBe('Your training over time')
  })

  it('plural das métricas pelo Intl, e sem forma base cadastrada', () => {
    // O que a T-150 acrescentou ao runtime: `metric.days` NÃO existe como chave — só
    // `metric.days.one` e `.other` —, e mesmo assim é uma `TKey` válida (ver `PluralBase` em
    // `i18n/index.ts`). Antes disso, cada palavra teria de ser repetida numa chave base.
    expect(translate('pt-BR', 'progress:metric.days', { n: 1 })).toBe('dia')
    expect(translate('pt-BR', 'progress:metric.days', { n: 3 })).toBe('dias')
    expect(translate('en', 'progress:metric.days', { n: 1 })).toBe('day')
    expect(translate('en', 'progress:metric.days', { n: 3 })).toBe('days')
    expect(translate('pt-BR', 'progress:metric.workouts', { n: 1 })).toBe('treino')
    expect(translate('en', 'progress:metric.workouts', { n: 2 })).toBe('workouts')
  })

  it('a faixa de ritmo interpola e pluraliza na mesma chave', () => {
    expect(
      translate('pt-BR', 'progress:analytics.range', { min: 38, max: 44, n: 1 }),
    ).toBe('de 38 a 44 rep/min em 1 treino')
    expect(translate('en', 'progress:analytics.range', { min: 38, max: 44, n: 5 })).toBe(
      'from 38 to 44 reps/min across 5 workouts',
    )
  })

})

describe('namespaces account + errors — a conta e as falhas nas duas línguas (T-151)', () => {
  it('resolve a mesma chave nas duas línguas', () => {
    expect(translate('pt-BR', 'account:eng.title')).toBe('Sua constância')
    expect(translate('en', 'account:eng.title')).toBe('Your consistency')
  })

  it('uma frase, uma casa: a falha de rede das TRÊS chamadas é a mesma chave', () => {
    // `session/admission`, `report/sessionReport` e `auth/api` liam três cópias iguais até a
    // T-151 (Descoberta `[T-150]`). O `errors` é a casa única.
    expect(translate('pt-BR', 'errors:api_down')).toBe('API fora do ar')
    expect(translate('en', 'errors:api_down_detail', { reason: 'Failed to fetch' })).toBe(
      'API is down: Failed to fetch',
    )
  })

  it('os quatro plurais da conta escolhem o balde pelo Intl, nas duas línguas', () => {
    const casos = [
      ['account:fire.days', 1, '1 dia seguido', '1 day in a row'],
      ['account:fire.days', 7, '7 dias seguidos', '7 days in a row'],
      ['account:eng.days', 1, 'dia seguido', 'day in a row'],
      ['account:eng.sessions', 2, 'sessões', 'sessions'],
      ['account:stored.suffix', 1, 'treino guardado', 'workout saved'],
      ['account:eng.days_trained', 3, 'dias treinados neste mês', 'days trained this month'],
    ] as const

    for (const [chave, n, esperadoPtBR, esperadoEn] of casos) {
      expect(translate('pt-BR', chave, { n })).toBe(esperadoPtBR)
      expect(translate('en', chave, { n })).toBe(esperadoEn)
    }
  })

})

describe('o portão da paridade de placeholder, nos NOVE namespaces (T-154)', () => {
  it('toda chave com {placeholder} no pt-BR tem exatamente os mesmos no en', () => {
    // Varre o índice, e não uma lista escrita à mão: um namespace novo entra em
    // `dict/pt-BR/index.ts` e passa a ser cobrado aqui sem ninguém tocar neste arquivo — a
    // mesma propriedade que faz o `TKey` crescer sozinho (T-142).
    for (const namespace of Object.keys(dictPtBR) as Array<keyof typeof dictPtBR>) {
      esperaMesmosPlaceholders(dictPtBR[namespace], dictEn[namespace], namespace)
    }
  })

  it('varre os nove — se um namespace novo nascer, ele entra sozinho', () => {
    expect(Object.keys(dictPtBR)).toHaveLength(9)
    expect(Object.keys(dictEn)).toEqual(Object.keys(dictPtBR))
  })
})
