// Controle de dev do gravador de fixtures (T-007). Não faz parte da UI de
// produto — a SPEC-013 não prevê nada disso na tela de sessão.
import { EDGE_TARGET_FPS } from '../capture/frameClock'
import { toCapabilityData } from '../probe/runProbe'
import { useSessionStore } from '../store/session'
import { downloadFixture, getFixtureRecorder, startNewRecording } from './recorder'

export function FixtureControls() {
  const recording = useSessionStore((state) => state.recording)
  const recordedFrames = useSessionStore((state) => state.recordedFrames)
  const capability = useSessionStore((state) => state.capability)
  const videoResolution = useSessionStore((state) => state.videoResolution)
  const setRecording = useSessionStore((state) => state.setRecording)
  const setRecordedFrames = useSessionStore((state) => state.setRecordedFrames)

  const start = () => {
    const recorder = startNewRecording()
    recorder.setContext({
      capability: capability ? toCapabilityData(capability) : null,
      video: videoResolution,
      fps: EDGE_TARGET_FPS,
    })
    setRecordedFrames(0)
    setRecording(true)
  }

  const stopAndSave = () => {
    const recorder = getFixtureRecorder()
    recorder.stop()
    setRecording(false)
    if (recorder.frameCount === 0) return

    // `prompt` é feio, mas é ferramenta de dev: um modal próprio seria escopo
    // que a task não pede.
    const label = window.prompt('Rótulo da fixture', 'polichinelo')
    if (label === null) return

    // `expected_reps` é o rótulo que faz a fixture valer como teste: sem ele o
    // núcleo tem os keypoints mas não sabe qual é a resposta certa.
    const reps = window.prompt('Quantas repetições você fez? (vazio = não sei)', '')
    const expected_reps = reps && Number.isFinite(Number(reps)) ? Number(reps) : null

    downloadFixture(recorder.build({ label, expected_reps }))
  }

  return (
    <button
      type="button"
      className={`stage__dev-rec ${recording ? 'stage__dev-rec--on' : ''}`}
      onClick={recording ? stopAndSave : start}
      title="Gravar fixture de keypoints para os testes do núcleo"
    >
      {recording ? `● gravando ${recordedFrames}` : '● gravar fixture'}
    </button>
  )
}
