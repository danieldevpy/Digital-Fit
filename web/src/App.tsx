import { useEffect } from 'react'
import { AccountSheet } from './auth/AccountSheet'
import { fetchMe } from './auth/api'
import { CameraView } from './capture/CameraView'
import { CoachTip } from './hud/CoachTip'
import { ExerciseCard } from './hud/ExerciseCard'
import { StatsBar } from './hud/StatsBar'
import { ReportSheet } from './report/ReportSheet'
import { useSession } from './session/useSession'
import { TabBar } from './shell/TabBar'
import { useAccountStore } from './store/account'
import { useSessionStore } from './store/session'

export function App() {
  const cameraStatus = useSessionStore((state) => state.cameraStatus)

  // A sessão só conversa com o gateway quando a câmera está de pé.
  useSession(cameraStatus === 'ready')

  // Quem já tinha entrado continua entrado ao reabrir o app: o refresh está no
  // `localStorage`, e o `authedFetch` o usa para renovar o access sozinho. Falhar aqui é
  // normal e silencioso — significa apenas "ninguém logado", que é o estado padrão do produto.
  useEffect(() => {
    void fetchMe().then((user) => useAccountStore.getState().setUser(user))
  }, [])

  return (
    <div className="phone">
      <div className="viewport">
        <CameraView />
        <StatsBar />
      </div>

      <div className="sheet">
        <ExerciseCard />
        <CoachTip />
      </div>

      <TabBar />

      {/* Por último no DOM de propósito: cobrem a sessão inteira quando aparecem. */}
      <ReportSheet />
      <AccountSheet />
    </div>
  )
}
