// Relógio que provoca re-render, para quem precisa expirar algo por tempo.
//
// Ler `Date.now()` direto no render é impuro e, pior, silencioso: o valor só
// mudaria quando outra coisa causasse re-render, e o card ficaria preso no
// último aviso mesmo depois de vencido.
import { useEffect, useState } from 'react'

export function useNow(active: boolean, intervalMs = 500): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(timer)
  }, [active, intervalMs])

  return now
}
