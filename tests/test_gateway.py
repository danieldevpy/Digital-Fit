"""Testes do gateway WebSocket e do token de sessão (T-005 / SPEC-002 e SPEC-009).

O WS é exercido de verdade pelo `WebsocketCommunicator` do Channels, com channel layer em
memória e um barramento falso no lugar do Redis.
"""

import asyncio

import pytest
from api.tokens import DEFAULT_TTL_S, InvalidToken, issue_token, verify_token
from channels.layers import channel_layers
from channels.testing import WebsocketCommunicator
from gateway.consumers import (
    CLIENT_INGEST_TYPES,
    CLOSE_BAD_SESSION,
    CLOSE_BAD_TOKEN,
    INGEST_BUFFER,
    SessionConsumer,
    session_group,
)
from gateway.relay import GROUP, AnalysisRelay

from tests.synthetic_keypoints import jumping_jack_poses, sequence
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    Envelope,
    EventType,
    Mode,
    PoseFrame,
    RepDetected,
    SessionCapability,
    SessionCompleted,
    SessionEndReason,
    Source,
    Stream,
    decode_envelope,
    encode_envelope,
    make_envelope,
)

SESSAO = "3f2b9c4e-0000-4000-8000-000000000001"


@pytest.fixture(autouse=True)
def canal_em_memoria(settings):
    """Channel layer em memória: nada de Redis no pytest."""
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    channel_layers.backends = {}  # descarta camadas ja instanciadas
    yield
    channel_layers.backends = {}


@pytest.fixture
def bus_falso(monkeypatch) -> InMemoryBus:
    """Substitui o Redis do gateway por um barramento em memória."""
    bus = InMemoryBus()
    monkeypatch.setattr("gateway.relay.bus", lambda: bus)
    return bus


async def conectar(token: str | None = None, session_id: str = SESSAO):
    """Abre o WS da sessão e devolve `(communicator, conectou)`."""
    if token is None:
        token = issue_token(session_id)
    comunicador = WebsocketCommunicator(
        SessionConsumer.as_asgi(), f"/ws/session/{session_id}?token={token}"
    )
    comunicador.scope["url_route"] = {"kwargs": {"session_id": session_id}}
    conectou, _ = await comunicador.connect()
    return comunicador, conectou


def envelope_pose(frame, session_id: str = SESSAO) -> Envelope:
    return make_envelope(
        PoseFrame(landmarks=[list(ponto) for ponto in frame.landmarks]),
        session_id=session_id,
        ts=frame.ts,
        seq=frame.seq,
        source=Source.EDGE,
    )


# --------------------------------------------------------------------------------------
# Token de sessão (SPEC-009)
# --------------------------------------------------------------------------------------


def test_token_valido_e_aceito() -> None:
    token = issue_token(SESSAO)

    assert verify_token(SESSAO, token) > 0


def test_token_expira_com_o_ttl_da_sessao() -> None:
    agora = 1_722_100_000
    token = issue_token(SESSAO, now=agora)

    assert verify_token(SESSAO, token, now=agora + DEFAULT_TTL_S - 1)
    with pytest.raises(InvalidToken, match="expirado"):
        verify_token(SESSAO, token, now=agora + DEFAULT_TTL_S)


def test_token_de_outra_sessao_nao_serve() -> None:
    """Sem isso, um token válido abriria o WS de qualquer sessão."""
    token = issue_token(SESSAO)

    with pytest.raises(InvalidToken, match="assinatura"):
        verify_token("3f2b9c4e-0000-4000-8000-000000000002", token)


@pytest.mark.parametrize("token", ["", "lixo", "123", "123.", ".abc", "abc.def"])
def test_token_malformado_e_recusado(token: str) -> None:
    with pytest.raises(InvalidToken):
        verify_token(SESSAO, token)


def test_assinatura_adulterada_e_recusada() -> None:
    expira, _, assinatura = issue_token(SESSAO).partition(".")
    adulterado = f"{expira}.{'A' * len(assinatura)}"

    with pytest.raises(InvalidToken, match="assinatura"):
        verify_token(SESSAO, adulterado)


def test_validade_esticada_invalida_a_assinatura() -> None:
    """Empurrar o `expires_at` para o futuro quebra o HMAC — é o ponto do token assinado."""
    expira, _, assinatura = issue_token(SESSAO).partition(".")
    esticado = f"{int(expira) + 3600}.{assinatura}"

    with pytest.raises(InvalidToken, match="assinatura"):
        verify_token(SESSAO, esticado)


# --------------------------------------------------------------------------------------
# Conexão
# --------------------------------------------------------------------------------------


async def test_ws_abre_com_token_valido(bus_falso) -> None:
    comunicador, conectou = await conectar()

    assert conectou
    await comunicador.disconnect()


async def test_ws_recusa_token_invalido(bus_falso) -> None:
    comunicador = WebsocketCommunicator(
        SessionConsumer.as_asgi(), f"/ws/session/{SESSAO}?token=lixo"
    )
    comunicador.scope["url_route"] = {"kwargs": {"session_id": SESSAO}}

    conectou, codigo = await comunicador.connect()

    assert not conectou
    assert codigo == CLOSE_BAD_TOKEN


async def test_ws_recusa_conexao_sem_token(bus_falso) -> None:
    comunicador = WebsocketCommunicator(SessionConsumer.as_asgi(), f"/ws/session/{SESSAO}")
    comunicador.scope["url_route"] = {"kwargs": {"session_id": SESSAO}}

    conectou, codigo = await comunicador.connect()

    assert not conectou
    assert codigo == CLOSE_BAD_TOKEN


async def test_ws_recusa_token_expirado(bus_falso) -> None:
    vencido = issue_token(SESSAO, ttl_s=-10)

    _, conectou = await conectar(token=vencido)

    assert not conectou


# --------------------------------------------------------------------------------------
# Ingestão: cliente → stream
# --------------------------------------------------------------------------------------


async def test_pose_frame_do_cliente_vai_para_pose_frames(bus_falso) -> None:
    comunicador, _ = await conectar()
    frame = sequence(jumping_jack_poses(1))[0]

    await comunicador.send_to(bytes_data=encode_envelope(envelope_pose(frame)))
    await asyncio.sleep(0.15)
    await comunicador.disconnect()

    assert len(bus_falso.published) == 1
    publicado = bus_falso.published[0]
    assert publicado.type is EventType.POSE_FRAME
    assert publicado.session_id == SESSAO
    assert PoseFrame.from_data(publicado.data).landmarks[0] == pytest.approx(
        [float(v) for v in frame.landmarks[0]]
    )


async def test_frame_raw_do_cliente_vai_para_frames_raw(bus_falso) -> None:
    """Modo cloud (T-015): imagem não pode cair no stream de entrada da análise.

    Se `frame.raw` for parar em `pose.frames`, o analysis-worker recebe JPEG onde espera 33
    landmarks — e o erro aparece longe daqui, dentro da FSM.
    """
    from workers.shared.events import FrameRaw

    comunicador, _ = await conectar()
    envelope = make_envelope(
        FrameRaw(jpeg=b"\xff\xd8\xff\xe0" + b"\x00" * 64, width=320, height=240),
        session_id=SESSAO,
        ts=1_722_100_000_000,
        seq=0,
        source=Source.EDGE,
    )

    await comunicador.send_to(bytes_data=encode_envelope(envelope))
    await asyncio.sleep(0.15)
    await comunicador.disconnect()

    assert [e.type for e in bus_falso.published_in(Stream.FRAMES_RAW)] == [EventType.FRAME_RAW]
    assert bus_falso.published_in(Stream.POSE_FRAMES) == []


async def test_capability_do_cliente_tambem_e_publicada(bus_falso) -> None:
    comunicador, _ = await conectar()
    envelope = make_envelope(
        SessionCapability(mode=Mode.EDGE, probe_fps=17.0, webgl=True, ua="Firefox"),
        session_id=SESSAO,
        ts=1_722_100_000_000,
        seq=0,
        source=Source.EDGE,
    )

    await comunicador.send_to(bytes_data=encode_envelope(envelope))
    await asyncio.sleep(0.15)
    await comunicador.disconnect()

    assert bus_falso.published[0].type is EventType.SESSION_CAPABILITY


async def test_cliente_pode_encerrar_a_propria_sessao(bus_falso) -> None:
    comunicador, _ = await conectar()
    envelope = make_envelope(
        SessionCompleted(reason=SessionEndReason.ABORTED),
        session_id=SESSAO,
        ts=1_722_100_005_000,
        seq=1,
        source=Source.EDGE,
    )

    await comunicador.send_to(bytes_data=encode_envelope(envelope))
    await asyncio.sleep(0.15)
    await comunicador.disconnect()

    assert bus_falso.published[0].type is EventType.SESSION_COMPLETED


async def test_cliente_nao_pode_injetar_rep_detected(bus_falso) -> None:
    """A contagem nasce no worker: cliente que publica `rep.detected` invalidaria tudo."""
    from workers.shared.events import Phase

    comunicador, _ = await conectar()
    falso = make_envelope(
        RepDetected(rep_count=999, phase=Phase.REST, duration_ms=1),
        session_id=SESSAO,
        ts=1_722_100_001_000,
        seq=1,
        source=Source.EDGE,
    )

    await comunicador.send_to(bytes_data=encode_envelope(falso))
    await asyncio.sleep(0.15)
    await comunicador.disconnect()

    assert bus_falso.published == []


async def test_envelope_de_outra_sessao_fecha_a_conexao(bus_falso) -> None:
    comunicador, _ = await conectar()
    intruso = envelope_pose(
        sequence(jumping_jack_poses(1))[0], session_id="3f2b9c4e-0000-4000-8000-000000000002"
    )

    await comunicador.send_to(bytes_data=encode_envelope(intruso))
    saida = await comunicador.receive_output(timeout=1)

    assert saida["type"] == "websocket.close"
    assert saida["code"] == CLOSE_BAD_SESSION
    assert bus_falso.published == []


async def test_envelope_corrompido_nao_derruba_a_conexao(bus_falso) -> None:
    """SPEC-002, critério 3."""
    comunicador, _ = await conectar()

    await comunicador.send_to(bytes_data=b"\x93\x01\x02\x03")
    await asyncio.sleep(0.1)
    frame = sequence(jumping_jack_poses(1))[0]
    await comunicador.send_to(bytes_data=encode_envelope(envelope_pose(frame)))
    await asyncio.sleep(0.15)

    assert len(bus_falso.published) == 1, "a conexao segue viva e publicando"
    await comunicador.disconnect()


async def test_texto_no_ws_e_ignorado(bus_falso) -> None:
    comunicador, _ = await conectar()

    await comunicador.send_to(text_data='{"type": "pose.frame"}')
    await asyncio.sleep(0.1)

    assert bus_falso.published == []
    await comunicador.disconnect()


async def test_backpressure_descarta_o_frame_mais_antigo(bus_falso, monkeypatch) -> None:
    """SPEC-002: buffer de 3 frames; frame novo vale mais que frame velho."""
    import gateway.consumers as consumers

    lentidao = {"ativa": True}

    def publicar_devagar(envelope, stream=None):
        import time

        while lentidao["ativa"]:
            time.sleep(0.01)
        return bus_falso.publish(envelope, stream=stream)

    monkeypatch.setattr(consumers, "publish_envelope", publicar_devagar, raising=False)
    monkeypatch.setattr("gateway.relay.publish_envelope", publicar_devagar)

    comunicador, _ = await conectar()
    frames = sequence(jumping_jack_poses(2))[:20]
    for frame in frames:
        await comunicador.send_to(bytes_data=encode_envelope(envelope_pose(frame)))
    await asyncio.sleep(0.2)
    lentidao["ativa"] = False
    await asyncio.sleep(0.2)
    await comunicador.disconnect()

    # Nunca mais de 3 frames em espera ⇒ o resto foi descartado, e não acumulado.
    assert len(bus_falso.published) <= INGEST_BUFFER + 2
    assert INGEST_BUFFER == 3


def test_tudo_que_o_cliente_publica_tem_consumidor() -> None:
    """Nada que o cliente envia pode cair num stream que ninguém lê.

    Até a T-015 valia o invariante mais simples "ingestão ⊆ entrada da análise". `frame.raw`
    quebrou isso de propósito: ele não vai para a análise, vai para o `pose-worker`, que o
    transforma em `pose.frame`. O invariante que continua verdadeiro — e que é o que
    realmente importa — é que todo tipo aceito tem um consumidor declarado.
    """
    from workers.shared.events import ANALYSIS_INPUT_TYPES, CONSUMER_GROUPS, STREAM_FOR_TYPE

    for tipo in CLIENT_INGEST_TYPES:
        if tipo in ANALYSIS_INPUT_TYPES:
            continue
        assert tipo is EventType.FRAME_RAW, f"{tipo} entra pelo cliente e ninguem consome"
        assert CONSUMER_GROUPS[STREAM_FOR_TYPE[tipo]]  # `pose-workers` (T-016)


# --------------------------------------------------------------------------------------
# Saída: events.analysis → cliente
# --------------------------------------------------------------------------------------


async def test_relay_empurra_rep_detected_ao_cliente(bus_falso) -> None:
    from workers.shared.events import Phase

    comunicador, _ = await conectar()
    rep = make_envelope(
        RepDetected(rep_count=3, phase=Phase.REST, duration_ms=900),
        session_id=SESSAO,
        ts=1_722_100_003_000,
        seq=7,
        source=Source.SYSTEM,
    )
    bus_falso.feed(Stream.EVENTS_ANALYSIS, rep)

    repassados = await _relay_once(bus_falso)
    recebido = await comunicador.receive_from(timeout=2)

    assert repassados == 1
    envelope = decode_envelope(recebido)
    assert envelope.type is EventType.REP_DETECTED
    assert RepDetected.from_data(envelope.data).rep_count == 3
    await comunicador.disconnect()


async def test_relay_nao_empurra_pose_frame_de_volta(bus_falso) -> None:
    comunicador, _ = await conectar()
    bus_falso.feed(Stream.EVENTS_ANALYSIS, envelope_pose(sequence(jumping_jack_poses(1))[0]))

    await _relay_once(bus_falso)

    assert await comunicador.receive_nothing(timeout=0.3)
    await comunicador.disconnect()


async def test_relay_nao_empurra_quality_signal(bus_falso) -> None:
    """`quality.signal` é insumo do feedback engine; o HUD vê `feedback.issued`."""
    from workers.shared.events import Code, QualitySignal

    comunicador, _ = await conectar()
    sinal = make_envelope(
        QualitySignal(code=Code.ARMS_TOO_LOW, value=95.0),
        session_id=SESSAO,
        ts=1_722_100_004_000,
        seq=8,
        source=Source.SYSTEM,
    )
    bus_falso.feed(Stream.EVENTS_ANALYSIS, sinal)

    await _relay_once(bus_falso)

    assert await comunicador.receive_nothing(timeout=0.3)
    await comunicador.disconnect()


async def test_evento_de_outra_sessao_nao_chega_neste_cliente(bus_falso) -> None:
    from workers.shared.events import Phase

    comunicador, _ = await conectar()
    de_outro = make_envelope(
        RepDetected(rep_count=1, phase=Phase.REST, duration_ms=800),
        session_id="3f2b9c4e-0000-4000-8000-000000000002",
        ts=1_722_100_002_000,
        seq=1,
        source=Source.SYSTEM,
    )
    bus_falso.feed(Stream.EVENTS_ANALYSIS, de_outro)

    await _relay_once(bus_falso)

    assert await comunicador.receive_nothing(timeout=0.3)
    await comunicador.disconnect()


async def test_relay_da_ack_em_tudo_que_le(bus_falso) -> None:
    from workers.shared.events import Phase

    for indice in range(3):
        bus_falso.feed(
            Stream.EVENTS_ANALYSIS,
            make_envelope(
                RepDetected(rep_count=indice + 1, phase=Phase.REST, duration_ms=900),
                session_id=SESSAO,
                ts=1_722_100_000_000 + indice,
                seq=indice,
                source=Source.SYSTEM,
            ),
        )

    await _relay_once(bus_falso)

    assert len(bus_falso.acked) == 3


async def test_relay_cria_o_grupo_de_consumo(bus_falso) -> None:
    await _relay_once(bus_falso)

    assert (Stream.EVENTS_ANALYSIS.value, GROUP) in bus_falso.groups


async def test_cliente_desconectado_nao_impede_o_relay(bus_falso) -> None:
    """Evento de sessão sem ninguém escutando é descartado pelo channel layer, sem erro."""
    from workers.shared.events import Phase

    bus_falso.feed(
        Stream.EVENTS_ANALYSIS,
        make_envelope(
            RepDetected(rep_count=1, phase=Phase.REST, duration_ms=900),
            session_id="sessao-sem-cliente",
            ts=1_722_100_000_000,
            seq=0,
            source=Source.SYSTEM,
        ),
    )

    assert await _relay_once(bus_falso) == 1


async def _relay_once(bus) -> int:
    """Roda um lote do relay numa thread (ele é síncrono por causa do XREADGROUP)."""
    relay = AnalysisRelay(consumer="teste")
    return await asyncio.to_thread(relay.run_once, bus)


def test_grupo_do_channel_layer_e_por_sessao() -> None:
    assert session_group(SESSAO) == f"session.{SESSAO}"
    assert session_group("outra") != session_group(SESSAO)
