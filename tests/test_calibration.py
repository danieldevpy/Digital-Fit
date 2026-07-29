"""Testes da calibração da sessão (T-019 / SPEC-004).

Duas camadas: o `Calibrator` puro (mediana, recusa de frame ruim, teto de tempo) e a
integração no worker — que é onde as consequências aparecem: a contagem não começa antes da
medida, e os 30 s passam a correr da calibração.
"""

from __future__ import annotations

import pytest

from tests.synthetic_keypoints import jumping_jack_poses, sequence, session_poses, still_poses
from workers.analysis_worker.calibration import (
    CALIBRATION_TIMEOUT_MS,
    MIN_CALIBRATION_FRAMES,
    Calibrator,
)
from workers.analysis_worker.router import AnalysisRouter
from workers.shared.events import (
    Envelope,
    EventType,
    Mode,
    PoseFrame,
    SessionCalibrated,
    SessionStarted,
    Source,
    make_envelope,
)
from workers.shared.normalize import Normalizer

SESSAO = "3f2b9c4e-0000-4000-8000-000000000001"


def normalizados(frames):
    normalizer = Normalizer()
    return [normalizer.push(frame) for frame in frames]


def envelope_pose(frame, session_id: str = SESSAO) -> Envelope:
    return make_envelope(
        PoseFrame(landmarks=[list(p) for p in frame.landmarks]),
        session_id=session_id,
        ts=frame.ts,
        seq=frame.seq,
        source=Source.EDGE,
    )


def envelope_started(session_id: str = SESSAO, *, countdown_s: int = 0) -> Envelope:
    """`session.started` do teste.

    `countdown_s=0` por padrão: estes testes são sobre CONTAGEM, e a preparação da T-049 só
    atrasaria o começo deles sem mudar o que verificam. Quem testa a preparação passa o valor
    explicitamente — é o assunto do teste, então tem de estar escrito nele.
    """
    return make_envelope(
        SessionStarted(
            exercise="jumping_jack", mode=Mode.EDGE, duration_s=30, countdown_s=countdown_s
        ),
        session_id=session_id,
        ts=1_722_100_000_000,
        seq=0,
        source=Source.SYSTEM,
    )


# --------------------------------------------------------------------------------------
# Calibrator
# --------------------------------------------------------------------------------------


def test_mede_o_corpo_depois_de_um_segundo_parado() -> None:
    calibrador = Calibrator()
    baseline = None

    for norm in normalizados(sequence(still_poses(20))):
        baseline = calibrador.push(norm)
        if baseline is not None:
            break

    assert baseline is not None
    assert baseline.torso and baseline.torso > 0
    assert baseline.shoulder_span and baseline.shoulder_span > 0
    assert baseline.wrist_rest_y is not None


def test_nao_mede_antes_da_janela_fechar() -> None:
    """Meia dúzia de frames não é uma medida: a SPEC-004 pede 1 s de mediana."""
    calibrador = Calibrator()

    for norm in normalizados(sequence(still_poses(5))):
        assert calibrador.push(norm) is None


def test_frames_poucos_nao_bastam_mesmo_com_tempo_passado() -> None:
    # Cadência baixíssima: o tempo passa mas quase não há amostra. Medir a mediana de 3
    # frames seria dar autoridade a um número que não tem.
    calibrador = Calibrator()
    frames = normalizados(sequence(still_poses(4), fps=2.0))

    assert all(calibrador.push(norm) is None for norm in frames)
    assert calibrador.samples < MIN_CALIBRATION_FRAMES


def test_frame_degradado_e_recusado() -> None:
    """Landmark 'adivinhado' pelo modelo viraria uma proporção inventada."""
    calibrador = Calibrator()

    for norm in normalizados(sequence(still_poses(20), visibility=0.1)):
        assert calibrador.push(norm) is None

    assert calibrador.samples == 0
    assert calibrador.discarded == 20


def test_falha_quando_estoura_o_teto() -> None:
    calibrador = Calibrator()
    frames = normalizados(sequence(still_poses(20), visibility=0.1))
    for norm in frames:
        calibrador.push(norm)

    inicio = frames[0].ts
    assert calibrador.failed(inicio + CALIBRATION_TIMEOUT_MS - 1) is False
    assert calibrador.failed(inicio + CALIBRATION_TIMEOUT_MS) is True


def test_reset_recomeca_do_zero() -> None:
    calibrador = Calibrator()
    for norm in normalizados(sequence(still_poses(10))):
        calibrador.push(norm)

    calibrador.reset()

    assert calibrador.samples == 0
    assert calibrador.discarded == 0


def test_mediana_ignora_o_frame_absurdo() -> None:
    """Média seria puxada por um outlier; mediana não. É por isso que a spec pede mediana."""
    calibrador = Calibrator(min_frames=3, window_ms=0)
    frames = normalizados(sequence(still_poses(12)))

    baseline = None
    for i, norm in enumerate(frames):
        if i == 1:
            # Um frame em que o modelo "esticou" o torso para o triplo.
            norm = type(norm)(
                ts=norm.ts,
                seq=norm.seq,
                points=norm.points,
                visibility=norm.visibility,
                torso=norm.torso * 3,
                shoulder_width=norm.shoulder_width,
                degraded=False,
            )
        baseline = calibrador.push(norm)
        if baseline is not None:
            break

    normal = frames[0].torso
    assert baseline is not None
    assert baseline.torso == pytest.approx(normal, rel=0.05)


# --------------------------------------------------------------------------------------
# Integração no worker
# --------------------------------------------------------------------------------------


def test_sessao_publica_session_calibrated_uma_vez() -> None:
    router = AnalysisRouter()
    router.handle(envelope_started(), now_wall_ms=1_000_000)

    saidas: list[Envelope] = []
    for frame in sequence(session_poses(jumping_jack_poses(3))):
        saidas.extend(router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66))

    calibrados = [e for e in saidas if e.type is EventType.SESSION_CALIBRATED]
    assert len(calibrados) == 1
    payload = SessionCalibrated.from_data(calibrados[0].data)
    assert payload.samples >= MIN_CALIBRATION_FRAMES
    assert payload.shoulder_span > 0


def test_nao_conta_repeticao_durante_a_calibracao() -> None:
    """Um "1" no placar enquanto a pessoa se posiciona seria uma rep que ela não fez."""
    router = AnalysisRouter()
    router.handle(envelope_started(), now_wall_ms=1_000_000)
    estado = router.sessions[SESSAO]

    # Só o countdown, sem exercício nenhum.
    for frame in sequence(still_poses(20)):
        router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66)

    assert estado.baseline is not None, "com pessoa parada e visivel, tem de calibrar"
    assert estado.analyzer.summary()["reps"] == 0


def test_baseline_chega_na_normalizacao_e_na_fsm() -> None:
    # Os dois consumidores têm de receber a MESMA medida: se só um receber, a normalização e
    # a FSM passam a raciocinar em escalas diferentes.
    router = AnalysisRouter()
    router.handle(envelope_started(), now_wall_ms=1_000_000)
    estado = router.sessions[SESSAO]

    for frame in sequence(still_poses(20)):
        router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66)

    assert estado.baseline is not None
    assert estado.analyzer.baseline is estado.baseline


def test_os_30s_correm_a_partir_da_calibracao() -> None:
    router = AnalysisRouter()
    router.handle(envelope_started(), now_wall_ms=1_000_000)
    estado = router.sessions[SESSAO]

    for frame in sequence(still_poses(20)):
        router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66)

    assert estado.first_frame_wall_ms == 1_000_000
    assert estado.exercise_started_wall_ms is not None
    # A âncora do timer é o fim da calibração, não o primeiro frame.
    assert estado.exercise_started_wall_ms > estado.first_frame_wall_ms


def test_contagem_completa_depois_do_countdown() -> None:
    """O caminho real: countdown parado e então o exercício — nenhuma rep se perde."""
    router = AnalysisRouter()
    router.handle(envelope_started(), now_wall_ms=1_000_000)

    saidas: list[Envelope] = []
    for frame in sequence(session_poses(jumping_jack_poses(5))):
        saidas.extend(router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66))

    reps = [e for e in saidas if e.type is EventType.REP_DETECTED]
    assert len(reps) == 5


# --------------------------------------------------------------------------------------
# Preparação "3, 2, 1" entre o corpo medido e a contagem valer (T-049 / SPEC-004)
# --------------------------------------------------------------------------------------


def test_sem_preparacao_a_contagem_vale_no_frame_seguinte() -> None:
    """`countdown_s=0` reproduz o comportamento anterior à T-049 — nada regrediu."""
    router = AnalysisRouter()
    router.handle(envelope_started(countdown_s=0), now_wall_ms=1_000_000)
    estado = router.sessions[SESSAO]

    for frame in sequence(still_poses(20)):
        router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66)

    assert estado.baseline is not None
    assert estado.counting_from_wall_ms == estado.exercise_started_wall_ms
    assert estado.counting(estado.counting_from_wall_ms) is True


def test_a_preparacao_adia_a_contagem_e_o_relogio_dos_30s() -> None:
    router = AnalysisRouter()
    router.handle(envelope_started(countdown_s=3), now_wall_ms=1_000_000)
    estado = router.sessions[SESSAO]

    for frame in sequence(still_poses(20)):
        router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66)

    medido_em = estado.counting_from_wall_ms - 3_000
    assert estado.counting(medido_em) is False
    assert estado.counting(medido_em + 2_999) is False
    assert estado.counting(medido_em + 3_000) is True
    # Os 30 s começam no "JÁ", não na medição: a preparação não é cobrada do treino.
    assert estado.exercise_started_wall_ms == estado.counting_from_wall_ms


def test_rep_feita_durante_a_preparacao_NAO_conta() -> None:
    """O motivo de a espera morar no servidor.

    Se fosse só animação no cliente, o polichinelo feito durante o "3, 2, 1" entraria no
    total — e o recurso estaria enganando quem confia nele.
    """

    def rodar(countdown_s: int) -> int:
        router = AnalysisRouter()
        router.handle(envelope_started(countdown_s=countdown_s), now_wall_ms=1_000_000)
        saidas: list[Envelope] = []
        for frame in sequence(session_poses(jumping_jack_poses(5))):
            saidas.extend(
                router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66)
            )
        return len([e for e in saidas if e.type is EventType.REP_DETECTED])

    # Os mesmos 5 polichinelos, a mesma sequência de frames: só muda a preparação.
    assert rodar(0) == 5
    # 10 s cobrem o movimento inteiro (~5 s a 15 fps): nada chega à FSM.
    assert rodar(10) == 0
    # E no meio do caminho a conta fecha: 3 s engolem as primeiras reps, não todas. Este é o
    # numero que prova que a janela é medida, e não que a contagem foi simplesmente desligada.
    assert rodar(3) == 2


def test_o_evento_de_calibracao_carrega_quanto_falta() -> None:
    """O cliente anima o "3, 2, 1" com este número — sem ele, não saberia o que desenhar."""
    router = AnalysisRouter()
    router.handle(envelope_started(countdown_s=3), now_wall_ms=1_000_000)

    saidas: list[Envelope] = []
    for frame in sequence(still_poses(20)):
        saidas.extend(router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66))

    calibrado = next(e for e in saidas if e.type is EventType.SESSION_CALIBRATED)
    assert calibrado.data["countdown_ms"] == 3_000


def test_a_cena_continua_avisando_durante_a_preparacao() -> None:
    """É justamente quando "entre no quadro" mais ajuda — a pessoa ainda está se ajeitando."""
    router = AnalysisRouter()
    router.handle(envelope_started(countdown_s=3), now_wall_ms=1_000_000)
    estado = router.sessions[SESSAO]

    for frame in sequence(still_poses(20)):
        router.handle(envelope_pose(frame), now_wall_ms=1_000_000 + frame.seq * 66)

    assert estado.baseline is not None
    assert estado.counting(estado.counting_from_wall_ms - 1) is False
    # O normalizador seguiu recebendo: o filtro chega quente no primeiro frame que vale.
    assert estado.frames >= 20
