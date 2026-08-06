// A demo visual de um exercício: a FOTO quando ela existe, a FIGURA quando não existe.
//
// Existe como componente próprio porque a regra "vazio é um estado suportado" (ver `demo_img`
// no catálogo) passou a valer em duas telas com visuais diferentes — o card grande do site e o
// card do carrossel da Escolha. Escrita duas vezes, ela se perde uma vez: o exercício novo
// chega antes da foto, e a tela que esqueceu o fallback põe ícone de imagem quebrada no lugar
// da pose. Aqui a regra é uma só; as telas variam só o `className`.
import type { ExerciseInfo } from '../session/catalog'
import { ExerciseIcon } from './exerciseIcon'

interface ExerciseDemoProps {
  exercise: string
  info: ExerciseInfo
  /** Classe da caixa — as duas telas dão a ela a MESMA altura nos dois ramos, para a grade não desalinhar. */
  className: string
  /** Classe extra só do ramo figura (o traço precisa de respiro que a fotografia não precisa). */
  figuraClassName: string
  /**
   * Adiar o carregamento até a imagem entrar em cena.
   *
   * **Padrão `false`, e a exceção é que precisa ser justificada** — o contrário do instinto.
   * Dentro de um contêiner com `overflow-x: auto` o Chrome nunca dispara o carregamento de uma
   * imagem `lazy`: ela fica com `currentSrc` vazio e `complete: false` para sempre, mesmo
   * visível na tela. Medido no navegador, não deduzido — foi assim que as fotos sumiram das
   * faixas da Escolha. Só ligue onde a rolagem for a do documento, como na vitrine do site.
   */
  lazy?: boolean
}

export function ExerciseDemo({
  exercise,
  info,
  className,
  figuraClassName,
  lazy = false,
}: ExerciseDemoProps) {
  if (!info.demo_img) {
    return <ExerciseIcon exercise={exercise} className={`${className} ${figuraClassName}`} />
  }
  return (
    <img
      className={className}
      src={info.demo_img}
      alt={`Demonstração: ${info.display_name}`}
      loading={lazy ? 'lazy' : 'eager'}
    />
  )
}
