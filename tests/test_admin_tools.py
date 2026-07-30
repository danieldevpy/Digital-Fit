"""Ferramentas de diagnóstico liberadas por conta (T-048).

A flag `is_admin` decide se o CLIENTE mostra a superfície de dev — chip de diagnóstico,
gravador de fixtures e, quando existir, a fonte de vídeo da T-040. Ela não abre dado de
ninguém: o que estes testes protegem é a única porta de entrada dela, o comando de manage.
Se um dia alguém aceitar `is_admin` no corpo de uma rota, os dois primeiros testes caem.
"""

from __future__ import annotations

from io import StringIO

import pytest
from api.models import User
from django.core.management import CommandError, call_command

from tests.test_auth import SENHA, autorizacao

EMAIL = "ana@exemplo.com"


@pytest.fixture
def usuario(db) -> User:
    return User.objects.create_user(email=EMAIL, password=SENHA, name="Ana")


def executar(*args: str) -> str:
    saida = StringIO()
    call_command("admin_tools", *args, stdout=saida)
    return saida.getvalue()


@pytest.mark.django_db
def test_conta_nova_nasce_sem_as_ferramentas(usuario) -> None:
    assert usuario.is_admin is False


@pytest.mark.django_db
def test_cadastro_nao_permite_a_pessoa_se_promover(client) -> None:
    """O caminho óbvio de ataque: mandar o campo junto e esperar que o servidor o aceite."""
    resposta = client.post(
        "/api/auth/register",
        data={"email": "esperta@exemplo.com", "password": SENHA, "is_admin": True},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    assert resposta.json()["user"]["is_admin"] is False
    assert User.objects.get(email="esperta@exemplo.com").is_admin is False


@pytest.mark.django_db
def test_me_carrega_a_flag_porque_e_o_cliente_que_a_consome(client, usuario) -> None:
    assert client.get("/api/me", **autorizacao(client)).json()["is_admin"] is False

    executar(EMAIL, "--on")

    assert client.get("/api/me", **autorizacao(client)).json()["is_admin"] is True


@pytest.mark.django_db
def test_comando_liga_e_desliga(usuario) -> None:
    executar(EMAIL, "--on")
    usuario.refresh_from_db()
    assert usuario.is_admin is True

    executar(EMAIL, "--off")
    usuario.refresh_from_db()
    assert usuario.is_admin is False


@pytest.mark.django_db
def test_sem_flag_o_comando_so_informa(usuario) -> None:
    usuario.is_admin = True
    usuario.save(update_fields=["is_admin"])

    saida = executar(EMAIL)

    assert "ligadas" in saida
    usuario.refresh_from_db()
    assert usuario.is_admin is True


@pytest.mark.django_db
def test_email_com_maiuscula_acha_a_conta(usuario) -> None:
    executar("Ana@Exemplo.com", "--on")

    usuario.refresh_from_db()
    assert usuario.is_admin is True


@pytest.mark.django_db
def test_conta_inexistente_falha_alto(db) -> None:
    with pytest.raises(CommandError, match="nao existe conta"):
        executar("ninguem@exemplo.com", "--on")


@pytest.mark.django_db
def test_listagem_mostra_quem_tem_acesso(usuario) -> None:
    assert "nenhuma conta" in executar("--list")

    executar(EMAIL, "--on")

    assert EMAIL in executar("--list")


@pytest.mark.django_db
def test_createsuperuser_cria_conta_com_as_ferramentas(db) -> None:
    """`createsuperuser` é o primeiro comando que qualquer um tenta — tem de funcionar.

    Até a T-048 ele estourava `AttributeError` porque o `UserManager` não tinha
    `create_superuser`. O conceito de admin não existia; agora existe.
    """
    call_command(
        "createsuperuser",
        interactive=False,
        email="chefe@exemplo.com",
        stdout=StringIO(),
    )

    usuario = User.objects.get(email="chefe@exemplo.com")
    assert usuario.is_admin is True
    # É a porta de bootstrap do painel (T-072): a primeira conta de operador não tem painel
    # onde ser criada.
    assert usuario.is_staff is True


@pytest.mark.django_db
def test_superuser_daqui_nao_e_superusuario_do_django(db) -> None:
    """Ele opera o painel; não ganha a árvore de permissões do Django."""
    usuario = User.objects.create_superuser(email="chefe@exemplo.com", password=SENHA)

    assert usuario.is_admin is True
    assert usuario.is_staff is True
    # Sem `PermissionsMixin` no modelo: não há `is_superuser`, grupo nem permissão por modelo.
    # `has_perm` responde pela conta inteira (`api/models.py`), e é o que o painel consulta.
    assert not hasattr(usuario, "is_superuser")
    assert not hasattr(usuario, "groups")
    assert usuario.has_perm("api.change_user") is True


@pytest.mark.django_db
def test_comando_liga_e_desliga_o_painel(usuario) -> None:
    executar(EMAIL, "--panel-on")
    usuario.refresh_from_db()
    assert usuario.is_staff is True
    # Os dois acessos são independentes: painel não acende as ferramentas do cliente.
    assert usuario.is_admin is False

    executar(EMAIL, "--panel-off")
    usuario.refresh_from_db()
    assert usuario.is_staff is False


@pytest.mark.django_db
def test_comando_concede_os_dois_de_uma_vez(usuario) -> None:
    """Promover alguém é uma operação só; rodar o comando duas vezes seria cerimônia."""
    executar(EMAIL, "--on", "--panel-on")

    usuario.refresh_from_db()
    assert (usuario.is_admin, usuario.is_staff) == (True, True)


@pytest.mark.django_db
def test_estado_mostra_os_dois_acessos(usuario) -> None:
    saida = executar(EMAIL)

    assert "ferramentas desligadas" in saida
    assert "painel bloqueado" in saida
