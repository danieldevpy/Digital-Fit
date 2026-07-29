// Auxiliar de teste: `localStorage` de mentira. Os testes rodam em `environment: 'node'`, onde
// `window` não existe — e é justamente esse o caso que `storage.ts` tem de sobreviver. Aqui o
// `window` é instalado à mão para exercitar o outro caso: o navegador de verdade.
export interface FakeStorage {
  store: Map<string, string>
  /** Quando true, todo `setItem` lança — é o Safari em navegação privada. */
  readOnly: boolean
}

export function installStorage(options: { readOnly?: boolean } = {}): FakeStorage {
  const fake: FakeStorage = { store: new Map(), readOnly: options.readOnly ?? false }

  const localStorage = {
    getItem: (chave: string) => fake.store.get(chave) ?? null,
    setItem: (chave: string, valor: string) => {
      if (fake.readOnly) throw new DOMException('QuotaExceededError')
      fake.store.set(chave, valor)
    },
    removeItem: (chave: string) => {
      fake.store.delete(chave)
    },
  }

  ;(globalThis as { window?: unknown }).window = { localStorage }
  return fake
}

export function uninstallStorage(): void {
  delete (globalThis as { window?: unknown }).window
}
