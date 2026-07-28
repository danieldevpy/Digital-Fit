"""Ciclo de sessão: `POST /api/sessions`, TTL e timer autoritativo (T-011 / SPEC-009)."""

import pytest
from api.sessions import (
    DEFAULT_DURATION_S,
    DENIED_CLOUD,
    SessionRequest,
    create_session,
    session_key,
)
from api.tokens import DEFAULT_TTL_S, InvalidToken, verify_token

from tests.synthetic_keypoints import jumping_jack_poses, sequence, session_poses, still_poses
from workers.analysis_worker.router import (
    NO_DATA_TIMEOUT_MS,
    TTL_MARGIN_MS,
    AnalysisRouter,
    SessionState,
)
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    EventType,
    Mode,
    PoseFrame,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    Source,
    Stream,
    make_envelope,
)

AGORA = 1_722_100_000


class FakeRedis:
    """Só o que `create_session` usa: `hset` e `expire`."""

    def __init__(self) -> None:
        self.hashes: dict[str, dict] = {}
        self.ttls: dict[str, int] = {}

    def hset(self, key: str, mapping: dict) -> None:
        self.hashes.setdefault(key, {}).update(mapping)

    def expire(self, key: str, ttl: int) -> None:
        self.ttls[key] = ttl


def criar(**kwargs):
    """Cria a sessão com Redis e barramento falsos."""
    pedido = kwargs.pop("pedido", None) or SessionRequest(
        exercise="jumping_jack", requested_mode=Mode.EDGE
    )
    redis = FakeRedis()
    bus = InMemoryBus()
    ticket = create_session(pedido, now=AGORA, redis_client=redis, event_bus=bus, **kwargs)
    return ticket, redis, bus


# --------------------------------------------------------------------------------------
# POST /api/sessions
# --------------------------------------------------------------------------------------


def test_sessao_nasce_com_ticket_completo() -> None:
    ticket, _, _ = criar()

    assert ticket.session_id
    assert ticket.mode == Mode.EDGE.value
    assert ticket.exercise == "jumping_jack"
    assert ticket.duration_s == DEFAULT_DURATION_S
    assert ticket.expires_at == AGORA + DEFAULT_TTL_S
    assert ticket.session_id in ticket.ws_url
    assert ticket.token in ticket.ws_url


def test_token_do_ticket_vale_para_a_sessao_do_ticket() -> None:
    ticket, _, _ = criar()

    assert verify_token(ticket.session_id, ticket.token, now=AGORA) == ticket.expires_at
    with pytest.raises(InvalidToken):
        verify_token("outra-sessao", ticket.token, now=AGORA)


def test_token_expira_com_o_ttl_de_45s() -> None:
    """SPEC-009: TTL de 45 s = 30 s de sessão + margem."""
    ticket, _, _ = criar()

    assert DEFAULT_TTL_S == 45
    with pytest.raises(InvalidToken, match="expirado"):
        verify_token(ticket.session_id, ticket.token, now=AGORA + DEFAULT_TTL_S)


def test_registro_em_redis_tem_ttl() -> None:
    ticket, redis, _ = criar()

    registro = redis.hashes[session_key(ticket.session_id)]
    assert registro["state"] == "created"
    assert registro["exercise"] == "jumping_jack"
    assert registro["duration_s"] == DEFAULT_DURATION_S
    assert redis.ttls[session_key(ticket.session_id)] == DEFAULT_TTL_S


def test_session_started_e_publicado_no_stream_de_entrada_da_analise() -> None:
    """Sem isso, o worker não saberia o exercício nem a duração da sessão."""
    ticket, _, bus = criar()

    entrada = [
        envelope
        for envelope in bus.published_in(Stream.POSE_FRAMES)
        if envelope.type is EventType.SESSION_STARTED
    ]
    assert len(entrada) == 1
    envelope = entrada[0]
    assert envelope.session_id == ticket.session_id
    dados = SessionStarted.from_data(envelope.data)
    assert dados.exercise == "jumping_jack"
    assert dados.duration_s == DEFAULT_DURATION_S
    assert dados.mode is Mode.EDGE


def test_session_started_tambem_vai_para_a_saida_da_analise() -> None:
    """O report-builder (SPEC-010) lê só `events.analysis`.

    Sem esta segunda publicação, o relatório não teria como saber de que exercício a sessão
    foi — e teria de perguntar ao Redis, quebrando a propriedade da spec: relatório derivável
    100% por replay dos eventos.
    """
    ticket, _, bus = criar()

    saida = [
        envelope
        for envelope in bus.published_in(Stream.EVENTS_ANALYSIS)
        if envelope.type is EventType.SESSION_STARTED
    ]
    assert len(saida) == 1
    assert saida[0].session_id == ticket.session_id
    assert SessionStarted.from_data(saida[0].data).exercise == "jumping_jack"


def test_probe_result_vira_session_capability() -> None:
    pedido = SessionRequest(
        exercise="jumping_jack",
        requested_mode=Mode.EDGE,
        probe={"fps": 18.5, "webgl": True, "ua": "Firefox/141"},
    )

    _, _, bus = criar(pedido=pedido)

    capability = bus.published_of(EventType.SESSION_CAPABILITY)
    assert len(capability) == 1
    assert capability[0].data["probe_fps"] == pytest.approx(18.5)


def test_probe_result_no_formato_do_contrato_tambem_vale() -> None:
    """O cliente manda o payload de `session.capability` inteiro, com `probe_fps`."""
    pedido = SessionRequest(
        exercise="jumping_jack",
        requested_mode=Mode.EDGE,
        probe={"mode": "edge", "probe_fps": 21.0, "webgl": True, "ua": "Chrome/141"},
    )

    _, _, bus = criar(pedido=pedido)

    capability = bus.published_of(EventType.SESSION_CAPABILITY)
    assert capability[0].data["probe_fps"] == pytest.approx(21.0)


def test_sem_probe_nao_ha_capability() -> None:
    _, _, bus = criar()

    assert bus.published_of(EventType.SESSION_CAPABILITY) == []


class SemaforoFalso:
    """Semáforo com resposta fixa — o comportamento real tem testes próprios em test_slots."""

    def __init__(self, *, concede: bool) -> None:
        self.concede = concede
        self.pedidos: list[str] = []

    def acquire(self, session_id: str, *, ttl_ms: int, now_ms: int | None = None) -> bool:
        del ttl_ms, now_ms
        self.pedidos.append(session_id)
        return self.concede


def test_cloud_com_vaga_e_admitido() -> None:
    """Desde a T-017 cloud é atendido quando há slot (SPEC-009)."""
    pedido = SessionRequest(exercise="jumping_jack", requested_mode=Mode.CLOUD)
    semaforo = SemaforoFalso(concede=True)

    ticket, redis, bus = criar(pedido=pedido, slots=semaforo)

    assert ticket.mode == Mode.CLOUD.value
    assert semaforo.pedidos == [ticket.session_id]
    assert redis.hashes, "sessao admitida nasce no Redis"
    assert bus.published, "sessao admitida publica session.started"


def test_cloud_sem_vaga_e_negado() -> None:
    """Sem slot livre: `denied_cloud`, e a sessão não chega a existir (SPEC-009)."""
    pedido = SessionRequest(exercise="jumping_jack", requested_mode=Mode.CLOUD)

    ticket, redis, bus = criar(pedido=pedido, slots=SemaforoFalso(concede=False))

    assert ticket.mode == DENIED_CLOUD
    assert redis.hashes == {}, "sessao negada nao nasce"
    assert bus.published == [], "sessao negada nao gera evento"


def test_edge_nunca_consulta_o_semaforo() -> None:
    # Edge não tem limite na Fase Inicial. Passar pelo semáforo aqui gastaria uma ida ao
    # Redis por sessão e, pior, faria o modo padrão do produto depender da capacidade cloud.
    semaforo = SemaforoFalso(concede=False)

    ticket, _, _ = criar(slots=semaforo)

    assert ticket.mode == Mode.EDGE.value
    assert semaforo.pedidos == []


def test_cada_sessao_tem_id_e_token_proprios() -> None:
    primeiro, _, _ = criar()
    segundo, _, _ = criar()

    assert primeiro.session_id != segundo.session_id
    assert primeiro.token != segundo.token


# --------------------------------------------------------------------------------------
# Validação do corpo
# --------------------------------------------------------------------------------------


def test_corpo_vazio_assume_polichinelo_no_modo_edge() -> None:
    pedido = SessionRequest.parse({})

    assert pedido.exercise == "jumping_jack"
    assert pedido.requested_mode is Mode.EDGE


def test_exercicio_desconhecido_e_recusado() -> None:
    with pytest.raises(ValueError, match="exercicio desconhecido"):
        SessionRequest.parse({"exercise": "levitacao"})


def test_modo_invalido_e_recusado() -> None:
    with pytest.raises(ValueError, match="requested_mode invalido"):
        SessionRequest.parse({"requested_mode": "telepatia"})


def test_probe_result_precisa_ser_objeto() -> None:
    with pytest.raises(ValueError, match="probe_result"):
        SessionRequest.parse({"probe_result": "15fps"})


def test_corpo_que_nao_e_objeto_e_recusado() -> None:
    with pytest.raises(ValueError, match="objeto JSON"):
        SessionRequest.parse(["jumping_jack"])


# --------------------------------------------------------------------------------------
# Endpoint HTTP
# --------------------------------------------------------------------------------------


def test_endpoint_cria_sessao(client, monkeypatch) -> None:
    redis, bus = FakeRedis(), InMemoryBus()
    # Patch em `api.views.create_session`, não em `api.sessions.create_session`: a view faz
    # `from api.sessions import create_session`, então a referência dela é resolvida no import.
    # Patchar o módulo de origem só funcionava quando a view ainda não tinha sido importada —
    # ou seja, dependia da ordem dos arquivos de teste.
    monkeypatch.setattr(
        "api.views.create_session",
        lambda pedido, **kwargs: create_session(pedido, redis_client=redis, event_bus=bus),
    )

    resposta = client.post(
        "/api/sessions",
        data={"exercise": "jumping_jack", "requested_mode": "edge"},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["mode"] == "edge"
    assert corpo["duration_s"] == DEFAULT_DURATION_S
    assert corpo["ws_url"].startswith("ws://")
    assert verify_token(corpo["session_id"], corpo["token"])


def test_endpoint_recusa_exercicio_desconhecido(client) -> None:
    resposta = client.post(
        "/api/sessions", data={"exercise": "levitacao"}, content_type="application/json"
    )

    assert resposta.status_code == 400
    assert "desconhecido" in resposta.json()["detail"]


def test_endpoint_responde_503_se_o_redis_estiver_fora(client, monkeypatch) -> None:
    def explodir(*args, **kwargs):
        raise ConnectionError("Redis inacessivel")

    monkeypatch.setattr("api.views.create_session", explodir)

    resposta = client.post("/api/sessions", data={}, content_type="application/json")

    assert resposta.status_code == 503
    assert "nao foi possivel criar a sessao" in resposta.json()["detail"]


def test_endpoint_aceita_apenas_post(client) -> None:
    assert client.get("/api/sessions").status_code == 405


# --------------------------------------------------------------------------------------
# Timer autoritativo no worker (SPEC-009)
# --------------------------------------------------------------------------------------


def estado(**kwargs) -> SessionState:
    base = {"session_id": "s1", "duration_s": 30, "opened_wall_ms": 1_000_000}
    return SessionState(**{**base, **kwargs})


def test_sessao_termina_quando_os_30s_correm() -> None:
    """Os 30 s correm da CALIBRAÇÃO, não do primeiro frame (T-019 / SPEC-004).

    O countdown é preparação; cobrá-lo do treino encurtaria a sessão de quem demora a se
    posicionar — e quem demora é exatamente quem mais precisa dos 30 s inteiros.
    """
    sessao = estado(
        first_frame_wall_ms=1_000_000,
        exercise_started_wall_ms=1_000_000,
        last_frame_wall_ms=1_029_000,
    )

    assert sessao.expiry_reason(1_029_999) is None
    assert sessao.expiry_reason(1_030_000) is SessionEndReason.COMPLETED


def test_o_countdown_nao_e_descontado_dos_30s() -> None:
    # Dois segundos entre o primeiro frame e a calibração: a sessão ainda tem de durar 30 s
    # DEPOIS de calibrada, terminando em 1_032_000 e não em 1_030_000.
    sessao = estado(
        first_frame_wall_ms=1_000_000,
        exercise_started_wall_ms=1_002_000,
        last_frame_wall_ms=1_031_000,
    )

    assert sessao.expiry_reason(1_030_000) is None
    assert sessao.expiry_reason(1_032_000) is SessionEndReason.COMPLETED


def test_sessao_que_nunca_calibra_morre_pelo_teto_de_vida() -> None:
    """Sem este teto, calibração que nunca fecha deixa a sessão presa para sempre.

    `no_data` não salva: ele exige que os frames PAREM, e uma pessoa no quadro em frames
    degradados continua mandando frames o tempo todo.
    """
    sessao = estado(first_frame_wall_ms=1_000_000, last_frame_wall_ms=1_040_000)

    assert sessao.expiry_reason(1_040_000) is None
    assert sessao.expiry_reason(1_045_000) is SessionEndReason.TIMEOUT


def test_sessao_sem_frame_nenhum_por_10s_e_abortada() -> None:
    """SPEC-009, critério 4."""
    sessao = estado()

    assert sessao.expiry_reason(1_000_000 + NO_DATA_TIMEOUT_MS - 1) is None
    assert sessao.expiry_reason(1_000_000 + NO_DATA_TIMEOUT_MS) is SessionEndReason.NO_DATA


def test_frames_que_param_no_meio_tambem_dao_no_data() -> None:
    sessao = estado(first_frame_wall_ms=1_000_000, last_frame_wall_ms=1_005_000)

    assert sessao.expiry_reason(1_005_000 + NO_DATA_TIMEOUT_MS) is SessionEndReason.NO_DATA


def test_duracao_vence_antes_do_ttl() -> None:
    """O TTL de 45 s protege token e registro; quem fecha a sessão é a duração ou a falta de dados.

    Com frames chegando, a regra de duração dispara muito antes do TTL — por isso `timeout` não
    é emitido pelo worker na Fase 0.
    """
    sessao = estado(
        duration_s=30,
        first_frame_wall_ms=1_000_000,
        exercise_started_wall_ms=1_000_000,
        last_frame_wall_ms=1_029_000,
    )

    assert sessao.expiry_reason(1_030_000) is SessionEndReason.COMPLETED
    assert TTL_MARGIN_MS == 15_000  # 30 s + 15 s = TTL de 45 s do token e do registro


def test_tick_fecha_a_sessao_e_publica_o_total_de_reps() -> None:
    router = AnalysisRouter()
    abertura = make_envelope(
        SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
        session_id="s1",
        ts=1_722_100_000_000,
        seq=0,
        source=Source.SYSTEM,
    )
    router.handle(abertura, now_wall_ms=1_000_000)
    for frame in sequence(session_poses(jumping_jack_poses(3))):
        router.handle(
            make_envelope(
                PoseFrame(landmarks=[list(p) for p in frame.landmarks]),
                session_id="s1",
                ts=frame.ts,
                seq=frame.seq,
                source=Source.EDGE,
            ),
            now_wall_ms=1_000_000 + frame.seq * 66,
        )

    saidas = router.tick(now_wall_ms=1_031_000)

    assert len(saidas) == 1
    payload = SessionCompleted.from_data(saidas[0].data)
    assert payload.reason is SessionEndReason.COMPLETED
    assert payload.rep_count == 3
    assert router.sessions == {}


def test_tick_nao_fecha_sessao_dentro_do_prazo() -> None:
    router = AnalysisRouter()
    router.handle(
        make_envelope(
            SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
            session_id="s1",
            ts=1_722_100_000_000,
            seq=0,
            source=Source.SYSTEM,
        ),
        now_wall_ms=1_000_000,
    )
    router.handle(
        make_envelope(
            PoseFrame(landmarks=[list(p) for p in sequence(still_poses(1))[0].landmarks]),
            session_id="s1",
            ts=1_722_100_000_100,
            seq=1,
            source=Source.EDGE,
        ),
        now_wall_ms=1_000_100,
    )

    assert router.tick(now_wall_ms=1_005_000) == []
    assert "s1" in router.sessions


def test_worker_publica_o_fim_por_timer_no_stream_de_saida() -> None:
    from workers.analysis_worker.main import run

    bus = InMemoryBus()
    router = AnalysisRouter()
    router.handle(
        make_envelope(
            SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
            session_id="s1",
            ts=1_722_100_000_000,
            seq=0,
            source=Source.SYSTEM,
        ),
        now_wall_ms=0,  # abriu "muito tempo atras" em relogio de parede
    )

    run(bus, consumer="teste", router=router, max_batches=1)

    fim = bus.published_of(EventType.SESSION_COMPLETED)
    assert len(fim) == 1
    assert fim[0].stream is Stream.EVENTS_ANALYSIS
    assert SessionCompleted.from_data(fim[0].data).reason is SessionEndReason.NO_DATA


def test_timer_usa_relogio_do_servidor_nao_do_cliente() -> None:
    """Celular com relógio adiantado não pode encurtar nem esticar a sessão."""
    router = AnalysisRouter()
    router.handle(
        make_envelope(
            SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
            session_id="s1",
            ts=1_722_100_000_000,
            seq=0,
            source=Source.SYSTEM,
        ),
        now_wall_ms=1_000_000,
    )
    # Cliente jura que já passaram horas (`ts` no futuro), mas só se passaram 100 ms de verdade.
    router.handle(
        make_envelope(
            PoseFrame(landmarks=[list(p) for p in sequence(still_poses(1))[0].landmarks]),
            session_id="s1",
            ts=1_722_200_000_000,
            seq=1,
            source=Source.EDGE,
        ),
        now_wall_ms=1_000_100,
    )

    assert router.tick(now_wall_ms=1_000_200) == []
    assert "s1" in router.sessions
