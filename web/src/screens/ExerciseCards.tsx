// Cards de exercício da SPEC-014 §2 — hoje a vitrine do SITE, na seção "Escolha seu exercício"
// do Index (T-067).
//
// **O app deixou de usá-los.** A tela Escolha passou a agrupar por categoria em faixas
// horizontais (`ExerciseRails`) porque a pilha de cards grandes não sobrevive ao catálogo da
// SPEC-020. Aqui a pilha longa continua certa: é uma página de marketing, onde a foto grande é
// o argumento e rolar é o que se espera fazer.
//
// Cada card é um LINK para o app, não um botão: quem decide entre Guia e Pré-config é o
// `guide_seen` do localStorage do APP, que esta origem não tem como ler. O "selecionado"
// também não se sabe daqui — a borda acesa só existe do lado do app.
import { useT } from '../i18n'
import { categoryLabel, useCatalog } from '../session/catalog'
import { appHref } from '../shell/origins'
import { ExerciseDemo } from '../ui/ExerciseDemo'
import { IconChevronRight, IconWave } from '../ui/icons'

export function ExerciseCards() {
  const t = useT()
  // Reativo de propósito: o catálogo do servidor chega DEPOIS do primeiro paint (T-074), e um
  // exercício desligado no painel tem que sumir daqui sozinho, sem recarregar.
  const { keys, catalog } = useCatalog()

  return (
    <div className="choose__list choose__list--grid">
      {keys.map((key) => {
        const info = catalog[key]
        if (!info) return null

        return (
          <a key={key} className="ex-card" href={appHref(`#/ex/${key}`)}>
            <p className="ex-card__cat">{categoryLabel(info.category)}</p>
            <h3 className="ex-card__name">{info.display_name}</h3>
            <span className="ex-card__badge">{t('funnel:card.duration')}</span>
            <IconWave className="ex-card__wave" />
            <ExerciseDemo
              exercise={key}
              info={info}
              className="ex-card__demo"
              figuraClassName="ex-card__demo--figura"
              // Aqui a rolagem é a do documento, então o adiamento funciona de verdade — e a
              // vitrine do site é longa o bastante para valer a pena.
              lazy
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
          </a>
        )
      })}
    </div>
  )
}
