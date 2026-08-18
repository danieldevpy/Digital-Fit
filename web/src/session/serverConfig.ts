// Busca do `GET /api/config` (SPEC-018, T-074).
//
// Uma chamada no boot do APP, e outra quando a conta muda (a resposta é por plano). Não vai para
// o bundle do SITE (ADR-010): a landing não decide nada por plano, e um fetch a mais na primeira
// tela do funil se pagaria com nada.
//
// **Falhar aqui é silencioso e normal.** Sem servidor, sem rede, ou com 500: o cliente fica com
// o que tiver — o último catálogo conhecido ou o embutido —, que é exatamente como ele
// funcionava antes desta task. Configuração indisponível é um treino a menos de personalização,
// nunca um erro na cara de quem ia treinar (P2 da SPEC-018, do lado de cá).
import { identityHeaders } from '../auth/storage'
import { localeHeaders } from '../i18n/http'
import { useConfigStore, type ServerConfig } from '../store/config'
import { apiBaseUrl } from './admission'

const ETAG_KEY = 'digitalfit.config_etag'
const CONFIG_KEY = 'digitalfit.config'

// `window.localStorage` e sempre dentro de `try`, como manda `auth/storage.ts`: ele falha de
// verdade (Safari em navegação privada lança ao escrever) e não existe fora do navegador. Perder
// o que está guardado custa um payload a mais, nunca uma falha.
function ler(chave: string): string | null {
  try {
    return window.localStorage.getItem(chave)
  } catch {
    return null
  }
}

function gravar(chave: string, valor: string | null): void {
  try {
    if (valor !== null) window.localStorage.setItem(chave, valor)
  } catch {
    // Sem armazenamento: revalidar volta a custar o payload inteiro, e só.
  }
}

/**
 * Recoloca no store a última configuração conhecida, antes de falar com a rede.
 *
 * **É o que faz o ETag valer alguma coisa.** Sem isto, uma aba nova teria store vazio, não
 * poderia mandar `If-None-Match` (um 304 sobre store vazio deixaria o app sem catálogo), e o
 * `GET /api/config` baixaria o payload inteiro em toda abertura — o 304 da spec seria
 * decoração. Com isto, o boot hidrata do disco, revalida, e o caso comum (nada mudou) custa
 * uma resposta sem corpo.
 *
 * O que está no disco nunca é a última palavra: a revalidação acontece sempre, e a trava de
 * verdade é a admissão. Catálogo velho no máximo mostra um card que o `POST /sessions` recusa
 * com mensagem clara — não abre nada que o plano não permita.
 */
export function hydrateStoredConfig(): boolean {
  const cru = ler(CONFIG_KEY)
  if (!cru) return false
  try {
    useConfigStore.getState().apply(JSON.parse(cru) as ServerConfig)
    return true
  } catch {
    // JSON corrompido ou de uma versão antiga do payload: descarta e segue com o embutido.
    return false
  }
}

/**
 * Lê a configuração do servidor e aplica no store. Devolve `true` quando algo foi aplicado.
 *
 * O `identityHeaders` vai junto porque a resposta é **por usuário**: o plano de quem chama
 * decide capacidades e, com a SPEC-020, o próprio conteúdo do catálogo.
 *
 * O 304 não aplica nada de propósito — ele confirma que o que já está no store continua valendo.
 * Por isso o `If-None-Match` só sai quando há catálogo em memória (hidratado ou recém-buscado):
 * revalidar com sucesso sobre um store vazio seria o pior dos dois mundos.
 */
export async function fetchServerConfig(fetchImpl: typeof fetch = fetch): Promise<boolean> {
  if (useConfigStore.getState().exercises === null) hydrateStoredConfig()
  const temCatalogo = useConfigStore.getState().exercises !== null
  const etag = temCatalogo ? ler(ETAG_KEY) : null

  try {
    const resposta = await fetchImpl(`${apiBaseUrl()}/api/config`, {
      headers: {
        ...identityHeaders(),
        // O idioma do CLIENTE, não o do navegador (T-153): o payload e o ETag desta rota
        // variam por locale desde a T-143, e sem este header o servidor responderia na língua
        // do navegador mesmo depois de a pessoa trocar o idioma no seletor.
        ...localeHeaders(),
        ...(etag ? { 'If-None-Match': etag } : {}),
      },
    })

    if (resposta.status === 304) return false
    if (!resposta.ok) return false

    const bruto = await resposta.text()
    useConfigStore.getState().apply(JSON.parse(bruto) as ServerConfig)
    // O corpo é guardado como veio; o ETag só depois, e só se o corpo foi aceito. Gravar o ETag
    // de um payload que não entrou faria a próxima revalidação devolver 304 sobre o nada.
    gravar(CONFIG_KEY, bruto)
    gravar(ETAG_KEY, resposta.headers.get('ETag'))
    return true
  } catch {
    return false
  }
}
