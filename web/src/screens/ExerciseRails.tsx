// A tela Escolha do APP: uma faixa horizontal por categoria (SPEC-020 §Escopo, "tela Escolha
// agrupada por categoria").
//
// **Por que faixa, e não a pilha de cards grandes da SPEC-014 §2.** Aquele desenho nasceu com
// dois exercícios: um card de ~260px por exercício, empilhado, cabia na tela. Com os quatro de
// hoje a Escolha já é meio metro de rolagem, e o Lote 1 da SPEC-020 (T-092…T-095) mais o wall
// sit levam isso a dez — a tela deixaria de ser uma escolha e viraria um catálogo que se
// percorre. A faixa troca o eixo: a altura para de crescer com o catálogo, e o que cresce é a
// rolagem lateral DENTRO da categoria, que é onde a comparação acontece ("qual cardio eu faço
// hoje?"), não entre categorias.
//
// A fraqueza conhecida da faixa é a descoberta: o que está fora do quadro não se anuncia. Daí o
// "ver todos", que abre a categoria numa grade — e só aparece quando há algo escondido de fato.
//
// O card GRANDE não morreu: ele continua sendo o do site (`ExerciseCards`), onde a foto é
// vitrine e a rolagem longa é o comportamento esperado de uma página de marketing.
import { useState } from 'react'
import { useT } from '../i18n'
import { groupByCategory, useCatalog } from '../session/catalog'
import { exercisePreference } from '../session/preferences'
import { ExerciseDemo } from '../ui/ExerciseDemo'
import { IconChevronRight } from '../ui/icons'
import { chooseExercise } from './funnel'

/**
 * Quantos cards cabem no quadro sem rolar, no aparelho mais estreito que suportamos.
 *
 * É o gatilho do "ver todos": com dois exercícios não há nada escondido, e um botão que promete
 * revelar o que já está à vista é ruído. Constante e não medida por JS de propósito — medir
 * daria um botão que aparece e some conforme a largura, piscando na rotação do aparelho.
 */
const CABEM_NO_QUADRO = 2

export function ExerciseRails() {
  const t = useT()
  // Reativo pela mesma razão do card do site: o catálogo do servidor chega DEPOIS do primeiro
  // paint (T-074), e um exercício desligado no painel tem que sumir daqui sozinho.
  const { keys, catalog } = useCatalog()
  const selecionado = exercisePreference()
  const grupos = groupByCategory(keys, catalog)
  const [abertas, setAbertas] = useState<string[]>([])

  return (
    <div className="rails">
      {grupos.map((grupo) => {
        const aberta = abertas.includes(grupo.category)
        const temEscondido = grupo.keys.length > CABEM_NO_QUADRO

        return (
          <section className="rail" key={grupo.category}>
            <header className="rail__head">
              <h2 className="rail__title">{grupo.label}</h2>
              <span className="rail__count num">{grupo.keys.length}</span>
              {temEscondido && (
                <button
                  type="button"
                  className="rail__all"
                  aria-expanded={aberta}
                  onClick={() =>
                    setAbertas((atuais) =>
                      aberta
                        ? atuais.filter((slug) => slug !== grupo.category)
                        : [...atuais, grupo.category],
                    )
                  }
                >
                  {aberta ? t('funnel:rail.collapse') : t('funnel:rail.see_all')}
                </button>
              )}
            </header>

            {/* `aria-label` na trilha, e não só o `h2`: aberta ou fechada ela é uma região que o
                leitor de tela anuncia ao entrar, e "Cardio" sozinho não diz que há rolagem. */}
            <div
              className={`rail__track ${aberta ? 'rail__track--aberta' : ''}`}
              aria-label={t('funnel:rail.track_aria', { category: grupo.label })}
            >
              {grupo.keys.map((key) => {
                const info = catalog[key]
                if (!info) return null
                return (
                  <button
                    key={key}
                    type="button"
                    className={`ex-mini ${key === selecionado ? 'ex-mini--on' : ''}`}
                    onClick={() => chooseExercise(key)}
                  >
                    <ExerciseDemo
                      exercise={key}
                      info={info}
                      className="ex-mini__demo"
                      figuraClassName="ex-mini__demo--figura"
                    />
                    <span className="ex-mini__badge num">{t('funnel:card.duration')}</span>
                    <span className="ex-mini__name">{info.display_name}</span>
                    <span className="ex-mini__foot">
                      <span
                        className="ex-mini__dot"
                        style={{ background: info.dot_color, boxShadow: `0 0 8px ${info.dot_color}` }}
                      />
                      <span className="ex-mini__group">{info.muscle_group}</span>
                      <IconChevronRight className="ex-mini__go" />
                    </span>
                  </button>
                )
              })}
            </div>
          </section>
        )
      })}
    </div>
  )
}
