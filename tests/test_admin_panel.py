"""Painel de operação (T-072 / SPEC-018).

O que estes testes protegem é a fronteira do painel, não o CRUD que o Django dá pronto:

- quem entra (`is_staff`) e quem **não** entra — inclusive quem tem a outra flag privilegiada;
- que o painel não existe com a variável desligada, nem no processo do gateway;
- que dado derivado de evento (`SessionResult`) não se edita por formulário.

O contrário disso já custou caro no projeto: a T-048 descobriu a superfície de dev exposta em
produção porque "comentário não é gate". Painel é a mesma classe de problema, com mais dado
atrás.
"""

from __future__ import annotations

import pytest
from api.models import SessionResult, User
from core.admin_gate import belongs_to_admin, block_admin
from core.urls import build_urlpatterns
from django.conf import settings

from tests.test_auth import SENHA

PAINEL = "/" + settings.ADMIN_PATH


@pytest.fixture
def comum(db) -> User:
    return User.objects.create_user(email="ana@exemplo.com", password=SENHA, name="Ana")


@pytest.fixture
def operador(db) -> User:
    return User.objects.create_user(
        email="chefe@exemplo.com", password=SENHA, name="Chefe", is_staff=True
    )


# --- a rota existe? ---------------------------------------------------------------------


def test_variavel_desligada_nao_monta_a_rota() -> None:
    """A garantia que importa em produção, e a única que não dá para exercer por requisição.

    Rota já importada não se desmonta — por isso os testes de acesso montam a URLconf do
    painel por `@pytest.mark.urls`, e a decisão de montá-la ou não é verificada aqui, na
    função que `core/urls.py` usa de verdade.
    """
    desligado = build_urlpatterns(admin_enabled=False, admin_path="painel/")
    ligado = build_urlpatterns(admin_enabled=True, admin_path="painel/")

    assert len(desligado) == 1
    assert len(ligado) == len(desligado) + 1


@pytest.mark.parametrize(
    ("caminho", "esperado"),
    [
        ("/painel", True),
        ("/painel/", True),
        ("/painel/api/user/", True),
        ("/api/sessions", False),
        ("/painelzinho/", False),
        # O caso que um `in` ingênuo bloquearia: a palavra existe, o prefixo não.
        ("/api/sessions/painel/", False),
    ],
)
def test_reconhece_o_que_e_do_painel(caminho: str, esperado: bool) -> None:
    assert belongs_to_admin(caminho, "painel/") is esperado


@pytest.mark.asyncio
async def test_gateway_nao_serve_o_painel_nem_com_a_variavel_ligada() -> None:
    """Critério 5 da SPEC-018.

    A separação por variável de ambiente cairia no dia em que alguém movesse
    `DJANGO_ENABLE_ADMIN` para o bloco compartilhado do compose. Esta trava é do processo.
    """
    chamou_o_app = False

    async def app_de_baixo(scope, receive, send) -> None:
        nonlocal chamou_o_app
        chamou_o_app = True

    respostas: list[dict] = []

    async def send(mensagem: dict) -> None:
        respostas.append(mensagem)

    async def receive() -> dict:
        return {"type": "http.request"}

    protegido = block_admin(app_de_baixo, "painel/")
    await protegido({"type": "http", "path": "/painel/"}, receive, send)

    assert respostas[0]["status"] == 404
    assert chamou_o_app is False

    # O que NÃO é do painel continua passando — inclusive o WebSocket, que é o que este
    # processo existe para servir.
    await protegido({"type": "http", "path": "/api/sessions"}, receive, send)
    assert chamou_o_app is True


# --- quem entra -------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_anonimo_nao_entra(client) -> None:
    resposta = client.get(PAINEL)

    assert resposta.status_code == 302
    assert "login" in resposta["Location"]


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_conta_comum_nao_entra(client, comum) -> None:
    client.force_login(comum)

    assert client.get(PAINEL).status_code == 302


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_ferramentas_de_diagnostico_nao_abrem_o_painel(client, comum) -> None:
    """O motivo de `is_staff` ser campo novo, e não um apelido de `is_admin` (SPEC-018).

    As contas com `is_admin` foram concedidas sob a promessa escrita de que a flag "não dá
    acesso a dado de ninguém". Se este teste passar a falhar, alguém uniu as duas — e promoveu
    em silêncio todo mundo que já tinha a primeira.
    """
    comum.is_admin = True
    comum.save(update_fields=["is_admin"])
    client.force_login(comum)

    assert client.get(PAINEL).status_code == 302


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_operador_entra(client, operador) -> None:
    resposta = client.get(PAINEL)  # sem login ainda
    assert resposta.status_code == 302

    client.force_login(operador)
    resposta = client.get(PAINEL)

    assert resposta.status_code == 200
    assert b"Digital Fit" in resposta.content


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_conta_desativada_perde_o_painel(client, operador) -> None:
    """`is_active` é o botão de emergência — tem de valer para o painel também."""
    client.force_login(operador)
    assert client.get(PAINEL).status_code == 200

    operador.is_active = False
    operador.save(update_fields=["is_active"])

    assert client.get(PAINEL).status_code == 302


# --- o que o painel deixa fazer -----------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_relatorio_de_sessao_nao_se_edita(client, operador) -> None:
    """Editar à mão criaria uma linha que nenhum replay reproduz (SPEC-010)."""
    SessionResult.objects.create(
        session_id="s-1", exercise="jumping_jack", mode="edge", reason="timeout", rep_count=12
    )
    client.force_login(operador)

    assert client.get(f"{PAINEL}api/sessionresult/").status_code == 200
    assert client.get(f"{PAINEL}api/sessionresult/add/").status_code == 403


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_painel_nao_promove_operador(client, operador, comum) -> None:
    """Conceder painel exige shell (`admin_tools --panel-on`), e o formulário não é atalho."""
    client.force_login(operador)

    resposta = client.post(
        f"{PAINEL}api/user/{comum.pk}/change/",
        data={
            "email": comum.email,
            "name": comum.name,
            "is_active": "on",
            "is_admin": "on",
            "is_staff": "on",
        },
    )

    assert resposta.status_code == 302  # salvou
    comum.refresh_from_db()
    assert comum.is_admin is True  # este o painel concede
    assert comum.is_staff is False  # este não


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_criar_conta_pelo_painel(client, operador) -> None:
    """Pela requisição, e não pelo formulário: o `ContaCreateForm` sozinho passava enquanto a
    tela respondia 500 — os `add_fieldsets` pedem um campo (`usable_password`) que só existe na
    forma do admin, e nada disso aparece instanciando a classe à mão.

    De quebra, a normalização do e-mail: sem ela `Ana@X.com` criada aqui conviveria com a
    `ana@x.com` do cadastro — duas linhas para a mesma pessoa, e a segunda sem conseguir entrar.
    """
    client.force_login(operador)

    assert client.get(f"{PAINEL}api/user/add/").status_code == 200

    resposta = client.post(
        f"{PAINEL}api/user/add/",
        data={
            "email": "Ana@Exemplo.COM",
            "name": "Ana",
            "usable_password": "true",
            "password1": SENHA,
            "password2": SENHA,
        },
    )

    assert resposta.status_code == 302, resposta.context["adminform"].form.errors
    assert User.objects.filter(email="ana@exemplo.com").exists()


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_troca_de_senha_pelo_painel(client, operador, comum) -> None:
    """O pedido de suporte mais comum, e a única razão de herdar do `UserAdmin` do Django."""
    client.force_login(operador)

    assert client.get(f"{PAINEL}api/user/{comum.pk}/password/").status_code == 200


@pytest.mark.django_db
def test_cadastro_pela_api_nao_concede_o_painel(client) -> None:
    """O caminho óbvio de ataque, agora para a flag que abre dado dos outros."""
    resposta = client.post(
        "/api/auth/register",
        data={"email": "esperta@exemplo.com", "password": SENHA, "is_staff": True},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    assert User.objects.get(email="esperta@exemplo.com").is_staff is False


@pytest.mark.django_db
def test_me_nao_conta_ao_cliente_quem_e_operador(client, operador) -> None:
    """`GET /api/me` é payload de produto; o cliente não tem tela que dependa do painel."""
    assert "is_staff" not in operador.to_dict()
