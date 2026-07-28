import { IconUser } from '../ui/icons'
import { PLACEHOLDER_TIP } from './placeholders'

export function CoachTip() {
  const { title, text } = PLACEHOLDER_TIP

  return (
    <article className="card card--tip">
      <div className="tip__avatar">
        <IconUser className="tip__avatar-icon" />
      </div>
      <div className="tip__body">
        <p className="tip__title">{title}</p>
        <p className="tip__text">{text}</p>
      </div>
      <button type="button" className="tip__action">
        Ver detalhes
      </button>
    </article>
  )
}
