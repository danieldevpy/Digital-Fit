// Quota diária do lado do cliente (SPEC-016, T-063).
//
// **A UI reflete o limite; quem trava é a API.** A spec é explícita: "a trava é sempre no
// servidor (quota/admission); a UI apenas reflete e vende o upgrade, nunca é a única barreira".
// Nada aqui decide nada — tudo é eco de um número que veio do `POST /api/sessions` ou desta
// chamada. Se este arquivo inteiro fosse apagado por um cliente adulterado, o limite
// continuaria valendo (é o critério 4 da spec, e há teste dele em `tests/test_quota.py`).
//
// O que este arquivo compra é a **outra metade do critério 1**: o sheet aparece *antes* de a
// câmera abrir. Sem o pré-voo, a pessoa daria permissão de câmera, esperaria o landmarker
// aquecer e se enquadraria — para só então ouvir "não". O limite continuaria correto e a
// experiência continuaria ruim.
import { identityHeaders, rememberDeviceId } from '../auth/storage'
import { apiBaseUrl } from './admission'

/**
 * A quota como o servidor a conta — espelho de `_snapshot_de_quota()` em `server/api/views.py`.
 *
 * Um tipo só porque é um corpo só: o mesmo objeto chega no ticket do 201, na recusa do 429 e no
 * pré-voo do `GET /api/quota`. Três tipos parecidos aqui seriam três leitores para o mesmo
 * número, e o terceiro é sempre o que esquece um campo.
 */
export interface QuotaSnapshot {
  used: number
  limit: number
  remaining: number
  /** Plano sem limite (`daily_sessions = 0`). Dito em voz alta para ausência não virar permissão. */
  unlimited: boolean
  allowed: boolean
  /** Próxima virada do contador, ISO 8601 em UTC. O rótulo "renova às 21:00" sai daqui. */
  resets_at: string
  plan: string
  plan_name: string
  /** Texto da recusa, editável no painel (SPEC-018 §C) — o cliente não tem cópia dele. */
  message: string
  /** Só no pré-voo do visitante: o id que o servidor gerou, para a contagem cair na mesma chave. */
  device_id?: string
}

/**
 * Lê quanto ainda dá para treinar hoje. `null` quando não deu para saber.
 *
 * Falhar é silencioso e devolve `null` de propósito, como o `fetchServerConfig`: sem rede, o
 * cliente fica com o que já tinha. Inventar um `allowed: true` aqui abriria a câmera de quem já
 * esgotou; inventar `allowed: false` trancaria quem não esgotou. `null` deixa a decisão para o
 * único lugar que sabe, que é a admissão.
 */
export async function fetchQuota(fetchImpl: typeof fetch = fetch): Promise<QuotaSnapshot | null> {
  try {
    const resposta = await fetchImpl(`${apiBaseUrl()}/api/quota`, { headers: identityHeaders() })
    if (!resposta.ok) return null
    const corpo = (await resposta.json()) as QuotaSnapshot
    // Mesma razão do ticket: na primeira visita quem gerou o id foi o servidor, e amanhã só
    // conta na mesma chave se o cliente guardar ESTE id.
    rememberDeviceId(corpo.device_id)
    return corpo
  } catch {
    return null
  }
}
