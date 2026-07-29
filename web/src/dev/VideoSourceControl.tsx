// Fonte de vídeo do painel de dev (T-040). Não é UI de produto — vive dentro do chip de
// diagnóstico, que por sua vez está atrás do gate da T-048.
//
// Dois botões e nada mais: escolher o arquivo, e baixar o que o navegador contou. O segundo
// só aparece quando existe relatório, porque antes disso não há o que exportar.
import { useRef } from 'react'
import { useSessionStore } from '../store/session'
import { buildParityResult, downloadParityResult } from './parityExport'
import { ACCEPTED_TYPES, shortName } from './videoSource'

export function VideoSourceControl() {
  const inputRef = useRef<HTMLInputElement>(null)
  const cameraControls = useSessionStore((state) => state.cameraControls)
  const videoSource = useSessionStore((state) => state.videoSource)
  const videoFileName = useSessionStore((state) => state.videoFileName)
  const report = useSessionStore((state) => state.report)
  const frameStats = useSessionStore((state) => state.frameStats)
  const poseDelegate = useSessionStore((state) => state.poseDelegate)

  const escolher = (evento: React.ChangeEvent<HTMLInputElement>) => {
    const arquivo = evento.target.files?.[0]
    if (arquivo) cameraControls?.startFile(arquivo)
    // Zera para que escolher o MESMO arquivo de novo dispare o `change` — repetir a medição
    // é o uso mais comum aqui.
    evento.target.value = ''
  }

  const exportar = () => {
    if (!report) return
    downloadParityResult(
      buildParityResult({
        report,
        videoName: videoFileName ? shortName(videoFileName) : 'sessao',
        frames: frameStats ? frameStats.seq + 1 : 0,
        delegate: poseDelegate,
        userAgent: navigator.userAgent,
      }),
    )
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        onChange={escolher}
        style={{ display: 'none' }}
      />
      <button type="button" className="stage__dev-stop" onClick={() => inputRef.current?.click()}>
        vídeo
      </button>
      {videoSource === 'file' && videoFileName && (
        <span title={videoFileName}>arq {shortName(videoFileName)}</span>
      )}
      {report && videoSource === 'file' && (
        <button type="button" className="stage__dev-stop" onClick={exportar}>
          baixar json
        </button>
      )}
    </>
  )
}
