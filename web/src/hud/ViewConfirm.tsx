// A trava de confirmação da variação (T-112) — o porquê dela está em `session/viewGate.ts`.
//
// Mora sobre a janela da câmera, no caminho do "Ligar câmera", porque é ali que a decisão vira
// ação: o próximo gesto de quem confirma é pegar o celular e colocá-lo no chão (ou em pé). Uma
// tela de ajustes teria a mesma informação e chegaria tarde.
//
// **Cards grandes e não um `<select>`.** As duas opções não são valores de um mesmo campo: são
// duas montagens de cena diferentes, e o que a pessoa precisa comparar é *o que fazer com o
// celular*, não o nome da vista. Por isso cada card carrega a frase inteira, e por isso os dois
// aparecem juntos — esconder um atrás de um menu é a mesma falha que a trava veio consertar.
//
// Responsivo pelo grid: lado a lado quando há largura, empilhados quando não há. `auto-fit` com
// `minmax` faz isso sem media query e sem medir nada em JS — o card decide sozinho quando não
// cabe mais ao lado do irmão.
import { useState } from 'react'
import { setViewPreference, viewsOf, type ViewId } from '../session/exerciseViews'
import { dismissViewGate } from '../session/viewGate'
import { IconAngle, IconCamera } from '../ui/icons'

interface Props {
  exercise: string
  /** A variação em vigor quando a trava abriu. */
  value: ViewId | null
  /** Confirmou: a tela segue para a câmera. Recebe a variação escolhida. */
  onConfirm: (id: ViewId) => void
  /** Saiu sem confirmar — nada avança, e nada é gravado. */
  onCancel: () => void
}

export function ViewConfirm({ exercise, value, onConfirm, onCancel }: Props) {
  const views = viewsOf(exercise)
  const [escolhida, setEscolhida] = useState<ViewId | null>(value)
  // Desmarcado por padrão, e isto é a decisão de produto desta caixa: quem chega aqui pela
  // primeira vez não tem como saber que vai querer dispensar o aviso. Marcar por conveniência
  // seria decidir por ela justamente na tela que existe para ela decidir.
  const [naoMostrar, setNaoMostrar] = useState(false)

  if (!views) return null
  const atual = views.find((v) => v.id === escolhida) ?? views[0]!

  const confirmar = () => {
    // A ordem importa: grava a escolha ANTES de dispensar a trava. Se a dispensa viesse
    // primeiro e a gravação falhasse (armazenamento cheio, modo privado), a pessoa ficaria sem
    // a trava E sem a preferência — o pior dos dois mundos.
    setViewPreference(exercise, atual.id)
    if (naoMostrar) dismissViewGate(exercise)
    onConfirm(atual.id)
  }

  return (
    <div className="vgate" role="dialog" aria-modal="true" aria-labelledby="vgate-titulo">
      <div className="vgate__box">
        <p className="vgate__kicker">
          <IconCamera className="vgate__kicker-icon" aria-hidden="true" />
          Antes de ligar a câmera
        </p>
        <h2 className="vgate__title" id="vgate-titulo">
          Onde você vai colocar o celular?
        </h2>
        {/* A frase que justifica a interrupção. Sem ela a trava é só um obstáculo; com ela é
            um aviso, e a diferença entre os dois é a pessoa entender o preço de errar. */}
        <p className="vgate__why">
          As duas contam suas repetições — mas cada uma precisa do celular num lugar diferente.
          Com a câmera na posição errada, o treino pode terminar com <strong>zero</strong>.
        </p>

        <div className="vgate__opts" role="radiogroup" aria-label="Posição da câmera">
          {views.map((view) => {
            const ligada = view.id === atual.id
            return (
              <button
                key={view.id}
                type="button"
                role="radio"
                aria-checked={ligada}
                className={`vgate__opt ${ligada ? 'vgate__opt--on' : ''}`}
                onClick={() => setEscolhida(view.id)}
              >
                <span className="vgate__opt-label">{view.label}</span>
                <span className="vgate__opt-phone">
                  <IconAngle className="vgate__opt-icon" aria-hidden="true" />
                  {view.phone}
                </span>
              </button>
            )
          })}
        </div>

        <label className="vgate__skip">
          <input
            type="checkbox"
            checked={naoMostrar}
            onChange={(evento) => setNaoMostrar(evento.target.checked)}
          />
          <span>
            Não mostrar novamente
            {/* Dizer para onde a escolha vai embora. Sem isto, "não mostrar" lê como "perdi o
                controle", e a pessoa não marca — ou marca e se arrepende sem saber o caminho
                de volta. */}
            <small>você continua trocando pelo card “Câmera”, na coluna da esquerda</small>
          </span>
        </label>

        <div className="vgate__acoes">
          <button type="button" className="vgate__voltar" onClick={onCancel}>
            Voltar
          </button>
          <button type="button" className="v2-cta vgate__ok" onClick={confirmar}>
            Confirmar e ligar câmera
          </button>
        </div>
      </div>
    </div>
  )
}
