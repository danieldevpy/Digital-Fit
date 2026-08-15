"""Adoção das sessões do aparelho no cadastro (T-087 / SPEC-019 §Anônimo).

O critério de aceite 5 da SPEC-019 é o teste principal daqui: *"cadastro com device_id que tem
sessões anônimas: `GET /api/engagement` já nasce com o fogo e `GET /api/sessions?mine` com o
histórico do aparelho"*. Ele fecha também a Descoberta `[T-121]` — até agora o cliente mesclava
sessões locais que o servidor não conhecia, e nada as adotava.

As outras três seções cobrem as **fronteiras** que a spec enumera, e elas importam tanto quanto
o caminho feliz: sem a de "só claims órfãs", dois cadastros no mesmo celular disputariam as
mesmas sessões.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from api.models import SessionClaim, SessionResult, User
from django.utils import timezone

SENHA = "polichinelo-2026"
APARELHO = "dev-do-visitante-01"


def sessao_anonima(*, device_id: str = APARELHO, dias_atras: int = 0, reps: int = 10) -> str:
    """Uma sessão de visitante: claim sem dono + relatório, como a admissão e o report-builder
    as escrevem."""
    sid = f"anon-{device_id}-{dias_atras}"
    SessionClaim.objects.create(session_id=sid, user=None, device_id=device_id)
    resultado = SessionResult.objects.create(
        session_id=sid, exercise="squat", mode="edge", reason="completed", rep_count=reps
    )
    SessionResult.objects.filter(pk=resultado.pk).update(
        created_at=timezone.now() - timedelta(days=dias_atras)
    )
    return sid


def cadastrar(client, email: str = "ana@exemplo.com", *, aparelho: str | None = APARELHO):
    extra = {"HTTP_X_DEVICE_ID": aparelho} if aparelho else {}
    return client.post(
        "/api/auth/register",
        data={"email": email, "password": SENHA, "name": "Ana"},
        content_type="application/json",
        **extra,
    )


def autorizacao(resposta) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {resposta.json()['access']}"}


# ======================================================================================
# Critério de aceite 5 — o fogo e o histórico sobrevivem à criação da conta.
# ======================================================================================


def test_a_conta_nasce_com_o_fogo_e_o_historico_do_aparelho(client, db) -> None:
    """O critério 5 inteiro, nas duas rotas que ele nomeia.

    Três dias seguidos como visitante e a conta criada no terceiro: o fogo tem de dizer 3. Sem
    a adoção, a mesma pessoa veria 1 — e a dor de recomeçar seria causada exatamente pela ação
    que o app pediu que ela fizesse.
    """
    for atras in (0, 1, 2):
        sessao_anonima(dias_atras=atras)

    resposta = cadastrar(client)
    assert resposta.status_code == 201, resposta.content
    cabecalho = autorizacao(resposta)

    engajamento = client.get("/api/engagement", **cabecalho).json()
    historico = client.get("/api/sessions?mine", **cabecalho).json()

    assert engajamento["streak"] == 3
    assert engajamento["today_active"] is True
    assert historico["count"] == 3


def test_o_cadastro_diz_quantas_sessoes_trouxe(client, db) -> None:
    """O CTA promete "não perca seu fogo"; o corpo confirma que a promessa foi cumprida."""
    sessao_anonima(dias_atras=0)
    sessao_anonima(dias_atras=1)

    corpo = cadastrar(client).json()

    assert corpo["adopted_sessions"] == 2


def test_quem_cria_conta_antes_de_treinar_adota_zero_sem_erro(client, db) -> None:
    """Zero é resposta legítima, e o campo não some por isso — sumir obrigaria o cliente a
    tratar ausência como "não sei"."""
    corpo = cadastrar(client).json()

    assert corpo["adopted_sessions"] == 0


def test_cadastro_sem_cabecalho_de_aparelho_continua_funcionando(client, db) -> None:
    """O cadastro não depende do aparelho: quem chega pelo site, num navegador que nunca abriu
    a câmera, não tem `X-Device-Id` nenhum para mandar."""
    sessao_anonima(dias_atras=0)

    resposta = cadastrar(client, aparelho=None)

    assert resposta.status_code == 201
    assert resposta.json()["adopted_sessions"] == 0


def test_cabecalho_malformado_nao_adota_e_nao_quebra(client, db) -> None:
    """Id fora do formato é id que nenhum cliente honesto mandou — e nunca virou chave no banco."""
    sessao_anonima(dias_atras=0)

    resposta = cadastrar(client, aparelho="../../etc/passwd")

    assert resposta.status_code == 201
    assert resposta.json()["adopted_sessions"] == 0


# ======================================================================================
# Fronteira 1 — só claims órfãs.
# ======================================================================================


def test_aparelho_ja_adotado_nao_e_reivindicavel_pelo_segundo_cadastro(client, db) -> None:
    """Sem o filtro `user IS NULL`, o segundo a se cadastrar no mesmo celular levaria as sessões
    do primeiro — e o primeiro veria o próprio histórico desaparecer."""
    sessao_anonima(dias_atras=0)
    sessao_anonima(dias_atras=1)

    primeira = cadastrar(client, "ana@exemplo.com")
    segunda = cadastrar(client, "bruno@exemplo.com")

    assert primeira.json()["adopted_sessions"] == 2
    assert segunda.json()["adopted_sessions"] == 0
    assert client.get("/api/sessions?mine", **autorizacao(primeira)).json()["count"] == 2
    assert client.get("/api/sessions?mine", **autorizacao(segunda)).json()["count"] == 0


def test_sessao_de_outro_aparelho_nao_e_adotada(client, db) -> None:
    sessao_anonima(device_id=APARELHO, dias_atras=0)
    sessao_anonima(device_id="dev-de-outra-pessoa", dias_atras=0)

    corpo = cadastrar(client).json()

    assert corpo["adopted_sessions"] == 1


# ======================================================================================
# Fronteira 2 — idempotente por construção.
# ======================================================================================


def test_adotar_de_novo_nao_faz_nada(db) -> None:
    """Depois da primeira passada não há mais claim órfã — não precisa de flag nem de tabela."""
    from api.auth import adotar_sessoes_do_aparelho

    sessao_anonima(dias_atras=0)
    usuario = User.objects.create_user(email="ana@exemplo.com", password=SENHA)

    assert adotar_sessoes_do_aparelho(usuario, APARELHO) == 1
    assert adotar_sessoes_do_aparelho(usuario, APARELHO) == 0


# ======================================================================================
# Fronteira 3 — só no registro.
# ======================================================================================


def test_login_com_o_cabecalho_do_aparelho_nao_adota_nada(client, db) -> None:
    """Não é um botão "importar aparelho". Quem quiser essa função escreve — e revisa estas
    fronteiras ao escrever."""
    User.objects.create_user(email="ana@exemplo.com", password=SENHA)
    sessao_anonima(dias_atras=0)

    resposta = client.post(
        "/api/auth/login",
        data={"email": "ana@exemplo.com", "password": SENHA},
        content_type="application/json",
        HTTP_X_DEVICE_ID=APARELHO,
    )

    assert resposta.status_code == 200
    assert "adopted_sessions" not in resposta.json()
    assert client.get("/api/sessions?mine", **autorizacao(resposta)).json()["count"] == 0


@pytest.mark.django_db(transaction=True)
def test_cadastro_recusado_nao_adota(client) -> None:
    """E-mail repetido responde 409 antes de qualquer escrita — a conta que adotaria não existe.

    `transaction=True` porque o 409 nasce de um `IntegrityError` de verdade (é o banco que
    decide, não um `exists()` antes que sempre teria janela): dentro do bloco atômico do teste
    padrão, o erro deixa a transação quebrada e nenhuma consulta posterior roda.
    """
    User.objects.create_user(email="ana@exemplo.com", password=SENHA)
    sessao_anonima(dias_atras=0)

    resposta = cadastrar(client, "ana@exemplo.com")

    assert resposta.status_code == 409
    assert SessionClaim.objects.filter(user__isnull=True, device_id=APARELHO).count() == 1


# ======================================================================================
# A leitura sem gerar id — a função que a T-087 precisou separar.
# ======================================================================================


@pytest.mark.parametrize("bruto", ["", "   ", "curto", "com espaço", None])
def test_device_id_declarado_nao_inventa_aparelho(bruto) -> None:
    """`device_id_from` gera um id quando não vem nenhum (é o que faz o trial funcionar na
    primeira visita). Aqui isso seria errado: um id inventado não pertence a aparelho nenhum, e
    a única coisa que faria é adotar zero claims com ar de que tentou."""
    from api.quota import device_id_declarado

    assert device_id_declarado({"X-Device-Id": bruto}) == ""


def test_device_id_declarado_devolve_o_id_valido() -> None:
    from api.quota import device_id_declarado

    assert device_id_declarado({"X-Device-Id": APARELHO}) == APARELHO
