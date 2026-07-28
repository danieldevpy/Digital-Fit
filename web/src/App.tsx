import { CameraView } from './capture/CameraView'

export function App() {
  return (
    <main className="app">
      <header className="app__header">
        <h1>Digital Fit</h1>
        <p>T-003 · validação visual: webcam + MediaPipe Pose (edge)</p>
      </header>
      <CameraView />
    </main>
  )
}
