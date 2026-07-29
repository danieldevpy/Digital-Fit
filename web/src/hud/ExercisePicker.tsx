// Escolha do exercício, na capa da câmera (T-051 / SPEC-007: "usuário seleciona o exercício").
//
// Até aqui o cliente mandava `DEFAULT_EXERCISE` fixo: um exercício novo podia estar pronto,
// testado e medido no worker, e ainda assim ser inalcançável pelo produto.
//
// **Não desenha nada enquanto houver um exercício só.** Um seletor de uma opção não é
// escolha, é ruído em cima da câmera — e o produto de hoje tem exatamente uma. O que esta
// task entrega é o caminho da escolha até o `POST /sessions`; a superfície aparece sozinha
// quando o catálogo crescer (T-032). O `null` aqui é a decisão, não um caso degenerado.
//
// Fica ao lado da preparação porque é o mesmo instante: logo antes de treinar, antes de a
// sessão abrir. Quando a aba Exercícios existir (T-046) ela vira a superfície de navegar e
// conhecer; isto continua sendo a escolha rápida de quem já sabe o que veio fazer.
import { useState } from 'react'
import { EXERCISE_CATALOG, EXERCISE_KEYS, offersChoice } from '../session/catalog'
import { exercisePreference, setExercisePreference } from '../session/preferences'

export function ExercisePicker() {
  const [escolhido, setEscolhido] = useState(() => exercisePreference())

  if (!offersChoice()) return null

  return (
    // `radiogroup` e não uma fileira de botões: são opções mutuamente exclusivas com uma já
    // marcada, e é isso que um leitor de tela precisa anunciar.
    <div className="exercise-pick" role="radiogroup" aria-label="Exercício">
      {EXERCISE_KEYS.map((chave) => {
        const info = EXERCISE_CATALOG[chave]
        if (!info) return null
        const ativo = chave === escolhido
        return (
          <button
            key={chave}
            type="button"
            role="radio"
            aria-checked={ativo}
            className={`exercise-pick__item ${ativo ? 'exercise-pick__item--on' : ''}`}
            onClick={() => setEscolhido(setExercisePreference(chave))}
          >
            {info.display_name}
          </button>
        )
      })}
    </div>
  )
}
