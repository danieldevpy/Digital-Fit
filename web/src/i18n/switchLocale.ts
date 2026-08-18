// Trocar de idioma em runtime (T-153, SPEC-025 §Notas técnicas).
//
// **Trocar a preferência não basta.** O store muda, a tela redesenha — e o catálogo, as
// conquistas e as mensagens de feedback continuam na língua anterior, porque as três chegaram
// do servidor e estão em cache. A SPEC-025 §Notas técnicas nomeia os dois caches que fariam
// isso acontecer, e é por eles que esta função existe:
//
//   - `GET /api/config` responde com ETag que INCLUI o locale (T-143). O `If-None-Match` que o
//     cliente guardou é o da língua velha, então o servidor devolve 200 com o corpo novo — mas
//     só se alguém pedir. Sem esta chamada, o catálogo traduzido só apareceria no próximo boot.
//   - `GET /api/engagement` é cacheado por `(usuário, dia, locale)` (T-143) e traz nome e
//     descrição de conquista já renderizados (T-145). `force: true` porque houve FATO novo, não
//     suspeita — a janela de frescor não sabe que o idioma mudou.
//
// **Este arquivo é do APP e o SITE não pode importá-lo** (ADR-010): ele puxa `session/` e
// `engagement/`, que não existem no bundle da landing. Lá a troca de idioma é outra coisa — uma
// navegação entre `/` e `/en/` (SPEC-025 §Escopo, "site por URL"), sem store e sem revalidação.
import { refreshEngagement } from '../engagement/store'
import { fetchServerConfig } from '../session/serverConfig'
import type { Locale } from './locale'
import { useI18nStore } from './store'

/**
 * Aplica o idioma escolhido: persiste, redesenha e revalida o que o servidor já tinha dito.
 *
 * A ordem importa. O `setLocale` vem PRIMEIRO e é síncrono: a tela inteira troca de língua no
 * mesmo quadro do toque, e as duas revalidações acontecem por baixo, sem espera e sem tela de
 * carregamento — o que vem do servidor é minoria do texto, e prender a troca à rede faria um
 * seletor que não responde em avião.
 *
 * Falha de rede é silenciosa pelo mesmo motivo do `fetchServerConfig` no boot: sem resposta, o
 * cliente segue com o que tem (catálogo embutido, que já está traduzido desde a T-152), e a
 * próxima abertura corrige. Idioma não é uma operação que possa falhar na cara de quem trocou.
 */
export function switchLocale(locale: Locale): void {
  if (useI18nStore.getState().locale === locale) return

  useI18nStore.getState().setLocale(locale)

  void fetchServerConfig()
  void refreshEngagement({ force: true })
}
