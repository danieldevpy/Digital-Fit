"""CORS da API (`core/cors.py`).

O cliente web só consegue abrir sessão se o navegador deixar — e o navegador só deixa com
estes cabeçalhos. Sem eles a T-014 morre no primeiro clique, sem erro no servidor.
"""

import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db


@pytest.fixture
def debug_ligado():
    """O Django força `DEBUG=False` em teste; o caminho "dev libera tudo" precisa dizer isso.

    Sem esta fixture, os testes de dev estariam medindo a configuração de produção.
    """
    with override_settings(DEBUG=True):
        yield


ORIGEM = "http://localhost:5173"


def test_preflight_responde_sem_chegar_na_view(debug_ligado) -> None:
    resposta = Client().options(
        "/api/sessions",
        HTTP_ORIGIN=ORIGEM,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
    )

    assert resposta.status_code == 204
    assert resposta["Access-Control-Allow-Origin"] == ORIGEM
    assert "POST" in resposta["Access-Control-Allow-Methods"]
    assert "Content-Type" in resposta["Access-Control-Allow-Headers"]


def test_resposta_normal_tambem_leva_o_cabecalho(debug_ligado) -> None:
    resposta = Client().get("/healthz", HTTP_ORIGIN=ORIGEM)

    assert resposta["Access-Control-Allow-Origin"] == ORIGEM
    assert "Origin" in resposta["Vary"]


def test_requisicao_sem_origem_nao_ganha_cabecalho(debug_ligado) -> None:
    """Chamada de servidor (curl, healthcheck) não é caso de CORS."""
    resposta = Client().get("/healthz")

    assert not resposta.has_header("Access-Control-Allow-Origin")


@override_settings(DEBUG=False, CORS_ALLOWED_ORIGINS=["https://app.digitalfit.example"])
def test_fora_de_debug_so_a_lista_passa() -> None:
    cliente = Client()

    permitida = cliente.get("/healthz", HTTP_ORIGIN="https://app.digitalfit.example")
    recusada = cliente.get("/healthz", HTTP_ORIGIN=ORIGEM)

    assert permitida["Access-Control-Allow-Origin"] == "https://app.digitalfit.example"
    assert not recusada.has_header("Access-Control-Allow-Origin")


@override_settings(DEBUG=False, CORS_ALLOWED_ORIGINS=[])
def test_producao_sem_lista_nao_libera_nada() -> None:
    resposta = Client().get("/healthz", HTTP_ORIGIN=ORIGEM)

    assert not resposta.has_header("Access-Control-Allow-Origin")


def test_em_debug_o_ip_da_lan_passa(debug_ligado) -> None:
    """O celular do teste entra pelo IP da rede — origem que ninguém lista de antemão."""
    resposta = Client().get("/healthz", HTTP_ORIGIN="http://192.168.0.104:5173")

    assert resposta["Access-Control-Allow-Origin"] == "http://192.168.0.104:5173"


def test_o_etag_e_legivel_pelo_javascript(debug_ligado) -> None:
    """Sem `Expose-Headers`, o navegador entrega a resposta e ESCONDE o `ETag` (T-074).

    É o teste do defeito que só o navegador mostrou: `curl` imprime o header (ignora CORS) e um
    teste com `fetch` dublado também, mas em `fetch` de verdade
    `resposta.headers.get('ETag')` volta `null` cross-origin. O sintoma não é erro nenhum — é o
    `GET /api/config` baixando o payload inteiro para sempre, em vez de custar 304.
    """
    resposta = Client().get("/healthz", HTTP_ORIGIN=ORIGEM)

    assert "ETag" in resposta["Access-Control-Expose-Headers"]


def test_o_preflight_aceita_o_cabecalho_de_revalidacao(debug_ligado) -> None:
    """`If-None-Match` não é cabeçalho simples: sem ele na lista, a revalidação nem sai."""
    resposta = Client().options(
        "/api/config",
        HTTP_ORIGIN=ORIGEM,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="If-None-Match",
    )

    assert "If-None-Match" in resposta["Access-Control-Allow-Headers"]


def test_o_preflight_aceita_o_cabecalho_de_idioma(debug_ligado) -> None:
    """`Accept-Language` (SPEC-025, T-143): um seletor de idioma que o cliente define à mão
    deixa de ser cabeçalho simples, e sem ele na lista o preflight recusaria a requisição antes
    dela sair."""
    resposta = Client().options(
        "/api/config",
        HTTP_ORIGIN=ORIGEM,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="Accept-Language",
    )

    assert "Accept-Language" in resposta["Access-Control-Allow-Headers"]
