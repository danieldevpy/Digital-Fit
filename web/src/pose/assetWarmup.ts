// Aquecimento dos assets de pose (T-070).
//
// Por que existe: o MediaPipe baixa o WASM DENTRO de `createFromOptions`. Como
// `createEdgePoseLandmarker` faz duas tentativas (GPU, depois CPU), e o prazo da T-069 corta a
// primeira enquanto o download dela ainda está no ar, a segunda tentativa começava um SEGUNDO
// download do mesmo arquivo de 11,5 MB. Medido em produção: 33,25s e 40,07s para o mesmo
// `vision_wasm_internal.wasm` — os dois dividindo a banda, um deles jogado no lixo depois.
//
// A solução é tirar o download de dentro da tentativa: baixa-se uma vez, para o cache HTTP, e só
// então se tenta criar o landmarker. As tentativas passam a custar compilação, não rede — e o
// prazo volta a medir o que foi feito para medir.
//
// Efeito colateral bem-vindo: com o download nas nossas mãos, dá para dizer quanto falta. São
// 17 MB no primeiro acesso; a diferença entre "está baixando, 40%" e uma tela muda é a
// diferença entre esperar e achar que travou.

/** Quanto já veio dos assets. `total` é `null` quando o servidor não manda `Content-Length`. */
export interface AssetProgress {
  recebidos: number
  total: number | null
}

/**
 * Baixa `urls` em sequência, relatando progresso.
 *
 * **Sequência, não paralelo**: são dois arquivos grandes indo para o mesmo lugar, e baixá-los
 * juntos só faria um roubar banda do outro — exatamente o defeito que este módulo conserta.
 *
 * Falha não é fatal e não sobe: se o aquecimento não funcionar (rede instável, `Content-Length`
 * ausente, `fetch` bloqueado), o MediaPipe ainda baixa por conta própria como sempre fez. Este
 * módulo é otimização e informação, nunca um novo ponto de falha no caminho de treinar.
 */
export async function warmAssets(
  urls: readonly string[],
  aoProgredir: (progresso: AssetProgress) => void,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  const total = await totalBytes(urls, fetchImpl)
  let recebidos = 0
  aoProgredir({ recebidos, total })

  for (const url of urls) {
    try {
      // `force-cache`: se já está no aparelho, isto é instantâneo e não gasta rede — é o caso
      // da segunda visita, que não deve pagar nada por este módulo existir.
      const resposta = await fetchImpl(url, { cache: 'force-cache' })
      if (!resposta.ok || !resposta.body) continue

      // Ler o corpo até o fim é o que faz o navegador GUARDAR a resposta. Abandonar o stream
      // no meio deixaria o cache incompleto, e o MediaPipe baixaria tudo de novo — o bug de
      // novo, por outro caminho.
      const leitor = resposta.body.getReader()
      for (;;) {
        const { done, value } = await leitor.read()
        if (done) break
        recebidos += value.byteLength
        aoProgredir({ recebidos, total })
      }
    } catch {
      // Segue para o próximo: um asset que não aqueceu ainda pode ser baixado pelo MediaPipe.
    }
  }
}

/**
 * Soma o `Content-Length` dos assets, por HEAD. `null` se qualquer um não responder o tamanho:
 * porcentagem calculada sobre total parcial mostraria "137%", que é pior que não mostrar nada.
 *
 * Também devolve `null` quando a resposta vem comprimida: `Content-Length` é o tamanho NA REDE
 * e os bytes que contamos saem do stream já descomprimido. Comparar os dois daria "340%" no dia
 * em que o gzip do `.wasm` for ligado no nginx — 11,0 MB lidos contra 3,2 MB anunciados.
 */
async function totalBytes(urls: readonly string[], fetchImpl: typeof fetch): Promise<number | null> {
  let soma = 0
  for (const url of urls) {
    try {
      const resposta = await fetchImpl(url, { method: 'HEAD' })
      if (resposta.headers.get('content-encoding')) return null
      const tamanho = Number(resposta.headers.get('content-length'))
      if (!Number.isFinite(tamanho) || tamanho <= 0) return null
      soma += tamanho
    } catch {
      return null
    }
  }
  return soma
}

/**
 * Como o aquecimento aparece na tela. Puro: é texto de produto, e a régua de "nunca mostrar
 * número inventado" vale aqui também — sem total conhecido, mostra o que já veio, não um palpite.
 */
export function warmupLabel({ recebidos, total }: AssetProgress): string {
  const mb = (bytes: number) => (bytes / 1024 / 1024).toFixed(1).replace('.', ',')
  // `recebidos > total` significa que o total não descreve o que estamos lendo (resposta
  // comprimida que passou pelo HEAD, redirect, servidor mentindo). Mostrar só o que veio é
  // honesto; mostrar "100% · 11,0 de 3,2 MB" seria absurdo na cara de quem espera.
  if (total === null || total <= 0 || recebidos > total) return `${mb(recebidos)} MB`
  return `${Math.round((recebidos / total) * 100)}% · ${mb(recebidos)} de ${mb(total)} MB`
}
