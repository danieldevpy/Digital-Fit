// Tela de conta e histórico (SPEC-011 / T-022). Abre pela aba Perfil e pela recusa do trial.
//
// Uma tela só para os dois estados — visitante e logado — porque é uma coisa só do ponto de
// vista de quem usa: "minha conta". O visitante vê o formulário e o motivo de criar conta; o
// logado vê o que treinou. Duas telas separadas obrigariam a navegar para descobrir em qual
// dos dois estados se está.
import { useState } from 'react'
import { EngagementSection } from '../engagement/EngagementSection'
import { useHistoryStore } from '../history/store'
import { useFreshHistory } from '../history/useFreshHistory'
import { formatDuration } from '../report/sessionReport'
import { getExercise } from '../session/catalog'
import { useAccountStore } from '../store/account'
import { BrandMark } from '../ui/BrandMark'
import { displayName, historyDate, historyTotals, quotaNotice } from './accountSummary'
import type { QuotaNotice } from './accountSummary'
import { login, logout, register } from './api'

/**
 * O sheet de limite da SPEC-016: contagem, hora em que renova e a saída.
 *
 * **Não há botão de assinar, e é de propósito.** A spec pede o CTA de assinatura "ainda sem
 * checkout — lista de espera/`em breve`", e um botão que não leva a lugar nenhum seria a
 * primeira afordância inventada de um app cuja regra é mostrar `--` quando não há dado
 * (SPEC-014). Enquanto o checkout não existe, o convite é uma frase; no dia em que existir,
 * vira botão nesta mesma linha.
 */
function QuotaBlock({ notice, upsell }: { notice: QuotaNotice; upsell: boolean }) {
  return (
    <div className="account__quota">
      <p className="account__quota-title">{notice.title}</p>
      <p className="account__quota-text">{notice.text}</p>
      <p className="account__quota-meta">
        {notice.count && <span className="tabular">{notice.count}</span>}
        {notice.renew && <span className="account__quota-renew">{notice.renew}</span>}
      </p>
      {upsell && (
        <p className="account__quota-soon">Assinatura em breve — e aí o limite deixa de existir.</p>
      )}
    </div>
  )
}

export function AccountSheet() {
  const open = useAccountStore((state) => state.sheetOpen)
  const status = useAccountStore((state) => state.status)

  if (!open) return null

  return (
    <div className="account" role="dialog" aria-label="Sua conta">
      <div className="account__card">
        <BrandMark center />
        {status === 'authenticated' ? <Conta /> : <Entrada />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------- visitante

function Entrada() {
  const [modo, setModo] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [nome, setNome] = useState('')

  const quota = useAccountStore((state) => state.quota)
  const blocked = useAccountStore((state) => state.quotaBlocked)
  const erro = useAccountStore((state) => state.formError)
  const busy = useAccountStore((state) => state.busy)
  const { setUser, setFormError, setBusy, openSheet } = useAccountStore.getState()

  const cadastro = modo === 'register'
  // Visitante não vê convite a assinar: para ele o próximo degrau é a conta, que é de graça e
  // está logo abaixo no formulário. Oferecer assinatura antes da conta seria pular o funil.
  const aviso = quotaNotice(quota, blocked)

  // O que este aparelho já treinou (T-121). Uma linha, não um painel: o Progresso é a tela
  // desses números (T-124), e aqui eles existem para dar MOTIVO ao formulário logo abaixo —
  // "você já tem 3 treinos e eles somem se limpar o navegador" é o argumento verdadeiro para
  // criar conta, e é o único CTA honesto enquanto a adoção das sessões do aparelho (T-087)
  // não existir.
  const guardadas = useHistoryStore((state) => state.sessions.length)

  const enviar = async (evento: React.FormEvent) => {
    evento.preventDefault()
    setBusy(true)
    setFormError(null)
    try {
      const sessao = cadastro
        ? await register(email.trim(), senha, nome.trim())
        : await login(email.trim(), senha)
      setUser(sessao.user)
    } catch (falha) {
      setFormError(falha instanceof Error ? falha.message : 'Não foi possível entrar.')
    }
  }

  return (
    <>
      <p className="account__title">{cadastro ? 'Criar conta' : 'Entrar'}</p>
      {aviso && <QuotaBlock notice={aviso} upsell={false} />}

      {guardadas > 0 && (
        <p className="account__hint">
          <span className="tabular">{guardadas}</span>
          {guardadas === 1 ? ' treino guardado' : ' treinos guardados'} neste aparelho — limpar
          o navegador leva embora. Com conta, ficam.
        </p>
      )}

      <form className="account__form" onSubmit={enviar}>
        {cadastro && (
          <label className="account__field">
            <span>Nome (opcional)</span>
            <input
              type="text"
              autoComplete="given-name"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
            />
          </label>
        )}

        <label className="account__field">
          <span>E-mail</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label className="account__field">
          <span>Senha</span>
          <input
            type="password"
            required
            autoComplete={cadastro ? 'new-password' : 'current-password'}
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
        </label>

        {erro && (
          <p className="account__error" role="alert">
            {erro}
          </p>
        )}

        <button type="submit" className="account__submit" disabled={busy}>
          {busy ? 'Só um instante…' : cadastro ? 'Criar conta' : 'Entrar'}
        </button>
      </form>

      <button
        type="button"
        className="account__switch"
        onClick={() => {
          setFormError(null)
          setModo(cadastro ? 'login' : 'register')
        }}
      >
        {cadastro ? 'Já tenho conta' : 'Criar uma conta'}
      </button>

      {/* Fechar continua disponível mesmo com o trial esgotado: o treino é que está
          bloqueado, não o aplicativo. Prender a pessoa na tela de cadastro seria o oposto
          de um funil. */}
      <button type="button" className="account__close" onClick={() => openSheet(false)}>
        Agora não
      </button>
    </>
  )
}

// -------------------------------------------------------------------------------- logado

function Conta() {
  const user = useAccountStore((state) => state.user)
  // Do store de histórico, não do de conta (T-121): esta folha deixou de ser a única tela que
  // sabe o que a pessoa treinou, e duas cópias da mesma lista divergem.
  const history = useHistoryStore((state) => state.sessions)
  const historyStatus = useHistoryStore((state) => state.status)
  const source = useHistoryStore((state) => state.source)
  const loadError = useHistoryStore((state) => state.loadError)
  const quota = useAccountStore((state) => state.quota)
  const blocked = useAccountStore((state) => state.quotaBlocked)
  const { openSheet, reset } = useAccountStore.getState()

  // Sair é a única ação destrutiva do app (leva embora o acesso e o histórico da tela). Ela
  // pede um segundo toque — não por burocracia, mas porque o toque errado aqui custa uma
  // sessão de login para desfazer (T-079).
  const [confirmandoSaida, setConfirmandoSaida] = useState(false)

  // Abrir a folha é "ganhar foco" (SPEC-024 §2): revalida ao montar e quando a página volta a
  // ficar visível. O fim de sessão não passa por aqui — ele invalida direto no store.
  useFreshHistory()

  const totais = historyTotals(history)
  const aviso = quotaNotice(quota, blocked)

  return (
    <>
      <p className="account__title">Olá, {displayName(user)}</p>
      <p className="account__email">{user?.email}</p>

      {/* Chip de plano (SPEC-016 §Fase Inicial). O nome vem do servidor (`Plan.nome`), não de
          um mapa de slugs no cliente: plano renomeado no painel aparece renomeado aqui. Sem
          quota conhecida o chip não aparece — inventar "Free" seria afirmar o plano de alguém
          com base em nada. */}
      {quota && (
        <p className="account__plan">
          <span className="account__plan-name">{quota.plan_name}</span>
          {/* "restam N", e não "N de M": o bloco logo abaixo diz "10 de 10 sessões de hoje"
              contando as USADAS, e o chip contava as RESTANTES no mesmo formato — dois
              significados para a mesma forma, na mesma tela. Visto no navegador com a conta
              esgotada: o chip dizia "0 de 10" ao lado de "10 de 10". A palavra desfaz. */}
          {!quota.unlimited && (
            <span className="account__plan-left tabular">restam {quota.remaining}</span>
          )}
        </p>
      )}

      {aviso && <QuotaBlock notice={aviso} upsell />}

      <EngagementSection />

      <div className="account__totals">
        <div className="account__total">
          <p className="account__total-value tabular">{totais.sessions}</p>
          <p className="account__total-label">sessões</p>
        </div>
        <div className="account__total">
          <p className="account__total-value tabular">{totais.reps}</p>
          <p className="account__total-label">repetições</p>
        </div>
        <div className="account__total">
          <p className="account__total-value tabular">{totais.bestCadence.toFixed(0)}</p>
          <p className="account__total-label">melhor rep/min</p>
        </div>
      </div>

      <p className="account__section-title">
        Histórico
        {history.length > 0 && (
          <span className="account__section-count tabular">{history.length}</span>
        )}
      </p>

      {historyStatus === 'loading' && <p className="account__hint">Carregando…</p>}
      {historyStatus === 'error' && (
        <p className="account__hint">Não consegui carregar seu histórico agora.</p>
      )}
      {/* Logado, mas o servidor não respondeu: o que está na tela é o que ESTE aparelho
          lembra. A lista continua — falha de rede não zera o progresso de ninguém (SPEC-024,
          critério 5) — mas dizer de onde ela veio é o que separa "desatualizado" de "mentira". */}
      {source === 'local' && history.length > 0 && (
        <p className="account__hint">Mostrando o que está guardado neste aparelho.</p>
      )}
      {/* Revalidação que falhou com dado bom na tela. Discreto de propósito: o número não está
          errado, só pode não ser o último. Um erro em vermelho aqui assustaria por causa de um
          Wi-Fi ruim. */}
      {loadError && source === 'server' && history.length > 0 && (
        <p className="account__hint">Não consegui atualizar agora — pode faltar algo recente.</p>
      )}
      {historyStatus === 'ready' && history.length === 0 && (
        <p className="account__hint">
          Nenhuma sessão ainda. Toque no botão do meio para treinar 30 segundos.
        </p>
      )}

      {/* Rola dentro de si (T-079). Antes a lista crescia com o histórico e empurrava as
          ações para fora da tela: com 20 sessões, "Fechar" só existia depois de rolar a folha
          inteira. Agora a lista é uma janela de altura fixa — o resumo em cima e as ações
          embaixo ficam sempre visíveis, e é o histórico que rola. */}
      {history.length > 0 && (
        <div className="account__history">
          <ul className="account__list">
            {history.map((sessao) => (
              <li key={sessao.session_id} className="account__item">
                {/* Qual exercício, e não só quando (T-055). A lista dizia "12 reps" sem dizer
                    de quê — legível enquanto havia um exercício, ilegível com quatro: 12
                    flexões e 12 polichinelos são a mesma linha e treinos diferentes. */}
                <span className="account__item-main">
                  <span className="account__item-ex">
                    {getExercise(sessao.exercise).display_name}
                  </span>
                  <span className="account__item-date">{historyDate(sessao.created_at)}</span>
                </span>
                <span className="account__item-reps tabular">{sessao.rep_count} reps</span>
                <span className="account__item-time tabular">
                  {formatDuration(sessao.duration_ms)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Hierarquia invertida em relação ao que existia (T-079): "Sair" era o botão roxo
          preenchido e "Fechar" o texto apagado logo abaixo — a ação destrutiva com a cara da
          principal, no lugar onde o polegar cai. Quem só queria voltar ao treino saía da
          conta. Agora o primário é fechar (o que 99% dos toques querem) e sair é discreto,
          separado por uma linha e com confirmação. */}
      <button type="button" className="account__submit" onClick={() => openSheet(false)}>
        Fechar
      </button>

      <div className="account__danger">
        {confirmandoSaida ? (
          <>
            <p className="account__danger-ask">Sair da conta neste aparelho?</p>
            <div className="account__danger-row">
              <button
                type="button"
                className="account__danger-cancel"
                onClick={() => setConfirmandoSaida(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="account__danger-confirm"
                onClick={() => {
                  logout()
                  reset()
                }}
              >
                Sair da conta
              </button>
            </div>
          </>
        ) : (
          <button
            type="button"
            className="account__leave"
            onClick={() => setConfirmandoSaida(true)}
          >
            Sair da conta
          </button>
        )}
      </div>
    </>
  )
}
