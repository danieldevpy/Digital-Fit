// O painel do fogo (SPEC-019 §Superfícies / T-088): sequência, calendário do mês, XP e meta.
//
// Sheet e não rota, como a AccountSheet — é uma explicação do número que está no chip, e sair
// da tela para lê-la faria perder o contexto que a explicação serve.
import { useState } from 'react'
import { updateProfile } from '../auth/api'
import { useHistoryStore } from '../history/store'
import { useAccountStore } from '../store/account'
import { AchievementGallery } from './AchievementGallery'
import { gradeDoMes, INICIAIS_DA_SEMANA } from './calendar'
import { diaDoFogo } from './fire'
import { refreshEngagement, useEngagementStore } from './store'
import { METAS, useEngagement } from './useEngagement'

const NOME_DA_META: Record<string, string> = {
  casual: 'Casual',
  regular: 'Regular',
  intenso: 'Intenso',
}

function Calendario({ hoje }: { hoje: string }) {
  const sessoes = useHistoryStore((state) => state.sessions)
  const grade = gradeDoMes(sessoes, hoje)

  return (
    <div className="eng__cal">
      <div className="eng__cal-week" aria-hidden="true">
        {INICIAIS_DA_SEMANA.map((letra, i) => (
          <span key={`${letra}-${i}`} className="eng__cal-weekday">
            {letra}
          </span>
        ))}
      </div>
      <div className="eng__cal-grid">
        {Array.from({ length: grade.offset }, (_, i) => (
          <span key={`vazio-${i}`} className="eng__cal-day eng__cal-day--empty" />
        ))}
        {grade.dias.map((dia) => (
          <span
            key={dia.dia}
            className={[
              'eng__cal-day',
              dia.ativo ? 'eng__cal-day--on' : '',
              dia.futuro ? 'eng__cal-day--future' : '',
              dia.hoje ? 'eng__cal-day--today' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            // O dia aceso é informação, não enfeite: quem usa leitor de tela precisa dela.
            aria-label={`${dia.numero}${dia.ativo ? ', treinou' : ''}`}
          >
            {dia.numero}
          </span>
        ))}
      </div>
      <p className="eng__cal-total">
        <span className="num tabular">{grade.ativos}</span> dias treinados neste mês
      </p>
    </div>
  )
}

function SeletorDeMeta({ atual }: { atual: string }) {
  const setUser = useAccountStore((state) => state.setUser)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const escolher = async (meta: string) => {
    if (meta === atual || salvando) return
    setSalvando(true)
    setErro(null)
    try {
      setUser(await updateProfile({ daily_goal: meta }))
      // A meta muda `goal_done_today` e `goal_target` no servidor — o painel tem de refletir
      // isso agora, não no próximo foco. `force` porque houve fato novo, não suspeita.
      await refreshEngagement({ force: true })
    } catch {
      setErro('Não foi possível salvar a meta.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="eng__goal">
      <p className="v2-label">Meta diária</p>
      <div className="eng__goal-opts" role="group" aria-label="Meta diária">
        {Object.entries(METAS).map(([slug, alvo]) => (
          <button
            key={slug}
            type="button"
            className={`eng__goal-opt ${slug === atual ? 'eng__goal-opt--on' : ''}`}
            onClick={() => void escolher(slug)}
            disabled={salvando}
            aria-pressed={slug === atual}
          >
            <span className="eng__goal-name">{NOME_DA_META[slug] ?? slug}</span>
            <span className="eng__goal-alvo num tabular">
              {alvo} {alvo === 1 ? 'sessão' : 'sessões'}
            </span>
          </button>
        ))}
      </div>
      {erro && <p className="eng__erro">{erro}</p>}
    </div>
  )
}

export function EngagementSheet() {
  const aberto = useEngagementStore((state) => state.sheetOpen)
  const fechar = useEngagementStore((state) => state.openSheet)
  const abrirConta = useAccountStore((state) => state.openSheet)
  const user = useAccountStore((state) => state.user)
  const hoje = diaDoFogo(new Date()) ?? ''
  const view = useEngagement(hoje)

  if (!aberto) return null

  return (
    <div className="account eng" role="dialog" aria-label="Seu engajamento">
      <div className="account__card">
        <header className="account__head">
          <h2 className="account__title">Sua constância</h2>
          <button type="button" className="account__close" onClick={() => fechar(false)}>
            Fechar
          </button>
        </header>

        <div className="eng__hero">
          <span className="eng__flame" aria-hidden="true">
            🔥
          </span>
          <p className="eng__streak num tabular">{view.pending ? '--' : view.streak}</p>
          <p className="eng__streak-label">
            {view.streak === 1 ? 'dia seguido' : 'dias seguidos'}
          </p>
          <p className="eng__best">
            Melhor sequência: <span className="num tabular">{view.bestStreak}</span>
          </p>
        </div>

        {/* O rótulo honesto do §Anônimo, e o CTA que a dor de perder a sequência sustenta. */}
        {view.source === 'local' && (
          <div className="eng__ghost">
            <p className="eng__ghost-title">Seu fogo vive só neste aparelho</p>
            <p className="eng__ghost-text">
              Limpar o navegador leva sua sequência embora. Uma conta guarda o que você já
              treinou — e é de graça.
            </p>
            <button
              type="button"
              className="eng__ghost-cta"
              onClick={() => {
                fechar(false)
                abrirConta(true)
              }}
            >
              Criar conta
            </button>
          </div>
        )}

        <Calendario hoje={hoje} />

        <div className="eng__row">
          <div className="eng__stat">
            <p className="v2-label">Meta de hoje</p>
            <p className="eng__stat-val num tabular">
              {view.sessionsToday}/{view.goalTarget}
            </p>
          </div>
          {/* XP e nível não existem para o visitante (§Planos) — a coluna some, e não vira
              `0`, que seria uma afirmação sobre pontos que ninguém podia ganhar. */}
          {view.xp !== null && (
            <>
              <div className="eng__stat">
                <p className="v2-label">XP</p>
                <p className="eng__stat-val num tabular">{view.xp}</p>
              </div>
              <div className="eng__stat">
                <p className="v2-label">Nível</p>
                <p className="eng__stat-val num tabular">{view.level}</p>
              </div>
            </>
          )}
        </div>

        {view.protections !== null && view.protections.total > 0 && (
          <p className="eng__prot">
            Proteções de sequência usadas neste mês:{' '}
            <span className="num tabular">
              {view.protections.used} de {view.protections.total}
            </span>
          </p>
        )}

        {/* A galeria é a "galeria do Perfil" que a spec pede: o Perfil abre ESTE painel, e
            duplicá-la nos dois lugares criaria duas telas para manter iguais. */}
        <AchievementGallery lista={view.achievements} />

        {user !== null && <SeletorDeMeta atual={user.daily_goal} />}
      </div>
    </div>
  )
}
