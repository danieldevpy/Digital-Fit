// Cards de exercício da SPEC-014 §2 — usados na tela Escolha (app) e na seção
// "Escolha seu exercício" do Index (site). Toque no card entra no funil da SPEC-015:
// primeiro acesso àquele exercício passa pelo Guia; repetente vai direto à pré-config.
import { categoryLabel, useCatalog } from '../session/catalog'
import { exercisePreference } from '../session/preferences'
import { appHref } from '../shell/origins'
import { ExerciseIcon } from '../ui/exerciseIcon'
import { IconChevronRight, IconWave } from '../ui/icons'
import { chooseExercise } from './funnel'

interface ExerciseCardsProps {
  grid?: boolean
  /**
   * No SITE (T-067) cada card é um LINK para o app, não um botão: quem decide entre Guia e
   * Pré-config é o `guide_seen` do localStorage do APP, que esta origem não tem como ler.
   * O "selecionado" também não se sabe daqui — a borda acesa só existe do lado do app.
   */
  openInApp?: boolean
}

export function ExerciseCards({ grid = false, openInApp = false }: ExerciseCardsProps) {
  const selected = openInApp ? null : exercisePreference()
  // Reativo de propósito: o catálogo do servidor chega DEPOIS do primeiro paint (T-074), e a
  // Escolha é a tela onde a diferença aparece — um exercício desligado no painel tem que sumir
  // daqui sozinho, sem recarregar.
  const { keys, catalog } = useCatalog()

  return (
    <div className={`choose__list ${grid ? 'choose__list--grid' : ''}`}>
      {keys.map((key) => {
        const info = catalog[key]
        if (!info) return null

        const conteudo = (
          <>
            <p className="ex-card__cat">{categoryLabel(info.category)}</p>
            <h3 className="ex-card__name">{info.display_name}</h3>
            <span className="ex-card__badge">30s</span>
            <IconWave className="ex-card__wave" />
            {/* Exercício sem foto desenha a figura, não uma imagem quebrada — ver o comentário
                de `demo_img` no catálogo. */}
            {info.demo_img ? (
              <img
                className="ex-card__demo"
                src={info.demo_img}
                alt={`Demonstração: ${info.display_name}`}
                loading="lazy"
              />
            ) : (
              <ExerciseIcon exercise={key} className="ex-card__demo ex-card__demo--figura" />
            )}
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
          </>
        )

        return openInApp ? (
          <a key={key} className="ex-card" href={appHref(`#/ex/${key}`)}>
            {conteudo}
          </a>
        ) : (
          <button
            key={key}
            type="button"
            className={`ex-card ${key === selected ? 'ex-card--on' : ''}`}
            onClick={() => chooseExercise(key)}
          >
            {conteudo}
          </button>
        )
      })}
    </div>
  )
}
