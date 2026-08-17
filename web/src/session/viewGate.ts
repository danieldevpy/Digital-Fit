// A trava de confirmação da variação de câmera (T-112).
//
// **Ela existe por um modo de falha, não por completude de interface.** A flexão tem duas
// vistas, e cada uma exige o celular num lugar diferente — deitado no chão ou em pé à frente.
// Quem não perceber a escolha monta a cena da vista errada, e o resultado não é uma contagem
// pior: é **zero**. E zero repetição não é lido como "montei errado", é lido como "esse app não
// funciona". A pessoa desinstala antes de descobrir que havia um botão.
//
// O controle da coluna (`ViewPicker` compacto) resolve para quem procura. Esta trava resolve
// para quem não sabe que precisa procurar — e essa é a maioria na primeira vez.
//
// Três regras, e a terceira é a que evita virar praga:
//
// 1. Só aparece para exercício que TEM variação. Polichinelo e agachamento nunca a veem.
// 2. Só aparece uma vez por visita à pré-configuração. Confirmou, ligou a câmera, tocou em
//    "Iniciar" — não pergunta de novo.
// 3. Quem marcar "não mostrar novamente" nunca mais a vê **naquele exercício**, e passa a
//    trocar pelo controle da coluna, que continua lá.
//
// A dispensa é POR EXERCÍCIO, como o guia visto e a própria variação. Não é detalhe: no dia em
// que outro exercício ganhar vistas, ele terá a mesma decisão de cena para ensinar, e herdar o
// "já sei" da flexão devolveria exatamente a sessão zerada que esta trava existe para impedir.
import { viewsOf } from './exerciseViews'

const DISPENSA_PREFIX = 'digitalfit.view_gate_off.'

/**
 * Quem marcou "não mostrar novamente" para este exercício.
 *
 * Sem armazenamento (Safari privado) devolve `false`: na dúvida a trava aparece. É o lado certo
 * do erro — o custo de perguntar de novo é um toque, e o custo de não perguntar é a sessão
 * inteira zerada.
 */
export function viewGateDismissed(exercise: string): boolean {
  try {
    return window.localStorage.getItem(DISPENSA_PREFIX + exercise) === '1'
  } catch {
    return false
  }
}

export function dismissViewGate(exercise: string): void {
  try {
    window.localStorage.setItem(DISPENSA_PREFIX + exercise, '1')
  } catch {
    // Sem armazenamento: a trava volta na próxima visita. Chato, não quebrado.
  }
}

/** Desfaz a dispensa. Existe para a tela poder oferecer o caminho de volta, e para os testes. */
export function restoreViewGate(exercise: string): void {
  try {
    window.localStorage.removeItem(DISPENSA_PREFIX + exercise)
  } catch {
    // idem
  }
}

/**
 * A trava tem de aparecer agora?
 *
 * `confirmadoPara` é o exercício já confirmado NESTA visita à tela — estado do componente, não
 * armazenamento. É o que faz a trava aparecer uma vez só: ela intercepta o "Ligar câmera", e
 * o "Iniciar Exercício" que vem depois passa direto.
 */
export function shouldConfirmView(
  exercise: string,
  { confirmadoPara }: { confirmadoPara?: string | null } = {},
): boolean {
  if (!viewsOf(exercise)) return false
  if (confirmadoPara === exercise) return false
  return !viewGateDismissed(exercise)
}
