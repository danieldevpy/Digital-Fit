// Assinatura da marca (T-081). Uma linha só, presente em toda tela do app.
//
// O site já se apresenta (logo grande na landing e no Sobre); dentro do app a marca não pode
// competir com o que a tela está fazendo — quem está treinando olha repetição e tempo, não
// logotipo. Por isso a assinatura é pequena, de baixo contraste e SEMPRE no mesmo canto de
// cada família de tela: nas telas de conteúdo, colada acima do título; nas telas de câmera,
// flutuando no topo-esquerdo, na faixa que o cabeçalho central deixa livre.
//
// É decoração, não navegação: não leva a lugar nenhum (a porta para o site é o Sobre) e sai
// da árvore de acessibilidade — um leitor de tela anunciando "Digital Fit" em cada tela é
// ruído, e o nome do app já está no `<title>`.
import { IconLogo } from './icons'

interface BrandMarkProps {
  /** Sobre a câmera: posicionamento absoluto no topo-esquerdo do palco. */
  floating?: boolean
  /** Centralizada — telas cujo título também é centralizado (Escolha, Guia, folhas). */
  center?: boolean
}

export function BrandMark({ floating = false, center = false }: BrandMarkProps) {
  return (
    <p
      className={`brand-mark ${floating ? 'brand-mark--float' : ''} ${
        center ? 'brand-mark--center' : ''
      }`}
      aria-hidden="true"
    >
      <IconLogo className="brand-mark__icon" />
      {/* "Digital Fit" é o NOME do produto, não texto de produto: fica igual nas duas línguas,
          pela mesma razão que `Category` guarda `forca` e não `"Força"` (SPEC-025 §Entidade —
          o que já é código, ou nome próprio, não vira chave de dicionário). Mesma decisão do
          `DIGITAL FIT` da landing (T-147). */}
      {/* eslint-disable i18next/no-literal-string */}
      <span>
        Digital <em>Fit</em>
      </span>
      {/* eslint-enable i18next/no-literal-string */}
    </p>
  )
}
