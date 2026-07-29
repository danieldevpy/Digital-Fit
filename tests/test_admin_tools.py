"""Ferramentas de diagnóstico liberadas por conta (T-048).

A flag `is_admin` decide se o CLIENTE mostra a superfície de dev — chip de diagnóstico,
gravador de fixtures e, quando existir, a fonte de vídeo da T-040. Ela não abre dado de
ninguém: o que estes testes protegem é a única porta de entrada dela, o comando de manage.
Se um dia alguém aceitar `is_admin` no corpo de uma rota, os dois primeiros testes caem.
"""

from __future__ import annotations

import pytest
from api.models import User
from django.core.management import CommandError, call_command

from tests.test_auth import SENHA, autorizacao

EMAIL = "ana@exemplo.com"


@pytest.fixture
def usuario(db) -> User:
    return User.objects.create_user(email=EMAIL, password=SENHA, name="Ana")


def executar(*args: str) -> str:
    from io import StringIO

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
