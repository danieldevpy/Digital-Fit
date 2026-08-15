// Casca do APP (SPEC-014, T-067): roteia por hash entre Escolha, Guia, Sessão
// (pré-config/treino), Progresso e Analytics. A landing não vive mais aqui — é o bundle do
// site (`src/site/`), e o app abre direto na pré-configuração, que é o "Início" da tab bar.
import { useEffect } from 'react'
import { AccountSheet } from '../auth/AccountSheet'
import { fetchMe } from '../auth/api'
import { refreshHistory } from '../history/refresh'
import { useHistoryStore } from '../history/store'
import { ReportSheet } from '../report/ReportSheet'
import { AchievementToast } from '../engagement/AchievementToast'
import { EngagementSheet } from '../engagement/EngagementSheet'
import { AnalyticsScreen } from '../screens/AnalyticsScreen'
import { ChooseScreen } from '../screens/ChooseScreen'
import { chooseExercise } from '../screens/funnel'
import { GuideScreen } from '../screens/GuideScreen'
import { ProgressScreen } from '../screens/ProgressScreen'
import { SessionScreen } from '../screens/SessionScreen'
import { podeAlimentarSessao } from '../session/pipelineGate'
import { fetchQuota } from '../session/quota'
import { fetchServerConfig } from '../session/serverConfig'
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

  // O que este aparelho treinou entra na tela ANTES de qualquer rede (T-121): é síncrono, sai
  // do `localStorage` e é a única fonte de quem não tem conta. Quem tem conta vê isto no
  // primeiro paint e o servidor corrige logo depois — nunca o contrário, que faria o número
  // aparecer do nada alguns segundos após a tela.
  useEffect(() => {
    useHistoryStore.getState().hydrate()
  }, [])

  // Catálogo e capacidades do servidor (SPEC-018 / T-074). Sem `await` e sem tela de espera: o
  // app já desenhou com o catálogo embutido, e esta chamada só **corrige** o que o painel mudou.
  // Falhar é silencioso pelo mesmo motivo do `fetchMe` acima — configuração indisponível é um
  // treino a menos de personalização, nunca um erro na cara de quem ia treinar.
  //
  // Depende de QUEM é a conta, não do status dela: a resposta é por plano, e entrar ou sair
  // troca o que se pode ver. O `status` também serviria, mas ele muda de `unknown` para
  // `anonymous` no boot sem o plano mudar — e isso custava um payload inteiro a mais em toda
  // abertura do app, medido no navegador.
  const contaId = useAccountStore((state) => state.user?.id ?? null)
  useEffect(() => {
    void fetchServerConfig()
  }, [contaId])

  // Trocou de identidade, troca de histórico (T-122). O `setUser` já devolveu a lista ao que o
  // APARELHO sabe; esta linha traz o que o servidor sabe sobre quem entrou agora. Sem ela, quem
  // faz login só veria as próprias sessões ao abrir o Perfil, e o Progresso ficaria mostrando
  // apenas o que o aparelho tem, calado sobre o resto.
  //
  // Depende de `contaId` **e** de `status` porque as duas trocas importam e nenhuma cobre a
  // outra: sair da conta mantém o id em `null` e muda só o status; trocar de conta mantém o
  // status em `authenticated` e muda só o id.
  const contaStatus = useAccountStore((state) => state.status)
  useEffect(() => {
    // `unknown` é o boot antes de o `/api/me` responder — buscar aqui seria perguntar o
    // histórico de uma identidade que ainda não se sabe qual é.
    if (contaStatus === 'unknown') return
    void refreshHistory()
  }, [contaId, contaStatus])

  // Pré-voo da quota (SPEC-016, T-063). É o que faz o sheet de limite aparecer ANTES de a
  // câmera abrir: sem ele, quem já esgotou daria permissão de câmera, esperaria o landmarker
  // aquecer e se enquadraria só para ouvir "não" na hora do play.
  //
  // Uma vez por identidade, e não a cada tela: depois de cada sessão quem atualiza o contador
  // é o próprio ticket (`useSession`), que acabou de contá-la e por isso sabe mais que uma
  // consulta nova. Falhar é silencioso pelo mesmo motivo das duas chamadas acima.
  useEffect(() => {
    // `null` é "não deu para saber", não "sem limite": nesse caso o store fica como estava, e
    // quem decide continua sendo a admissão. Escrever o `null` apagaria o sheet de quem já
    // esgotou por causa de um Wi-Fi ruim.
    void fetchQuota().then((quota) => {
      if (quota) useAccountStore.getState().setQuota(quota)
    })
  }, [contaId])

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
      <EngagementSheet />
      <AchievementToast />
    </div>
  )
}
