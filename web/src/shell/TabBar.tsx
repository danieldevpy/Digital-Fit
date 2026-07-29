// Bottom nav do app shell (SPEC-013 §5). Perfil abre a conta e o histórico (SPEC-011 /
// T-022). Exercícios e Progresso seguem placeholders declarados: não têm spec de Fase
// Inicial — progresso entre sessões é Fase Evolução da SPEC-010 —, então avisam "em breve"
// em vez de navegar para lugar nenhum.
import { useEffect, useRef, useState } from 'react'
import { useAccountStore } from '../store/account'
import { useSessionStore } from '../store/session'
import { IconChart, IconDumbbell, IconHome, IconPulse, IconUser } from '../ui/icons'

const TABS = [
  { id: 'inicio', label: 'Início', Icon: IconHome, ready: true },
  { id: 'exercicios', label: 'Exercícios', Icon: IconDumbbell, ready: false },
  { id: 'progresso', label: 'Progresso', Icon: IconChart, ready: false },
  { id: 'perfil', label: 'Perfil', Icon: IconUser, ready: true },
] as const

const ACTIVE_TAB = 'inicio'
const HINT_MS = 1800

export function TabBar() {
  const [hint, setHint] = useState<string | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cameraControls = useSessionStore((state) => state.cameraControls)
  const cameraStatus = useSessionStore((state) => state.cameraStatus)

  useEffect(() => () => clearTimeout(timeoutRef.current ?? undefined), [])

  const showHint = (label: string) => {
    setHint(`${label}: em breve`)
    clearTimeout(timeoutRef.current ?? undefined)
    timeoutRef.current = setTimeout(() => setHint(null), HINT_MS)
  }

  const isRunning = cameraStatus === 'ready' || cameraStatus === 'requesting'

  const openAccount = useAccountStore((state) => state.openSheet)

  const acao = (id: string, label: string, ready: boolean) => {
    if (id === 'perfil') return () => openAccount(true)
    return ready ? undefined : () => showHint(label)
  }

  const renderTab = ({ id, label, Icon, ready }: (typeof TABS)[number]) => (
    <button
      key={id}
      type="button"
      className={`tab ${id === ACTIVE_TAB ? 'tab--active' : ''}`}
      aria-current={id === ACTIVE_TAB ? 'page' : undefined}
      aria-disabled={ready ? undefined : true}
      onClick={acao(id, label, ready)}
    >
      <Icon className="tab__icon" />
      <span className="tab__label">{label}</span>
    </button>
  )

  return (
    <>
      {hint && <p className="tabbar__hint">{hint}</p>}
      <nav className="tabbar" aria-label="Navegação principal">
        {TABS.slice(0, 2).map(renderTab)}

        <button
          type="button"
          className="tab-fab"
          aria-label={isRunning ? 'Encerrar sessão' : 'Iniciar sessão'}
          onClick={() => (isRunning ? cameraControls?.stop() : cameraControls?.start())}
        >
          <IconPulse className="tab-fab__icon" />
        </button>

        {TABS.slice(2).map(renderTab)}
      </nav>
    </>
  )
}
