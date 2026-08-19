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
import { t, tDynamic, useLocale } from '../i18n'
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
  /**
   * Imagem de demonstração (SPEC-015: "todo exercício tem demo visual").
   *
   * **Vazio é um estado suportado**, e não um esquecimento: exercício novo chega antes da
   * foto, e apontar para um arquivo que não existe põe ícone de imagem quebrada no card. Quem
   * cai no vazio desenha a FIGURA do exercício (`ExerciseIcon`) — a mesma silhueta do resto do
   * app, que afirma a pose certa sem prometer uma fotografia.
   */
  demo_img: string
  /**
   * Como montar a cena para ESTE exercício (SPEC-015 / SPEC-020 Tier C).
   *
   * Era uma frase fixa dentro da tela do Guia — "celular apoiado na vertical, uns 2 metros" —
   * verdadeira enquanto todo exercício era em pé. A flexão e o abdominal pedem o oposto
   * (celular deitado no chão, de lado), e instrução de cena errada aqui não é erro de texto: é
   * a sessão inteira sair zerada porque o worker não viu o corpo. Vazio cai na frase padrão.
   */
  scene_tip?: string
  /** Cor do dot de grupo no card da Escolha (SPEC-014 §2). */
  dot_color: string
  /** Passos do exemplo guiado (SPEC-015). Vazio não quebra: o Guia mostra demo + cena. */
  guide_steps: { img: string; text: string }[]
  /** Insumo do kcal (SPEC-016/017). `undefined` no embutido: o servidor é quem sabe. */
  met?: number
  /**
   * Ritmo em que o `met` vale, em rep/min (T-128). Anda **em par** com ele: o MET de tabela
   * descreve o gasto a uma intensidade, e é este número que diz qual. Sozinho, o MET não vira
   * caloria por repetição — vira `--`.
   */
  ref_cadence_rpm?: number
  /** Selo de qualidade (SPEC-020). Quem o usa na tela é a T-090/T-091, não esta task. */
  maturity?: string
}

/**
 * Rótulo de exibição de uma categoria (namespace `catalog`, T-152: `category.<slug>`).
 *
 * O catálogo guarda o **slug** desde a T-074 porque categoria virou contrato — conquistas
 * (SPEC-019) e o mix por objetivo (SPEC-022) consomem os slugs, e o cliente guardava a string
 * de exibição (`'Cardio'`, `'Força'`). Slug desconhecido devolve ele mesmo em vez de vazio:
 * uma categoria nova no servidor aparece feia, e não some da tela. Chave montada em tempo de
 * execução ⇒ `tDynamic`, não `t()` (a chave não é um literal estático — ver o docstring dela).
 */
export function categoryLabel(slug: string): string {
  return tDynamic(`catalog:category.${slug}`, slug)
}

/**
 * Ordem das seções da tela Escolha — do que aquece para o que exige (SPEC-020 §Categorias).
 *
 * Vive aqui e não na tela porque é a mesma decisão de produto que o `CATEGORY_LABELS`: a
 * ordem em que as categorias se apresentam é conteúdo, não layout. A tela só desenha.
 */
const CATEGORY_ORDER = ['cardio', 'forca', 'core', 'mobilidade']

export interface CategoryGroup {
  /** Slug da categoria — o que os consumidores de contrato leem. */
  category: string
  /** Rótulo de exibição já resolvido, para a tela não ter que chamar `categoryLabel`. */
  label: string
  /** Chaves dos exercícios da categoria, na ordem do catálogo (que é a `ordem` do servidor). */
  keys: string[]
}

/**
 * Agrupa o catálogo em seções por categoria (SPEC-020 §Escopo: "tela Escolha agrupada por
 * categoria").
 *
 * **Categoria desconhecida vira seção própria no fim, e não some.** O servidor pode servir uma
 * categoria que este cliente não conhece — foi o `[A/T-051]` inteiro —, e engolir o exercício
 * aqui recriaria o mesmo sintoma pelo outro lado: o exercício existe, a admissão aceita, e a
 * tela não o mostra. Aparecer com o slug cru é feio; sumir é bug.
 *
 * Função pura, fora do componente, porque é a única parte disto que dá para cobrar por teste
 * sem DOM — a suíte do web roda em `node`.
 */
export function groupByCategory(
  keys: string[],
  catalog: Record<string, ExerciseInfo>,
): CategoryGroup[] {
  const porCategoria = new Map<string, string[]>()
  for (const key of keys) {
    const info = catalog[key]
    if (!info) continue
    const atual = porCategoria.get(info.category)
    if (atual) atual.push(key)
    else porCategoria.set(info.category, [key])
  }

  // As conhecidas na ordem declarada; as demais depois, na ordem em que apareceram no catálogo
  // (que é a `ordem` do servidor — o operador ainda manda no que vem antes dentro do resto).
  const conhecidas = CATEGORY_ORDER.filter((slug) => porCategoria.has(slug))
  const resto = [...porCategoria.keys()].filter((slug) => !CATEGORY_ORDER.includes(slug))

  return [...conhecidas, ...resto].map((category) => ({
    category,
    label: categoryLabel(category),
    keys: porCategoria.get(category)!,
  }))
}

/**
 * A frase de cena padrão — a que valia para todo mundo enquanto todo exercício era em pé.
 *
 * Vive aqui, e não dentro da tela do Guia, porque agora ela é o **fallback** de um campo do
 * catálogo: quem não declara `scene_tip` recebe esta.
 *
 * **Função, não constante** (T-152, namespace `catalog`: `scene.padrao`) — de propósito, o
 * mesmo motivo do comentário em `TABS` de `shell/TabBar.tsx`: uma `const` de módulo chamaria
 * `t()` uma vez só, na primeira importação, e congelaria no idioma de quando o bundle carregou.
 * Quem consome (`GuideScreen.tsx`) passa a chamar `cenaPadrao()`.
 */
export function cenaPadrao(): string {
  return t('catalog:scene.padrao')
}

/** A cena dos exercícios de chão (SPEC-020 Tier C): o celular deita junto com a pessoa. */
function cenaChao(): string {
  return t('catalog:scene.chao')
}

/**
 * O catálogo embutido. Os campos de TEXTO (`display_name`, `muscle_group`, `default_tip`,
 * `scene_tip`, `guide_steps[].text`) são **getters**, pela mesma razão de `cenaPadrao()` acima:
 * este objeto é montado uma vez só, no import — sem getter, o texto congelaria no idioma
 * detectado nesse instante e nunca mais mudaria, nem trocando `useI18nStore.setLocale` depois
 * (é exatamente o bug que `EXERCISE_CATALOG.squat.display_name` teria se fosse `string` solta).
 * `category`, `maturity`, `demo_img`, `dot_color`, `main_angle` continuam literais: são
 * vocabulário de contrato ou caminho de arquivo, não texto.
 */
export const EXERCISE_CATALOG: Record<string, ExerciseInfo> = {
  jumping_jack: {
    get display_name() {
      return t('catalog:exercise.jumping_jack.display_name')
    },
    category: 'cardio',
    maturity: 'validado',
    get muscle_group() {
      return t('catalog:exercise.jumping_jack.muscle_group')
    },
    get default_tip() {
      return t('catalog:exercise.jumping_jack.default_tip')
    },
    main_angle: 'arm_abduction',
    demo_img: '/img/guia/polichinelo-2.jpg',
    dot_color: '#34d399',
    get guide_steps() {
      return [
        { img: '/img/guia/polichinelo-1.jpg', text: t('catalog:exercise.jumping_jack.guide_step.0') },
        { img: '/img/guia/polichinelo-2.jpg', text: t('catalog:exercise.jumping_jack.guide_step.1') },
        { img: '/img/guia/polichinelo-1.jpg', text: t('catalog:exercise.jumping_jack.guide_step.2') },
      ]
    },
  },
  squat: {
    get display_name() {
      return t('catalog:exercise.squat.display_name')
    },
    category: 'forca',
    maturity: 'validado',
    get muscle_group() {
      return t('catalog:exercise.squat.muscle_group')
    },
    get default_tip() {
      return t('catalog:exercise.squat.default_tip')
    },
    main_angle: 'none',
    demo_img: '/img/guia/agachamento-2.jpg',
    dot_color: '#4d8cff',
    get guide_steps() {
      return [
        { img: '/img/guia/agachamento-1.jpg', text: t('catalog:exercise.squat.guide_step.0') },
        { img: '/img/guia/agachamento-2.jpg', text: t('catalog:exercise.squat.guide_step.1') },
        { img: '/img/guia/agachamento-1.jpg', text: t('catalog:exercise.squat.guide_step.2') },
      ]
    },
  },
  // Os dois de chão (T-106/T-107). As fotos são de PERFIL com a câmera no chão de propósito:
  // a demo do Guia é a primeira coisa que ensina o enquadramento, e enquadramento errado num
  // exercício de chão não é estética — é a sessão inteira sair zerada.
  flexao: {
    get display_name() {
      return t('catalog:exercise.flexao.display_name')
    },
    category: 'forca',
    // `validado` desde a T-113 (migration 0019): decisão de produto de liberar para todo
    // mundo. Tem lastro — a T-111 mediu oito itens de corpus, MAE de 0,20 rep nas duas vistas.
    maturity: 'validado',
    get muscle_group() {
      return t('catalog:exercise.flexao.muscle_group')
    },
    get default_tip() {
      return t('catalog:exercise.flexao.default_tip')
    },
    main_angle: 'none',
    demo_img: '/img/guia/flexao-2.jpg',
    dot_color: '#f59e0b',
    get scene_tip() {
      return cenaChao()
    },
    get guide_steps() {
      return [
        { img: '/img/guia/flexao-1.jpg', text: t('catalog:exercise.flexao.guide_step.0') },
        { img: '/img/guia/flexao-1.jpg', text: t('catalog:exercise.flexao.guide_step.1') },
        { img: '/img/guia/flexao-2.jpg', text: t('catalog:exercise.flexao.guide_step.2') },
      ]
    },
  },
  abdominal: {
    get display_name() {
      return t('catalog:exercise.abdominal.display_name')
    },
    category: 'core',
    // `validado` desde a T-113 (migration 0019), por decisão de produto — e **sem medição por
    // trás**: não existe um único vídeo de gente real de abdominal, os limiares vêm do gerador
    // sintético, e a dívida segue declarada em `SEM_MATERIAL_REAL`
    // (`tests/test_corpus_regressao.py`). O caminho de volta é o campo Maturidade no painel.
    maturity: 'validado',
    get muscle_group() {
      return t('catalog:exercise.abdominal.muscle_group')
    },
    get default_tip() {
      return t('catalog:exercise.abdominal.default_tip')
    },
    main_angle: 'none',
    demo_img: '/img/guia/abdominal-2.jpg',
    dot_color: '#a78bfa',
    get scene_tip() {
      return cenaChao()
    },
    get guide_steps() {
      return [
        { img: '/img/guia/abdominal-1.jpg', text: t('catalog:exercise.abdominal.guide_step.0') },
        { img: '/img/guia/abdominal-1.jpg', text: t('catalog:exercise.abdominal.guide_step.1') },
        { img: '/img/guia/abdominal-2.jpg', text: t('catalog:exercise.abdominal.guide_step.2') },
      ]
    },
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
    scene_tip: ex.scene_tip,
    dot_color: ex.dot_color,
    guide_steps: ex.guide_steps,
    met: ex.met,
    ref_cadence_rpm: ex.ref_cadence_rpm,
    maturity: ex.maturity,
  }
}

/**
 * O embutido, filtrado pelo que é seguro mostrar antes de o servidor falar (T-090).
 *
 * O embutido é o catálogo do **primeiro paint e do offline**, e ele lista tudo que este bundle
 * conhece — inclusive exercício `beta`, que a SPEC-020 reserva a contas com ferramentas de dev.
 * Sem este filtro, quem abre o app vê por um instante dois cards que o `POST /sessions` recusa:
 * é o `[A/T-051]` na janela mais curta e mais difícil de reproduzir que existe.
 *
 * `validado` e nada além, de propósito. O cliente **não sabe o plano** antes do `GET /api/config`
 * — nem se a conta tem `is_admin` —, então o único piso honesto é o que vale para todo mundo.
 * Quem tem direito a mais espera a resposta do servidor, que vem em milissegundos e manda.
 */
function embutidoVisivel(): Record<string, ExerciseInfo> {
  return Object.fromEntries(
    Object.entries(EXERCISE_CATALOG).filter(([, info]) => info.maturity === 'validado'),
  )
}

/**
 * O catálogo em vigor: servidor por cima do embutido, ou o embutido seguro enquanto ele não chega.
 *
 * **Substituição, não mesclagem campo a campo.** Quando o servidor fala, ele fala sobre *o que
 * existe* — um exercício que ele não listou está desligado, fora do plano ou abaixo da
 * maturidade que este solicitante alcança, e mantê-lo por herança do embutido recriaria o card
 * que a admissão recusa, que é o `[A/T-051]` de volta.
 */
export function currentCatalog(): Record<string, ExerciseInfo> {
  const doServidor = useConfigStore.getState().exercises
  if (!doServidor) return embutidoVisivel()
  return Object.fromEntries(doServidor.map((ex) => [ex.slug, daServidor(ex)]))
}

/** Versão reativa de `currentCatalog` — as telas que listam exercícios usam esta. */
export function useCatalog(): { keys: string[]; catalog: Record<string, ExerciseInfo> } {
  const doServidor = useConfigStore((state) => state.exercises)
  // Assina o locale (T-152): os campos de texto do embutido são getters resolvidos por `t()` a
  // cada leitura (correto mesmo sem isto), mas sem o locale nas dependências do `useMemo` o
  // COMPONENTE não teria motivo para re-renderizar ao trocar de idioma — o objeto memoizado
  // continuaria de pé, e ninguém chamaria os getters de novo até a próxima causa de render.
  const locale = useLocale()
  return useMemo(() => {
    const catalog = doServidor
      ? Object.fromEntries(doServidor.map((ex) => [ex.slug, daServidor(ex)]))
      : embutidoVisivel()
    return { keys: Object.keys(catalog), catalog }
    // `locale` não aparece no corpo do memo — os getters do embutido leem o store sozinhos
    // (`t()`). Ele está aqui só como GATILHO de recomputação para o componente re-renderizar
    // ao trocar de idioma; o lint não tem como saber disso e sinaliza "dependência
    // desnecessária" por engano.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doServidor, locale])
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
