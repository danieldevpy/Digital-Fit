// O gatilho de foco, do lado do React (SPEC-024 §2 / T-122).
//
// Um hook e não uma chamada solta em cada tela porque são DOIS gatilhos, e o segundo é o que
// faltava no produto inteiro: não havia um `visibilitychange` em lugar nenhum de `web/src`.
// Quem esconde o app no bolso e volta cinco minutos depois não remonta componente nenhum — sem
// este ouvinte, a tela fica com o número que tinha quando o celular foi guardado.
//
// O terceiro gatilho (fim de sessão) não mora aqui: ele nasce onde o relatório chega
// (`store/session.ts`), porque não depende de tela aberta nenhuma.
import { useEffect } from 'react'
import { refreshHistory } from './refresh'

/**
 * O `visibilitychange` dispara nas duas pontas — ao esconder e ao voltar — e só a volta
 * interessa.
 *
 * Revalidar ao ESCONDER gastaria rede para atualizar o que ninguém está vendo, e o navegador
 * costuma congelar a aba escondida no meio do pedido: o resultado seria uma requisição que
 * morre pela metade toda vez que alguém troca de app.
 *
 * Função exportada e não `if` dentro do hook porque é a regra, e a suíte roda em ambiente
 * `node` — sem isto ela só seria verificável à mão, num celular.
 */
export function deveRevalidarAoMudarVisibilidade(hidden: boolean): boolean {
  return !hidden
}

/** Chamado por toda tela que mostra dado acumulado: Progresso, Analytics e o Perfil. */
export function useFreshHistory(): void {
  useEffect(() => {
    void refreshHistory()

    // `document` pode não existir (SSR, teste em ambiente `node`): a tela continua funcionando
    // com o gatilho de montagem acima, que é o caso comum.
    if (typeof document === 'undefined') return

    const aoMudarVisibilidade = () => {
      if (deveRevalidarAoMudarVisibilidade(document.hidden)) void refreshHistory()
    }

    document.addEventListener('visibilitychange', aoMudarVisibilidade)
    return () => document.removeEventListener('visibilitychange', aoMudarVisibilidade)
  }, [])
}
