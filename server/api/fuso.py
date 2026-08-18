"""O fuso de quem treina (T-156, SPEC-019 §Fuso / SPEC-025 §Fora de escopo).

A SPEC-025 tirou o fuso do próprio escopo com uma frase que também é o motivo desta task:
*"não é idioma: é o mesmo 'não se restringir a um país' por outro eixo"*. O fogo, a meta diária
e o TTL do cache viravam o dia às 00h de **São Paulo**, para todo mundo — quem treina às 22h em
Lisboa caía no dia seguinte, e o streak quebrava sozinho sem nada na tela explicando. O modo de
falha é o pior que existe numa mecânica de retenção: silencioso, e do lado de quem estava certo.

**Por que cabeçalho e não coluna no perfil.** O fuso é do APARELHO, não da conta: a mesma pessoa
treina no celular em viagem e no notebook em casa, e o que ela chama de "hoje" é o do relógio
que está olhando. Guardar no perfil obrigaria a manter uma preferência sincronizada com algo que
o navegador já sabe responder sozinho (`Intl.DateTimeFormat().resolvedOptions().timeZone`) — e
obrigaria a ter conta, quando treinar sem conta é garantia da SPEC-011. O cabeçalho é a mesma
doutrina do `Accept-Language` (SPEC-025 §3.4): o cliente resolve, o servidor obedece.

**Rejeitado: deduzir o fuso do IP.** Mesmo argumento que tirou GeoIP da decisão de idioma —
acerta o país e erra a pessoa, e erra de novo com VPN. O navegador entrega o fuso que a pessoa
configurou; não há por que adivinhar o que já foi respondido.

**O default continua sendo São Paulo, e isso é conservador de propósito.** Cliente antigo,
`evalctl`, teste e qualquer chamada sem o cabeçalho continuam vendo exatamente o dia de antes
desta task. Trocar o default para UTC teria movido a virada de todo mundo que já usa o produto
— uma correção que quebraria streaks reais para consertar um caso que ainda não existe.
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = ["CABECALHO_DE_FUSO", "FUSO_PADRAO", "normalizar_fuso", "resolve_fuso"]

#: O fuso de quem não disse qual é o seu. Ver o docstring do módulo: é o de antes da T-156.
FUSO_PADRAO = ZoneInfo("America/Sao_Paulo")

#: Não existe cabeçalho padrão para fuso (o `Accept-Language` do tempo nunca foi criado), então
#: é um `X-` nosso. Precisa entrar em `core/cors.py` — como `X-Device-Id` e `If-None-Match`
#: precisaram — senão o navegador não deixa a requisição sair e o sintoma aparece como
#: "engajamento não carrega", nunca como CORS.
CABECALHO_DE_FUSO = "X-Timezone"


def normalizar_fuso(nome: str | None) -> ZoneInfo:
    """Nome IANA (`America/Sao_Paulo`, `Europe/Lisbon`) → `ZoneInfo`, com o padrão como rede.

    Valor desconhecido cai no padrão em silêncio, e não levanta: o fuso chega de um cabeçalho
    que qualquer cliente pode mandar errado, e derrubar o `GET /api/engagement` por causa disso
    trocaria um dia deslocado por uma tela vazia. A base de fusos do sistema também pode ser
    mais velha que o navegador de quem chama (`ZoneInfoNotFoundError`) — o mesmo tratamento.
    """
    if not nome:
        return FUSO_PADRAO
    limpo = nome.strip()
    # Um `X-` de cliente é entrada não confiável: o `ZoneInfo` resolve caminho de arquivo, e
    # nome com `..` ou `/` inicial é a forma clássica de pedir para ler o que não devia.
    if not limpo or limpo.startswith("/") or ".." in limpo:
        return FUSO_PADRAO
    try:
        return ZoneInfo(limpo)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return FUSO_PADRAO


def resolve_fuso(request: Any) -> ZoneInfo:
    """O fuso desta requisição: `?tz=` > `X-Timezone` > `FUSO_PADRAO`.

    Mesma cadeia e mesma ordem do `api.i18n.resolve_locale`, e pelo mesmo motivo: um override
    explícito na URL é um pedido direto e não pode perder para o cabeçalho automático. Serve ao
    diagnóstico ("me mostra como fica em Lisboa") sem exigir trocar o relógio do aparelho.

    Duck typing em `query_params`/`GET` para aceitar tanto `Request` do DRF quanto
    `HttpRequest` — igual ao `resolve_locale`, e pelo mesmo motivo: testável sem Django de pé.
    """
    params = getattr(request, "query_params", None)
    if params is None:
        params = getattr(request, "GET", {})
    override = (params.get("tz") or "").strip()
    if override:
        return normalizar_fuso(override)

    headers = getattr(request, "headers", None) or {}
    return normalizar_fuso(headers.get(CABECALHO_DE_FUSO))
