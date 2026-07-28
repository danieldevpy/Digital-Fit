import { CameraView } from './capture/CameraView'
import { CoachTip } from './hud/CoachTip'
import { ExerciseCard } from './hud/ExerciseCard'
import { StatsBar } from './hud/StatsBar'
import { ReportSheet } from './report/ReportSheet'
import { useSession } from './session/useSession'
import { TabBar } from './shell/TabBar'
import { useSessionStore } from './store/session'

export function App() {
  const cameraStatus = useSessionStore((state) => state.cameraStatus)

  // A sessão só conversa com o gateway quando a câmera está de pé.
  useSession(cameraStatus === 'ready')

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

      {/* Por último no DOM de propósito: cobre a sessão inteira quando ela termina. */}
      <ReportSheet />
    </div>
  )
}
