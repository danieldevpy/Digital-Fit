// Calorias ao vivo (SPEC-016 Fase Inicial, critério 3): "mede só na hora".
//
// **Isto não contradiz "a UI nunca mostra número inventado".** A regra da SPEC-014 proíbe
// número que o servidor não forneceu — e é por ela que FC continua `--` até haver sensor. Aqui
// os dois insumos que decidem o resultado vêm de fora do cliente: o **MET** é dado do catálogo
// servido (`Exercise.met`, T-074, editável no painel) e o **tempo** é o da sessão que o
// servidor admitiu. O que o cliente põe de si é o peso, e ele entra marcado como estimativa
// justamente porque é a única parte que não sabemos.
//
// Sem MET não há conta e não há número: volta `null`, e a tela mostra `--`. É o caso do
// catálogo embutido (que não tem `met` — "o servidor é quem sabe") e o do app offline. Um MET
// médio chutado aqui seria a mentira silenciosa que a regra existe para impedir: ninguém veria
// diferença entre a caloria de um polichinelo e a de um alongamento.
//
// O acúmulo (dia, semana, histórico) **não** entra nesta task: é capacidade de assinante
// (`kcal_accumulation` no `Plan`) e a task dele é a T-064. O Free mede na hora e não soma —
// e é por isso que este módulo não tem estado nenhum.

/**
 * Peso assumido quando não sabemos o real, em kg.
 *
 * Sai daqui na T-065 (SPEC-017, perfil físico), que é quando a pessoa passa a poder informar o
 * peso dela. Até lá, é premissa declarada em vez de dado — e a tela diz isso com todas as
 * letras (`ESTIMATED_LABEL`), porque um número derivado de um peso inventado sem aviso seria
 * apresentado com a mesma confiança de uma repetição contada de verdade.
 */
export const DEFAULT_WEIGHT_KG = 70

/** O que a tela escreve ao lado do número. Curto porque o card do HUD é pequeno. */
export const ESTIMATED_LABEL = 'estimado'

/**
 * Calorias gastas até agora nesta sessão. `null` quando não dá para saber.
 *
 * Fórmula MET clássica: `kcal/min = MET × 3,5 × peso(kg) / 200`. É a mesma do
 * *Compendium of Physical Activities*, que é de onde os valores de `Exercise.met` vêm — usar
 * outra conta com aqueles números daria um resultado que não é nem uma coisa nem outra.
 *
 * Função pura, com o tempo como parâmetro: sem relógio de dentro, ela se testa com um objeto e
 * o mesmo insumo dá sempre o mesmo número (convenção da casa para tudo que é derivação).
 */
export function liveKcal(
  met: number | undefined,
  elapsedS: number,
  weightKg: number = DEFAULT_WEIGHT_KG,
): number | null {
  if (!met || met <= 0 || !Number.isFinite(met)) return null
  if (!Number.isFinite(elapsedS) || elapsedS <= 0) return 0
  return (met * 3.5 * weightKg * (elapsedS / 60)) / 200
}

/**
 * O número como ele aparece no card. `--` quando não há o que mostrar.
 *
 * Uma casa decimal porque 30 s de polichinelo dão ~4 kcal: arredondar para inteiro faria o
 * card ficar parado em "4" durante um terço da sessão, e um número parado durante o esforço lê
 * como "não está me vendo" — a mesma razão pela qual o ângulo do agachamento é `--`.
 */
export function formatKcal(kcal: number | null): string {
  if (kcal === null) return '--'
  return kcal.toFixed(1).replace('.', ',')
}
