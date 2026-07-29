// Fonte de vídeo em arquivo (T-040 / SPEC-012, Fase Evolução).
//
// Substitui a câmera como origem do MESMO `<video>` que o pipeline edge já lê. É essa a razão
// de a task ser pequena: `useEdgePipeline` nunca soube de onde vinha a imagem — ele lê do
// elemento. Trocar `srcObject` (MediaStream) por `src` (blob do arquivo) não muda uma linha
// dele.
//
// O que isso destrava, e que nenhum teste do repositório fazia: medir o MediaPipe **do
// navegador** (WASM/GPU) contra um vídeo rotulado. O `eval/parity.py` diz isso na própria
// docstring — "o edge aqui é o MediaPipe do Python, não o do navegador" — e essa era a lacuna.
//
// Não é UI de produto: só existe atrás do gate da T-048.

/** Formatos que o `<video>` do navegador toca. O corpus da T-038 é mp4. */
export const ACCEPTED_TYPES = 'video/mp4,video/webm,video/quicktime,video/*'

export interface LoadedVideo {
  width: number
  height: number
  durationS: number
  /** Chamar ao trocar de arquivo: o object URL segura o blob na memória até ser revogado. */
  release: () => void
}

/**
 * Carrega o arquivo no elemento e **para no primeiro frame**.
 *
 * Parado de propósito: quem dá o play é o pipeline, depois do probe. Se tocasse já, os ~2 s
 * do capability probe comeriam o começo do vídeo — e o começo é justamente onde a pessoa está
 * parada para a calibração (SPEC-004). A contagem sairia sistematicamente diferente da do
 * harness, que lê o arquivo do frame zero, e a paridade mediria o próprio erro de montagem.
 */
export async function loadVideoFile(
  video: HTMLVideoElement,
  file: File,
): Promise<LoadedVideo> {
  const url = URL.createObjectURL(file)
  const release = () => URL.revokeObjectURL(url)

  video.srcObject = null
  video.src = url
  video.muted = true // sem isto o navegador recusa o play() programático
  video.loop = false
  video.playbackRate = 1

  try {
    await esperarMetadados(video)
  } catch (erro) {
    release()
    throw erro
  }

  await seekTo(video, 0)
  return {
    width: video.videoWidth,
    height: video.videoHeight,
    durationS: Number.isFinite(video.duration) ? video.duration : 0,
    release,
  }
}

function esperarMetadados(video: HTMLVideoElement): Promise<void> {
  if (video.readyState >= video.HAVE_METADATA) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const ok = () => {
      limpar()
      resolve()
    }
    const falha = () => {
      limpar()
      reject(new Error('Não consegui ler este vídeo. Tente um .mp4 (H.264).'))
    }
    const limpar = () => {
      video.removeEventListener('loadedmetadata', ok)
      video.removeEventListener('error', falha)
    }
    video.addEventListener('loadedmetadata', ok, { once: true })
    video.addEventListener('error', falha, { once: true })
  })
}

/**
 * Posiciona e espera o frame estar decodificado.
 *
 * O `seeked` não basta sozinho em todo navegador: ele pode disparar antes de `HAVE_CURRENT_DATA`,
 * e o pipeline descartaria os primeiros frames por `readyState` baixo — perdendo exatamente o
 * trecho parado que a calibração consome.
 */
export function seekTo(video: HTMLVideoElement, segundos: number): Promise<void> {
  if (video.currentTime === segundos && video.readyState >= video.HAVE_CURRENT_DATA) {
    return Promise.resolve()
  }
  return new Promise((resolve) => {
    const pronto = () => {
      if (video.readyState < video.HAVE_CURRENT_DATA) return
      video.removeEventListener('seeked', pronto)
      video.removeEventListener('canplay', pronto)
      resolve()
    }
    video.addEventListener('seeked', pronto)
    video.addEventListener('canplay', pronto)
    video.currentTime = segundos
  })
}

/** Volta ao início e toca. É o que o pipeline chama quando o probe termina. */
export async function rewindAndPlay(video: HTMLVideoElement): Promise<void> {
  await seekTo(video, 0)
  await video.play()
}

/** Nome sem extensão, para a UI e para o JSON de paridade casar com o nome do vídeo. */
export function shortName(fileName: string): string {
  return fileName.replace(/\.[^.]+$/, '')
}
