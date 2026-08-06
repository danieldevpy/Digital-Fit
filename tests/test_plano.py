"""Atribuição de plano por linha de comando (SPEC-016 / SPEC-018 §E).

Enquanto não há checkout (T-036), este comando é a única porta pela qual alguém vira
assinante — e nenhuma rota da API aceita `plan` no corpo, pelo mesmo motivo que nenhuma
aceita `is_admin`. O primeiro teste é o que protege isso.

Estes testes existem porque a versão anterior desta função era um `.sh` com Python dentro de
um heredoc, e o **caminho de erro dela estava quebrado**: o heredoc não era citado, então
`f"...{$EMAIL}..."` virava `f"...{ana@exemplo.com}..."`, que o Python interpreta como
`ana @ exemplo.com` — o operador de multiplicação de matriz — e avalia como `NameError`. Quem
digitasse o e-mail errado recebia um traceback em vez de "conta não encontrada". Por isso o
teste do e-mail inexistente está aqui, e por isso ele verifica a exceção do comando e não a
saída.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from api.models import Plan, User
from django.core.management import CommandError, call_command

from tests.test_auth import SENHA, autorizacao

EMAIL = "ana@exemplo.com"


@pytest.fixture
def usuario(db) -> User:
    return User.objects.create_user(email=EMAIL, password=SENHA, name="Ana")


def executar(*args: str) -> str:
    saida = StringIO()
    call_command("plano", *args, stdout=saida)
    return saida.getvalue()


@pytest.mark.django_db
def test_cadastro_nao_permite_a_pessoa_se_dar_um_plano(client) -> None:
    """O caminho óbvio de ataque: mandar o campo junto e esperar que o servidor o aceite."""
    assinante = Plan.objects.get(slug="subscriber")

    resposta = client.post(
        "/api/auth/register",
        {"email": "nova@exemplo.com", "password": SENHA, "plan": assinante.id},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    assert User.objects.get(email="nova@exemplo.com").plan is None


@pytest.mark.django_db
def test_conta_nova_nasce_sem_plano_atribuido(usuario) -> None:
    """Nulo é o caso normal e significa "o default" — ver o comentário no modelo."""
    assert usuario.plan is None
    assert "default" in executar(EMAIL)


@pytest.mark.django_db
def test_atribui_o_plano_com_prazo_de_um_ano(usuario) -> None:
    saida = executar(EMAIL, "--set", "subscriber")

    usuario.refresh_from_db()
    assert usuario.plan is not None
    assert usuario.plan.slug == "subscriber"
    assert usuario.plan_until is not None
    # 365 dias, com folga para o teste não depender do segundo em que roda.
    assert timedelta(days=364) < usuario.plan_until - datetime.now(UTC) <= timedelta(days=365)
    assert "subscriber" in saida


@pytest.mark.django_db
def test_prazo_configuravel(usuario) -> None:
    executar(EMAIL, "--set", "subscriber", "--dias", "30")

    usuario.refresh_from_db()
    assert usuario.plan_until is not None
    assert timedelta(days=29) < usuario.plan_until - datetime.now(UTC) <= timedelta(days=30)


@pytest.mark.django_db
def test_sem_prazo_deixa_plan_until_nulo(usuario) -> None:
    executar(EMAIL, "--set", "subscriber", "--sem-prazo")

    usuario.refresh_from_db()
    assert usuario.plan is not None
    assert usuario.plan_until is None


@pytest.mark.django_db
def test_clear_devolve_a_conta_ao_default(usuario) -> None:
    executar(EMAIL, "--set", "subscriber")

    executar(EMAIL, "--clear")

    usuario.refresh_from_db()
    assert usuario.plan is None
    assert usuario.plan_until is None


@pytest.mark.django_db
def test_plano_inexistente_diz_quais_existem(usuario) -> None:
    """A mensagem de erro é a documentação que a pessoa lê no pior momento."""
    with pytest.raises(CommandError) as erro:
        executar(EMAIL, "--set", "premium-que-nao-existe")

    assert "subscriber" in str(erro.value)


@pytest.mark.django_db
def test_conta_inexistente_e_erro_e_nao_silencio(usuario) -> None:
    with pytest.raises(CommandError):
        executar("ninguem@exemplo.com", "--set", "subscriber")


@pytest.mark.django_db
def test_email_com_maiuscula_acha_a_conta(usuario) -> None:
    """Mesma normalização do cadastro — senão o suporte digita o e-mail do cliente e erra."""
    executar("Ana@Exemplo.com", "--set", "subscriber")

    usuario.refresh_from_db()
    assert usuario.plan is not None


@pytest.mark.django_db
def test_plano_vencido_e_dito_com_todas_as_letras(usuario) -> None:
    """`capabilities_for` já trata esta conta como default; a saída não pode sugerir o oposto."""
    usuario.plan = Plan.objects.get(slug="subscriber")
    usuario.plan_until = datetime.now(UTC) - timedelta(days=1)
    usuario.save()

    assert "VENCIDO" in executar(EMAIL)


@pytest.mark.django_db
def test_lista_os_planos_que_existem(usuario) -> None:
    saida = executar("--list")

    assert "subscriber" in saida
    assert "free" in saida


@pytest.mark.django_db
def test_sem_email_e_sem_list_e_erro(usuario) -> None:
    with pytest.raises(CommandError):
        executar()


@pytest.mark.django_db
def test_o_plano_atribuido_vale_na_api(client, usuario) -> None:
    """O teste que fecha o circuito: o comando muda o que a conta PODE, não só uma coluna."""
    executar(EMAIL, "--set", "subscriber")

    corpo = client.get("/api/config", **autorizacao(client, EMAIL)).json()

    assert corpo["plan"]["slug"] == "subscriber"
