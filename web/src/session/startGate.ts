// Portão do CTA da pré-configuração: só se inicia o exercício com a câmera JÁ ligada.
//
// Até aqui o "Iniciar Exercício" fazia duas coisas de uma vez — pedia a câmera e navegava para
// o treino. Quem chegava com a câmera desligada saía da pré-configuração no exato instante em
// que o navegador abre o diálogo de permissão: o treino começava com a pessoa lendo um popup,
// e o enquadramento (silhueta-guia, espelhar, zoom, aviso de cena) — que é a razão de esta
// tela existir — passava batido. Pior no caso de permissão negada: navegava do mesmo jeito,
// para uma tela de treino sem imagem nenhuma.
//
// A regra, então: o CTA tem dois degraus. Primeiro ligar a câmera e se ver; só depois iniciar.
//
// Função pura e separada do componente pelo mesmo motivo do `pipelineGate`: é uma REGRA de
// ordem, e regra se testa com uma tabela de estados, não montando React.
import type { CameraStatus } from '../store/session'

/** O que o toque no CTA faz agora. `aguardar` não faz nada — é o botão travado. */
export type StartAction = 'ligar' | 'aguardar' | 'iniciar'

export interface StartCta {
  action: StartAction
  label: string
  /** Só enquanto o navegador decide a permissão: tocar de novo não adianta e reabre nada. */
  disabled: boolean
}

/**
 * `denied` e `error` continuam clicáveis e com o mesmo rótulo de `idle`: o motivo da falha já
 * está escrito na capa da câmera (`CameraView`), e o que sobra ao botão é a única coisa útil —
 * tentar de novo depois de liberar a permissão no navegador.
 */
export function ctaDeInicio(cameraStatus: CameraStatus): StartCta {
  if (cameraStatus === 'ready') return { action: 'iniciar', label: 'Iniciar Exercício', disabled: false }
  if (cameraStatus === 'requesting') return { action: 'aguardar', label: 'Abrindo câmera…', disabled: true }
  return { action: 'ligar', label: 'Ligar câmera', disabled: false }
}
