// Casca do APP (SPEC-014, T-067): roteia por hash entre Escolha, Guia, Sessão
// (pré-config/treino), Progresso e Analytics. A landing não vive mais aqui — é o bundle do
// site (`src/site/`), e o app abre direto na pré-configuração, que é o "Início" da tab bar.
import { useEffect } from 'react'
import { AccountSheet } from '../auth/AccountSheet'
import { fetchMe } from '../auth/api'
import { ReportSheet } from '../report/ReportSheet'
import { AnalyticsScreen } from '../screens/AnalyticsScreen'
import { ChooseScreen } from '../screens/ChooseScreen'
import { chooseExercise } from '../screens/funnel'
import { GuideScreen } from '../screens/GuideScreen'
import { ProgressScreen } from '../screens/ProgressScreen'
import { SessionScreen } from '../screens/SessionScreen'
import { podeAlimentarSessao } from '../session/pipelineGate'
import { useSession } from '../session/useSession'
import { navigate, useRoute } from '../shell/nav'
import { useAccountStore } from '../store/account'
import { useSessionStore } from '../store/session'

export function AppShell() {
  const poseStatus = useSessionStore((state) => state.poseStatus)
  const probeStatus = useSessionStore((state) => state.probeStatus)
  const route = useRoute()

  // A sessão só conversa com o gateway na tela de treino — a pré-configuração mostra a câmera
  // como espelho, sem abrir sessão (SPEC-014 §3).
  //
  // E não basta a câmera estar de pé (era o gatilho até a T-069): o servidor começa a contar
  // os 10s de `no_data` na admissão, então pedir a sessão antes de o pipeline poder emitir
  // frame é gastar o prazo dele baixando modelo. Quem manda aqui é o pipeline.
  const pronto = podeAlimentarSessao({ poseStatus, probeStatus })
  useSession(pronto && route.screen === 'treino')

  // Quem já tinha entrado continua entrado ao reabrir o app: o refresh está no
  // `localStorage`, e o `authedFetch` o usa para renovar o access sozinho. Falhar aqui é
  // normal e silencioso — significa apenas "ninguém logado", que é o estado padrão do produto.
  useEffect(() => {
    void fetchMe().then((user) => useAccountStore.getState().setUser(user))
  }, [])

  // Ponte `#/ex/<slug>` vinda do site: só o app sabe se o guia daquele exercício já foi visto
  // (SPEC-015), porque `guide_seen` mora no localStorage DESTA origem. A rota é trocada por
  // cima para o back não cair de volta na ponte.
  const abrir = route.screen === 'abrirExercicio' ? route.exercise : null
  useEffect(() => {
    if (abrir !== null) chooseExercise(abrir, { replace: true })
  }, [abrir])

  // `#/entrar` (o "Entrar" do site): abre a folha de conta e sai da própria rota, para o
  // fechar da folha não deixar o app parado numa rota que só sabe reabri-la.
  const querEntrar = route.screen === 'entrar'
  useEffect(() => {
    if (!querEntrar) return
    useAccountStore.getState().openSheet(true)
    navigate({ screen: 'preparar' }, { replace: true })
  }, [querEntrar])

  const emSessao = route.screen === 'preparar' || route.screen === 'treino'

  return (
    <div className="app">
      <div className="app__phone">
        {route.screen === 'exercicios' && <ChooseScreen />}
        {route.screen === 'guia' && <GuideScreen exercise={route.exercise} />}
        {/* Pré-config e treino são o MESMO componente montado: a CameraView não pode
            desmontar na passagem, senão o stream morre no meio do fluxo. */}
        {emSessao && <SessionScreen mode={route.screen as 'preparar' | 'treino'} />}
        {route.screen === 'progresso' && <ProgressScreen />}
        {route.screen === 'analytics' && <AnalyticsScreen />}
      </div>

      {/* Por último no DOM de propósito: cobrem a tela inteira quando aparecem. */}
      <ReportSheet />
      <AccountSheet />
    </div>
  )
}
