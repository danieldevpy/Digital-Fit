// Persistência local de identidade (SPEC-011): id do aparelho e tokens JWT.
//
// Tudo passa por aqui em vez de chamar `localStorage` direto porque ele **falha de verdade**:
// Safari em navegação privada lança ao escrever, e um `setItem` solto derrubaria a admissão
// inteira por causa de um id de funil. Aqui a falha vira "não guardei" — o app continua, o
// visitante ganha um device novo a cada visita e nunca esbarra no trial. É o comportamento
// certo: a spec diz que isto é funil, não segurança.

const DEVICE_KEY = 'digitalfit.device_id'
const ACCESS_KEY = 'digitalfit.access'
const REFRESH_KEY = 'digitalfit.refresh'

function ler(chave: string): string | null {
  try {
    return window.localStorage.getItem(chave)
  } catch {
    return null
  }
}

function gravar(chave: string, valor: string | null): void {
  try {
    if (valor === null) window.localStorage.removeItem(chave)
    else window.localStorage.setItem(chave, valor)
  } catch {
    // Sem armazenamento: segue em memória pelo tempo da aba.
  }
}

/**
 * Id do aparelho para o trial anônimo. `null` até a API devolver o primeiro — quem gera é o
 * servidor (`api/trial.py`), e inventar um aqui criaria dois formatos do mesmo id.
 */
export function deviceId(): string | null {
  return ler(DEVICE_KEY)
}

export function rememberDeviceId(id: string | null | undefined): void {
  if (id) gravar(DEVICE_KEY, id)
}

/**
 * Só o aparelho, sem o `Authorization`.
 *
 * É o que o cadastro manda (T-087): o servidor usa o id para adotar as sessões que este
 * aparelho fez como visitante. Mandar um `Authorization` velho junto seria dizer "já estou
 * logado" na requisição que existe para criar a conta.
 */
export function deviceHeaders(): Record<string, string> {
  const device = deviceId()
  return device ? { 'X-Device-Id': device } : {}
}

export interface TokenPair {
  access: string
  refresh: string
}

export function storedTokens(): Partial<TokenPair> {
  return { access: ler(ACCESS_KEY) ?? undefined, refresh: ler(REFRESH_KEY) ?? undefined }
}

export function storeTokens(tokens: Partial<TokenPair>): void {
  if (tokens.access !== undefined) gravar(ACCESS_KEY, tokens.access)
  if (tokens.refresh !== undefined) gravar(REFRESH_KEY, tokens.refresh)
}

export function clearTokens(): void {
  gravar(ACCESS_KEY, null)
  gravar(REFRESH_KEY, null)
}

/**
 * Cabeçalhos de identidade de toda chamada à API.
 *
 * O `X-Device-Id` vai **junto** com o `Authorization` quando os dois existem: o servidor é
 * quem decide qual usar (logado ignora o aparelho), e o cliente que resolvesse isso sozinho
 * teria de espelhar a regra de quota — duas fontes da verdade para a mesma decisão.
 */
export function identityHeaders(): Record<string, string> {
  const headers: Record<string, string> = { ...deviceHeaders() }
  const { access } = storedTokens()
  if (access) headers.Authorization = `Bearer ${access}`
  return headers
}
