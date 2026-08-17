import { afterEach, describe, expect, it, vi } from 'vitest'

import { installStorage, uninstallStorage } from '../auth/testStorage'
import { requestSession } from './admission'
import {
  EXERCISE_VIEWS,
  currentView,
  setViewPreference,
  viewPreference,
  viewsOf,
} from './exerciseViews'

afterEach(() => {
  uninstallStorage()
  vi.restoreAllMocks()
})

describe('variação de câmera (T-111)', () => {
  it('exercício sem variação não oferece escolha nenhuma', () => {
    installStorage()

    // Mesma regra do `offersChoice` do catálogo: a superfície aparece quando existe o que
    // escolher. O polichinelo é de frente e ponto — perguntar seria um toque sem resposta.
    expect(viewsOf('jumping_jack')).toBeUndefined()
    expect(viewPreference('jumping_jack')).toBeNull()
    expect(currentView('jumping_jack')).toBeUndefined()
  })

  it('quem nunca escolheu recebe a primeira variação, que é a que o Guia já ensinava', () => {
    installStorage()

    // `profile` é o default por continuidade: é a vista das fotos do Guia desde a T-106, e
    // mudar o default embaixo de quem já aprendeu a montar a cena seria trocar o produto sem
    // avisar. As duas contam exato no corpus.
    expect(viewPreference('flexao')).toBe('profile')
    expect(currentView('flexao')?.id).toBe('profile')
  })

  it('a escolha sobrevive à próxima sessão, e é POR EXERCÍCIO', () => {
    const fake = installStorage()

    setViewPreference('flexao', 'frontal')

    expect(viewPreference('flexao')).toBe('frontal')
    expect(fake.store.get('digitalfit.view.flexao')).toBe('frontal')
    // Nada foi decidido em nome de outro exercício.
    expect(fake.store.get('digitalfit.view.abdominal')).toBeUndefined()
  })

  it('id que não existe mais cai no default em vez de virar escolha fantasma', () => {
    // O mesmo caso do slug morto do `exercisePreference`: um valor guardado hoje pode deixar
    // de existir amanhã, e a tela mostraria uma escolha que o servidor ignora.
    const fake = installStorage()
    fake.store.set('digitalfit.view.flexao', 'de-cabeca-para-baixo')

    expect(viewPreference('flexao')).toBe('profile')
  })

  it('gravar lixo cai no default em vez de gravar lixo', () => {
    installStorage()

    expect(setViewPreference('flexao', 'obliqua' as never)).toBe('profile')
    expect(viewPreference('flexao')).toBe('profile')
  })

  it('sem armazenamento (Safari privado) o app segue com o default', () => {
    installStorage({ readOnly: true })

    expect(() => setViewPreference('flexao', 'frontal')).not.toThrow()
    expect(viewPreference('flexao')).toBe('profile')
  })

  it('cada variação traz cena e passos próprios — é isso que ela muda', () => {
    // Se as duas dessem a mesma instrução, a escolha não teria consequência nenhuma: o que a
    // pessoa faz ANTES de deitar no chão é o conteúdo inteiro desta decisão.
    const [lado, frente] = EXERCISE_VIEWS.flexao!

    expect(lado!.scene_tip).not.toBe(frente!.scene_tip)
    expect(lado!.phone).toContain('deitado')
    expect(frente!.phone).toContain('em pé')
    expect(lado!.guide_steps).toHaveLength(3)
    expect(frente!.guide_steps).toHaveLength(3)
  })

  it('os ids são os do contrato de eventos, e não rótulos de tela', () => {
    // "De lado" é o que a pessoa lê; `profile` é o que o `session.started` carrega. Trocar um
    // pelo outro faria a escolha atravessar a rede e não significar nada no worker.
    expect(EXERCISE_VIEWS.flexao!.map((v) => v.id)).toEqual(['profile', 'frontal'])
  })
})

describe('a variação atravessa a admissão (T-111)', () => {
  function fetchFalso() {
    // Tipado como `fetch` porque é o SEGUNDO argumento que este teste inspeciona: um
    // `vi.fn(async () => ...)` sem assinatura faz o TypeScript concluir que a chamada não tem
    // argumento nenhum, e `calls[0][1]` vira erro de tipo.
    return vi.fn<typeof fetch>(async () =>
      new Response(
        JSON.stringify({
          session_id: 's',
          token: 't',
          ws_url: 'ws://x/ws/session/s?token=t',
          mode: 'edge',
          exercise: 'flexao',
          duration_s: 30,
          expires_at: 1,
          quota: { allowed: true, used: 0, limit: 10, unlimited: false },
        }),
        { status: 200 },
      ),
    )
  }

  it('vai no corpo do POST /sessions — senão seria enfeite de tela', () => {
    installStorage()
    const fetchImpl = fetchFalso()

    void requestSession(
      { exercise: 'flexao', requestedMode: 'edge', probe: null, view: 'frontal' },
      fetchImpl,
    )

    const corpo = JSON.parse(fetchImpl.mock.calls[0]![1]!.body as string)
    expect(corpo.view).toBe('frontal')
  })

  it('exercício sem variação não manda campo nenhum', () => {
    installStorage()
    const fetchImpl = fetchFalso()

    void requestSession(
      { exercise: 'jumping_jack', requestedMode: 'edge', probe: null, view: null },
      fetchImpl,
    )

    // Ausente, e não `""` ou `null`: ausência já significa "ninguém disse" no contrato, e o
    // exercício cai na detecção geométrica.
    expect(JSON.parse(fetchImpl.mock.calls[0]![1]!.body as string)).not.toHaveProperty('view')
  })
})
