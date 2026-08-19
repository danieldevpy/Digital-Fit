// Preferência de câmera (SPEC-027 §A). Mesma casa e mesmo motivo das outras preferências de
// conforto (`zoomPrefs.ts`, `session/preferences.ts`): fica no aparelho, não é meta do
// servidor e não exige conta — a SPEC-011 garante treinar sem cadastro, e uma preferência que
// só funcionasse depois de cadastrar seria uma pequena punição por não se cadastrar.
//
// O que se guarda é a INTENÇÃO (`user`/`environment`), nunca o `deviceId` — ver `facing.ts`.
//
// O espelho NÃO é guardado aqui, nem em lugar nenhum: ele se deduz da câmera
// (`mirrorDefaultFor`). Um segundo estado salvo seria um segundo jeito de a tela abrir errada.
import { FACING_DEFAULT, isFacing, type Facing } from './facing'

const FACING_KEY = 'digitalfit.camera_facing'

export function facingPreference(): Facing {
  try {
    const bruto = window.localStorage.getItem(FACING_KEY)
    // Nunca escolheu: vale o default do produto, não o que o aparelho listar primeiro.
    return isFacing(bruto) ? bruto : FACING_DEFAULT
  } catch {
    return FACING_DEFAULT
  }
}

export function setFacingPreference(facing: Facing): Facing {
  try {
    window.localStorage.setItem(FACING_KEY, facing)
  } catch {
    // Sem armazenamento (Safari privado): vale pela sessão atual e pronto.
  }
  return facing
}
