// Tela de conta e histórico (SPEC-011 / T-022). Abre pela aba Perfil e pela recusa do trial.
//
// Uma tela só para os dois estados — visitante e logado — porque é uma coisa só do ponto de
// vista de quem usa: "minha conta". O visitante vê o formulário e o motivo de criar conta; o
// logado vê o que treinou. Duas telas separadas obrigariam a navegar para descobrir em qual
// dos dois estados se está.
import { useEffect, useState } from 'react'
import { formatDuration } from '../report/sessionReport'
import { useAccountStore } from '../store/account'
import { displayName, historyDate, historyTotals, trialMessage } from './accountSummary'
import { fetchHistory, login, logout, register } from './api'

export function AccountSheet() {
  const open = useAccountStore((state) => state.sheetOpen)
  const status = useAccountStore((state) => state.status)

  if (!open) return null

  return (
    <div className="account" role="dialog" aria-label="Sua conta">
      <div className="account__card">
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

  const trial = useAccountStore((state) => state.trial)
  const blocked = useAccountStore((state) => state.trialBlocked)
  const erro = useAccountStore((state) => state.formError)
  const busy = useAccountStore((state) => state.busy)
  const { setUser, setFormError, setBusy, openSheet } = useAccountStore.getState()

  const cadastro = modo === 'register'
  const aviso = trialMessage(trial, blocked)

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
      {aviso && <p className="account__trial">{aviso}</p>}

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
  const history = useAccountStore((state) => state.history)
  const historyStatus = useAccountStore((state) => state.historyStatus)
  const { openSheet, reset, startHistory, applyHistory, failHistory } = useAccountStore.getState()

  useEffect(() => {
    if (historyStatus !== 'idle') return
    startHistory()
    fetchHistory()
      .then(applyHistory)
      .catch(() => failHistory())
  }, [historyStatus, startHistory, applyHistory, failHistory])

  const totais = historyTotals(history)

  return (
    <>
      <p className="account__title">Olá, {displayName(user)}</p>
      <p className="account__email">{user?.email}</p>

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

      <p className="account__section-title">Histórico</p>

      {historyStatus === 'loading' && <p className="account__hint">Carregando…</p>}
      {historyStatus === 'error' && (
        <p className="account__hint">Não consegui carregar seu histórico agora.</p>
      )}
      {historyStatus === 'ready' && history.length === 0 && (
        <p className="account__hint">
          Nenhuma sessão ainda. Toque no botão do meio para treinar 30 segundos.
        </p>
      )}

      {history.length > 0 && (
        <ul className="account__list">
          {history.map((sessao) => (
            <li key={sessao.session_id} className="account__item">
              <span className="account__item-date">{historyDate(sessao.created_at)}</span>
              <span className="account__item-reps tabular">{sessao.rep_count} reps</span>
              <span className="account__item-time tabular">
                {formatDuration(sessao.duration_ms)}
              </span>
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        className="account__submit"
        onClick={() => {
          logout()
          reset()
        }}
      >
        Sair
      </button>
      <button type="button" className="account__close" onClick={() => openSheet(false)}>
        Fechar
      </button>
    </>
  )
}
