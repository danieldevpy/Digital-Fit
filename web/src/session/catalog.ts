// Catálogo de exercícios (SPEC-013 §Notas técnicas + SPEC-018 §B).
//
// **O cliente deixou de ser a fonte da verdade sobre o que existe (T-074).** Quem manda é o
// `GET /api/config`, resolvido pelo mesmo `exercises_for()` que a admissão usa — era essa
// divergência que o `[A/T-051]` registrava: "o catálogo do cliente e o registro do servidor
// podem divergir sem ninguém ver".
//
// O que sobra aqui é o **default embutido**: primeiro paint sem rede e fallback offline. Ele
// não some quando o servidor chega, e não é apagado quando o servidor falha — a tela nunca
// espera por rede para desenhar, e nunca fica vazia porque a rede caiu.
//
// Regra de leitura, portanto: `getExercise` e companhia leem o catálogo **mesclado**
// (servidor por cima do embutido); `EXERCISE_CATALOG` e `EXERCISE_KEYS` continuam sendo o
// embutido puro, e é isso que o teste da figura (T-082) deve cobrar — figura nova exige
// deploy, então cobrar figura de exercício que só existe no servidor seria cobrar o impossível.
import { useMemo } from 'react'
import { useConfigStore, type ServerExercise } from '../store/config'

export interface ExerciseInfo {
  display_name: string
  /** Slug do vocabulário de contrato (`cardio`, `forca`, `core`, `mobilidade`), não rótulo. */
  category: string
  muscle_group: string
  /** Estado vazio do card do treinador — ele nunca fica sem texto. */
  default_tip: string
  /**
   * Qual ângulo a barra de métricas exibe ao vivo (T-044).
   *
   * `none` não é ausência de dado: é a afirmação de que, para este exercício, **nenhum ângulo
   * lido no plano da imagem diz a verdade**. No agachamento o joelho viaja para a frente e
   * uma câmera frontal lê ~133° onde o corpo faz 80° (medido na T-052). Mostrar esse número
   * seria pior que mostrar "--": ele mal se mexe enquanto a pessoa agacha, e um número parado
   * na tela durante o esforço lê como "não está me vendo" — exatamente a ansiedade que o
   * esqueleto sobre a imagem existe para evitar (SPEC-013).
   */
  main_angle: 'arm_abduction' | 'none'
  /** Imagem de demonstração (SPEC-015: "todo exercício tem demo visual"). */
  demo_img: string
  /** Cor do dot de grupo no card da Escolha (SPEC-014 §2). */
  dot_color: string
  /** Passos do exemplo guiado (SPEC-015). Vazio não quebra: o Guia mostra demo + cena. */
  guide_steps: { img: string; text: string }[]
  /** Insumo do kcal (SPEC-016/017). `undefined` no embutido: o servidor é quem sabe. */
  met?: number
  /** Selo de qualidade (SPEC-020). Quem o usa na tela é a T-090/T-091, não esta task. */
  maturity?: string
}

/**
 * Rótulo de exibição de uma categoria.
 *
 * O catálogo guarda o **slug** desde a T-074 porque categoria virou contrato — conquistas
 * (SPEC-019) e o mix por objetivo (SPEC-022) consomem os slugs, e o cliente guardava a string
 * de exibição (`'Cardio'`, `'Força'`). Slug desconhecido devolve ele mesmo em vez de vazio:
 * uma categoria nova no servidor aparece feia, e não some da tela.
 */
const CATEGORY_LABELS: Record<string, string> = {
  cardio: 'Cardio',
  forca: 'Força',
  core: 'Core',
  mobilidade: 'Mobilidade',
}

export function categoryLabel(slug: string): string {
  return CATEGORY_LABELS[slug] ?? slug
}

export const EXERCISE_CATALOG: Record<string, ExerciseInfo> = {
  jumping_jack: {
    display_name: 'Polichinelo',
    category: 'cardio',
    muscle_group: 'Corpo inteiro',
    default_tip: 'Mantenha o core contraído e movimentos controlados.',
    main_angle: 'arm_abduction',
    demo_img: '/img/guia/polichinelo-2.jpg',
    dot_color: '#34d399',
    guide_steps: [
      { img: '/img/guia/polichinelo-1.jpg', text: 'Fique em pé, de frente para a câmera, corpo inteiro visível, braços ao lado do corpo.' },
      { img: '/img/guia/polichinelo-2.jpg', text: 'Salte abrindo as pernas e levando os braços acima da cabeça, ao mesmo tempo.' },
      { img: '/img/guia/polichinelo-1.jpg', text: 'Volte à posição inicial no salto seguinte — cada ida e volta conta uma repetição.' },
    ],
  },
  squat: {
    display_name: 'Agachamento',
    category: 'forca',
    muscle_group: 'Pernas e glúteos',
    default_tip: 'Desça com o peso nos calcanhares e o peito aberto.',
    main_angle: 'none',
    demo_img: '/img/guia/agachamento-2.jpg',
    dot_color: '#4d8cff',
    guide_steps: [
      { img: '/img/guia/agachamento-1.jpg', text: 'Pés na largura dos ombros, pontas levemente para fora, braços à frente para equilibrar.' },
      { img: '/img/guia/agachamento-2.jpg', text: 'Desça empurrando o quadril para trás, peso nos calcanhares, até as coxas ficarem paralelas ao chão.' },
      { img: '/img/guia/agachamento-1.jpg', text: 'Suba estendendo as pernas sem tirar os pés do chão — subida completa conta a repetição.' },
    ],
  },
}

export const DEFAULT_EXERCISE = 'jumping_jack'

/**
 * Os exercícios **embutidos**, em ordem de exibição.
 *
 * Exercício novo pede também a FIGURA da pose, em `ui/exerciseFigures.ts` (T-082). Essa não
 * grita em produção — cai numa figura neutra em pé —, então quem cobra é
 * `ui/exerciseIcon.test.ts`, que falha nomeando o slug sem figura.
 */
export const EXERCISE_KEYS = Object.keys(EXERCISE_CATALOG)

function daServidor(ex: ServerExercise): ExerciseInfo {
  return {
    display_name: ex.display_name,
    category: ex.category,
    muscle_group: ex.muscle_group,
    default_tip: ex.default_tip,
    // O contrato do campo é fechado no cliente (`arm_abduction | none`) e aberto no servidor
    // (CharField). Valor desconhecido cai em `none`, que é o único default honesto: mostrar um
    // ângulo que este cliente não sabe ler daria número errado na barra de métricas.
    main_angle: ex.main_angle === 'arm_abduction' ? 'arm_abduction' : 'none',
    demo_img: ex.demo_img,
    dot_color: ex.dot_color,
    guide_steps: ex.guide_steps,
    met: ex.met,
    maturity: ex.maturity,
  }
}

/**
 * O catálogo em vigor: servidor por cima do embutido, ou só o embutido enquanto ele não chega.
 *
 * **Substituição, não mesclagem campo a campo.** Quando o servidor fala, ele fala sobre *o que
 * existe* — um exercício que ele não listou está desligado ou fora do plano, e mantê-lo por
 * herança do embutido recriaria o card que a admissão recusa, que é o `[A/T-051]` de volta.
 */
export function currentCatalog(): Record<string, ExerciseInfo> {
  const doServidor = useConfigStore.getState().exercises
  if (!doServidor) return EXERCISE_CATALOG
  return Object.fromEntries(doServidor.map((ex) => [ex.slug, daServidor(ex)]))
}

/** Versão reativa de `currentCatalog` — as telas que listam exercícios usam esta. */
export function useCatalog(): { keys: string[]; catalog: Record<string, ExerciseInfo> } {
  const doServidor = useConfigStore((state) => state.exercises)
  return useMemo(() => {
    const catalog = doServidor
      ? Object.fromEntries(doServidor.map((ex) => [ex.slug, daServidor(ex)]))
      : EXERCISE_CATALOG
    return { keys: Object.keys(catalog), catalog }
  }, [doServidor])
}

export function isExerciseKey(key: unknown): key is string {
  // `Object.hasOwn` e não `in`: `in` percorre o protótipo, e `'toString' in EXERCISE_CATALOG`
  // é `true`. Um `toString` guardado no aparelho passaria por exercício válido, iria parar no
  // `POST /sessions` e faria `getExercise` devolver uma função no lugar do card.
  return typeof key === 'string' && Object.hasOwn(currentCatalog(), key)
}

/**
 * Há escolha a oferecer? Com um exercício só, não — e a tela não desenha nada (T-051).
 *
 * Regra e não `&&` solto no componente porque é a decisão de produto desta task: o caminho da
 * escolha existe desde já, a superfície aparece quando houver o que escolher.
 */
export function offersChoice(): boolean {
  return Object.keys(currentCatalog()).length > 1
}

export function getExercise(key: string | null): ExerciseInfo {
  const catalogo = currentCatalog()
  // `Object.hasOwn` e não indexação direta, pela mesma razão do `isExerciseKey`: com chave
  // herdada (`toString`) o acesso devolveria uma função, o `??` não dispararia, e quem
  // chamasse `.display_name` receberia `undefined` no meio da tela.
  if (typeof key === 'string' && Object.hasOwn(catalogo, key)) return catalogo[key]!
  // O default pode não estar no catálogo do servidor (exercício desligado no painel). Cair no
  // primeiro que existe é melhor que devolver `undefined` — e melhor que voltar ao embutido,
  // que traria de volta um card que a admissão recusa.
  return catalogo[DEFAULT_EXERCISE] ?? Object.values(catalogo)[0] ?? EXERCISE_CATALOG[DEFAULT_EXERCISE]!
}

/** "CARDIO • CORPO INTEIRO" da referência. */
export function exerciseSubtitle(exercise: ExerciseInfo): string {
  return `${categoryLabel(exercise.category)} • ${exercise.muscle_group}`
}
