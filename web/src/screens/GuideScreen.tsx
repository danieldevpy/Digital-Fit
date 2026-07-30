// Tela Guia / exemplo passo a passo (SPEC-015). Estática de propósito: aqui não monta
// câmera nem sessão — é o respiro entre escolher e treinar.
import { exerciseSubtitle, getExercise } from '../session/catalog'
import { setGuideSeen } from '../session/preferences'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { IconPlay } from '../ui/icons'

export function GuideScreen({ exercise }: { exercise: string }) {
  const info = getExercise(exercise)

  // "Pular" também marca como visto: pular é uma resposta, não uma falha do funil.
  const seguir = () => {
    setGuideSeen(exercise)
    navigate({ screen: 'preparar' })
  }

  return (
    <>
      <div className="guide">
        <p className="guide__kicker">Exemplo guiado</p>
        <h1 className="guide__title">{info.display_name}</h1>
        <p className="guide__sub">{exerciseSubtitle(info)}</p>

        <img
          className="guide__demo"
          src={info.demo_img}
          alt={`Demonstração do exercício ${info.display_name}`}
        />

        {info.guide_steps.length > 0 && (
          <div className="guide__steps">
            {info.guide_steps.map((step, i) => (
              <div className="guide-step" key={i}>
                <span className="guide-step__n">{i + 1}</span>
                <img className="guide-step__img" src={step.img} alt="" loading="lazy" />
                <p className="guide-step__text">{step.text}</p>
              </div>
            ))}
          </div>
        )}

        <p className="guide__scene">
          <strong>Prepare a cena:</strong> celular apoiado na vertical, uns 2 metros de
          distância, corpo inteiro no quadro e luz vindo de frente.
        </p>

        <div className="guide__cta">
          <button type="button" className="v2-cta" onClick={seguir}>
            Entendi, vamos lá
            <span className="v2-cta__play">
              <IconPlay className="v2-cta__play-icon" />
            </span>
          </button>
        </div>
        <button type="button" className="guide__skip" onClick={seguir}>
          Pular exemplo
        </button>
      </div>
      <TabBar />
    </>
  )
}
