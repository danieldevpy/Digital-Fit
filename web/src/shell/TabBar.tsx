// Bottom nav do APP (SPEC-014 §Mapa de navegação, revisada na T-068).
//
// Quatro itens: Início · Progresso · Analytics · Perfil. "Início" é a PRÉ-CONFIGURAÇÃO, não
// a landing — a landing virou site (T-067), e o que abre quando alguém abre o app é a tela
// de preparar o treino. A escolha de exercício saiu da barra porque já tem porta própria e
// melhor: o card EXERCÍCIO da pré-configuração.
//
// Na tela de treino a MESMA barra aparece com um botão central (o play/stop da sessão). A
// referência tinha um player flutuante solto no rodapé, e em aparelho real ele colidia com
// pill, toast e barra do navegador. Um FAB dentro da barra resolve por construção: existe um
// rodapé só, e o empilhamento é do fluxo, não de `position: absolute`.
import { Fragment, type ReactNode } from 'react'
import { useAccountStore } from '../store/account'
import { IconChart, IconHome, IconPulse, IconUser } from '../ui/icons'
import { navigate, useRoute } from './nav'

type TabId = 'inicio' | 'progresso' | 'analytics' | 'perfil'

/** Qual aba acende para cada tela. O funil todo (escolha, guia, treino) pertence ao Início. */
const ACTIVE: Record<string, TabId> = {
  preparar: 'inicio',
  treino: 'inicio',
  exercicios: 'inicio',
  guia: 'inicio',
  abrirExercicio: 'inicio',
  entrar: 'inicio',
  progresso: 'progresso',
  analytics: 'analytics',
}

const TABS: { id: TabId; label: string; Icon: (props: { className?: string }) => ReactNode }[] = [
  { id: 'inicio', label: 'Início', Icon: IconHome },
  { id: 'progresso', label: 'Progresso', Icon: IconChart },
  { id: 'analytics', label: 'Analytics', Icon: IconPulse },
  { id: 'perfil', label: 'Perfil', Icon: IconUser },
]

/** Onde o FAB entra na lista: entre Progresso e Analytics, o meio de quatro itens. */
const FAB_INDEX = 2

interface TabBarProps {
  /** Botão central — a tela de treino manda o play/stop da sessão. */
  center?: ReactNode
}

export function TabBar({ center }: TabBarProps) {
  const route = useRoute()
  const openAccount = useAccountStore((state) => state.openSheet)

  const active = ACTIVE[route.screen] ?? 'inicio'

  const onTap = (id: TabId) => {
    if (id === 'inicio') navigate({ screen: 'preparar' })
    else if (id === 'progresso') navigate({ screen: 'progresso' })
    else if (id === 'analytics') navigate({ screen: 'analytics' })
    else openAccount(true)
  }

  return (
    <nav
      className={`tabbar-v2 ${center ? 'tabbar-v2--fab' : ''}`}
      aria-label="Navegação principal"
    >
      {TABS.map(({ id, label, Icon }, indice) => (
        <Fragment key={id}>
          {center && indice === FAB_INDEX && <span className="tabv2__fab">{center}</span>}
          <button
            type="button"
            className={`tabv2 ${id === active ? 'tabv2--active' : ''}`}
            aria-current={id === active ? 'page' : undefined}
            onClick={() => onTap(id)}
          >
            <Icon className="tabv2__icon" />
            <span>{label}</span>
          </button>
        </Fragment>
      ))}
    </nav>
  )
}
