// O aviso de conquista nova (SPEC-019 §Conquistas / T-089).
//
// O servidor **não guarda "notificado em"** — a spec recusa a tabela —, então quem sabe o que
// esta pessoa ainda não viu é o cliente, por diff contra o `localStorage`. O diff em si mora no
// store (ver `store.ts`, campo `novas`) e não aqui: ele pertence ao instante em que o dado
// chega, e este componente pode nem estar montado nessa hora.
//
// Este arquivo é só a apresentação da fila: mostra a primeira, some sozinho, passa para a
// próxima.
import { useEffect } from 'react'
import { useEngagementStore } from './store'

/** Quanto tempo o aviso fica na tela antes de sair sozinho. */
export const DURACAO_MS = 6000

export function AchievementToast() {
  const atual = useEngagementStore((state) => state.novas[0])
  const dispensar = useEngagementStore((state) => state.dispensarNova)

  useEffect(() => {
    if (!atual) return
    // Uma de cada vez, e por tempo: duas conquistas ganhas na mesma sessão (acontece — a
    // primeira sessão de alguém dispara `primeira-sessao` e pode disparar outra) empilhariam
    // dois cartões um sobre o outro se aparecessem juntas.
    const timer = setTimeout(dispensar, DURACAO_MS)
    return () => clearTimeout(timer)
  }, [atual, dispensar])

  if (!atual) return null

  return (
    <div className="ach-toast" role="status" aria-live="polite">
      <span className="ach-toast__badge" aria-hidden="true">
        🎖️
      </span>
      <span className="ach-toast__texto">
        <strong className="ach-toast__title">Nova conquista</strong>
        <span className="ach-toast__name">{atual.name}</span>
      </span>
      <button
        type="button"
        className="ach-toast__close"
        onClick={dispensar}
        aria-label="Fechar aviso"
      >
        ×
      </button>
    </div>
  )
}
