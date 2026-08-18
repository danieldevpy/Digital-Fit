"""Negociação de locale (SPEC-025 §Notas técnicas, T-143).

A mesma pergunta se repete em toda rota que serve texto ou guarda payload pronto para cache:
"em que língua eu respondo, e como isso não vaza para o cache?". Este pacote responde só a
primeira metade — `resolve_locale`. A segunda metade (o locale entrando como dimensão do ETag
de `GET /api/config` e da chave de `GET /api/engagement`) mora em `api.config.config_etag` e
`api.engagement_cache`, exatamente onde as outras dimensões da mesma pergunta já moravam.

**Por que a negociação não é o `django.utils.translation` de série.** O mecanismo do Django
resolve local de sessão/cookie/cabeçalho para renderizar template, e este produto não tem
template: o corpo é JSON montado à mão (`config_payload`, `Engajamento.to_dict`), e o catálogo
de texto (T-144/T-146) segue o mesmo padrão do `FeedbackCatalog` — YAML carregado em código, não
`.po`/`.mo`. `resolve_locale` só decide QUAL chave desse catálogo vale para esta requisição.
"""

from __future__ import annotations

from typing import Any

__all__ = ["DEFAULT_LOCALE", "LOCALES", "SOURCE_LOCALE", "resolve_locale"]

#: Locales que o produto fala. `pt-BR` primeiro por ser a língua de origem do conteúdo — ver
#: `SOURCE_LOCALE`. Tupla e não `set`: a ordem é estável e há lugares que a usam como preferência
#: (ex.: escolher o primeiro suportado entre vários pesos empatados no cabeçalho).
LOCALES: tuple[str, ...] = ("pt-BR", "en")

#: O locale em que o conteúdo nasce no código — nome de conquista, mensagem de feedback, texto de
#: guia. Todo catálogo de tradução (T-144/T-146) parte daqui como origem, nunca como fallback de
#: requisição: ver `DEFAULT_LOCALE` para esse segundo papel.
SOURCE_LOCALE = "pt-BR"

#: Locale de quem não mandou preferência nenhuma reconhecível — nem `?locale=`, nem
#: `Accept-Language` com um idioma que o produto fale. **Inglês, não `SOURCE_LOCALE`**: um
#: visitante sem cabeçalho reconhecível tem mais chance de estar fora do Brasil do que dentro —
#: quem tem o app em português manda o cabeçalho pt-BR do próprio aparelho. Tratar "não sei" como
#: "português" enviesaria a leitura errada para o lado mais populoso hoje, não para o lado neutro.
DEFAULT_LOCALE = "en"

#: Primeiro subtag de idioma (ISO 639-1, as duas letras antes do primeiro `-`/`_`) mapeado para o
#: locale canônico do produto. Fora daqui é "desconhecido" (critério 1 da spec) — cai em
#: `DEFAULT_LOCALE`, nunca em erro: locale é preferência de exibição, não parâmetro que possa
#: recusar uma requisição.
_FAMILIA_PARA_LOCALE: dict[str, str] = {
    "pt": "pt-BR",
    "en": "en",
}


def _normalizar_tag(tag: str) -> str | None:
    """Um único language-range (sem vírgula) para o locale canônico, ou `None` se desconhecido.

    Cobre os formatos que aparecem na prática — `pt`, `pt-BR`, `pt-br`, `pt_BR`, e qualquer um
    deles com `;q=0.9` pendurado (o parâmetro de peso do `Accept-Language`, RFC 9110 §12.5.4) —
    com uma regra só: normaliza separador e caixa, e compara pela família de duas letras. Uma
    lista de sinônimos linha a linha divergiria no dia em que alguém lembrasse de `PT_br` e
    esquecesse `Pt-BR`.
    """
    primeiro = tag.split(";", 1)[0].strip()
    if not primeiro or primeiro == "*":
        return None
    familia = primeiro.replace("_", "-").split("-", 1)[0].lower()
    return _FAMILIA_PARA_LOCALE.get(familia)


def _melhor_locale_do_cabecalho(accept_language: str) -> str:
    """O locale suportado de maior peso em `Accept-Language`, ou `DEFAULT_LOCALE` se nenhum bater.

    Pesa por `q` e não pega o primeiro item da lista: um cabeçalho real é algo como
    `en-US,en;q=0.9,pt-BR;q=0.8`, e o primeiro nem sempre é o que o produto suporta. Em empate de
    peso, quem apareceu antes no cabeçalho vence — é a ordem de preferência real de quem mandou.
    """
    candidatos: list[tuple[float, int, str]] = []
    for indice, parte in enumerate(accept_language.split(",")):
        parte = parte.strip()
        if not parte:
            continue
        peso = 1.0
        if ";q=" in parte:
            _, _, valor_q = parte.partition(";q=")
            try:
                peso = float(valor_q.strip())
            except ValueError:
                peso = 0.0
        locale = _normalizar_tag(parte)
        if locale is not None:
            candidatos.append((peso, -indice, locale))

    if not candidatos:
        return DEFAULT_LOCALE
    candidatos.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidatos[0][2]


def resolve_locale(request: Any) -> str:
    """O locale desta requisição (SPEC-025 critério 1): `?locale=` > `Accept-Language` > default.

    Prioridade explícita: `?locale=` é um pedido direto, e não faz sentido perder para um
    cabeçalho automático que o navegador manda sozinho. Presente, ele decide — normalizado como
    qualquer outro valor, e um valor que não normaliza para nada cai no `DEFAULT_LOCALE` (não
    "ignora o override e olha o cabeçalho", que seria uma segunda regra de prioridade escondida
    dentro da primeira). Sem override, quem decide é o cabeçalho; sem cabeçalho reconhecível,
    `DEFAULT_LOCALE`.

    Aceita tanto `rest_framework.request.Request` (o tipo usado nas views, com `.query_params`)
    quanto `django.http.HttpRequest` (com `.GET`) — as views deste projeto usam DRF, mas a função
    não depende disso: é resolvida por duck typing para poder ser testada sem Django de pé.
    """
    params = getattr(request, "query_params", None)
    if params is None:
        params = getattr(request, "GET", {})
    override = (params.get("locale") or "").strip()
    if override:
        return _normalizar_tag(override) or DEFAULT_LOCALE

    headers = getattr(request, "headers", None) or {}
    cabecalho = headers.get("Accept-Language", "") or ""
    return _melhor_locale_do_cabecalho(cabecalho)
