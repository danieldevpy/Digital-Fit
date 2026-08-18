import { describe, expect, it } from 'vitest'

import { useI18nStore } from './store'
import { resolveFromTable, t, tDynamic, translate } from './index'

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
