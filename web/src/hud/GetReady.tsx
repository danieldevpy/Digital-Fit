// Preparação entre "corpo medido" e "vale agora" (T-049 / SPEC-004).
//
// A regra de UX que guiou o desenho: **isto não pode virar mais uma espera**. A pessoa já
// esperou a câmera abrir, o modelo carregar e o corpo ser medido. Um quarto passo com texto
// para ler seria atrito.
//
// Então o número é enorme, sozinho, no centro, e cada segundo tem uma batida visual própria
// (a animação reinicia a cada troca porque a `key` muda). Sem botão, sem instrução: quem está
// a três segundos de pular não vai ler uma frase. O único texto é o "JÁ!", que aparece no
// instante da virada e some junto com a tela.
import { useEffect, useState } from 'react'
import { useSessionStore } from '../store/session'

/** Quanto falta, em segundos inteiros — 3, 2, 1 e então 0 (que vira "JÁ!"). */
function segundosRestantes(ate: number, agora: number): number {
  return Math.max(0, Math.ceil((ate - agora) / 1000))
}

export function GetReady() {
  const sessionStatus = useSessionStore((state) => state.sessionStatus)
  const countingFrom = useSessionStore((state) => state.countingFrom)
  const [agora, setAgora] = useState(() => Date.now())

  const ativo = sessionStatus === 'preparing' && countingFrom !== null

  useEffect(() => {
    if (!ativo) return
    // 100 ms e não 1000: o número tem de trocar junto com o relógio, não até 1 s depois dele.
    const id = setInterval(() => setAgora(Date.now()), 100)
    return () => clearInterval(id)
  }, [ativo])

  if (!ativo || countingFrom === null) return null

  const restam = segundosRestantes(countingFrom, agora)
  const rotulo = restam > 0 ? String(restam) : 'JÁ!'

  return (
    <div className="getready" role="status" aria-live="assertive">
      {/* `key` no próprio número: trocar de "3" para "2" remonta o nó e a animação recomeça.
          Sem isso o CSS animaria uma vez só e os outros segundos entrariam sem batida. */}
      <p key={rotulo} className={`getready__tick ${restam === 0 ? 'getready__tick--go' : ''}`}>
        {rotulo}
      </p>
      <p className="getready__hint">preparando…</p>
    </div>
  )
}
