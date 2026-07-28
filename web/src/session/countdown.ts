// Countdown COSMÉTICO dos 30s (SPEC-013 §3): a autoridade do fim da sessão é o
// servidor (SPEC-009) — quem encerra é `session.completed`, não este relógio.
import { useEffect, useState } from 'react'
import { useSessionStore } from '../store/session'

/** Cadência do tique. 250ms mantém o segundo trocando sem custo perceptível. */
const TICK_MS = 250

export function secondsLeft(startedAt: number | null, durationS: number, now: number): number {
  if (startedAt === null) return durationS
  const elapsed = (now - startedAt) / 1000
  return Math.max(0, Math.min(durationS, Math.ceil(durationS - elapsed)))
}

export function formatClock(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds))
  const minutes = Math.floor(safe / 60)
  const rest = safe % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

export function useCountdown(): { secondsLeft: number; durationS: number } {
  const startedAt = useSessionStore((state) => state.startedAt)
  const durationS = useSessionStore((state) => state.durationS)
  const sessionStatus = useSessionStore((state) => state.sessionStatus)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (sessionStatus !== 'running') return
    const timer = setInterval(() => setNow(Date.now()), TICK_MS)
    return () => clearInterval(timer)
  }, [sessionStatus])

  return { secondsLeft: secondsLeft(startedAt, durationS, now), durationS }
}
