// Bottom nav v2 (SPEC-014): flutuante, 4 itens, sem FAB — iniciar treino é papel dos CTAs
// das telas, como na referência. Progresso segue placeholder declarado ("em breve"): a tela
// real é a T-046. Perfil abre a conta e o histórico (SPEC-011 / T-022).
import { useEffect, useRef, useState } from 'react'
import { useAccountStore } from '../store/account'
import { IconChart, IconDumbbell, IconHome, IconUser } from '../ui/icons'
import { navigate, useRoute } from './nav'

const HINT_MS = 1800

/** Qual aba acende para cada tela. Pré-config/treino acendem Início, como na referência. */
const ACTIVE: Record<string, 'inicio' | 'exercicios' | 'progresso' | 'perfil'> = {
  index: 'inicio',
  preparar: 'inicio',
  treino: 'inicio',
  sobre: 'inicio',
  exercicios: 'exercicios',
  guia: 'exercicios',
}

export function TabBar() {
  const [hint, setHint] = useState<string | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const route = useRoute()
  const openAccount = useAccountStore((state) => state.openSheet)

  useEffect(() => () => clearTimeout(timeoutRef.current ?? undefined), [])

  const showHint = (label: string) => {
    setHint(`${label}: em breve`)
    clearTimeout(timeoutRef.current ?? undefined)
    timeoutRef.current = setTimeout(() => setHint(null), HINT_MS)
  }

  const active = ACTIVE[route.screen] ?? 'inicio'

  const onTap = (id: (typeof TABS)[number]['id']) => {
    if (id === 'inicio') navigate({ screen: 'index' })
    else if (id === 'exercicios') navigate({ screen: 'exercicios' })
    else if (id === 'progresso') showHint('Progresso')
    else openAccount(true)
  }

  return (
    <>
      {hint && <p className="tabbar__hint">{hint}</p>}
      <nav className="tabbar-v2" aria-label="Navegação principal">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            className={`tabv2 ${id === active ? 'tabv2--active' : ''}`}
            aria-current={id === active ? 'page' : undefined}
            onClick={() => onTap(id)}
          >
            <Icon className="tabv2__icon" />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </>
  )
}

const TABS = [
  { id: 'inicio', label: 'Início', Icon: IconHome },
  { id: 'exercicios', label: 'Exercícios', Icon: IconDumbbell },
  { id: 'progresso', label: 'Progresso', Icon: IconChart },
  { id: 'perfil', label: 'Perfil', Icon: IconUser },
] as const
