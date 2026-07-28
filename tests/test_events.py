"""Testes do contrato de eventos (T-002 / SPEC-002).

Cobrem o que o resto do sistema assume: round-trip de serialização sem perda, rejeição de
envelope inválido (SPEC-002, critério 3) e a tabela de roteamento por tipo.
"""

import msgpack
import pytest

from workers.shared.events import (
    ANALYSIS_INPUT_TYPES,
    CLIENT_PUSH_TYPES,
    CONSUMER_GROUPS,
    LANDMARK_COUNT,
    LANDMARK_NAMES,
    PROTOCOL_VERSION,
    STREAM_FOR_TYPE,
    Code,
    Envelope,
    EventType,
    EventValidationError,
    ExercisePhase,
    FeedbackIssued,
    Landmark,
    Mode,
    Phase,
    PoseFrame,
    QualitySignal,
    RepDetected,
    SceneWarning,
    SessionCapability,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    Severity,
    Source,
    Stream,
    decode_envelope,
    encode_envelope,
    from_stream_fields,
    make_envelope,
    to_stream_fields,
)

SESSION_ID = "3f2b9c4e-0000-4000-8000-000000000001"


def landmarks(visibility: float = 0.9) -> list[list[float]]:
    """33 landmarks sintéticos — só a forma importa aqui."""
    return [[0.5, 0.5, 0.0, visibility] for _ in range(LANDMARK_COUNT)]


def envelope_de(payload, *, seq: int = 1, source: Source = Source.EDGE) -> Envelope:
    return make_envelope(payload, session_id=SESSION_ID, ts=1722100000123, seq=seq, source=source)


PAYLOADS = [
    SessionCapability(mode=Mode.EDGE, probe_fps=17.5, webgl=True, ua="Firefox/141.0"),
    SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
    PoseFrame(landmarks=landmarks()),
    PoseFrame(landmarks=landmarks(0.2), degraded=True, norm={"torso": 1.0}),
    ExercisePhase(phase=Phase.OPEN),
    RepDetected(rep_count=7, phase=Phase.CLOSED, duration_ms=820),
    QualitySignal(code=Code.ARMS_TOO_LOW, value=88.4, rep_index=7),
    QualitySignal(code=Code.LEGS_TOO_CLOSED),
    SceneWarning(code=Code.OUT_OF_FRAME, severity=Severity.WARNING, hint="afaste-se da camera"),
    FeedbackIssued(
        code=Code.ARMS_TOO_LOW,
        severity=Severity.INFO,
        message="Estenda mais os bracos acima da cabeca",
    ),
    SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=23),
]


# --------------------------------------------------------------------------------------
# Round-trip
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("payload", PAYLOADS, ids=lambda p: type(p).__name__)
def test_round_trip_msgpack_preserva_payload(payload) -> None:
    original = envelope_de(payload)

    recuperado = decode_envelope(encode_envelope(original))

    assert recuperado == original
    assert recuperado.payload() == payload


@pytest.mark.parametrize("payload", PAYLOADS, ids=lambda p: type(p).__name__)
def test_round_trip_stream_fields(payload) -> None:
    original = envelope_de(payload)

    assert from_stream_fields(to_stream_fields(original)) == original


def test_from_stream_fields_aceita_chave_str() -> None:
    """Alguns clientes Redis devolvem chaves decodificadas."""
    original = envelope_de(ExercisePhase(phase=Phase.CLOSED))
    campos = {"e": encode_envelope(original)}

    assert from_stream_fields(campos) == original


def test_from_stream_fields_sem_campo_falha() -> None:
    with pytest.raises(EventValidationError, match="sem o campo"):
        from_stream_fields({b"outro": b"x"})


def test_envelope_serializado_tem_exatamente_as_chaves_do_contrato() -> None:
    bruto = msgpack.unpackb(encode_envelope(envelope_de(PoseFrame(landmarks=landmarks()))))

    assert set(bruto) == {"v", "type", "session_id", "ts", "seq", "source", "data"}
    assert bruto["v"] == PROTOCOL_VERSION
    assert bruto["type"] == "pose.frame"
    assert bruto["source"] == "edge"


def test_make_envelope_usa_o_tipo_do_payload() -> None:
    envelope = envelope_de(RepDetected(rep_count=1, phase=Phase.CLOSED, duration_ms=700))

    assert envelope.type is EventType.REP_DETECTED
    assert envelope.stream is Stream.EVENTS_ANALYSIS


# --------------------------------------------------------------------------------------
# Validação do envelope (SPEC-002, critério 3)
# --------------------------------------------------------------------------------------


def test_envelope_valido_aceita_seq_zero() -> None:
    envelope = envelope_de(ExercisePhase(phase=Phase.OPEN), seq=0)

    assert envelope.seq == 0


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("type", "pose.inventado"),
        ("source", "carrier_pigeon"),
        ("session_id", ""),
        ("session_id", 42),
        ("ts", 0),
        ("ts", -1),
        ("ts", "1722100000123"),
        ("seq", -1),
        ("seq", 1.5),
        ("v", 2),
        ("data", ["nao", "e", "mapa"]),
    ],
)
def test_envelope_invalido_e_rejeitado(campo: str, valor) -> None:
    bruto = envelope_de(ExercisePhase(phase=Phase.OPEN)).to_dict()
    bruto[campo] = valor

    with pytest.raises(EventValidationError):
        Envelope.from_dict(bruto)


@pytest.mark.parametrize("campo", ["type", "session_id", "ts", "seq", "source"])
def test_envelope_sem_campo_obrigatorio_e_rejeitado(campo: str) -> None:
    bruto = envelope_de(ExercisePhase(phase=Phase.OPEN)).to_dict()
    del bruto[campo]

    with pytest.raises(EventValidationError, match="envelope incompleto"):
        Envelope.from_dict(bruto)


@pytest.mark.parametrize("bruto", [b"", b"\xc1lixo", msgpack.packb([1, 2, 3])])
def test_bytes_invalidos_sao_rejeitados_sem_estourar_outra_excecao(bruto: bytes) -> None:
    with pytest.raises(EventValidationError):
        decode_envelope(bruto)


def test_seq_bool_nao_passa_por_int() -> None:
    """`True` é `int` em Python — o contrato não aceita isso."""
    bruto = envelope_de(ExercisePhase(phase=Phase.OPEN)).to_dict()
    bruto["seq"] = True

    with pytest.raises(EventValidationError):
        Envelope.from_dict(bruto)


# --------------------------------------------------------------------------------------
# Validação de payload
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("quantidade", [0, 32, 34])
def test_pose_frame_exige_33_landmarks(quantidade: int) -> None:
    with pytest.raises(EventValidationError, match="33 entradas"):
        PoseFrame.from_data({"landmarks": [[0.0, 0.0, 0.0, 1.0]] * quantidade})


def test_pose_frame_exige_quatro_componentes_por_landmark() -> None:
    pontos = landmarks()
    pontos[17] = [0.1, 0.2]

    with pytest.raises(EventValidationError, match="landmark 17"):
        PoseFrame.from_data({"landmarks": pontos})


def test_pose_frame_omite_campos_opcionais_quando_vazios() -> None:
    data = PoseFrame(landmarks=landmarks()).to_data()

    assert set(data) == {"landmarks"}


def test_payload_sem_campo_obrigatorio_e_rejeitado() -> None:
    with pytest.raises(EventValidationError, match="campo obrigatorio ausente"):
        RepDetected.from_data({"rep_count": 3, "phase": "closed"})


def test_codigo_desconhecido_e_rejeitado() -> None:
    with pytest.raises(EventValidationError, match="code invalido"):
        SceneWarning.from_data({"code": "SUNGLASSES_TOO_COOL"})


def test_scene_warning_tem_severidade_padrao() -> None:
    assert SceneWarning.from_data({"code": "TOO_FAR"}).severity is Severity.WARNING


# --------------------------------------------------------------------------------------
# Tabelas do contrato
# --------------------------------------------------------------------------------------


def test_todo_tipo_tem_stream_e_payload() -> None:
    assert set(STREAM_FOR_TYPE) == set(EventType)
    for tipo in EventType:
        envelope = Envelope(
            type=tipo, session_id=SESSION_ID, ts=1, seq=0, source=Source.SYSTEM, data={}
        )
        assert isinstance(envelope.stream, Stream)


def test_pose_frame_vai_para_o_stream_de_entrada_da_analise() -> None:
    assert STREAM_FOR_TYPE[EventType.POSE_FRAME] is Stream.POSE_FRAMES
    assert STREAM_FOR_TYPE[EventType.SESSION_STARTED] is Stream.POSE_FRAMES


def test_saidas_da_analise_vao_para_events_analysis() -> None:
    saidas = {
        EventType.EXERCISE_PHASE,
        EventType.REP_DETECTED,
        EventType.QUALITY_SIGNAL,
        EventType.SCENE_WARNING,
        EventType.FEEDBACK_ISSUED,
        EventType.SESSION_COMPLETED,
    }

    assert {STREAM_FOR_TYPE[tipo] for tipo in saidas} == {Stream.EVENTS_ANALYSIS}


def test_cliente_nunca_recebe_pose_frame_de_volta() -> None:
    assert EventType.POSE_FRAME not in CLIENT_PUSH_TYPES
    assert EventType.QUALITY_SIGNAL not in CLIENT_PUSH_TYPES  # o HUD vê feedback.issued
    assert EventType.REP_DETECTED in CLIENT_PUSH_TYPES
    assert set(EventType) >= CLIENT_PUSH_TYPES


def test_consumer_groups_cobrem_os_streams() -> None:
    assert set(CONSUMER_GROUPS) == set(Stream)
    assert "analysis" in CONSUMER_GROUPS[Stream.POSE_FRAMES]
    assert "gateway" in CONSUMER_GROUPS[Stream.EVENTS_ANALYSIS]


def test_landmarks_seguem_o_padrao_mediapipe() -> None:
    assert len(LANDMARK_NAMES) == LANDMARK_COUNT == len(Landmark)
    assert LANDMARK_NAMES[0] == "nose"
    assert LANDMARK_NAMES[Landmark.LEFT_SHOULDER] == "left_shoulder"
    assert Landmark.RIGHT_HIP == 24
    assert LANDMARK_NAMES[-1] == "right_foot_index"


def test_tipos_em_dot_case_e_codigos_em_screaming_snake() -> None:
    for tipo in EventType:
        assert tipo.value == tipo.value.lower()
        assert "." in tipo.value
    for code in Code:
        assert code.value == code.value.upper()


def test_analise_consome_frames_e_ciclo_de_sessao() -> None:
    assert EventType.POSE_FRAME in ANALYSIS_INPUT_TYPES
    assert EventType.SESSION_STARTED in ANALYSIS_INPUT_TYPES
    # Encerrar a sessao e ENTRADA da analise: quem publica na rota padrao manda para
    # events.analysis, onde o worker nao escuta, e a sessao nunca fecharia.
    assert EventType.SESSION_COMPLETED in ANALYSIS_INPUT_TYPES
    assert EventType.REP_DETECTED not in ANALYSIS_INPUT_TYPES
    assert EventType.FEEDBACK_ISSUED not in ANALYSIS_INPUT_TYPES


def test_saidas_da_analise_nao_sao_entradas_dela() -> None:
    """Sem isso, um evento de saida poderia realimentar o worker."""
    saidas = {
        EventType.EXERCISE_PHASE,
        EventType.REP_DETECTED,
        EventType.QUALITY_SIGNAL,
        EventType.FEEDBACK_ISSUED,
    }

    assert saidas & ANALYSIS_INPUT_TYPES == set()
