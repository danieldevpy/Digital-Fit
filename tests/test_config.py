"""Resolução de configuração de negócio (SPEC-018, T-073).

Os testes seguem os critérios de aceite da spec. O que eles guardam, acima de tudo, é a
promessa da task: **ligar a SPEC-018 não muda comportamento nenhum**. Por isso vários deles
comparam o valor resolvido com a constante que existia antes — se alguém "melhorar" um default
por engano, é aqui que aparece, e não em produção.
"""

from datetime import UTC, datetime, timedelta

import pytest
from api import quota
from api.config import (
    PLAN_ANON,
    PLAN_FREE,
    PLAN_SUBSCRIBER,
    SNAPSHOT_KEY,
    Capabilities,
    capabilities_for,
)
from api.models import Plan, SiteConfig, User
from api.sessions import DEFAULT_DURATION_S
from api.tokens import DEFAULT_TTL_S
from django.core.cache import cache
from django.core.exceptions import ValidationError

from workers.shared.events import DEFAULT_COUNTDOWN_S, MAX_COUNTDOWN_S
from workers.shared.slots import DEFAULT_CLOUD_SLOTS, GRACE_MS


@pytest.fixture(autouse=True)
def _limpa_snapshot():
    cache.delete(SNAPSHOT_KEY)
    yield
    cache.delete(SNAPSHOT_KEY)


# --------------------------------------------------------------------------------------
# P2 — o piso do código. Estes rodam SEM banco: é a prova de que a leitura pode falhar
# inteira e ainda assim nascer uma sessão (critério de aceite 2).
# --------------------------------------------------------------------------------------


def test_sem_banco_nenhum_o_anonimo_recebe_o_trial_de_hoje() -> None:
    caps = capabilities_for(None)

    assert caps.plan_slug == PLAN_ANON
    assert caps.daily_sessions == quota.TRIAL_LIMIT
    assert caps.quota_message == quota.TRIAL_MESSAGE
    assert caps.from_db is False


def test_sem_banco_nenhum_os_parametros_globais_sao_as_constantes_de_hoje() -> None:
    caps = capabilities_for(None)

    assert caps.default_duration_s == DEFAULT_DURATION_S
    assert caps.default_countdown_s == DEFAULT_COUNTDOWN_S
    assert caps.countdown_max_s == MAX_COUNTDOWN_S
    assert caps.ticket_ttl_s == DEFAULT_TTL_S
    assert caps.cloud_slots == DEFAULT_CLOUD_SLOTS
    assert caps.cloud_grace_ms == GRACE_MS


def test_banco_fora_do_ar_nao_levanta_e_devolve_o_piso(monkeypatch) -> None:
    """Critério 2 da spec: com a leitura de config derrubada de propósito, a sessão ainda nasce."""

    def explode() -> dict:
        raise RuntimeError("postgres fora do ar")

    monkeypatch.setattr("api.config._read_snapshot_from_db", explode)

    caps = capabilities_for(None)

    assert caps.daily_sessions == quota.TRIAL_LIMIT
    assert caps.from_db is False


def test_cache_fora_do_ar_cai_para_o_banco(monkeypatch, db) -> None:
    def explode(*_a, **_kw):
        raise RuntimeError("redis fora do ar")

    monkeypatch.setattr("api.config.cache.get", explode)
    monkeypatch.setattr("api.config.cache.set", explode)

    caps = capabilities_for(None)

    # Veio do Postgres (a migration de dados criou o `anon`), apesar de o cache não responder.
    assert caps.from_db is True
    assert caps.plan_slug == PLAN_ANON


# --------------------------------------------------------------------------------------
# A migration de dados — "os valores de hoje"
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_migration_cria_os_tres_planos_e_o_singleton() -> None:
    assert set(Plan.objects.values_list("slug", flat=True)) == {
        PLAN_ANON,
        PLAN_FREE,
        PLAN_SUBSCRIBER,
    }
    assert Plan.objects.filter(is_default=True).count() == 1
    assert Plan.objects.get(is_default=True).slug == PLAN_FREE
    assert SiteConfig.objects.filter(pk=1).exists()


@pytest.mark.django_db
def test_conta_free_tem_a_quota_diaria_da_spec_016() -> None:
    """Os 10/dia que a T-073 deixou prontos e a T-063 ligou (migration `0010_quota_do_free`).

    Este teste afirmava o contrário até a T-063 (`daily_sessions == 0`, ilimitado). A inversão
    é o produto mudando de ideia por spec — não um teste sendo consertado.
    """
    usuario = User.objects.create_user(email="a@x.com", password="segredo123")

    caps = capabilities_for(usuario)

    assert caps.plan_slug == PLAN_FREE
    assert caps.daily_sessions == quota.FREE_LIMIT
    assert caps.unlimited_sessions is False
    assert caps.quota_message == quota.FREE_MESSAGE


@pytest.mark.django_db
def test_duracao_e_faixa_de_hoje_sao_30s_fixos() -> None:
    caps = capabilities_for(None)

    assert caps.duration_s() == DEFAULT_DURATION_S
    # Pedir mais não amplia: a faixa configurável é a T-064.
    assert caps.duration_s(300) == DEFAULT_DURATION_S
    assert caps.duration_s(1) == DEFAULT_DURATION_S


@pytest.mark.django_db
def test_cloud_continua_livre_para_todos_os_planos() -> None:
    assert all(p.allow_cloud for p in Plan.objects.all())


# --------------------------------------------------------------------------------------
# Resolução de plano
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_plano_atribuido_vence_o_default() -> None:
    assinatura = Plan.objects.get(slug=PLAN_SUBSCRIBER)
    usuario = User.objects.create_user(email="b@x.com", password="segredo123", plan=assinatura)

    caps = capabilities_for(usuario)

    assert caps.plan_slug == PLAN_SUBSCRIBER
    assert caps.daily_workout is True
    assert caps.streak_protections_month == 2


@pytest.mark.django_db
def test_assinatura_vencida_cai_para_o_default_na_leitura() -> None:
    """Sem job de expiração: um cron seria um segundo lugar onde o plano é decidido."""
    assinatura = Plan.objects.get(slug=PLAN_SUBSCRIBER)
    ontem = datetime.now(UTC) - timedelta(days=1)
    usuario = User.objects.create_user(
        email="c@x.com", password="segredo123", plan=assinatura, plan_until=ontem
    )

    assert capabilities_for(usuario).plan_slug == PLAN_FREE


@pytest.mark.django_db
def test_assinatura_no_prazo_continua_valendo() -> None:
    assinatura = Plan.objects.get(slug=PLAN_SUBSCRIBER)
    amanha = datetime.now(UTC) + timedelta(days=1)
    usuario = User.objects.create_user(
        email="d@x.com", password="segredo123", plan=assinatura, plan_until=amanha
    )

    assert capabilities_for(usuario).plan_slug == PLAN_SUBSCRIBER


@pytest.mark.django_db
def test_plano_apagado_da_tabela_cai_no_piso_do_proprio_slug() -> None:
    """Não é erro: é o estado antes da migration, e o de quem apagou uma linha por fora."""
    Plan.objects.filter(slug=PLAN_ANON).delete()

    caps = capabilities_for(None)

    assert caps.plan_slug == PLAN_ANON
    assert caps.daily_sessions == quota.TRIAL_LIMIT


# --------------------------------------------------------------------------------------
# Cache e invalidação — critério 1 (mudar no painel vale sem restart)
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_mudar_o_plano_muda_a_capacidade_sem_restart() -> None:
    assert capabilities_for(None).daily_sessions == 3

    plano = Plan.objects.get(slug=PLAN_ANON)
    plano.daily_sessions = 7
    plano.save()

    assert capabilities_for(None).daily_sessions == 7


@pytest.mark.django_db
def test_salvar_plano_incrementa_a_versao_da_configuracao() -> None:
    antes = SiteConfig.objects.get(pk=1).version

    plano = Plan.objects.get(slug=PLAN_FREE)
    plano.nome = "Grátis"
    plano.save()

    assert SiteConfig.objects.get(pk=1).version == antes + 1


@pytest.mark.django_db
def test_salvar_a_propria_configuracao_nao_entra_em_laco() -> None:
    """O bump usa `queryset.update()`, que não dispara `post_save` — contador, não laço."""
    config = SiteConfig.objects.get(pk=1)
    antes = config.version

    config.cloud_slots = 4
    config.save()

    assert SiteConfig.objects.get(pk=1).version == antes + 1


@pytest.mark.django_db
def test_apagar_plano_tambem_invalida() -> None:
    capabilities_for(None)  # aquece o snapshot
    assert cache.get(SNAPSHOT_KEY) is not None

    Plan.objects.filter(slug=PLAN_SUBSCRIBER).delete()

    assert cache.get(SNAPSHOT_KEY) is None


# --------------------------------------------------------------------------------------
# Validação de consequência (SPEC-018 §Sobre o limite do admin)
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_duracao_minima_acima_da_maxima_e_recusada() -> None:
    plano = Plan.objects.get(slug=PLAN_FREE)
    plano.session_min_s = 120
    plano.session_max_s = 30

    with pytest.raises(ValidationError):
        plano.full_clean()


@pytest.mark.django_db
def test_preparacao_absurda_e_recusada() -> None:
    plano = Plan.objects.get(slug=PLAN_FREE)
    plano.countdown_max_s = 120

    with pytest.raises(ValidationError):
        plano.full_clean()


@pytest.mark.django_db
def test_default_de_reps_fora_da_propria_faixa_e_recusado() -> None:
    config = SiteConfig.objects.get(pk=1)
    config.reps_default = 99

    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_min_maturity_nao_oferece_beta() -> None:
    """`beta` é ferramenta de dev (`is_admin`), nunca capacidade de plano (SPEC-020)."""
    valores = [v for v, _ in Plan._meta.get_field("min_maturity").choices]

    assert "beta" not in valores


# --------------------------------------------------------------------------------------
# A admissão de verdade — a ligação que a T-073 promete
#
# `tests/test_sessions.py::admissao_falsa` troca `create_session` por um lambda que descarta
# os kwargs, então nada lá provaria que a view resolve capacidade e a repassa. Estes exercitam
# `POST /api/sessions` com o Redis dublado mas os argumentos reais.
# --------------------------------------------------------------------------------------


class RedisFalso:
    """Só o que a admissão usa: hash da sessão e o contador diário."""

    def __init__(self) -> None:
        self.contadores: dict[str, int] = {}

    def hset(self, key: str, mapping: dict) -> None: ...
    def expire(self, key: str, ttl: int) -> None: ...

    def get(self, key: str):
        return self.contadores.get(key)

    def incr(self, key: str) -> int:
        self.contadores[key] = self.contadores.get(key, 0) + 1
        return self.contadores[key]


@pytest.fixture
def admissao(monkeypatch):
    from workers.shared.bus import InMemoryBus

    redis = RedisFalso()
    barramento = InMemoryBus()
    falso = type("B", (), {"client": redis, "publish": barramento.publish})()
    monkeypatch.setattr("api.views.bus", lambda: falso)
    monkeypatch.setattr("api.sessions.bus", lambda: falso)
    monkeypatch.setattr("api.views.create_session", _create_session_com_bus(barramento, redis))
    return redis


def _create_session_com_bus(barramento, redis):
    from api.sessions import create_session

    def _criar(pedido, **kwargs):
        kwargs.setdefault("redis_client", redis)
        kwargs.setdefault("event_bus", barramento)
        return create_session(pedido, **kwargs)

    return _criar


@pytest.mark.django_db
def test_admissao_usa_a_quota_do_plano_anon(client, admissao) -> None:
    """Critério 1 da spec no caminho que importa: painel muda o limite, a recusa muda junto."""
    Plan.objects.filter(slug=PLAN_ANON).update(daily_sessions=1)
    Plan.objects.get(slug=PLAN_ANON).save()  # dispara a invalidação

    corpo = {"exercise": "jumping_jack", "requested_mode": "edge"}
    primeira = client.post("/api/sessions", data=corpo, content_type="application/json")
    assert primeira.status_code == 201
    aparelho = primeira.json()["device_id"]
    assert primeira.json()["quota"]["limit"] == 1

    segunda = client.post(
        "/api/sessions",
        data=corpo,
        content_type="application/json",
        headers={quota.DEVICE_HEADER: aparelho},
    )

    assert segunda.status_code == 429
    assert segunda.json()["code"] == "trial_exhausted"


@pytest.mark.django_db
def test_plano_ilimitado_nao_gasta_contador(client, admissao) -> None:
    """O `free` de hoje é 0 = ilimitado; o anônimo com 0 tem que se comportar igual."""
    Plan.objects.filter(slug=PLAN_ANON).update(daily_sessions=0)
    Plan.objects.get(slug=PLAN_ANON).save()

    corpo = {"exercise": "jumping_jack", "requested_mode": "edge"}
    for _ in range(5):
        resposta = client.post("/api/sessions", data=corpo, content_type="application/json")
        assert resposta.status_code == 201

    assert admissao.contadores == {}


@pytest.mark.django_db
def test_duracao_do_ticket_vem_do_plano(client, admissao) -> None:
    resposta = client.post(
        "/api/sessions",
        data={"exercise": "jumping_jack", "requested_mode": "edge"},
        content_type="application/json",
    )

    # Continua 30 s — é o ponto da task: a origem do número mudou, o número não.
    assert resposta.json()["duration_s"] == DEFAULT_DURATION_S

    Plan.objects.filter(slug=PLAN_ANON).update(session_min_s=45, session_max_s=45)
    Plan.objects.get(slug=PLAN_ANON).save()
    SiteConfig.objects.filter(pk=1).update(default_duration_s=45)
    SiteConfig.objects.get(pk=1).save()

    depois = client.post(
        "/api/sessions",
        data={"exercise": "jumping_jack", "requested_mode": "edge"},
        content_type="application/json",
    )

    assert depois.json()["duration_s"] == 45


@pytest.mark.django_db
def test_plano_sem_cloud_recebe_denied_cloud(client, admissao) -> None:
    """A trava é de plano e não de vaga — e a resposta é a mesma, de propósito."""
    from api.sessions import DENIED_CLOUD

    Plan.objects.filter(slug=PLAN_ANON).update(allow_cloud=False)
    Plan.objects.get(slug=PLAN_ANON).save()

    resposta = client.post(
        "/api/sessions",
        data={"exercise": "jumping_jack", "requested_mode": "cloud"},
        content_type="application/json",
    )

    assert resposta.json()["mode"] == DENIED_CLOUD


def test_capabilities_e_congelado() -> None:
    caps = capabilities_for(None)

    with pytest.raises(AttributeError):
        caps.daily_sessions = 999  # type: ignore[misc]

    assert isinstance(caps, Capabilities)
