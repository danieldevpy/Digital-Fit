"""Quota diária por plano (SPEC-016, T-063).

Um arquivo por **critério de aceite** da spec, porque são eles que decidem se a task está
pronta:

1. a 11ª sessão do dia de uma conta Free é recusada pelo servidor, e a UI sabe disso antes de
   abrir a câmera (é para isso que existe o `GET /api/quota`);
2. assinante não é recusado;
3. kcal ao vivo — do lado do cliente, em `web/src/session/kcal.test.ts`;
4. forjar o cliente não fura a quota.

O critério 4 é o mais fácil de fingir que se testou. Um teste que só chama o endpoint pelo
caminho normal prova que o caminho normal funciona — não que não há outro. Os testes daqui
atacam os três atalhos que um cliente adulterado tentaria: trocar de aparelho, pular o
pré-voo e mandar limite no corpo.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from api import quota
from api.config import PLAN_FREE, PLAN_SUBSCRIBER
from api.models import Plan, SessionClaim, User

from tests.test_sessions import FakeRedis, admissao_falsa

SENHA = "polichinelo-2026"
CORPO = {"exercise": "jumping_jack", "requested_mode": "edge"}


@pytest.fixture
def conta(db) -> User:
    """Conta sem plano atribuído — ou seja, `free`, que é o `is_default` da tabela."""
    return User.objects.create_user(email="ana@exemplo.com", password=SENHA, name="Ana")


def autorizacao(client) -> dict[str, str]:
    resposta = client.post(
        "/api/auth/login",
        data={"email": "ana@exemplo.com", "password": SENHA},
        content_type="application/json",
    )
    assert resposta.status_code == 200, resposta.content
    return {"HTTP_AUTHORIZATION": f"Bearer {resposta.json()['access']}"}


def treinar(client, monkeypatch, *, headers=None, redis=None):
    redis = admissao_falsa(monkeypatch, redis)
    resposta = client.post(
        "/api/sessions", data=CORPO, content_type="application/json", **(headers or {})
    )
    return resposta, redis


# --------------------------------------------------------------------------------------
# A regra do contador, sem HTTP
# --------------------------------------------------------------------------------------


def test_a_chave_muda_com_a_identidade_e_a_regra_nao() -> None:
    """O parágrafo da SPEC-018 §A dito como teste."""
    agora = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
    usuario = type("U", (), {"pk": 7})()

    assert quota.quota_key(None, "dev-1", now=agora) == "trial:dev-1:2026-07-31"
    assert quota.quota_key(usuario, "dev-1", now=agora) == "df:quota:7:2026-07-31"


def test_conta_e_aparelho_contam_separado() -> None:
    """Quem cria conta no meio do dia não herda o que gastou como visitante.

    Herdar seria a conta parecendo um downgrade exatamente no momento em que o funil pede que
    ela pareça um upgrade.
    """
    redis = FakeRedis()
    usuario = type("U", (), {"pk": 7})()
    for _ in range(3):
        quota.consume(redis, quota.quota_key(None, "dev-1"), limit=3)

    assert not quota.status_for(redis, quota.quota_key(None, "dev-1"), limit=3).allowed
    assert quota.status_for(redis, quota.quota_key(usuario, ""), limit=10).allowed


def test_limite_zero_e_ilimitado() -> None:
    """`daily_sessions = 0` é como o `Plan` diz "sem limite", e só aqui isso é interpretado."""
    parado = quota.QuotaStatus(used=999, limit=0, resets_at=quota.resets_at())

    assert parado.unlimited
    assert parado.allowed
    assert parado.remaining == 0


def test_o_contador_vira_na_meia_noite_utc() -> None:
    """23:59 de um dia e 00:01 do outro não podem cair na mesma chave."""
    quase = datetime(2026, 7, 31, 23, 59, tzinfo=UTC)

    assert quota.resets_at(quase) == datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    assert quota.quota_key(None, "d", now=quase) != quota.quota_key(
        None, "d", now=datetime(2026, 8, 1, 0, 1, tzinfo=UTC)
    )


# --------------------------------------------------------------------------------------
# Critério 1 — a 11ª sessão do dia é recusada
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_decima_primeira_sessao_do_dia_e_recusada(client, conta, monkeypatch) -> None:
    """O critério 1 ao pé da letra: dez passam, a décima primeira não.

    O `10` não está escrito aqui como número mágico — vem de `quota.FREE_LIMIT`, que é o piso
    do código, e o teste seguinte é quem prova que a linha do banco diz o mesmo.
    """
    redis = FakeRedis()
    cabecalhos = autorizacao(client)

    for numero in range(1, quota.FREE_LIMIT + 1):
        resposta, redis = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)
        assert resposta.status_code == 201, f"sessao {numero} deveria passar"
        assert resposta.json()["quota"]["used"] == numero
        assert resposta.json()["quota"]["remaining"] == quota.FREE_LIMIT - numero

    resposta, _ = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)

    assert resposta.status_code == 429
    corpo = resposta.json()
    # Código próprio, e não o `trial_exhausted` do visitante: a ação de quem lê é outra —
    # aqui não adianta criar conta, a conta é que chegou ao limite.
    assert corpo["code"] == "quota_exceeded"
    assert "🎉" in corpo["detail"]
    assert corpo["quota"]["remaining"] == 0
    assert corpo["quota"]["resets_at"].endswith("Z")
    # Sessão recusada não nasce: nada de `SessionClaim` órfão nem de contador andando.
    assert SessionClaim.objects.count() == quota.FREE_LIMIT


@pytest.mark.django_db
def test_o_piso_do_codigo_e_a_linha_do_banco_dizem_o_mesmo_numero(conta) -> None:
    """Piso divergente do banco é uma quota que muda sozinha quando o Postgres tosse.

    A migration `0010_quota_do_free` e a constante `FREE_LIMIT` são dois lugares com o mesmo
    número por uma razão boa (migration não importa código de aplicação, ver o docstring dela)
    — e dois lugares com o mesmo número precisam de alguém cobrando.
    """
    assert Plan.objects.get(slug=PLAN_FREE).daily_sessions == quota.FREE_LIMIT
    assert Plan.objects.get(slug=PLAN_FREE).quota_message == quota.FREE_MESSAGE


@pytest.mark.django_db
def test_o_painel_manda_no_limite_e_nao_o_codigo(client, conta, monkeypatch) -> None:
    """O que a T-073 prometeu: mudar o limite é editar uma linha, não fazer deploy."""
    Plan.objects.filter(slug=PLAN_FREE).update(daily_sessions=1)
    Plan.objects.get(slug=PLAN_FREE).save()  # dispara a invalidação do snapshot

    redis = FakeRedis()
    cabecalhos = autorizacao(client)
    primeira, redis = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)
    segunda, _ = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)

    assert primeira.status_code == 201
    assert segunda.status_code == 429


# --------------------------------------------------------------------------------------
# Critério 2 — assinante não é recusado
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_assinante_nao_e_recusado_nem_gasta_contador(client, conta, monkeypatch) -> None:
    """Critério 2, com a "flag manual no banco" que a spec descreve.

    E mais um bocado: o assinante não escreve contador nenhum. Uma chave por dia por assinante
    seria lixo no Redis para responder uma pergunta cuja resposta é sempre "pode".
    """
    User.objects.filter(pk=conta.pk).update(plan=Plan.objects.get(slug=PLAN_SUBSCRIBER))

    redis = FakeRedis()
    cabecalhos = autorizacao(client)
    for _ in range(quota.FREE_LIMIT + 3):
        resposta, redis = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)
        assert resposta.status_code == 201
        assert resposta.json()["quota"]["unlimited"] is True
        # Sem limite não há recusa, e sem recusa não há texto de recusa: o campo vem vazio em
        # vez de carregar uma frase falsa esperando quem a exiba.
        assert resposta.json()["quota"]["message"] == ""

    assert redis.counters == {}


# --------------------------------------------------------------------------------------
# Critério 4 — forjar o cliente não fura a quota
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_trocar_de_aparelho_nao_zera_a_quota_da_conta(client, conta, monkeypatch) -> None:
    """O atalho óbvio: a conta manda um `X-Device-Id` novo a cada requisição.

    Funcionaria se a chave da conta tivesse device dentro. Não tem — e é por isso que
    `quota_key` é uma função só, e não uma escolha de quem chama.
    """
    Plan.objects.filter(slug=PLAN_FREE).update(daily_sessions=2)
    Plan.objects.get(slug=PLAN_FREE).save()

    redis = FakeRedis()
    cabecalhos = autorizacao(client)
    for indice in range(2):
        resposta, redis = treinar(
            client,
            monkeypatch,
            headers={**cabecalhos, "HTTP_X_DEVICE_ID": f"aparelho-inventado-{indice}"},
            redis=redis,
        )
        assert resposta.status_code == 201

    resposta, _ = treinar(
        client,
        monkeypatch,
        headers={**cabecalhos, "HTTP_X_DEVICE_ID": "aparelho-inventado-99"},
        redis=redis,
    )

    assert resposta.status_code == 429


@pytest.mark.django_db
def test_limite_no_corpo_da_requisicao_e_ignorado(client, conta, monkeypatch) -> None:
    """Um cliente adulterado mandando `daily_sessions` não compra capacidade nenhuma.

    Parece óbvio porque `SessionRequest.parse` só lê três campos — e é exatamente por ser
    óbvio que ninguém escreveria este teste, e que um dia alguém passaria o corpo inteiro
    adiante "para não perder informação".
    """
    Plan.objects.filter(slug=PLAN_FREE).update(daily_sessions=1)
    Plan.objects.get(slug=PLAN_FREE).save()

    redis = admissao_falsa(monkeypatch)
    cabecalhos = autorizacao(client)
    client.post("/api/sessions", data=CORPO, content_type="application/json", **cabecalhos)

    resposta = client.post(
        "/api/sessions",
        data={**CORPO, "daily_sessions": 999, "quota": {"limit": 999}, "plan": PLAN_SUBSCRIBER},
        content_type="application/json",
        **cabecalhos,
    )

    assert resposta.status_code == 429
    assert redis.counters  # contou uma, e só uma


@pytest.mark.django_db
def test_pular_o_pre_voo_nao_ajuda(client, conta, monkeypatch) -> None:
    """A trava é a admissão, não o `GET /api/quota`.

    O pré-voo existe para a UI *refletir* o limite (SPEC-016: "a UI apenas reflete e vende o
    upgrade, nunca é a única barreira"). Um cliente que simplesmente não o chamasse tem de
    esbarrar do mesmo jeito.
    """
    Plan.objects.filter(slug=PLAN_FREE).update(daily_sessions=1)
    Plan.objects.get(slug=PLAN_FREE).save()

    redis = FakeRedis()
    cabecalhos = autorizacao(client)
    primeira, redis = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)
    assert primeira.status_code == 201

    # Nenhum `GET /api/quota` no meio — direto para a admissão.
    segunda, _ = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)

    assert segunda.status_code == 429


# --------------------------------------------------------------------------------------
# GET /api/quota — o pré-voo que faz o sheet aparecer antes da câmera
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_pre_voo_da_conta_conta_o_que_a_admissao_contou(client, conta, monkeypatch) -> None:
    """O número do pré-voo e o número da admissão saem do mesmo contador.

    Dois contadores dariam uma tela dizendo "restam 4" e um servidor recusando na 3ª — o tipo
    de divergência que a pessoa lê como bug do app, não como limite de plano.
    """
    redis = FakeRedis()
    cabecalhos = autorizacao(client)
    for _ in range(3):
        _, redis = treinar(client, monkeypatch, headers=cabecalhos, redis=redis)

    resposta = client.get("/api/quota", **cabecalhos)

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["plan"] == PLAN_FREE
    assert corpo["used"] == 3
    assert corpo["remaining"] == quota.FREE_LIMIT - 3
    assert corpo["allowed"] is True
    assert corpo["message"] == quota.FREE_MESSAGE
    # A resposta muda a cada sessão: cache nenhum, nem privado.
    assert resposta["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_pre_voo_do_visitante_devolve_o_aparelho(client, monkeypatch) -> None:
    """Mesma razão do ticket: na primeira visita quem gera o id é o servidor."""
    admissao_falsa(monkeypatch)

    resposta = client.get("/api/quota")

    corpo = resposta.json()
    assert corpo["plan"] == "anon"
    assert corpo["limit"] == quota.TRIAL_LIMIT
    assert corpo["device_id"]


@pytest.mark.django_db
def test_pre_voo_diz_esgotado_antes_de_qualquer_sessao_nova(client, conta, monkeypatch) -> None:
    """O critério 1 tem uma segunda metade: *"a UI mostra o sheet antes de abrir a câmera"*.

    Sem esta resposta a pessoa daria permissão de câmera, esperaria o landmarker aquecer e se
    enquadraria — para só então ouvir "não".
    """
    Plan.objects.filter(slug=PLAN_FREE).update(daily_sessions=1)
    Plan.objects.get(slug=PLAN_FREE).save()

    cabecalhos = autorizacao(client)
    _, redis = treinar(client, monkeypatch, headers=cabecalhos)
    admissao_falsa(monkeypatch, redis)

    resposta = client.get("/api/quota", **cabecalhos)

    assert resposta.json()["allowed"] is False
    assert resposta.json()["remaining"] == 0


@pytest.mark.django_db
def test_pre_voo_com_redis_fora_diz_que_nao_sabe(client, conta, monkeypatch) -> None:
    """503, e não `used: 0`.

    Um zero inventado apagaria o sheet de quem já esgotou, e o passo seguinte dessa pessoa
    seria a câmera abrindo para uma sessão que o servidor vai recusar. "Não sei" dito como
    erro deixa o cliente ficar com o que já tinha.
    """

    class RedisMorto:
        def get(self, key):
            raise ConnectionError("sem redis")

    monkeypatch.setattr("api.views.bus", lambda: type("B", (), {"client": RedisMorto()})())

    resposta = client.get("/api/quota", **autorizacao(client))

    assert resposta.status_code == 503


@pytest.mark.django_db
def test_pre_voo_do_assinante_nao_toca_no_redis(client, conta, monkeypatch) -> None:
    """Plano ilimitado responde pelo plano, sem ler contador — nem quando o Redis está fora."""
    User.objects.filter(pk=conta.pk).update(plan=Plan.objects.get(slug=PLAN_SUBSCRIBER))
    monkeypatch.setattr("api.views.bus", lambda: 1 / 0)  # tocar no Redis aqui é erro

    resposta = client.get("/api/quota", **autorizacao(client))

    assert resposta.status_code == 200
    assert resposta.json()["unlimited"] is True
    assert resposta.json()["allowed"] is True
