import { describe, expect, it } from 'vitest'

import { EXERCISE_CATALOG, EXERCISE_KEYS } from '../session/catalog'
import { EXERCISE_FIGURES } from './exerciseFigures'

describe('figura de exercício (T-082)', () => {
  it('todo exercício do catálogo tem figura registrada', () => {
    // ESTE é o teste da task. O bug que ele impede não é de código, é de processo: o
    // agachamento entrou no catálogo em T-051 e herdou o boneco de braços pro alto do
    // polichinelo, porque nada no repositório lembrava que faltava desenhar a pose dele.
    // Ninguém revisa um card pequeno num canto da pré-configuração; o teste revisa.
    //
    // Falhou? Desenhe a pose em `ui/icons.tsx` (seção "figuras de exercício") e registre em
    // `EXERCISE_FIGURES`. O fallback em pé existe para produção não quebrar, não para deixar
    // o exercício sem figura passar batido.
    const semFigura = EXERCISE_KEYS.filter((key) => !Object.hasOwn(EXERCISE_FIGURES, key))

    expect(semFigura, `exercícios sem figura em EXERCISE_FIGURES: ${semFigura.join(', ')}`).toEqual(
      [],
    )
  })

  it('nenhuma figura sobra apontando para exercício que não existe', () => {
    // A direção contrária, que envelhece pior: exercício removido do catálogo deixa figura
    // órfã, e a próxima pessoa a ler o registro acredita que o slug ainda vale.
    const orfas = Object.keys(EXERCISE_FIGURES).filter((key) => !Object.hasOwn(EXERCISE_CATALOG, key))

    expect(orfas, `figuras sem exercício correspondente: ${orfas.join(', ')}`).toEqual([])
  })
})
