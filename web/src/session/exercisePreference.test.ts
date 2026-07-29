import { afterEach, describe, expect, it } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import { DEFAULT_EXERCISE, EXERCISE_KEYS, getExercise, isExerciseKey, offersChoice } from './catalog'
import { exercisePreference, setExercisePreference } from './preferences'

afterEach(uninstallStorage)

describe('preferência de exercício (T-051)', () => {
  it('quem nunca escolheu recebe o exercício padrão', () => {
    installStorage()
    expect(exercisePreference()).toBe(DEFAULT_EXERCISE)
  })

  it('a escolha sobrevive à próxima sessão', () => {
    installStorage()
    // Com um exercício no catálogo isto ainda prova a ida e volta pelo armazenamento.
    setExercisePreference(DEFAULT_EXERCISE)
    expect(exercisePreference()).toBe(DEFAULT_EXERCISE)
  })

  it('slug que não existe mais no catálogo NÃO é devolvido', () => {
    // O caso que derrubaria o produto: um aparelho parado há meses guardou `flexao`, o
    // exercício saiu do catálogo, e agora toda tentativa de treinar bateria na recusa do
    // servidor sem nenhum caminho de volta pela interface. Validar na leitura resolve.
    const fake = installStorage()
    fake.store.set('digitalfit.exercise', 'levitacao')

    expect(exercisePreference()).toBe(DEFAULT_EXERCISE)
  })

  it('gravar lixo cai no padrão em vez de gravar lixo', () => {
    installStorage()
    expect(setExercisePreference('levitacao')).toBe(DEFAULT_EXERCISE)
    expect(exercisePreference()).toBe(DEFAULT_EXERCISE)
  })

  it('sem armazenamento (Safari privado) o app segue com o padrão', () => {
    installStorage({ readOnly: true })
    expect(() => setExercisePreference(DEFAULT_EXERCISE)).not.toThrow()
    expect(exercisePreference()).toBe(DEFAULT_EXERCISE)
  })
})

describe('catálogo', () => {
  it('o exercício padrão está no catálogo — senão nada abre sessão', () => {
    expect(isExerciseKey(DEFAULT_EXERCISE)).toBe(true)
    expect(EXERCISE_KEYS).toContain(DEFAULT_EXERCISE)
  })

  it('`isExerciseKey` recusa o que não é chave, inclusive não-string', () => {
    expect(isExerciseKey('levitacao')).toBe(false)
    expect(isExerciseKey(null)).toBe(false)
    expect(isExerciseKey(42)).toBe(false)
    // O que separa "chave do catálogo" de "propriedade herdada de Object": sem o `in` na
    // instância certa, `toString` passaria por exercício válido.
    expect(isExerciseKey('toString')).toBe(false)
  })

  it('`getExercise` devolve um exercício de verdade mesmo para chave herdada', () => {
    // Sem a guarda, `EXERCISE_CATALOG['toString']` devolve uma função — o `??` não dispara e
    // `.display_name` vira `undefined` no meio da tela.
    expect(getExercise('toString').display_name).toBe(getExercise(null).display_name)
    expect(typeof getExercise('levitacao').display_name).toBe('string')
  })

  it('não oferece escolha enquanto houver um exercício só', () => {
    // Trava a decisão da T-051: o caminho da escolha existe desde já, a superfície aparece
    // quando o catálogo crescer. Este teste vira `true` sozinho no dia da T-032.
    expect(offersChoice()).toBe(EXERCISE_KEYS.length > 1)
  })
})
