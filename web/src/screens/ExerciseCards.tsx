// Cards de exercício da SPEC-014 §2 — usados na tela Escolha (mobile) e na seção
// "Escolha seu exercício" do Index desktop. Toque no card entra no funil da SPEC-015:
// primeiro acesso àquele exercício passa pelo Guia; repetente vai direto à pré-config.
import { EXERCISE_CATALOG, EXERCISE_KEYS } from '../session/catalog'
import { exercisePreference } from '../session/preferences'
import { IconChevronRight, IconWave } from '../ui/icons'
import { chooseExercise } from './funnel'

export function ExerciseCards({ grid = false }: { grid?: boolean }) {
  const selected = exercisePreference()

  return (
    <div className={`choose__list ${grid ? 'choose__list--grid' : ''}`}>
      {EXERCISE_KEYS.map((key) => {
        const info = EXERCISE_CATALOG[key]
        if (!info) return null
        return (
          <button
            key={key}
            type="button"
            className={`ex-card ${key === selected ? 'ex-card--on' : ''}`}
            onClick={() => chooseExercise(key)}
          >
            <p className="ex-card__cat">{info.category}</p>
            <h3 className="ex-card__name">{info.display_name}</h3>
            <span className="ex-card__badge">30s</span>
            <IconWave className="ex-card__wave" />
            <img
              className="ex-card__demo"
              src={info.demo_img}
              alt={`Demonstração: ${info.display_name}`}
              loading="lazy"
            />
            <span className="ex-card__foot">
              <span
                className="ex-card__dot"
                style={{ background: info.dot_color, boxShadow: `0 0 8px ${info.dot_color}` }}
              />
              <span className="ex-card__group">{info.muscle_group}</span>
              <span className="ex-card__go">
                <IconChevronRight className="ex-card__go-icon" />
              </span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
