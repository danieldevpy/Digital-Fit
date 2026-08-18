// O fuso do aparelho (T-156, SPEC-019 §Fuso).
//
// O fogo, a meta diária e o TTL do cache viravam o dia às 00h de **São Paulo**, para todo
// mundo. Quem treina às 22h em Lisboa caía no dia seguinte e via o streak quebrar sozinho —
// modo de falha silencioso, e do lado de quem estava certo. O servidor passou a resolver a
// virada pelo fuso de quem treina (`api/fuso.py`); este arquivo é quem conta a ele qual é.
//
// **Do APARELHO, e não da conta**: a mesma pessoa treina no celular em viagem e no notebook em
// casa, e "hoje" é o do relógio que ela está olhando. É a mesma casa e o mesmo motivo das
// outras preferências de aparelho (`digitalfit.locale`, `digitalfit.countdown_s`) — só que esta
// nem precisa ser guardada: o navegador já sabe responder.

/**
 * O nome IANA do fuso deste aparelho (`America/Sao_Paulo`, `Europe/Lisbon`).
 *
 * String vazia quando o ambiente não sabe responder (Node antigo, `Intl` capado). Vazio é
 * tratado como ausência pelo servidor, que cai no padrão — nunca como "UTC", que seria inventar
 * uma resposta e deslocar o dia de quem não tinha problema nenhum.
 */
export function deviceTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
}

/**
 * O cabeçalho do fuso, no padrão de `localeHeaders()` (`i18n/http.ts`).
 *
 * Objeto vazio quando não há fuso a declarar — mandar `X-Timezone: ` vazio faria o servidor
 * gastar uma normalização para chegar ao mesmo default.
 */
export function timezoneHeaders(): Record<string, string> {
  const fuso = deviceTimeZone()
  return fuso ? { 'X-Timezone': fuso } : {}
}
