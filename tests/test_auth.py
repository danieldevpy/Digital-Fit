"""Contas, trial anônimo e histórico (T-022 / SPEC-011).

Organizado pelos **três critérios de aceite** da spec, porque são eles que dizem se a task
está pronta:

1. 4ª sessão do dia no mesmo aparelho é negada com mensagem de upgrade;
2. usuário logado vê só o histórico dele, e relatório de sessão alheia dá 404;
3. token expirado renova sem derrubar sessão de treino em andamento.

O terceiro é o mais interessante de testar, porque a propriedade não está no código de auth:
está na arquitetura. O WebSocket é autenticado pelo token HMAC do ticket (SPEC-009), que não
sabe nada de usuário — então um JWT vencido no meio dos 30 s não tem por onde interferir. O
teste existe para que uma "melhoria" futura que ligue o WS ao JWT quebre aqui.
"""

from __future__ import annotations

import pytest
from api.models import SessionClaim, SessionResult, User
from api.tokens import verify_token
from api.trial import TRIAL_LIMIT, TrialStatus, device_id_from, quota_key, status_for
from api.trial import consume as consumir_trial

from tests.test_sessions import FakeRedis, admissao_falsa

SENHA = "polichinelo-2026"


@pytest.fixture
def usuario(db) -> User:
    return User.objects.create_user(email="ana@exemplo.com", password=SENHA, name="Ana")


def autorizacao(client, email: str = "ana@exemplo.com", senha: str = SENHA) -> dict[str, str]:
    """Faz login e devolve o header pronto."""
    resposta = client.post(
        "/api/auth/login",
        data={"email": email, "password": senha},
        content_type="application/json",
    )
    assert resposta.status_code == 200, resposta.content
    return {"HTTP_AUTHORIZATION": f"Bearer {resposta.json()['access']}"}


def abrir_sessao(client, monkeypatch, *, headers=None, redis=None) -> tuple[int, dict]:
    redis = admissao_falsa(monkeypatch, redis)
    resposta = client.post(
        "/api/sessions",
        data={"exercise": "jumping_jack", "requested_mode": "edge"},
        content_type="application/json",
        **(headers or {}),
    )
    return resposta.status_code, resposta.json()


# --------------------------------------------------------------------------------------
# Contas
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_cadastro_ja_devolve_tokens(client) -> None:
    """Obrigar um login logo depois do cadastro seria um passo a mais no funil, sem ganho."""
    resposta = client.post(
        "/api/auth/register",
        data={"email": "Bia@Exemplo.COM", "password": SENHA, "name": "Bia"},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["access"] and corpo["refresh"]
    # E-mail normalizado: "Bia@Exemplo.COM" e "bia@exemplo.com" são a mesma pessoa tentando
    # entrar, e duas contas seriam uma pessoa que não consegue logar.
    assert corpo["user"]["email"] == "bia@exemplo.com"
    assert User.objects.filter(email="bia@exemplo.com").exists()


@pytest.mark.django_db
def test_cadastro_com_email_repetido_da_409(client, usuario) -> None:
    resposta = client.post(
        "/api/auth/register",
        data={"email": "ana@exemplo.com", "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 409


@pytest.mark.django_db
@pytest.mark.parametrize(
    "corpo",
    [
        {"password": SENHA},
        {"email": "nao-e-email", "password": SENHA},
        {"email": "c@exemplo.com"},
    ],
)
def test_cadastro_recusa_corpo_invalido(client, corpo) -> None:
    resposta = client.post("/api/auth/register", data=corpo, content_type="application/json")

    assert resposta.status_code == 400


@pytest.mark.django_db
def test_senha_errada_e_email_inexistente_dao_a_mesma_resposta(client, usuario) -> None:
    """Mensagens diferentes fariam do login um verificador de "esta pessoa tem conta aqui?"."""
    errada = client.post(
        "/api/auth/login",
        data={"email": "ana@exemplo.com", "password": "outra-coisa"},
        content_type="application/json",
    )
    inexistente = client.post(
        "/api/auth/login",
        data={"email": "ninguem@exemplo.com", "password": SENHA},
        content_type="application/json",
    )

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json()["detail"] == inexistente.json()["detail"]


@pytest.mark.django_db
def test_me_devolve_quem_esta_logado_e_401_sem_token(client, usuario) -> None:
    assert client.get("/api/me").status_code == 401

    resposta = client.get("/api/me", **autorizacao(client))

    assert resposta.status_code == 200
    assert resposta.json()["email"] == "ana@exemplo.com"


@pytest.mark.django_db
def test_conta_inativa_nao_loga(client, usuario) -> None:
    User.objects.filter(pk=usuario.pk).update(is_active=False)

    resposta = client.post(
        "/api/auth/login",
        data={"email": "ana@exemplo.com", "password": SENHA},
        content_type="application/json",
    )

    assert resposta.status_code == 401


# --------------------------------------------------------------------------------------
# Critério 1 — trial anônimo: a 4ª sessão do dia é negada
# --------------------------------------------------------------------------------------


def test_contador_do_trial_vive_no_redis_e_expira() -> None:
    redis = FakeRedis()

    assert status_for(redis, "dev-1") == TrialStatus(used=0)
    for esperado in (1, 2, 3):
        assert consumir_trial(redis, "dev-1").used == esperado
    assert not status_for(redis, "dev-1").allowed
    # TTL posto na primeira contagem, não em toda: sem isso a chave renovaria o prazo a cada
    # sessão e um aparelho ativo nunca zeraria.
    assert redis.ttls[quota_key("dev-1")] > 0


def test_aparelhos_diferentes_tem_trials_independentes() -> None:
    redis = FakeRedis()
    for _ in range(TRIAL_LIMIT):
        consumir_trial(redis, "dev-1")

    assert not status_for(redis, "dev-1").allowed
    assert status_for(redis, "dev-2").allowed


def test_device_id_torto_e_trocado_por_um_novo() -> None:
    """Um id livre viraria chave de Redis arbitrária vinda do navegador."""
    assert device_id_from({"X-Device-Id": "a" * 40}) == "a" * 40
    assert device_id_from({"X-Device-Id": "curto"}) != "curto"
    assert device_id_from({"X-Device-Id": "trial:*:2026-07-28"}).isalnum()
    assert len(device_id_from({})) >= 8


@pytest.mark.django_db
def test_quarta_sessao_do_dia_e_negada_com_convite_a_criar_conta(client, monkeypatch) -> None:
    """Critério 1 da SPEC-011, ponta a ponta pelo endpoint."""
    redis = FakeRedis()
    device = {"HTTP_X_DEVICE_ID": "aparelho-de-teste-01"}

    for numero in range(1, TRIAL_LIMIT + 1):
        codigo, corpo = abrir_sessao(client, monkeypatch, headers=device, redis=redis)
        assert codigo == 201, f"sessao {numero} deveria passar"
        assert corpo["trial"]["used"] == numero
        assert corpo["trial"]["remaining"] == TRIAL_LIMIT - numero

    codigo, corpo = abrir_sessao(client, monkeypatch, headers=device, redis=redis)

    assert codigo == 429
    assert corpo["code"] == "trial_exhausted"
    # A recusa diz o que fazer, não só o que aconteceu: é o momento em que a conta faz sentido.
    assert "conta" in corpo["detail"].lower()
    assert SessionClaim.objects.count() == TRIAL_LIMIT


@pytest.mark.django_db
def test_a_admissao_devolve_o_device_id_que_gerou(client, monkeypatch) -> None:
    """Primeira visita: quem gera o id é o servidor, e o cliente precisa recebê-lo de volta."""
    redis = FakeRedis()
    _, primeira = abrir_sessao(client, monkeypatch, redis=redis)
    device = primeira["device_id"]
    assert device

    _, segunda = abrir_sessao(
        client, monkeypatch, headers={"HTTP_X_DEVICE_ID": device}, redis=redis
    )

    assert segunda["trial"]["used"] == 2


@pytest.mark.django_db
def test_usuario_logado_nao_gasta_trial(client, usuario, monkeypatch) -> None:
    """A conta É o upgrade nesta fase: planos pagos são Fase Evolução."""
    redis = FakeRedis()
    cabecalhos = {**autorizacao(client), "HTTP_X_DEVICE_ID": "aparelho-de-teste-01"}

    for _ in range(TRIAL_LIMIT + 2):
        codigo, corpo = abrir_sessao(client, monkeypatch, headers=cabecalhos, redis=redis)
        assert codigo == 201
        assert "trial" not in corpo

    assert redis.counters == {}
    assert SessionClaim.objects.filter(user=usuario).count() == TRIAL_LIMIT + 2
    # Sessão de quem tem conta não carrega aparelho: o device só existe para contar trial.
    assert set(SessionClaim.objects.values_list("device_id", flat=True)) == {""}


@pytest.mark.django_db
def test_sessao_recusada_nao_gasta_trial(client, monkeypatch) -> None:
    """Perder um terço do trial porque o servidor não tinha vaga seria cobrar pelo erro dele."""
    redis = FakeRedis()
    monkeypatch.setattr("api.views.bus", lambda: type("B", (), {"client": redis})())
    monkeypatch.setattr(
        "api.views.create_session",
        lambda pedido, **kwargs: __import__(
            "api.sessions", fromlist=["create_session"]
        ).create_session(
            pedido,
            redis_client=redis,
            event_bus=__import__("workers.shared.bus", fromlist=["InMemoryBus"]).InMemoryBus(),
            slots=type("Cheio", (), {"acquire": lambda self, *a, **k: False})(),
        ),
    )

    resposta = client.post(
        "/api/sessions",
        data={"exercise": "jumping_jack", "requested_mode": "cloud"},
        content_type="application/json",
        HTTP_X_DEVICE_ID="aparelho-de-teste-01",
    )

    assert resposta.status_code == 201
    assert resposta.json()["mode"] == "denied_cloud"
    assert redis.counters == {}
    assert SessionClaim.objects.count() == 0


# --------------------------------------------------------------------------------------
# Critério 2 — histórico é só meu; sessão alheia dá 404
# --------------------------------------------------------------------------------------


def relatorio(session_id: str, **kwargs) -> SessionResult:
    base = {"exercise": "jumping_jack", "mode": "edge", "reason": "completed", "rep_count": 12}
    return SessionResult.objects.create(session_id=session_id, **{**base, **kwargs})


@pytest.mark.django_db
def test_historico_traz_so_as_sessoes_do_usuario(client, usuario) -> None:
    outra = User.objects.create_user(email="bia@exemplo.com", password=SENHA)
    SessionClaim.objects.create(session_id="minha-1", user=usuario)
    SessionClaim.objects.create(session_id="minha-2", user=usuario)
    SessionClaim.objects.create(session_id="da-bia", user=outra)
    SessionClaim.objects.create(session_id="de-ninguem", device_id="dev-1")
    for sid in ("minha-1", "minha-2", "da-bia", "de-ninguem"):
        relatorio(sid)

    resposta = client.get("/api/sessions?mine", **autorizacao(client))

    assert resposta.status_code == 200
    assert {item["session_id"] for item in resposta.json()["results"]} == {"minha-1", "minha-2"}


@pytest.mark.django_db
def test_historico_exige_conta_e_exige_o_filtro(client, usuario) -> None:
    assert client.get("/api/sessions?mine").status_code == 401
    # Sem `?mine` a pergunta seria "as sessões de quem?" — não existe listagem global.
    assert client.get("/api/sessions", **autorizacao(client)).status_code == 400


@pytest.mark.django_db
def test_relatorio_de_sessao_alheia_da_404(client, usuario) -> None:
    """Critério 2. 403 confirmaria que a sessão existe; 404 não conta nada a ninguém."""
    outra = User.objects.create_user(email="bia@exemplo.com", password=SENHA)
    SessionClaim.objects.create(session_id="da-bia", user=outra)
    relatorio("da-bia")

    resposta = client.get("/api/sessions/da-bia/report", **autorizacao(client))

    assert resposta.status_code == 404
    # `pending: false` de propósito: com `true` o cliente ficaria repetindo para sempre um
    # pedido que nunca vai ser atendido.
    assert resposta.json()["pending"] is False


@pytest.mark.django_db
def test_dono_le_o_proprio_relatorio(client, usuario) -> None:
    SessionClaim.objects.create(session_id="minha-1", user=usuario)
    relatorio("minha-1", rep_count=21)

    resposta = client.get("/api/sessions/minha-1/report", **autorizacao(client))

    assert resposta.status_code == 200
    assert resposta.json()["rep_count"] == 21


@pytest.mark.django_db
def test_sessao_anonima_continua_aberta_por_id(client) -> None:
    """A Fase 0 inteira é anônima e precisa continuar funcionando: o id é um UUID e o
    cliente que abriu a sessão é quem o tem."""
    SessionClaim.objects.create(session_id="anonima-1", device_id="dev-1")
    relatorio("anonima-1")

    assert client.get("/api/sessions/anonima-1/report").status_code == 200


@pytest.mark.django_db
def test_relatorio_que_ainda_nao_existe_continua_dizendo_pending(client) -> None:
    """A T-020 depende disto: "404" ali quer dizer "ainda não", e o cliente repete."""
    resposta = client.get("/api/sessions/nunca-vista/report")

    assert resposta.status_code == 404
    assert resposta.json()["pending"] is True


# --------------------------------------------------------------------------------------
# Critério 3 — o token vence, o treino não cai
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_refresh_devolve_access_novo(client, usuario) -> None:
    login = client.post(
        "/api/auth/login",
        data={"email": "ana@exemplo.com", "password": SENHA},
        content_type="application/json",
    ).json()

    resposta = client.post(
        "/api/auth/refresh",
        data={"refresh": login["refresh"]},
        content_type="application/json",
    )

    assert resposta.status_code == 200
    assert resposta.json()["access"]
    # Sem rotação: o mesmo refresh continua valendo, e é isso que faz a renovação ser um
    # detalhe invisível durante o treino.
    assert (
        client.post(
            "/api/auth/refresh",
            data={"refresh": login["refresh"]},
            content_type="application/json",
        ).status_code
        == 200
    )


@pytest.mark.django_db
def test_refresh_invalido_da_401(client) -> None:
    resposta = client.post(
        "/api/auth/refresh", data={"refresh": "nao.e.um.token"}, content_type="application/json"
    )

    assert resposta.status_code == 401


@pytest.mark.django_db
def test_o_treino_em_andamento_nao_depende_do_jwt(client, usuario, monkeypatch) -> None:
    """Critério 3, na raiz: o WebSocket é autenticado pelo token HMAC do ticket (SPEC-009).

    O ticket sai da admissão e vale 45 s por conta própria. Nenhum JWT participa dele — então
    o access vencer no segundo 20 do treino não tem por onde derrubar a sessão. Se alguém um
    dia amarrar o WS ao JWT, este teste é o alarme.
    """
    codigo, ticket = abrir_sessao(client, monkeypatch, headers=autorizacao(client))
    assert codigo == 201

    # Sem nenhum header de autenticação, como o gateway faz: só o par (session_id, token).
    assert verify_token(ticket["session_id"], ticket["token"])
    assert "token" not in ticket["ws_url"].split("?")[0]
    assert ticket["token"] in ticket["ws_url"]


# --------------------------------------------------------------------------------------
# Rate limit das rotas de auth
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_rotas_de_auth_tem_rate_limit_por_ip(client, usuario, monkeypatch) -> None:
    """Não substitui senha boa; torna caro varrer senhas."""
    from api.auth import AuthThrottle

    # `rate` como atributo de classe: o `SimpleRateThrottle` só consulta as settings quando a
    # instância não tem taxa própria, então isto vale sem mexer em configuração global.
    monkeypatch.setattr(AuthThrottle, "rate", "3/min", raising=False)

    codigos = [
        client.post(
            "/api/auth/login",
            data={"email": "ana@exemplo.com", "password": "errada"},
            content_type="application/json",
        ).status_code
        for _ in range(5)
    ]

    assert codigos == [401, 401, 401, 429, 429]


@pytest.mark.django_db
def test_admissao_nao_tem_rate_limit_de_auth(client, monkeypatch) -> None:
    """Limitar `POST /sessions` por IP mataria academia e casa com NAT — quem limita a
    admissão é a quota do trial, que conta aparelho e não endereço."""
    from api.auth import AuthThrottle

    monkeypatch.setattr(AuthThrottle, "rate", "1/min", raising=False)
    redis = FakeRedis()

    codigos = [
        abrir_sessao(client, monkeypatch, headers={"HTTP_X_DEVICE_ID": f"dev-{i}"}, redis=redis)[0]
        for i in range(4)
    ]

    assert codigos == [201, 201, 201, 201]
