// Navegação da casca visual. Ainda sem rotas: as telas Exercícios / Progresso /
// Perfil não existem em nenhuma spec da Fase 0.
import { IconChart, IconDumbbell, IconHome, IconPulse, IconUser } from '../ui/icons'

const TABS = [
  { id: 'inicio', label: 'Início', Icon: IconHome },
  { id: 'exercicios', label: 'Exercícios', Icon: IconDumbbell },
  { id: 'progresso', label: 'Progresso', Icon: IconChart },
  { id: 'perfil', label: 'Perfil', Icon: IconUser },
] as const

const ACTIVE_TAB = 'inicio'

export function TabBar() {
  const [first, second, third, fourth] = TABS

  return (
    <nav className="tabbar" aria-label="Navegação principal">
      {[first, second].map(({ id, label, Icon }) => (
        <button
          key={id}
          type="button"
          className={`tab ${id === ACTIVE_TAB ? 'tab--active' : ''}`}
          aria-current={id === ACTIVE_TAB ? 'page' : undefined}
        >
          <Icon className="tab__icon" />
          <span className="tab__label">{label}</span>
        </button>
      ))}

      <button type="button" className="tab-fab" aria-label="Iniciar sessão">
        <IconPulse className="tab-fab__icon" />
      </button>

      {[third, fourth].map(({ id, label, Icon }) => (
        <button key={id} type="button" className="tab">
          <Icon className="tab__icon" />
          <span className="tab__label">{label}</span>
        </button>
      ))}
    </nav>
  )
}
