// Contador `seq` do cliente.
//
// O contrato diz: "contador monotônico **por sessão** (nunca repete nem
// retrocede)" — por SESSÃO, não por tipo de evento. Então `session.capability` e
// os `pose.frame` não podem ter cada um o seu contador começando em 0.
//
// Por isso o `seq` do envelope sai daqui, e não do frame clock: o frame clock
// continua dono do `ts` e da decimação, mas o número que vai no fio é deste
// sequenciador, compartilhado por tudo que o cliente emite.
//
// Ver a descoberta [B/T-004] no BACKLOG: se o Agente A decidir que `seq` é por
// tipo, este módulo some e o frame clock volta a ser a fonte.

export interface ClientSequencer {
  /** Próximo `seq`. Nunca repete nem retrocede dentro da sessão. */
  next(): number
  readonly current: number
  reset(): void
}

export function createClientSequencer(): ClientSequencer {
  let seq = 0
  return {
    next: () => seq++,
    get current() {
      return seq
    },
    reset() {
      seq = 0
    },
  }
}
