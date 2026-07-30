// Portão de partida da sessão (T-069).
//
// O bug que originou este módulo: a sessão abria em `cameraStatus === 'ready'`, o MESMO sinal
// que dispara o carregamento do pipeline. Só que o servidor começa a contar os 10s de
// `no_data` na ADMISSÃO (SPEC-009), e entre a câmera abrir e o primeiro `pose.frame` sair o
// cliente ainda precisa baixar ~17 MB de WASM + modelo, compilar, inicializar a GPU e gastar
// 2s no probe. Em aparelho com cache frio — uma aba anônima é isso para sempre — o prazo
// estourava antes do primeiro frame, e a sessão morria dizendo "paramos de te ver na câmera".
// A pessoa estava lá, no lugar certo. Quem não estava pronto era o app.
//
// A regra, então: não se pede ao servidor uma sessão que ainda não se tem como alimentar.
//
// Função pura e de propósito separada do store: é uma REGRA de ordem, e regra se testa com
// uma tabela de estados, não montando React.
import type { PoseStatus, ProbeStatus } from '../store/session'

export interface PipelineGateInput {
  poseStatus: PoseStatus
  probeStatus: ProbeStatus
}

/**
 * O pipeline já tem como emitir frame?
 *
 * Exige o landmarker de pé E o probe decidido, porque é depois do probe que o laço de envio
 * começa — seja o de edge (landmarks) ou o de cloud (JPEG). `probeStatus === 'error'` conta
 * como decidido: probe que falha não impede a sessão, decide CLOUD (SPEC-001) e o laço sobe
 * igual. Já `poseStatus === 'error'` não abre nada: sem landmarker não existe frame para
 * enviar, e abrir sessão nesse estado só produziria um `no_data` de 10s.
 */
export function podeAlimentarSessao({ poseStatus, probeStatus }: PipelineGateInput): boolean {
  if (poseStatus !== 'ready') return false
  return probeStatus === 'done' || probeStatus === 'error'
}

/** Em que ponto do aquecimento o pipeline está — é o que a tela precisa dizer a quem espera. */
export type PipelinePhase = 'parado' | 'carregando' | 'medindo' | 'pronto' | 'falhou'

export function pipelinePhase({ poseStatus, probeStatus }: PipelineGateInput): PipelinePhase {
  if (poseStatus === 'error') return 'falhou'
  if (poseStatus === 'idle') return 'parado'
  if (poseStatus === 'loading') return 'carregando'
  if (probeStatus === 'running') return 'medindo'
  return podeAlimentarSessao({ poseStatus, probeStatus }) ? 'pronto' : 'carregando'
}
