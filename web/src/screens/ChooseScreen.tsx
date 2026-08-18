// Tela Escolha de exercício (SPEC-014 §2, tela 2 da referência), agora agrupada por categoria
// em faixas horizontais — o porquê da troca está no cabeçalho do `ExerciseRails`.
import { useT } from '../i18n'
import { TabBar } from '../shell/TabBar'
import { BrandMark } from '../ui/BrandMark'
import { ExerciseRails } from './ExerciseRails'

export function ChooseScreen() {
  const t = useT()

  return (
    <>
      <div className="choose">
        <BrandMark center />
        <h1 className="choose__title">{t('funnel:choose.title')}</h1>
        <p className="choose__subtitle">
          {t('funnel:choose.subtitle_top')} <em>{t('funnel:choose.subtitle_em')}</em>
        </p>
        <ExerciseRails />
      </div>
      <TabBar />
    </>
  )
}
