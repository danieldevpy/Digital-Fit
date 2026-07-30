// Tela Escolha de exercício (SPEC-014 §2, tela 2 da referência).
import { TabBar } from '../shell/TabBar'
import { ExerciseCards } from './ExerciseCards'

export function ChooseScreen() {
  return (
    <>
      <div className="choose">
        <h1 className="choose__title">Escolha seu exercício</h1>
        <p className="choose__subtitle">
          Treinos rápidos, <em>resultados reais</em>
        </p>
        <ExerciseCards />
      </div>
      <TabBar />
    </>
  )
}
