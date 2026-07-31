"""O carimbo de configuração da sessão (SPEC-018 critério 8, T-075).

A cadeia inteira em um arquivo, porque é a cadeia que é a entrega: a versão nasce na resolução
da API, viaja no `session.started`, atravessa o report-builder e sai no
`GET /api/sessions/{id}/report`. Testar cada elo isolado deixaria passar exatamente o defeito
que interessa — um elo que perde o número no meio do caminho.

A propriedade que mais importa aqui não é "o número aparece", é **o número é do passado**: o
relatório tem de dizer sob qual configuração a sessão foi produzida, não sob qual configuração
o banco está agora. Um relatório que consulta o `SiteConfig` no momento da gravação parece
certo em todo teste feito no mesmo minuto, e mente sobre toda sessão de ontem.
"""

from __future__ import annotations

import pytest
from api.config import PLAN_ANON, SNAPSHOT_KEY, capabilities_for
from api.management.commands.report_builder import persist
from api.models import Plan, SessionResult, SiteConfig
from api.sessions import SessionRequest, create_session
from django.core.cache import cache

from tests.test_config import RedisFalso
from workers.report_builder.builder import ReportAccumulator
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    EventType,
    Mode,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    Source,
    Stream,
    make_envelope,
)


@pytest.fixture(autouse=True)
def _limpa_snapshot():
    cache.delete(SNAPSHOT_KEY)
    yield
    cache.delete(SNAPSHOT_KEY)


@pytest.fixture
def admissao(monkeypatch):
    """Como a `admissao` da `test_config`, mas devolvendo o barramento.

    Aqui o que se inspeciona é o evento publicado, não o contador do trial — e o
    `session.started` é o único lugar onde o carimbo existe antes do relatório.
    """
    redis = RedisFalso()
    barramento = InMemoryBus()
    falso = type("B", (), {"client": redis, "publish": barramento.publish})()
    monkeypatch.setattr("api.views.bus", lambda: falso)
    monkeypatch.setattr("api.sessions.bus", lambda: falso)

    def _criar(pedido, **kwargs):
        kwargs.setdefault("redis_client", redis)
        kwargs.setdefault("event_bus", barramento)
        return create_session(pedido, **kwargs)

    monkeypatch.setattr("api.views.create_session", _criar)
    return barramento


def versao_carimbada(barramento: InMemoryBus, session_id: str) -> int:
    """A versão que viajou no `session.started` desta sessão."""
    abertura = [
        envelope
        for envelope in barramento.published_in(Stream.EVENTS_ANALYSIS)
        if envelope.type is EventType.SESSION_STARTED and envelope.session_id == session_id
    ]
    assert len(abertura) == 1, f"esperava uma abertura para {session_id}, vi {len(abertura)}"
    return SessionStarted.from_data(abertura[0].data).config_version


def consolidar(barramento: InMemoryBus, session_id: str, *, reps: int = 12) -> None:
    """Fecha a sessão pelo caminho de verdade: acumulador puro + o `persist` do report-builder.

    Sem dublê de relatório de propósito — se o carimbo se perdesse entre o `SessionReport` e a
    coluna do Postgres, um `SessionResult.objects.create(...)` de mentira esconderia.
    """
    acumulador = ReportAccumulator()
    for envelope in barramento.published_in(Stream.EVENTS_ANALYSIS):
        if envelope.session_id == session_id:
            acumulador.push(envelope)

    fim = make_envelope(
        SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=reps),
        session_id=session_id,
        ts=1_722_100_030_000,
        seq=99,
        source=Source.SYSTEM,
    )
    relatorio = acumulador.push(fim)
    assert relatorio is not None
    persist(relatorio)


def abrir_sessao(client) -> str:
    resposta = client.post(
        "/api/sessions",
        data={"exercise": "jumping_jack", "requested_mode": "edge"},
        content_type="application/json",
    )
    assert resposta.status_code == 201, resposta.content
    return resposta.json()["session_id"]


# --------------------------------------------------------------------------------------
# O carimbo na admissão
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_admissao_carimba_a_versao_que_valia_no_momento(client, admissao) -> None:
    esperada = capabilities_for(None).config_version

    sessao = abrir_sessao(client)

    assert versao_carimbada(admissao, sessao) == esperada


@pytest.mark.django_db
def test_mudanca_no_painel_aparece_na_proxima_sessao(client, admissao) -> None:
    """A versão é o que separa "antes" de "depois" de uma edição no painel."""
    antes = abrir_sessao(client)

    plano = Plan.objects.get(slug=PLAN_ANON)
    plano.daily_sessions = 0  # ilimitado: a segunda sessão não pode esbarrar na quota
    plano.save()  # o `post_save` incrementa `SiteConfig.version`

    depois = abrir_sessao(client)

    assert versao_carimbada(admissao, depois) > versao_carimbada(admissao, antes)


def test_sem_capacidade_resolvida_o_carimbo_e_zero() -> None:
    """P2: configuração fora do ar não derruba a sessão — e não inventa uma versão.

    `create_session` sem `caps` é o caminho degradado (e o caminho dos testes que não sobem
    banco). Carimbar a versão de outra pessoa aqui seria pior do que não carimbar nada.
    """
    barramento = InMemoryBus()
    ticket = create_session(
        SessionRequest(exercise="jumping_jack", requested_mode=Mode.EDGE),
        now=1_722_100_000,
        redis_client=RedisFalso(),
        event_bus=barramento,
    )

    assert versao_carimbada(barramento, ticket.session_id) == 0


# --------------------------------------------------------------------------------------
# O relatório — critério 8 da SPEC-018
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_relatorio_diz_sob_qual_versao_a_sessao_foi_produzida(client, admissao) -> None:
    """O critério 8 inteiro, pelo caminho de verdade."""
    sessao = abrir_sessao(client)
    consolidar(admissao, sessao)

    corpo = client.get(f"/api/sessions/{sessao}/report").json()

    assert corpo["config_version"] == capabilities_for(None).config_version
    assert corpo["config_version"] == SiteConfig.objects.get(pk=1).version


@pytest.mark.django_db
def test_duas_sessoes_separadas_por_uma_edicao_no_painel(client, admissao) -> None:
    """A pergunta de suporte que este campo existe para responder.

    "Este treino rodou antes ou depois de eu mexer na configuração?" — sem o carimbo, a resposta
    dependia de cruzar o horário do `LogEntry` do painel com o `created_at` do relatório no olho.
    """
    antiga = abrir_sessao(client)

    plano = Plan.objects.get(slug=PLAN_ANON)
    plano.daily_sessions = 0
    plano.save()

    nova = abrir_sessao(client)
    consolidar(admissao, antiga)
    consolidar(admissao, nova)

    relatorios = {
        sessao: client.get(f"/api/sessions/{sessao}/report").json()["config_version"]
        for sessao in (antiga, nova)
    }

    assert relatorios[antiga] < relatorios[nova]


@pytest.mark.django_db
def test_relatorio_guarda_a_versao_da_admissao_e_nao_a_de_agora(client, admissao) -> None:
    """A propriedade que impede o relatório de mentir sobre o passado.

    A configuração muda **depois** de a sessão fechar; o relatório continua dizendo a versão sob
    a qual aquela contagem nasceu. É a mesma promessa da SPEC-010 (derivável por replay) dita em
    uma coluna: quem grava não consulta o banco de configuração, só copia o que veio no evento.
    """
    sessao = abrir_sessao(client)
    consolidar(admissao, sessao)
    da_admissao = SessionResult.objects.get(session_id=sessao).config_version

    plano = Plan.objects.get(slug=PLAN_ANON)
    plano.daily_sessions = 0
    plano.save()
    consolidar(admissao, sessao)  # reprocessamento: o mesmo `session.completed` de novo

    atual = SiteConfig.objects.get(pk=1).version
    assert atual > da_admissao
    assert client.get(f"/api/sessions/{sessao}/report").json()["config_version"] == da_admissao


@pytest.mark.django_db
def test_relatorio_de_sessao_anterior_a_task_diz_zero() -> None:
    """Linha gravada antes desta coluna existir: `0` é "não registrada", não erro."""
    SessionResult.objects.create(session_id="antiga", exercise="jumping_jack", mode="edge")

    assert SessionResult.objects.get(session_id="antiga").to_report()["config_version"] == 0
