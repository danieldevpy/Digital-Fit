"""Negociação de locale (SPEC-025 §Notas técnicas, T-143).

Função pura, testável sem banco e sem Django de pé de verdade: um objeto qualquer com
`.query_params`/`.GET` e `.headers` já basta, porque é isso que `resolve_locale` promete aceitar
por duck typing (tanto o `rest_framework.request.Request` das views quanto um
`django.http.HttpRequest` cru).
"""

from __future__ import annotations

import pytest
from api.i18n import DEFAULT_LOCALE, LOCALES, SOURCE_LOCALE, resolve_locale


class RequestFalso:
    """O suficiente de uma requisição para `resolve_locale`: parâmetros de query e cabeçalhos."""

    def __init__(
        self, *, query: dict[str, str] | None = None, headers: dict[str, str] | None = None
    ):
        self.query_params = query or {}
        self.headers = headers or {}


class RequestDjangoCru:
    """Sem `.query_params` (só o `HttpRequest` puro tem `.GET`) — prova o fallback duck-typed."""

    def __init__(self, *, GET: dict[str, str] | None = None, headers: dict[str, str] | None = None):
        self.GET = GET or {}
        self.headers = headers or {}


# ==========================================================================================
# As constantes exportadas — o contrato que T-144/T-146 importam
# ==========================================================================================


def test_locales_e_pt_br_e_en() -> None:
    assert LOCALES == ("pt-BR", "en")


def test_source_locale_e_pt_br() -> None:
    """A língua de origem do conteúdo hardcoded (nome de conquista, mensagem de feedback)."""
    assert SOURCE_LOCALE == "pt-BR"


def test_default_locale_e_en() -> None:
    """Quem não manda sinal nenhum cai em inglês, não em português — critério 1 da spec."""
    assert DEFAULT_LOCALE == "en"


# ==========================================================================================
# Prioridade: ?locale= > Accept-Language > default
# ==========================================================================================


def test_sem_override_e_sem_cabecalho_cai_no_default() -> None:
    assert resolve_locale(RequestFalso()) == DEFAULT_LOCALE


def test_override_vence_o_cabecalho() -> None:
    pedido = RequestFalso(query={"locale": "pt"}, headers={"Accept-Language": "en"})

    assert resolve_locale(pedido) == "pt-BR"


def test_override_desconhecido_nao_cai_de_volta_no_cabecalho() -> None:
    """O override é explícito: um valor que não normaliza cai no default, e não faz o pedido
    voltar a espiar o Accept-Language — seria uma segunda regra de prioridade escondida."""
    pedido = RequestFalso(query={"locale": "xx"}, headers={"Accept-Language": "pt-BR"})

    assert resolve_locale(pedido) == DEFAULT_LOCALE


def test_override_vazio_e_tratado_como_ausente() -> None:
    pedido = RequestFalso(query={"locale": ""}, headers={"Accept-Language": "pt-BR"})

    assert resolve_locale(pedido) == "pt-BR"


def test_funciona_com_request_django_cru_sem_query_params() -> None:
    """O fallback para `.GET` — o `HttpRequest` puro, fora do `@api_view` do DRF."""
    pedido = RequestDjangoCru(GET={"locale": "en"})

    assert resolve_locale(pedido) == "en"


# ==========================================================================================
# Normalização — os quatro casos que a spec nomeia, mais o realista
# ==========================================================================================


@pytest.mark.parametrize(
    "valor",
    ["pt", "pt-br", "pt-BR", "pt_BR", "pt_br", "PT-BR", "pt-BR;q=0.9", " pt-BR ", "pt;q=1.0"],
)
def test_normaliza_variantes_de_portugues_para_pt_br(valor: str) -> None:
    pedido = RequestFalso(headers={"Accept-Language": valor})

    assert resolve_locale(pedido) == "pt-BR"


@pytest.mark.parametrize("valor", ["en", "en-US", "en-GB", "EN", "en;q=0.8"])
def test_normaliza_variantes_de_ingles_para_en(valor: str) -> None:
    pedido = RequestFalso(headers={"Accept-Language": valor})

    assert resolve_locale(pedido) == "en"


@pytest.mark.parametrize("valor", ["es", "es-ES", "fr", "de-DE", "*", "", "  ", "zz-top;q=0.9"])
def test_idioma_desconhecido_cai_no_default(valor: str) -> None:
    pedido = RequestFalso(headers={"Accept-Language": valor})

    assert resolve_locale(pedido) == DEFAULT_LOCALE


def test_cabecalho_ausente_cai_no_default() -> None:
    assert resolve_locale(RequestFalso(headers={})) == DEFAULT_LOCALE


# ==========================================================================================
# Cabeçalho real: múltiplos idiomas com peso (RFC 9110 §12.5.4)
# ==========================================================================================


def test_escolhe_o_maior_peso_e_nao_o_primeiro_da_lista() -> None:
    pedido = RequestFalso(headers={"Accept-Language": "en-US;q=0.5,pt-BR;q=0.9"})

    assert resolve_locale(pedido) == "pt-BR"


def test_empate_de_peso_favorece_quem_apareceu_primeiro() -> None:
    """Sem `;q=`, o peso implícito é 1.0 — os dois primeiros itens empatam, e a ordem do
    cabeçalho é a preferência real de quem mandou."""
    pedido = RequestFalso(headers={"Accept-Language": "en, pt-BR"})

    assert resolve_locale(pedido) == "en"


def test_ignora_idioma_nao_suportado_no_meio_da_lista() -> None:
    pedido = RequestFalso(headers={"Accept-Language": "fr-FR;q=0.9, pt-BR;q=0.5"})

    assert resolve_locale(pedido) == "pt-BR"


def test_peso_malformado_nao_derruba_a_resolucao() -> None:
    """`;q=abacate` não é motivo para a rota inteira quebrar — locale é preferência de exibição,
    nunca parâmetro que recusa uma requisição."""
    pedido = RequestFalso(headers={"Accept-Language": "pt-BR;q=abacate, en;q=0.9"})

    assert resolve_locale(pedido) == "en"
