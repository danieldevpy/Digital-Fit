"""Testes do analysis-worker (T-009 / SPEC-007).

O barramento é o `InMemoryBus`: dá para testar o worker inteiro — consumo, FSM, publicação e
ack — sem Redis no ar.
"""

import pytest

from tests.synthetic_keypoints import (
    jumping_jack_poses,
    sequence,
    session_poses,
    squat_poses,
    still_poses,
)
from workers.analysis_worker.main import BATCH, GROUP, Shutdown, run
from workers.analysis_worker.router import DEFAULT_DURATION_S, AnalysisRouter
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    Envelope,
    EventType,
    Mode,
    PoseFrame,
    RepDetected,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    Source,
    Stream,
    make_envelope,
)

SESSAO = "3f2b9c4e-0000-4000-8000-000000000001"


def envelope_pose(frame, session_id: str = SESSAO) -> Envelope:
    return make_envelope(
        PoseFrame(landmarks=[list(ponto) for ponto in frame.landmarks]),
        session_id=session_id,
        ts=frame.ts,
        seq=frame.seq,
        source=Source.EDGE,
    )


def envelope_started(
    session_id: str = SESSAO,
    *,
    exercise: str = "jumping_jack",
    duration_s: int = 30,
    countdown_s: int = 0,
) -> Envelope:
    """`session.started` do teste.

    `countdown_s=0` por padrão: estes testes são sobre CONTAGEM, e a preparação da T-049 só
    atrasaria o começo deles sem mudar o que verificam. Quem testa a preparação passa o valor
    explicitamente — é o assunto do teste, então tem de estar escrito nele.
    """
    return make_envelope(
        SessionStarted(
            exercise=exercise, mode=Mode.EDGE, duration_s=duration_s, countdown_s=countdown_s
        ),
        session_id=session_id,
        ts=1_722_100_000_000,
        seq=0,
        source=Source.SYSTEM,
    )


def envelope_completed(
    session_id: str = SESSAO, reason: SessionEndReason = SessionEndReason.COMPLETED
) -> Envelope:
    return make_envelope(
        SessionCompleted(reason=reason),
        session_id=session_id,
        ts=1_722_100_030_000,
        seq=999,
        source=Source.SYSTEM,
    )


def rodar(*envelopes: Envelope) -> tuple[InMemoryBus, AnalysisRouter]:
    """Alimenta o barramento e roda lotes suficientes para esvaziá-lo (o lote é de 50)."""
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, *envelopes)
    router = run(bus, consumer="teste", max_batches=len(envelopes) // BATCH + 2)
    return bus, router


# --------------------------------------------------------------------------------------
# Caminho principal
# --------------------------------------------------------------------------------------


def test_worker_conta_reps_e_publica_em_events_analysis() -> None:
    frames = [envelope_pose(frame) for frame in sequence(session_poses(jumping_jack_poses(5)))]

    bus, _ = rodar(envelope_started(), *frames)

    reps = bus.published_of(EventType.REP_DETECTED)
    assert len(reps) == 5
    assert [envelope.stream for envelope in reps] == [Stream.EVENTS_ANALYSIS] * 5
    assert RepDetected.from_data(reps[-1].data).rep_count == 5


def test_eventos_de_saida_carregam_a_sessao_e_seq_monotonico() -> None:
    frames = [envelope_pose(frame) for frame in sequence(session_poses(jumping_jack_poses(3)))]

    bus, _ = rodar(envelope_started(), *frames)

    assert {envelope.session_id for envelope in bus.published} == {SESSAO}
    seqs = [envelope.seq for envelope in bus.published]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


def test_saida_e_marcada_como_produzida_pelo_sistema() -> None:
    bus, _ = rodar(
        envelope_started(),
        *[envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(1)))],
    )

    assert {envelope.source for envelope in bus.published} == {Source.SYSTEM}


def test_todos_os_eventos_lidos_recebem_ack() -> None:
    frames = [envelope_pose(frame) for frame in sequence(session_poses(jumping_jack_poses(2)))]

    bus, _ = rodar(envelope_started(), *frames)

    assert len(bus.acked) == len(frames) + 1


def test_grupo_de_consumo_e_criado_no_start() -> None:
    bus = InMemoryBus()

    run(bus, consumer="teste", max_batches=1)

    assert (Stream.POSE_FRAMES.value, GROUP) in bus.groups


def test_fases_e_sinais_tambem_saem_no_stream() -> None:
    frames = [
        envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(2, amplitude=0.6)))
    ]

    bus, _ = rodar(envelope_started(), *frames)

    assert bus.published_of(EventType.QUALITY_SIGNAL)
    assert not bus.published_of(EventType.REP_DETECTED)


def test_frames_do_polichinelo_limpo_geram_fases_abertas_e_fechadas() -> None:
    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(2)))]

    bus, _ = rodar(envelope_started(), *frames)

    assert len(bus.published_of(EventType.EXERCISE_PHASE)) == 4


# --------------------------------------------------------------------------------------
# Estado de sessão
# --------------------------------------------------------------------------------------


def test_session_started_abre_a_sessao_com_o_exercicio_pedido() -> None:
    _, router = rodar(envelope_started(duration_s=45))

    estado = router.sessions[SESSAO]
    assert estado.exercise == "jumping_jack"
    assert estado.duration_s == 45
    assert estado.mode is Mode.EDGE


def test_sessao_de_agachamento_conta_agachamentos() -> None:
    """A costura que os testes de FSM não cobrem: `session.started` → `get_analyzer` → contagem.

    Vale a pena existir separada porque é onde um exercício novo pode estar perfeito e ainda
    assim nunca rodar — o worker escolhe o analisador pelo slug, e ninguém mais faz isso.
    """
    frames = [envelope_pose(f) for f in sequence(session_poses(squat_poses(4)))]

    bus, router = rodar(envelope_started(exercise="squat"), *frames)

    estado = router.sessions[SESSAO]
    assert estado.exercise == "squat"
    assert estado.analyzer.summary()["exercise"] == "squat"
    assert estado.analyzer.summary()["reps"] == 4
    reps = bus.published_of(EventType.REP_DETECTED)
    assert len(reps) == 4


def test_frame_sem_session_started_abre_sessao_com_o_padrao() -> None:
    """Corrida de eventos não pode custar repetições."""
    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(3)))]

    bus, router = rodar(*frames)

    assert router.sessions[SESSAO].duration_s == DEFAULT_DURATION_S
    assert len(bus.published_of(EventType.REP_DETECTED)) == 3


def test_exercicio_desconhecido_nao_abre_sessao_nem_derruba_o_worker() -> None:
    bus, router = rodar(envelope_started(exercise="levitacao"))

    assert router.sessions == {}
    assert bus.published == []


def test_sessoes_diferentes_nao_se_misturam() -> None:
    outra = "3f2b9c4e-0000-4000-8000-000000000002"
    frames_a = [envelope_pose(f, SESSAO) for f in sequence(session_poses(jumping_jack_poses(3)))]
    frames_b = [envelope_pose(f, outra) for f in sequence(session_poses(jumping_jack_poses(1)))]

    bus, router = rodar(envelope_started(SESSAO), envelope_started(outra), *frames_a, *frames_b)

    assert router.sessions[SESSAO].analyzer.summary()["reps"] == 3
    assert router.sessions[outra].analyzer.summary()["reps"] == 1
    reps_por_sessao = [envelope.session_id for envelope in bus.published_of(EventType.REP_DETECTED)]
    assert reps_por_sessao.count(SESSAO) == 3
    assert reps_por_sessao.count(outra) == 1


def test_session_completed_fecha_a_sessao_e_reemite_com_o_total() -> None:
    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(4)))]

    bus, router = rodar(envelope_started(), *frames, envelope_completed())

    assert SESSAO not in router.sessions
    fim = bus.published_of(EventType.SESSION_COMPLETED)
    assert len(fim) == 1
    payload = SessionCompleted.from_data(fim[0].data)
    assert payload.rep_count == 4
    assert payload.reason is SessionEndReason.COMPLETED


def test_session_completed_de_sessao_desconhecida_e_ignorado() -> None:
    bus, _ = rodar(envelope_completed("sessao-fantasma"))

    assert bus.published == []


def test_frames_depois_do_fim_abrem_sessao_nova_do_zero() -> None:
    """Sem isso, um frame atrasado somaria repetição a uma sessão já encerrada."""
    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(2)))]

    bus, router = rodar(envelope_started(), *frames, envelope_completed(), frames[0])

    assert router.sessions[SESSAO].analyzer.summary()["reps"] == 0
    assert len(bus.published_of(EventType.SESSION_COMPLETED)) == 1


def test_session_capability_nao_produz_evento_de_analise() -> None:
    from workers.shared.events import SessionCapability

    capability = make_envelope(
        SessionCapability(mode=Mode.EDGE, probe_fps=18.0, webgl=True),
        session_id=SESSAO,
        ts=1_722_100_000_000,
        seq=0,
        source=Source.EDGE,
    )

    bus, _ = rodar(capability)

    assert bus.published == []


# --------------------------------------------------------------------------------------
# Robustez
# --------------------------------------------------------------------------------------


def test_pose_frame_invalido_nao_derruba_o_worker() -> None:
    ruim = Envelope(
        type=EventType.POSE_FRAME,
        session_id=SESSAO,
        ts=1_722_100_000_100,
        seq=1,
        source=Source.EDGE,
        data={"landmarks": [[0.0, 0.0, 0.0, 1.0]] * 10},  # 10 landmarks, não 33
    )
    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(2)))]

    bus, _ = rodar(envelope_started(), ruim, *frames)

    assert len(bus.published_of(EventType.REP_DETECTED)) == 2
    assert len(bus.acked) == len(frames) + 2  # o inválido também recebe ack


def test_frames_degradados_nao_geram_evento_de_execucao() -> None:
    """SPEC-007: frame ruim não conta nem penaliza — mas a cena avisa (SPEC-003/T-013).

    Desde a T-019 a afirmação é ainda mais forte: com todos os frames degradados a baseline
    nunca é medida, e sem baseline o exercício **não começa** (SPEC-004, critério 2). Os
    frames ruins nem chegam à FSM — ficam no calibrador, que os recusa.
    """
    frames = [envelope_pose(f) for f in sequence(still_poses(30), visibility=0.1)]

    bus, router = rodar(envelope_started(), *frames)

    assert bus.published_of(EventType.REP_DETECTED) == []
    assert bus.published_of(EventType.QUALITY_SIGNAL) == []
    assert bus.published_of(EventType.EXERCISE_PHASE) == []
    assert bus.published_of(EventType.SCENE_WARNING), "usuario fora do quadro precisa ser avisado"

    estado = router.sessions[SESSAO]
    assert estado.baseline is None, "sessao nunca deve comecar sem medida"
    assert estado.exercise_started_wall_ms is None
    assert estado.calibrator.discarded == 30
    assert bus.published_of(EventType.SESSION_CALIBRATED) == []


def test_falha_no_processamento_nao_impede_ack_nem_o_resto_do_lote() -> None:
    class RouterExplosivo(AnalysisRouter):
        def handle(self, envelope):
            if envelope.type is EventType.POSE_FRAME and envelope.seq == 1:
                raise RuntimeError("boom")
            return super().handle(envelope)

    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(2)))]
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, envelope_started(), *frames)

    run(bus, consumer="teste", router=RouterExplosivo(), max_batches=4)

    assert len(bus.acked) == len(frames) + 1
    assert bus.published_of(EventType.REP_DETECTED)


def test_shutdown_encerra_o_loop() -> None:
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, envelope_started())
    shutdown = Shutdown()
    shutdown.requested = True

    run(bus, consumer="teste", router=AnalysisRouter(), shutdown=shutdown)

    assert bus.acked == [], "com parada pedida, nenhum evento e consumido"
    assert (Stream.POSE_FRAMES.value, GROUP) in bus.groups, "o grupo ainda e garantido"


def test_loop_sem_eventos_nao_publica_nada() -> None:
    bus = InMemoryBus()

    run(bus, consumer="teste", max_batches=3)

    assert bus.published == []


def test_router_reaproveitado_entre_lotes_mantem_a_contagem() -> None:
    """O worker real roda muitos lotes; o estado atravessa todos."""
    router = AnalysisRouter()
    frames = sequence(session_poses(jumping_jack_poses(4)))
    bus = InMemoryBus()

    bus.feed(Stream.POSE_FRAMES, envelope_started(), *[envelope_pose(f) for f in frames[:30]])
    run(bus, consumer="teste", router=router, max_batches=3)
    bus.feed(Stream.POSE_FRAMES, *[envelope_pose(f) for f in frames[30:]])
    run(bus, consumer="teste", router=router, max_batches=3)

    assert router.sessions[SESSAO].analyzer.summary()["reps"] == 4


# --------------------------------------------------------------------------------------
# Roteador em isolamento
# --------------------------------------------------------------------------------------


def test_router_devolve_envelopes_prontos_para_publicar() -> None:
    router = AnalysisRouter()
    router.handle(envelope_started())

    saidas = [
        envelope
        for frame in sequence(session_poses(jumping_jack_poses(1)))
        for envelope in router.handle(envelope_pose(frame))
    ]

    assert saidas
    for envelope in saidas:
        assert envelope.session_id == SESSAO
        assert envelope.stream is Stream.EVENTS_ANALYSIS
        assert envelope.ts > 0


def test_router_nao_mexe_no_envelope_de_entrada() -> None:
    router = AnalysisRouter()
    entrada = envelope_pose(sequence(session_poses(jumping_jack_poses(1)))[0])
    copia = entrada.to_dict()

    router.handle(entrada)

    assert entrada.to_dict() == copia


@pytest.mark.parametrize(
    "motivo",
    [
        SessionEndReason.COMPLETED,
        SessionEndReason.TIMEOUT,
        SessionEndReason.ABORTED,
        SessionEndReason.NO_DATA,
    ],
)
def test_qualquer_motivo_de_fim_encerra_a_sessao(motivo: SessionEndReason) -> None:
    _, router = rodar(envelope_started(), envelope_completed(reason=motivo))

    assert router.sessions == {}


# --------------------------------------------------------------------------------------
# Vaga cloud (T-017 / SPEC-009, critério 2)
# --------------------------------------------------------------------------------------


class SemaforoEspiao:
    def __init__(self) -> None:
        self.liberadas: list[str] = []

    def release(self, session_id: str) -> bool:
        self.liberadas.append(session_id)
        return True


@pytest.mark.parametrize(
    "motivo",
    [
        SessionEndReason.COMPLETED,
        SessionEndReason.TIMEOUT,
        SessionEndReason.ABORTED,
        SessionEndReason.NO_DATA,
    ],
)
def test_vaga_cloud_e_liberada_em_todos_os_finais(motivo: SessionEndReason) -> None:
    """Critério 2 da SPEC-009. Um caminho de fim esquecido come uma vaga para sempre."""
    semaforo = SemaforoEspiao()
    router = AnalysisRouter(slots=semaforo)

    router.handle(envelope_started())
    router.handle(envelope_completed(reason=motivo))

    assert semaforo.liberadas == [SESSAO]


def test_vaga_cloud_e_liberada_quando_o_timer_do_servidor_fecha() -> None:
    # Este é o caminho que NÃO passa por `session.completed` vindo de fora: o worker decide
    # sozinho, no `tick`. É o mais fácil de esquecer justamente por isso.
    semaforo = SemaforoEspiao()
    router = AnalysisRouter(slots=semaforo)
    router.handle(envelope_started())

    saidas = router.tick(now_wall_ms=_wall_ms_apos_o_prazo())

    assert [e.type for e in saidas] == [EventType.SESSION_COMPLETED]
    assert semaforo.liberadas == [SESSAO]


def test_falha_ao_liberar_vaga_nao_impede_o_fim_da_sessao() -> None:
    # O score de expiração do semáforo recolhe a vaga sozinho; travar o encerramento por
    # causa disso deixaria o usuário sem o resultado do treino.
    class SemaforoQuebrado:
        def release(self, session_id: str) -> bool:
            raise ConnectionError("redis fora")

    router = AnalysisRouter(slots=SemaforoQuebrado())
    router.handle(envelope_started())

    saidas = router.handle(envelope_completed(reason=SessionEndReason.COMPLETED))

    assert [e.type for e in saidas] == [EventType.SESSION_COMPLETED]
    assert router.sessions == {}


def _wall_ms_apos_o_prazo() -> int:
    import time

    return int(time.time() * 1000) + (DEFAULT_DURATION_S + 5) * 1000
