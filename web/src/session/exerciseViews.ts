// Variações de câmera de um exercício (T-111) — a escolha de QUEM TREINA, não do modelo.
//
// Uma flexão de frente e uma de lado são a mesma flexão e duas geometrias sem nada em comum:
// de lado o corpo atravessa a imagem na horizontal, de frente ele encolhe contra a lente. O
// worker sabe medir as duas, e sabe até adivinhar qual é (`flexao.py`) — mas adivinhar é o
// caminho que este arquivo existe para evitar. A vista troca a régua da contagem, e uma
// adivinhação que oscile no meio da série troca a régua com a pessoa em movimento; um toque
// aqui custa um segundo e o erro custa o treino inteiro.
//
// **Por que a variação mora no cliente e não no catálogo do servidor.** Ela é feita de três
// coisas — o rótulo, a instrução de cena e os passos do exemplo — e as três são texto que ESTE
// bundle sabe desenhar, do mesmo jeito que a figura do exercício (`ui/exerciseFigures.ts`).
// Exercício que o servidor publique sem entrada aqui simplesmente não oferece variação, e o
// analisador cai na detecção geométrica: degrada para o comportamento anterior, não quebra.
// Levá-la para o painel (SPEC-018) é task própria — está na Descoberta [A/T-111].
//
// O valor viaja no `POST /sessions` → `session.started` → analisador. Os identificadores são
// os do contrato (`CameraView` em `workers/shared/events.py`): quem renomear um lado aqui tem
// de renomear lá, e é de propósito que sejam a mesma string.
//
// **`label`/`short`/`phone`/`scene_tip`/`guide_steps[].text` são getters** (T-152, namespace
// `catalog`: `view.<exercise>.<view>.*`) — mesma razão de `EXERCISE_CATALOG` em
// `session/catalog.ts`: `EXERCISE_VIEWS` é montado uma vez só, no import, e sem getter o texto
// congelaria no idioma detectado nesse instante.
import { t } from '../i18n'

/** Espelho de `CameraView` no contrato de eventos. */
export type ViewId = 'frontal' | 'profile'

export interface ExerciseView {
  id: ViewId
  /** Rótulo do botão no Guia, onde há largura para a frase inteira. */
  label: string
  /**
   * Rótulo na coluna da pré-configuração, que tem 92 px de largura num celular — medido: com
   * o `label` inteiro os dois botões quebram em duas linhas, e micro-rótulo quebrado é
   * exatamente o tipo de coisa que faz a pessoa não entender o que está escolhendo. A frase
   * completa continua logo abaixo, no `phone`.
   */
  short: string
  /** Onde fica o celular — a única frase que muda o que a pessoa faz ANTES de começar. */
  phone: string
  /** Como montar a cena para esta variação (substitui o `scene_tip` do exercício). */
  scene_tip: string
  /**
   * A foto grande do Guia desta variação, quando ela existe — `undefined` cai na do catálogo.
   *
   * É a maior imagem da tela e a primeira que a pessoa vê, então é ela que ensina a vista antes
   * de qualquer texto: deixar a foto de perfil no alto de uma tela que diz «de frente» é
   * contradizer a própria instrução no tamanho grande. Opcional porque a foto por vista é um
   * luxo — vista sem acervo próprio continua usando a do exercício em vez de não mostrar nada.
   */
  demo_img?: string
  /** Passos do exemplo guiado desta variação (SPEC-015). */
  guide_steps: { img: string; text: string }[]
}

/**
 * As variações por exercício, na ordem em que a tela as mostra. A **primeira é o default** de
 * quem nunca escolheu.
 *
 * Na flexão a primeira é `profile`, e não é escolha estética: é a vista que o Guia já ensina
 * desde a T-106, com fotos de perfil, e manter o default é não mudar o produto embaixo de quem
 * já aprendeu a montar a cena. As duas contam exato no corpus (16/16/11 de lado, 20/20 de
 * frente), então o default é continuidade, não preferência técnica.
 */
export const EXERCISE_VIEWS: Record<string, ExerciseView[]> = {
  flexao: [
    {
      id: 'profile',
      get label() {
        return t('catalog:view.flexao.profile.label')
      },
      get short() {
        return t('catalog:view.flexao.profile.short')
      },
      get phone() {
        return t('catalog:view.flexao.profile.phone')
      },
      get scene_tip() {
        return t('catalog:view.flexao.profile.scene_tip')
      },
      get guide_steps() {
        return [
          { img: '/img/guia/flexao-1.jpg', text: t('catalog:view.flexao.profile.guide_step.0') },
          { img: '/img/guia/flexao-1.jpg', text: t('catalog:view.flexao.profile.guide_step.1') },
          { img: '/img/guia/flexao-2.jpg', text: t('catalog:view.flexao.profile.guide_step.2') },
        ]
      },
    },
    {
      id: 'frontal',
      get label() {
        return t('catalog:view.flexao.frontal.label')
      },
      get short() {
        return t('catalog:view.flexao.frontal.short')
      },
      get phone() {
        return t('catalog:view.flexao.frontal.phone')
      },
      get scene_tip() {
        return t('catalog:view.flexao.frontal.scene_tip')
      },
      // As fotos são a própria lição desta vista: enquadramento errado num exercício de chão
      // zera a sessão, e a foto de perfil ensinava a cena errada para quem escolheu «De frente».
      // Nenhuma imagem de perfil sobra aqui — o `-1` é a prancha e o `-2` é a descida, as duas
      // enquadradas como o celular em pé enxerga.
      demo_img: '/img/guia/flexao-frente-2.jpg',
      get guide_steps() {
        return [
          {
            img: '/img/guia/flexao-frente-1.jpg',
            text: t('catalog:view.flexao.frontal.guide_step.0'),
          },
          {
            img: '/img/guia/flexao-frente-1.jpg',
            text: t('catalog:view.flexao.frontal.guide_step.1'),
          },
          {
            img: '/img/guia/flexao-frente-2.jpg',
            text: t('catalog:view.flexao.frontal.guide_step.2'),
          },
        ]
      },
    },
  ],
}

/** As variações deste exercício, ou `undefined` para quem não tem — a tela não desenha nada. */
export function viewsOf(exercise: string): ExerciseView[] | undefined {
  const views = EXERCISE_VIEWS[exercise]
  return views && views.length > 1 ? views : undefined
}

const VIEW_PREFIX = 'digitalfit.view.'

/**
 * A variação escolhida para este exercício. Guardada POR EXERCÍCIO, como o guia visto: quem
 * treina flexão de lado pode treinar outra coisa de frente, e uma preferência global misturaria
 * as duas respostas numa só.
 *
 * Validada na LEITURA e não só na escrita, pelo mesmo motivo do `exercisePreference`: um valor
 * guardado hoje pode deixar de existir amanhã, e um id morto no armazenamento viraria uma
 * escolha que a tela mostra e o servidor ignora.
 */
export function viewPreference(exercise: string): ViewId | null {
  const views = viewsOf(exercise)
  if (!views) return null
  const padrao = views[0]!.id
  try {
    const bruto = window.localStorage.getItem(VIEW_PREFIX + exercise)
    return views.some((v) => v.id === bruto) ? (bruto as ViewId) : padrao
  } catch {
    return padrao
  }
}

export function setViewPreference(exercise: string, id: ViewId): ViewId | null {
  const views = viewsOf(exercise)
  if (!views) return null
  const valor = views.some((v) => v.id === id) ? id : views[0]!.id
  try {
    window.localStorage.setItem(VIEW_PREFIX + exercise, valor)
  } catch {
    // Sem armazenamento (Safari privado): vale pela sessão atual e pronto.
  }
  return valor
}

/** A variação em vigor, já resolvida — é dela que saem a cena e os passos do Guia. */
export function currentView(exercise: string): ExerciseView | undefined {
  const views = viewsOf(exercise)
  if (!views) return undefined
  const id = viewPreference(exercise)
  return views.find((v) => v.id === id) ?? views[0]
}
