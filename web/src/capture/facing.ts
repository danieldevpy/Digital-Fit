// Qual câmera olha, e o que cai disso (SPEC-027 §A/§B).
//
// Tudo aqui é função pura: `useCamera.ts` tem `getUserMedia`, `<video>` e permissão, e nada
// disso é testável em `environment: 'node'`. As DECISÕES — que restrição pedir, em que
// direção espelhar, se o controle existe — moram neste arquivo justamente para poderem ser
// cobradas sem câmera, que é a regra da casa para lógica de análise e vale igual aqui.

/**
 * A INTENÇÃO, não o hardware: "a que aponta para mim" × "a que aponta para longe de mim".
 *
 * Nunca `deviceId` (SPEC-027 §A). Um `deviceId` aponta para uma lente específica —
 * grande-angular, teleobjetiva — e o mapeamento muda entre versões de sistema e entre
 * navegadores no mesmo aparelho. Guardar a lente seria guardar um endereço que se muda
 * sozinho; guardar a intenção é guardar o que a pessoa quis dizer.
 */
export type Facing = 'user' | 'environment'

/** Quem treina sozinho é a maioria, e para essa pessoa a frontal é a câmera do produto. */
export const FACING_DEFAULT: Facing = 'user'

export function isFacing(valor: unknown): valor is Facing {
  return valor === 'user' || valor === 'environment'
}

export function otherFacing(atual: Facing): Facing {
  return atual === 'user' ? 'environment' : 'user'
}

/**
 * O espelho é CONSEQUÊNCIA da câmera, não gosto (SPEC-027 §B).
 *
 * Frontal espelha: quem treina de frente para o aparelho espera se ver como num espelho, e
 * levantar o braço direito tem de levantar o braço direito do outro lado da tela. Traseira
 * não espelha: quem segura o celular não está se vendo, está vendo OUTRA pessoa de fora — ali
 * o espelho inverteria a cena para o operador e para qualquer olho que revisse depois.
 *
 * O botão Espelhar continua existindo e continua vencendo; isto é só o valor com que a tela
 * abre a cada vez que a câmera muda.
 */
export function mirrorDefaultFor(facing: Facing): boolean {
  return facing === 'user'
}

/**
 * Quem manda no rótulo é o TRACK, não o pedido (SPEC-027 §A).
 *
 * Aparelho que ignora a restrição sem levantar erro existe, e nesse caso o botão passaria a
 * dizer "traseira" sobre uma imagem frontal. `fallback` cobre o navegador que simplesmente não
 * relata `facingMode` (desktop, quase sempre): ali não há o que corrigir, e o pedido é a melhor
 * informação disponível.
 */
export function facingFromSettings(
  settings: { facingMode?: string } | undefined,
  fallback: Facing,
): Facing {
  const relatado = settings?.facingMode
  return isFacing(relatado) ? relatado : fallback
}

/**
 * O controle só existe onde há escolha — mesmo precedente do `ZoomControl`, que só aparece
 * quando o hardware expõe `zoom.min < 1`. Controle que não faz nada é pior que controle
 * ausente: ele ensina que o app está quebrado.
 *
 * A contagem roda DEPOIS de o stream abrir (`useCamera.ts`), porque antes da permissão o
 * navegador devolve entradas sem `label` e, em parte deles, sem contagem confiável.
 *
 * iPhone lista várias `videoinput` da traseira (as lentes). Isso não atrapalha: a única
 * pergunta que o controle faz é "há mais de uma?", e qual delas ninguém escolhe.
 */
export function hasCameraChoice(devices: readonly { kind: string }[]): boolean {
  return devices.filter((device) => device.kind === 'videoinput').length >= 2
}

/**
 * `ideal` para abrir, `exact` para trocar — e a diferença não é estilo (SPEC-027 §A).
 *
 * `{ ideal: 'environment' }` num aparelho sem traseira **não falha**: entrega a frontal em
 * silêncio, e o botão passaria a mentir sobre qual câmera está no ar. Na troca, portanto, vale
 * `exact`, cujo `OverconstrainedError` é a única forma de descobrir que o aparelho não tem a
 * câmera pedida. Na abertura normal vale `ideal`: ali não há nada para descobrir, e falhar a
 * abertura inteira porque a câmera preferida sumiu seria trocar um rótulo errado por uma tela
 * preta.
 */
export function facingConstraint(
  facing: Facing,
  precisao: 'ideal' | 'exact',
): MediaTrackConstraints {
  return precisao === 'exact' ? { facingMode: { exact: facing } } : { facingMode: { ideal: facing } }
}
