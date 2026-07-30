// Casca do app v2 (SPEC-014): roteia por hash entre Index, Escolha, Guia, Sessão
// (pré-config/treino) e Sobre. Só o Index escapa da coluna mobile.
import { useEffect } from 'react'
import { AccountSheet } from './auth/AccountSheet'
import { fetchMe } from './auth/api'
import { ReportSheet } from './report/ReportSheet'
import { AboutScreen } from './screens/AboutScreen'
import { ChooseScreen } from './screens/ChooseScreen'
import { GuideScreen } from './screens/GuideScreen'
import { IndexScreen } from './screens/IndexScreen'
import { SessionScreen } from './screens/SessionScreen'
import { useSession } from './session/useSession'
import { useRoute } from './shell/nav'
import { useAccountStore } from './store/account'
import { useSessionStore } from './store/session'

export function App() {
  const cameraStatus = useSessionStore((state) => state.cameraStatus)
  const route = useRoute()

  // A sessão só conversa com o gateway na tela de treino com a câmera de pé — a
  // pré-configuração mostra a câmera como espelho, sem abrir sessão (SPEC-014 §3).
  useSession(cameraStatus === 'ready' && route.screen === 'treino')

  // Quem já tinha entrado continua entrado ao reabrir o app: o refresh está no
  // `localStorage`, e o `authedFetch` o usa para renovar o access sozinho. Falhar aqui é
  // normal e silencioso — significa apenas "ninguém logado", que é o estado padrão do produto.
  useEffect(() => {
    void fetchMe().then((user) => useAccountStore.getState().setUser(user))
  }, [])

  const emSessao = route.screen === 'preparar' || route.screen === 'treino'

  return (
    <div className="app">
      {route.screen === 'index' ? (
        <IndexScreen />
      ) : (
        <div className="app__phone">
          {route.screen === 'exercicios' && <ChooseScreen />}
          {route.screen === 'guia' && <GuideScreen exercise={route.exercise} />}
          {/* Pré-config e treino são o MESMO componente montado: a CameraView não pode
              desmontar na passagem, senão o stream morre no meio do fluxo. */}
          {emSessao && <SessionScreen mode={route.screen as 'preparar' | 'treino'} />}
          {route.screen === 'sobre' && <AboutScreen />}
        </div>
      )}

      {/* Por último no DOM de propósito: cobrem a tela inteira quando aparecem. */}
      <ReportSheet />
      <AccountSheet />
    </div>
  )
}
