// Tela Guia / exemplo passo a passo (SPEC-015). Estática de propósito: aqui não monta
// câmera nem sessão — é o respiro entre escolher e treinar.
import { useState } from 'react'
import { useT } from '../i18n'
import { cenaPadrao, exerciseSubtitle, getExercise } from '../session/catalog'
import { setViewPreference, viewPreference, viewsOf } from '../session/exerciseViews'
import { setGuideSeen } from '../session/preferences'
import { navigate } from '../shell/nav'
import { TabBar } from '../shell/TabBar'
import { BrandMark } from '../ui/BrandMark'
import { ExerciseIcon } from '../ui/exerciseIcon'
import { IconPlay } from '../ui/icons'
import { ViewPicker } from '../ui/ViewPicker'

export function GuideScreen({ exercise }: { exercise: string }) {
  const t = useT()
  const info = getExercise(exercise)
  // A variação é escolhida AQUI e na pré-config, e o Guia é o lugar onde ela se explica: é a
  // tela que existe para ensinar a montar a cena, e montar a cena é justamente o que muda
  // entre as duas. Trocar aqui reescreve os passos e a instrução de cena logo abaixo.
  const [viewId, setViewId] = useState(() => viewPreference(exercise))
  const views = viewsOf(exercise)
  const view = views?.find((v) => v.id === viewId) ?? views?.[0]
  const passos = view?.guide_steps ?? info.guide_steps
  const cena = view?.scene_tip ?? info.scene_tip ?? cenaPadrao()
  // A foto grande também é da vista: ela é a primeira coisa que a tela diz, e dizer «de frente»
  // no botão com uma foto de perfil no alto é ensinar duas cenas ao mesmo tempo.
  const demo = view?.demo_img ?? info.demo_img

  // "Pular" também marca como visto: pular é uma resposta, não uma falha do funil.
  const seguir = () => {
    setGuideSeen(exercise)
    navigate({ screen: 'preparar' })
  }

  return (
    <>
      <div className="guide">
        <BrandMark center />
        <p className="guide__kicker">{t('funnel:guide.kicker')}</p>
        <h1 className="guide__title">{info.display_name}</h1>
        <p className="guide__sub">{exerciseSubtitle(info)}</p>

        {/* Sem foto, a figura do exercício. Um `src` vazio renderiza ícone de imagem
            quebrada, que é pior que não prometer fotografia nenhuma. */}
        {demo ? (
          <img
            className="guide__demo"
            src={demo}
            alt={t('funnel:guide.demo_alt', { exercise: info.display_name })}
          />
        ) : (
          <ExerciseIcon exercise={exercise} className="guide__demo guide__demo--figura" />
        )}

        {/* Antes dos passos, e não depois: a variação decide o que os passos dizem, e ler
            "deite o celular no chão" para só então descobrir que havia outra opção é a ordem
            errada de aprender. */}
        <ViewPicker
          exercise={exercise}
          value={viewId}
          onChange={(id) => setViewId(setViewPreference(exercise, id))}
        />

        {passos.length > 0 && (
          <div className="guide__steps">
            {passos.map((step, i) => (
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
          <strong>{t('funnel:guide.scene_label')}</strong> {cena}
        </p>

        <div className="guide__cta">
          <button type="button" className="v2-cta" onClick={seguir}>
            {t('funnel:guide.cta')}
            <span className="v2-cta__play">
              <IconPlay className="v2-cta__play-icon" />
            </span>
          </button>
        </div>
        <button type="button" className="guide__skip" onClick={seguir}>
          {t('funnel:guide.skip')}
        </button>
      </div>
      <TabBar />
    </>
  )
}
