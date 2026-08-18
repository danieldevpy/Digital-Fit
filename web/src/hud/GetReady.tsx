// Preparação entre "corpo medido" e "vale agora" (T-049 / SPEC-004).
//
// A tela tem UM trabalho: deixar claro que aquilo é tempo de se preparar e que o exercício
// começa quando acabar. Alguém que veja isto pela primeira vez não pode ficar em dúvida se já
// devia estar pulando — errar isso custa as primeiras repetições.
//
// Daí a estrutura em três níveis, do mais rápido de ler para o mais lento:
//
//   1. o anel que se esvazia — dá o "está acabando" no periférico, sem leitura nenhuma;
//   2. o número gigante — dá o quanto falta;
//   3. a linha de apoio — diz o que fazer, e some no instante em que a ação começa.
//
// O anel repete o vocabulário do `TimerRing` dos 30 s (mesmo gradiente, mesma técnica) porque
// é a mesma ideia visual: um tempo que corre. Aprender duas linguagens para dois relógios no
// mesmo produto seria custo sem retorno.
import { useEffect, useState } from 'react'
import { useT } from '../i18n'
import { getExercise } from '../session/catalog'
import {
  DIAL_CIRCUMFERENCE,
  DIAL_RADIUS,
  DIAL_SIZE,
  DIAL_STROKE,
  fracaoRestante,
  segundosRestantes,
} from './getReadyDial'
import { useSessionStore } from '../store/session'

export function GetReady() {
  const t = useT()
  const sessionStatus = useSessionStore((state) => state.sessionStatus)
  const countingFrom = useSessionStore((state) => state.countingFrom)
  const exerciseKey = useSessionStore((state) => state.exerciseKey)
  // O denominador do anel vem do store, não de um `useState` sincronizado por efeito: ele é
  // dado do servidor (`countdown_ms`), e derivá-lo do relógio local faria o total mudar a
  // cada render — o anel nunca chegaria a zero.
  const totalMs = useSessionStore((state) => state.countdownMs)
  const [agora, setAgora] = useState(() => Date.now())

  const ativo = sessionStatus === 'preparing' && countingFrom !== null

  useEffect(() => {
    if (!ativo) return
    // Um quadro de vídeo, não um segundo: o anel precisa correr liso, e o número tem de
    // trocar junto com o relógio em vez de até 1 s depois dele.
    let raf = 0
    const passo = () => {
      setAgora(Date.now())
      raf = requestAnimationFrame(passo)
    }
    raf = requestAnimationFrame(passo)
    return () => cancelAnimationFrame(raf)
  }, [ativo])

  if (!ativo || countingFrom === null) return null

  const restam = segundosRestantes(countingFrom, agora)
  const fracao = fracaoRestante(countingFrom, agora, totalMs)
  const comecou = restam === 0
  const exercicio = getExercise(exerciseKey).display_name.toLowerCase()

  return (
    <div className="getready" role="status" aria-live="assertive">
      <p className="getready__eyebrow">
        {comecou ? t('session:getready.eyebrow.go') : t('session:getready.eyebrow.prepare')}
      </p>

      <div className={`getready__dial ${comecou ? 'getready__dial--go' : ''}`}>
        <svg width={DIAL_SIZE} height={DIAL_SIZE} viewBox={`0 0 ${DIAL_SIZE} ${DIAL_SIZE}`} aria-hidden="true">
          <defs>
            {/* Mesmos tokens do TimerRing (SPEC-013 §Design tokens). */}
            <linearGradient id="getreadyGradient" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0%" stopColor="#7c5cff" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>
          </defs>
          <circle
            cx={DIAL_SIZE / 2}
            cy={DIAL_SIZE / 2}
            r={DIAL_RADIUS}
            fill="none"
            stroke="rgba(255,255,255,0.10)"
            strokeWidth={DIAL_STROKE}
          />
          <circle
            cx={DIAL_SIZE / 2}
            cy={DIAL_SIZE / 2}
            r={DIAL_RADIUS}
            fill="none"
            stroke="url(#getreadyGradient)"
            strokeWidth={DIAL_STROKE}
            strokeLinecap="round"
            strokeDasharray={DIAL_CIRCUMFERENCE}
            strokeDashoffset={DIAL_CIRCUMFERENCE * (1 - fracao)}
            transform={`rotate(-90 ${DIAL_SIZE / 2} ${DIAL_SIZE / 2})`}
          />
        </svg>

        {/* `key` no conteúdo: trocar de "3" para "2" remonta o nó e a animação recomeça. Sem
            isso o CSS animaria uma vez só e os outros segundos entrariam sem batida. */}
        <p
          key={comecou ? 'go' : restam}
          className={`getready__tick ${comecou ? 'getready__tick--go' : ''} tabular`}
        >
          {comecou ? t('session:getready.go') : restam}
        </p>
      </div>

      {/* A linha que resolve a dúvida "já é pra começar?". Depois do VAI! ela some: aí a
          resposta é óbvia, e texto sobrando na tela durante o exercício é ruído. */}
      {!comecou && (
        <p className="getready__hint">
          {/* Singular de propósito: pluralizar com `+ "s"` funcionaria para "polichinelo" e
              quebraria no primeiro exercício com nome que não aceita o sufixo. Quebrada em
              `_lead`/`_mid` porque o nome do exercício e o "VAI!" são `<strong>` no meio da
              frase — mesma solução do `view.why.*` na T-148. */}
          {t('session:getready.hint_lead')} <strong>{exercicio}</strong>{' '}
          {t('session:getready.hint_mid')} <strong>{t('session:getready.go')}</strong>
        </p>
      )}
    </div>
  )
}
