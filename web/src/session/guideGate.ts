// Quando o exemplo guiado aparece sozinho, e quando o link que o reabre chama atenção.
//
// A regra da SPEC-015 era "uma vez por exercício, para todo mundo". Ela tratava o exemplo como
// **onboarding** — algo que se consome e se encerra. Na prática ele é outra coisa: é a
// instrução de ENQUADRAMENTO, e enquadramento errado não deixa a pessoa insegura, deixa a
// sessão zerada (a T-106 gastou uma task inteira nisso). Quem já treina sabe montar a cena;
// quem chegou agora, não — e "já viu uma vez" não é a mesma pergunta que "já sabe".
//
// Daí o eixo virar a IDENTIDADE em vez do histórico:
//
//   - **sem conta** → o exemplo abre toda vez que a pessoa TROCA de exercício. Não a cada
//     sessão: séries repetidas não passam por aqui, e transformar o exemplo em pedágio de
//     cada play seria fricção que a conta remove — o que a SPEC-011 recusa por escrito.
//   - **com conta** → nunca abre sozinho. Em troca, o link "ver exemplo" se destaca enquanto
//     aquele exercício não tiver sido visto, e emudece depois.
//
// O `guide_seen` continua sendo gravado e continua importando; ele só deixou de decidir a
// abertura para decidir o destaque.
import { storedTokens } from '../auth/storage'
import type { AccountStatus } from '../store/account'

/**
 * Esta pessoa tem conta, **até onde dá para saber agora**.
 *
 * O `status` do store nasce `unknown` e só vira `authenticated` quando o `fetchMe` volta — uma
 * ida à rede. E o caminho mais apertado do produto roda antes disso: a ponte `#/ex/<slug>` do
 * site dispara o `chooseExercise` num efeito de boot. Esperar o `fetchMe` ali abriria o exemplo
 * na cara de quem tem conta, que é exatamente o incômodo que esta mudança existe para tirar.
 *
 * O refresh guardado é o sinal SÍNCRONO que responde a tempo. Ele pode estar vencido — e nesse
 * caso alguém efetivamente deslogado deixa de ver o exemplo automático. É o erro barato dos
 * dois: o link continua na tela, destacado. O caro seria o contrário.
 */
export function temConta(status: AccountStatus): boolean {
  if (status !== 'unknown') return status === 'authenticated'
  return Boolean(storedTokens().refresh)
}

export interface EstadoDoExemplo {
  /** Abrir o exemplo agora, sem perguntar (a pessoa acabou de trocar de exercício). */
  abrirAgora: boolean
  /** O link "ver exemplo" deve chamar atenção nesta tela? */
  destacarLink: boolean
}

/**
 * As duas decisões saem da MESMA função de propósito: elas são complementares, e separadas
 * acabariam divergindo até existir o estado absurdo — o exemplo abre sozinho *e* o link pisca
 * pedindo que o abram.
 */
export function estadoDoExemplo({
  temConta,
  jaViu,
}: {
  temConta: boolean
  jaViu: boolean
}): EstadoDoExemplo {
  return {
    abrirAgora: !temConta,
    // Só para quem tem conta: quem não tem acabou de ver o exemplo inteiro, e destacar o link
    // de volta para o que se acabou de fechar é ruído.
    destacarLink: temConta && !jaViu,
  }
}
