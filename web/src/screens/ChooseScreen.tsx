// Tela Escolha de exercício (SPEC-014 §2, tela 2 da referência), agora agrupada por categoria
// em faixas horizontais — o porquê da troca está no cabeçalho do `ExerciseRails`.
import { TabBar } from '../shell/TabBar'
import { BrandMark } from '../ui/BrandMark'
import { ExerciseRails } from './ExerciseRails'

export function ChooseScreen() {
  return (
    <>
      <div className="choose">
        <BrandMark center />
        <h1 className="choose__title">Escolha seu exercício</h1>
        <p className="choose__subtitle">
          Treinos rápidos, <em>resultados reais</em>
        </p>
        <ExerciseRails />
      </div>
      <TabBar />
    </>
  )
}
