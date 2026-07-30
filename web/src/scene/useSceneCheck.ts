// Amostragem da cena na pré-configuração (T-085).
//
// Uma foto de 160×120 por segundo, num canvas que nunca entra no DOM, para responder três
// perguntas que quem está do outro lado do celular não consegue responder sozinho: está
// escuro? a luz está atrás? a lente está suja?
//
// **A imagem não sai do aparelho.** No modo edge nada de pixel sobe (é a promessa
// keypoint-first da arquitetura), e é por isso que esta medição só pode acontecer aqui, no
// cliente — o servidor não tem o que olhar. A SPEC-003 já previa exatamente este desenho
// ("amostrado 1×/s no edge via canvas").
//
// O custo é desprezível perto do que roda ao lado: ~19k pixels, duas passadas, uma vez por
// segundo — ordens de grandeza abaixo de uma inferência de pose, que acontece 15× por segundo
// no mesmo vídeo.
import { useEffect, type RefObject } from 'react'
import { useSessionStore } from '../store/session'
import {
  AMOSTRA_ALTURA,
  AMOSTRA_LARGURA,
  STREAK_INICIAL,
  acumular,
  avaliarCena,
  confirmado,
  measureScene,
  type SceneStreak,
} from './sceneQuality'

/** Uma amostra por segundo: é o intervalo que a SPEC-003 prevê para a análise de luz. */
export const INTERVALO_MS = 1000

export function useSceneCheck(videoRef: RefObject<HTMLVideoElement | null>, enabled: boolean) {
  useEffect(() => {
    const { setSceneAdvice } = useSessionStore.getState()
    if (!enabled) {
      setSceneAdvice(null)
      return
    }

    const video = videoRef.current
    if (!video) return

    const canvas = document.createElement('canvas')
    canvas.width = AMOSTRA_LARGURA
    canvas.height = AMOSTRA_ALTURA
    // `willReadFrequently`: sem isto o navegador tende a manter o canvas na GPU e cada
    // `getImageData` paga uma leitura de volta, que é justamente o que fazemos toda vez.
    const contexto = canvas.getContext('2d', { willReadFrequently: true })
    if (!contexto) return

    let streak: SceneStreak = STREAK_INICIAL

    const amostrar = () => {
      if (video.readyState < video.HAVE_CURRENT_DATA || video.videoWidth === 0) return

      contexto.drawImage(video, 0, 0, AMOSTRA_LARGURA, AMOSTRA_ALTURA)
      let dados: ImageData
      try {
        dados = contexto.getImageData(0, 0, AMOSTRA_LARGURA, AMOSTRA_ALTURA)
      } catch {
        // Canvas contaminado (fonte de outra origem). Não acontece com `getUserMedia`, mas se
        // acontecer o certo é ficar quieto: um aviso de cena não vale um erro na tela de quem
        // só quer treinar.
        return
      }

      const conselho = avaliarCena(measureScene(dados.data, AMOSTRA_LARGURA, AMOSTRA_ALTURA))
      streak = acumular(streak, conselho?.code ?? null)
      // Só mexe na tela com o veredito confirmado — inclusive para APAGAR o aviso. Alguém
      // passando na frente da luz não acende nada, e uma amostra boa solta não apaga um aviso
      // que continua valendo.
      if (confirmado(streak)) setSceneAdvice(conselho)
    }

    const timer = setInterval(amostrar, INTERVALO_MS)
    return () => {
      clearInterval(timer)
      useSessionStore.getState().setSceneAdvice(null)
    }
  }, [videoRef, enabled])
}
