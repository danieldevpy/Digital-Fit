"""Testes do replay contra a stack (T-133).

O que dá para cobrir sem docker de pé é a fronteira: o envelope que sai no fio e a leitura dos
eventos que voltam. O resto — admissão, WebSocket, relógio do servidor — é justamente a parte
que só existe integrada, e medir isso é o propósito do comando, não do teste.

O envelope tem teste próprio por um motivo concreto: a primeira versão deste replay mandou
JSON de texto num canal que só aceita msgpack binário. O gateway registrou "enviou texto no WS;
ignorado" para os 548 frames, a sessão morreu de `no_data`, e por alguns minutos aquilo pareceu
um bug de contagem do servidor. Um envelope errado não estoura — ele mente.
"""

from __future__ import annotations

import msgpack

from eval.stack import StackResult, _resultado, build_frame_envelope
from workers.shared.keypoints import KeypointFixture
from workers.shared.normalize import RawFrame


def _fixture(reps: int | None = 18) -> KeypointFixture:
    frames = [RawFrame(ts=i * 66, seq=i, landmarks=[[0.5, 0.5, 0.0, 1.0]] * 33) for i in range(3)]
    return KeypointFixture(label="teste", frames=frames, exercise="squat", expected_reps=reps)


def test_envelope_e_o_mesmo_contrato_do_cliente() -> None:
    envelope = build_frame_envelope("s-1", 7, 1_700_000_000_000, [[0.1, 0.2, 0.3, 1.0]])

    assert envelope == {
        "v": 1,
        "type": "pose.frame",
        "session_id": "s-1",
        "ts": 1_700_000_000_000,
        "seq": 7,
        "source": "edge",
        "data": {"landmarks": [[0.1, 0.2, 0.3, 1.0]]},
    }


def test_envelope_sobrevive_a_ida_e_volta_em_msgpack() -> None:
    # É como ele trafega. Se algum campo virar tipo que o msgpack não carrega, é aqui que dói —
    # e não em produção, com o gateway descartando frame em silêncio.
    envelope = build_frame_envelope("s-1", 0, 1_700_000_000_000, [[0.1, 0.2, 0.3, 1.0]])

    assert msgpack.unpackb(msgpack.packb(envelope, use_bin_type=True), raw=False) == envelope


def test_resultado_le_a_contagem_do_session_completed() -> None:
    eventos = [
        {"type": "session.calibrated", "data": {"torso": 0.13, "samples": 16}},
        {"type": "scene.warning", "data": {"code": "TOO_FAR"}},
        {"type": "scene.warning", "data": {"code": "TOO_FAR"}},
        {"type": "rep.detected", "data": {}},
        {"type": "session.completed", "data": {"reason": "completed", "rep_count": 15}},
    ]

    resultado = _resultado(_fixture(), "squat", "s-1", 512, eventos)

    assert resultado.reps == 15
    assert resultado.reason == "completed"
    assert resultado.frames_sent == 512
    assert resultado.expected_reps == 18
    assert resultado.scene_warnings == {"TOO_FAR": 2}
    assert resultado.calibration["samples"] == 16


def test_sessao_sem_completed_nao_vira_zero_silencioso() -> None:
    """Sem `session.completed` a sessão não contou zero: ela não terminou.

    Confundir os dois é exatamente o erro que este módulo existe para desfazer — treze sessões
    de agachamento com `no_data` foram lidas por semanas como "o agachamento conta zero".
    """
    resultado = _resultado(_fixture(), "squat", "s-1", 0, [])

    assert resultado.reason == "sem session.completed"
    assert resultado.to_dict()["reason"] == "sem session.completed"


def test_resumo_diz_o_rotulo_mesmo_quando_nao_existe() -> None:
    resultado = _resultado(_fixture(reps=None), "squat", "s-1", 10, [])

    assert "[rotulo ?]" in resultado.summary_line()


def test_to_dict_marca_a_perna() -> None:
    resultado = StackResult(
        label="x", exercise="squat", session_id="s-1", reps=1, reason="completed", frames_sent=1
    )

    # Sem isto um relatório da stack seria indistinguível de um do harness ou do navegador.
    assert resultado.to_dict()["source"] == "stack"
