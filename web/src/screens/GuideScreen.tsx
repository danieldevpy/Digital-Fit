// Tela Guia / exemplo passo a passo (SPEC-015). Estática de propósito: aqui não monta
// câmera nem sessão — é o respiro entre escolher e treinar.
import { CENA_PADRAO, exerciseSubtitle, getExercise } from '../session/catalog'
import { setGuideSeen } from '../session/preferences'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { BrandMark } from '../ui/BrandMark'
import { ExerciseIcon } from '../ui/exerciseIcon'
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
        <BrandMark center />
        <p className="guide__kicker">Exemplo guiado</p>
        <h1 className="guide__title">{info.display_name}</h1>
        <p className="guide__sub">{exerciseSubtitle(info)}</p>

        {/* Sem foto, a figura do exercício. Um `src` vazio renderiza ícone de imagem
            quebrada, que é pior que não prometer fotografia nenhuma. */}
        {info.demo_img ? (
          <img
            className="guide__demo"
            src={info.demo_img}
            alt={`Demonstração do exercício ${info.display_name}`}
          />
        ) : (
          <ExerciseIcon exercise={exercise} className="guide__demo guide__demo--figura" />
        )}

        {info.guide_steps.length > 0 && (
          <div className="guide__steps">
            {info.guide_steps.map((step, i) => (
              <div className="guide-step" key={i}>
                <span className="guide-step__n">{i + 1}</span>
                {step.img && (
                  <img className="guide-step__img" src={step.img} alt="" loading="lazy" />
                )}
                <p className="guide-step__text">{step.text}</p>
              </div>
            ))}
          </div>
        )}

        <p className="guide__scene">
          <strong>Prepare a cena:</strong> {info.scene_tip || CENA_PADRAO}
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
