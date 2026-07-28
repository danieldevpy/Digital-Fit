import { CameraView } from './capture/CameraView'
import { CoachTip } from './hud/CoachTip'
import { ExerciseCard } from './hud/ExerciseCard'
import { StatsBar } from './hud/StatsBar'
import { TabBar } from './shell/TabBar'

export function App() {
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
    </div>
  )
}
