// Calorias ao vivo (SPEC-016 Fase Inicial, critério 3): "mede só na hora".
//
// **Por repetição, não por tempo decorrido.** A T-063 entregou `MET × 3,5 × peso / 200 ×
// minutos` — a fórmula clássica, aplicada ao insumo errado. Ela cobra a mesma caloria de quem
// faz 40 polichinelos em 30 s e de quem fica parado olhando a câmera: o número sobe com o
// relógio, não com o esforço. Num app que conta repetição por visão computacional, ignorar a
// contagem e faturar tempo de tela é a mentira mais fácil de não perceber — ninguém compara
// duas sessões de 30 s lado a lado, e as duas dariam 4,9 kcal.
//
// **Isto não contradiz "a UI nunca mostra número inventado".** A regra da SPEC-014 proíbe
// número que o servidor não forneceu — e é por ela que FC continua `--`. Aqui os três insumos
// que decidem o resultado vêm de fora do cliente: o **MET** e a **cadência de referência** são
// dado do catálogo servido (`Exercise`, editável no painel), e as **repetições** são as do
// `rep.detected` (SPEC-007), contadas pelo analysis-worker. A T-128 deixou o kcal mais perto
// da regra, não mais longe: antes o único insumo era o relógio do próprio cliente.
//
// O que o cliente põe de si é o peso, e ele entra marcado como estimativa justamente por ser a
// única parte que não sabemos. Sem MET ou sem cadência de referência não há conta e não há
// número: volta `null`, e a tela mostra `--`.
//
// O acúmulo (dia, semana, histórico) **não** mora aqui: é capacidade de assinante
// (`kcal_accumulation` no `Plan`) e a task dele é a T-064. Este módulo não tem estado nenhum —
// é a garantia por construção de que nada soma entre sessões.

/**
 * Peso assumido quando não sabemos o real, em kg.
 *
 * Sai daqui na T-065 (SPEC-017, perfil físico), que é quando a pessoa passa a poder informar o
 * peso dela. Até lá, é premissa declarada em vez de dado — e a tela diz isso com todas as
 * letras (`ESTIMATED_LABEL`), porque um número derivado de um peso inventado sem aviso seria
 * apresentado com a mesma confiança de uma repetição contada de verdade.
 */
import { t } from '../i18n'
import { formatNumber } from '../i18n/format'

/**
 * Placeholder honesto (SPEC-014, "honestidade > fidelidade"): sem MET ou sem cadência de
 * referência o card mostra isto, e não um número derivado de palpite. Traço, não texto — não
 * passa por tradução.
 */
const NOT_AVAILABLE = '--'

export const DEFAULT_WEIGHT_KG = 70

/**
 * O que a tela escreve ao lado do número. Curto porque o card do HUD é pequeno.
 *
 * Virou função na T-150 (era `const ESTIMATED_LABEL`): constante resolvida no import congelaria
 * a palavra no idioma de quando o bundle carregou — a mesma lição do `EXERCISE_CATALOG` na
 * T-152 e do `CAMERA_LABEL` na T-149.
 */
export function estimatedLabel(): string {
  return t('session:label.estimated')
}

/**
 * Quanto o gasto por repetição responde ao ritmo.
 *
 * `0.25` quer dizer: dobrar a cadência encarece cada repetição em 25%. O efeito é real —
 * acelerar piora a economia de movimento (mais aceleração e frenagem por repetição, menos
 * aproveitamento do ciclo elástico) — e é **modesto** de propósito. O ganho principal de quem
 * acelera já está contado antes deste multiplicador: mais rápido = mais repetições = mais
 * calorias, linearmente. Este fator é só o extra por ineficiência; um valor alto aqui contaria
 * a velocidade duas vezes.
 */
const INTENSITY_K = 0.25

/**
 * Teto e piso do multiplicador.
 *
 * A trava não é elegância, é defesa. A cadência ao vivo é `reps / tempo`, e nos primeiros
 * segundos de sessão esse quociente é instável por construção; uma repetição falsa-positiva em
 * sequência produziria um pico. Sem limite, o pico viraria um número absurdo no card — e um
 * número absurdo destrói a confiança em todos os outros que estão na mesma tela.
 */
const INTENSITY_MIN = 0.9
const INTENSITY_MAX = 1.3

/**
 * Só a partir daqui a cadência medida vale alguma coisa (segundos de sessão).
 *
 * Antes disso o multiplicador é `1`. Com 3 s decorridos, uma repetição a mais ou a menos move a
 * cadência em 20 rpm — o multiplicador saltaria entre os extremos e o card ficaria piscando
 * durante justamente o trecho em que a pessoa está se ajustando. Mesma ideia do aquecimento
 * descartado no probe da T-084: medir cedo demais é medir ruído.
 */
const CADENCE_WINDOW_S = 6

/** Insumos do kcal ao vivo. Todos de fora do cliente, menos o peso. */
export interface KcalInput {
  /** MET de tabela do exercício, servido pelo catálogo. `undefined` = o servidor não falou. */
  met: number | undefined
  /** Ritmo em que aquele MET vale (rep/min), servido junto. Sem ele o MET não vira kcal/rep. */
  refCadenceRpm: number | undefined
  /** Repetições contadas pelo servidor até agora (`rep.detected`). */
  reps: number
  /** Segundos de sessão já corridos — usado só para o ritmo, nunca para o total. */
  elapsedS: number
  weightKg?: number
}

/**
 * Quanto custa UMA repetição no ritmo de referência, em kcal.
 *
 * O MET descreve gasto por minuto a uma intensidade; dividir pela cadência daquela intensidade
 * converte "por minuto" em "por repetição". É essa divisão que a T-063 não tinha como fazer —
 * faltava a cadência no catálogo — e é por isso que ela acabou multiplicando por minutos.
 */
export function kcalPerRep(
  met: number | undefined,
  refCadenceRpm: number | undefined,
  weightKg: number = DEFAULT_WEIGHT_KG,
): number | null {
  if (!met || met <= 0 || !Number.isFinite(met)) return null
  if (!refCadenceRpm || refCadenceRpm <= 0 || !Number.isFinite(refCadenceRpm)) return null
  return (met * 3.5 * weightKg) / 200 / refCadenceRpm
}

/**
 * Multiplicador de ritmo: quanto o ritmo medido encarece cada repetição.
 *
 * `1` no ritmo de referência — e é essa igualdade que faz a fórmula nova reduzir exatamente à
 * antiga quando a pessoa treina no ritmo que o MET pressupõe. A mudança da T-128 não reescala o
 * produto; ela faz o número responder a quem está treinando.
 */
export function intensityMultiplier(
  cadenceRpm: number,
  refCadenceRpm: number | undefined,
): number {
  if (!refCadenceRpm || refCadenceRpm <= 0) return 1
  if (!Number.isFinite(cadenceRpm) || cadenceRpm <= 0) return 1
  const bruto = 1 + INTENSITY_K * (cadenceRpm / refCadenceRpm - 1)
  return Math.max(INTENSITY_MIN, Math.min(INTENSITY_MAX, bruto))
}

/** Ritmo médio da sessão até agora, em rep/min. `null` enquanto a janela não fecha. */
export function liveCadenceRpm(reps: number, elapsedS: number): number | null {
  if (elapsedS < CADENCE_WINDOW_S || reps <= 0) return null
  return (reps / elapsedS) * 60
}

/**
 * Calorias gastas até agora nesta sessão. `null` quando não dá para saber.
 *
 * Função pura, com repetições e tempo como parâmetros: sem relógio de dentro, ela se testa com
 * um objeto e o mesmo insumo dá sempre o mesmo número (convenção da casa para tudo que é
 * derivação). Chamá-la duas vezes com o mesmo estado não soma nada — ela não acumula, ela
 * recalcula.
 */
export function liveKcal({
  met,
  refCadenceRpm,
  reps,
  elapsedS,
  weightKg = DEFAULT_WEIGHT_KG,
}: KcalInput): number | null {
  const porRep = kcalPerRep(met, refCadenceRpm, weightKg)
  if (porRep === null) return null
  if (!Number.isFinite(reps) || reps <= 0) return 0

  const cadencia = liveCadenceRpm(reps, elapsedS)
  const fator = cadencia === null ? 1 : intensityMultiplier(cadencia, refCadenceRpm)
  return reps * porRep * fator
}

/**
 * O número como ele aparece no card. `--` quando não há o que mostrar.
 *
 * Uma casa decimal porque uma repetição de polichinelo custa ~0,2 kcal: arredondar para inteiro
 * faria o card ficar parado em "4" por cinco repetições seguidas — e um número parado durante o
 * esforço lê como "não está me vendo", a mesma razão pela qual o ângulo do agachamento é `--`.
 */
export function formatKcal(kcal: number | null): string {
  if (kcal === null) return NOT_AVAILABLE
  // Uma casa decimal SEMPRE, e o separador do idioma ativo: `.toFixed(1).replace('.', ',')`
  // escrevia a vírgula brasileira à mão e mostrava "4,9 kcal" numa tela em inglês (armadilha
  // §2.6 do PLANO-I18N, a mesma que o `warmupLabel` tinha na T-149).
  return formatNumber(kcal, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}
