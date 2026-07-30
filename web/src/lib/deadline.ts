// Prazo para promessa que pode não voltar nunca (T-069).
//
// Nasceu do delegate GPU do MediaPipe: `createFromOptions` cai para CPU só quando REJEITA, e
// uma inicialização de GPU que trava não rejeita — fica pendente para sempre. O resultado era
// um app parado em "preparando", sem erro, sem fallback e sem nada na tela explicando.
//
// Promessa não se cancela em JS. Então o prazo tem duas partes: desistir de esperar, e ter um
// destino para o valor que chegar tarde. Sem a segunda, um contexto de GPU nasceria depois do
// fallback e ficaria vivo em paralelo com o de CPU.

export class DeadlineError extends Error {
  constructor(oQue: string, ms: number) {
    super(`${oQue}: tempo esgotado após ${ms}ms`)
    this.name = 'DeadlineError'
  }
}

export interface DeadlineOptions<T> {
  /** Nome do que estava sendo esperado, para a mensagem de erro. */
  oQue: string
  /** Destino do valor que chegar depois do prazo — é aqui que se fecha o recurso órfão. */
  aoChegarTarde?: (valor: T) => void
}

/**
 * Rejeita com `DeadlineError` se `promessa` não resolver em `ms`.
 *
 * O `setTimeout` é limpo nos dois caminhos: sem isso, um prazo de 12s manteria um timer vivo
 * (e o Node esperando por ele nos testes) muito depois de a promessa já ter voltado.
 */
export function comPrazo<T>(
  promessa: Promise<T>,
  ms: number,
  { oQue, aoChegarTarde }: DeadlineOptions<T>,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    let decidido = false

    const timer = setTimeout(() => {
      if (decidido) return
      decidido = true
      reject(new DeadlineError(oQue, ms))
    }, ms)

    promessa.then(
      (valor) => {
        clearTimeout(timer)
        if (decidido) {
          // Chegou tarde: quem pediu já seguiu por outro caminho. O valor não pode
          // simplesmente vazar — devolvê-lo aqui é o que permite fechá-lo.
          aoChegarTarde?.(valor)
          return
        }
        decidido = true
        resolve(valor)
      },
      (erro: unknown) => {
        clearTimeout(timer)
        // Rejeição depois do prazo é silenciosa de propósito: o erro já foi reportado como
        // prazo esgotado, e um segundo throw viraria `unhandledrejection` sem dono.
        if (decidido) return
        decidido = true
        reject(erro)
      },
    )
  })
}
