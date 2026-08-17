"""Testes do analysis-worker (T-009 / SPEC-007).

O barramento é o `InMemoryBus`: dá para testar o worker inteiro — consumo, FSM, publicação e
ack — sem Redis no ar.
"""

import time

import pytest

from tests.synthetic_keypoints import (
    jumping_jack_poses,
    sequence,
    session_poses,
    squat_poses,
    still_poses,
)
from workers.analysis_worker.main import BATCH, GROUP, Shutdown, run
from workers.analysis_worker.router import (
    DEFAULT_DURATION_S,
    ENDED_MEMORY_MS,
    AnalysisRouter,
)
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
    SetMode,
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
    set_mode: SetMode = SetMode.LIVRE,
    target_reps: int = 0,
) -> Envelope:
    """`session.started` do teste.

    `countdown_s=0` por padrão: estes testes são sobre CONTAGEM, e a preparação da T-049 só
    atrasaria o começo deles sem mudar o que verificam. Quem testa a preparação passa o valor
    explicitamente — é o assunto do teste, então tem de estar escrito nele.
    """
    return make_envelope(
        SessionStarted(
            exercise=exercise,
            mode=Mode.EDGE,
            duration_s=duration_s,
            countdown_s=countdown_s,
            set_mode=set_mode,
            target_reps=target_reps,
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


def agora_ms() -> int:
    """Relógio de parede em ms — o mesmo que o roteador usa quando ninguém lhe passa um."""
    return int(time.time() * 1000)


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


def test_frames_depois_do_fim_sao_descartados() -> None:
    """Frame atrasado não soma repetição à sessão encerrada — e não abre uma nova (T-077).

    Até a T-077 ele abria: a sessão "nova" nascia com o MESMO `session_id`, contava o que a
    pessoa fizesse depois do fim, morria de `no_data` 10 s depois e emitia um segundo
    `session.completed`. Como o report-builder faz upsert por `session_id` (SPEC-010), esse
    segundo relatório sobrescrevia o bom. Medido em produção antes do conserto: uma sessão de
    26 reps virou "4 reps · no_data" no banco.

    Por isso o teste olha para as três coisas ao mesmo tempo: nenhuma sessão viva, nenhum
    `session.completed` a mais, e nenhuma repetição contada depois do fim.
    """
    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(2)))]

    bus, router = rodar(envelope_started(), *frames, envelope_completed(), *frames)

    assert router.sessions == {}
    assert len(bus.published_of(EventType.SESSION_COMPLETED)) == 1
    assert router.ended[SESSAO].ignored == len(frames)


def test_fim_por_prazo_tambem_fecha_a_porta() -> None:
    """O caminho REAL do bug era o `tick`, não o `session.completed` de fora.

    Em produção quem encerra é o timer autoritativo do servidor (os 30 s), e ele passa pelo
    `tick`. Se só o `_on_session_completed` marcasse o fim, o conserto não valeria justamente
    no caminho em que o problema aconteceu.
    """
    frames = [envelope_pose(f) for f in sequence(session_poses(jumping_jack_poses(2)))]
    _, router = rodar(envelope_started(), *frames)

    fim = router.tick(now_wall_ms=agora_ms() + 31_000)
    assert len(fim) == 1
    assert SessionCompleted.from_data(fim[0].data).reason is SessionEndReason.COMPLETED

    depois = router.handle(frames[0])

    assert depois == []
    assert router.sessions == {}


def test_a_lapide_e_esquecida_depois_da_janela() -> None:
    """A memória do fim é limitada por tempo: worker de pé por semanas não pode vazar."""
    _, router = rodar(envelope_started(), envelope_completed())
    assert SESSAO in router.ended

    router.tick(now_wall_ms=agora_ms() + ENDED_MEMORY_MS + 1)

    assert router.ended == {}


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


# --------------------------------------------------------------------------------------
# Modo contado (T-135 / SPEC-023)
# --------------------------------------------------------------------------------------

#: Relógio de parede PARADO durante toda a série contada.
#:
#: Não é conveniência de teste — é o que separa os dois modos. Com a parede congelada nenhuma
#: regra de parede pode fechar a sessão (nem a janela, nem `no_data`, nem o teto absoluto);
#: logo, o que fechar, fechou pelo `ts` dos frames, que é a autoridade do modo contado. É a
#: mesma propriedade que faz o replay de um stream gravado reproduzir o mesmo fim (critério 10).
PAREDE_PARADA = 1_000_000


def alimentar(router: AnalysisRouter, poses, *, wall_ms: int = PAREDE_PARADA) -> list[Envelope]:
    """Passa uma sessão inteira (countdown + exercício) pelo roteador, sem mexer na parede."""
    saidas: list[Envelope] = []
    for frame in sequence(session_poses(poses)):
        saidas.extend(router.handle(envelope_pose(frame), now_wall_ms=wall_ms))
    return saidas


def _serie_contada(
    poses, *, target_reps: int, duration_s: int = 30, wall_ms: int = PAREDE_PARADA
) -> tuple[AnalysisRouter, list[Envelope]]:
    router = AnalysisRouter()
    router.handle(
        envelope_started(duration_s=duration_s, set_mode=SetMode.CONTADO, target_reps=target_reps),
        now_wall_ms=wall_ms,
    )
    saidas = alimentar(router, poses, wall_ms=wall_ms)
    # O tick roda a cada volta do loop do worker; aqui ele fecha a série que estourou o teto.
    saidas.extend(router.tick(now_wall_ms=wall_ms))
    return router, saidas


def test_meta_encerra_a_serie_no_frame_da_nesima_repeticao() -> None:
    """Critério 1 da SPEC-023: 15 reps com meta 15 termina em `target_reached`, não no teto.

    O "no frame da 15ª rep" é a parte que importa e a mais fácil de perder: um fim carimbado
    no `tick` seguinte carregaria o atraso do loop dentro do "tempo até a meta", que é
    justamente o número que esta spec promete medir.
    """
    router, saidas = _serie_contada(jumping_jack_poses(15), target_reps=15)

    fins = [e for e in saidas if e.type is EventType.SESSION_COMPLETED]
    reps = [e for e in saidas if e.type is EventType.REP_DETECTED]
    assert len(fins) == 1
    payload = SessionCompleted.from_data(fins[0].data)
    assert payload.reason is SessionEndReason.TARGET_REACHED
    assert payload.rep_count == 15
    # O fim tem o `ts` da 15ª repetição — mesmo frame, mesmo instante.
    assert fins[0].ts == reps[-1].ts
    assert router.sessions == {}


def test_meta_atingida_fecha_a_porta_para_o_resto_da_serie() -> None:
    """Quem continua se mexendo depois da meta não ganha repetição extra.

    Mesma família do bug da T-077: o fim tem de deixar lápide, senão o frame seguinte abre uma
    sessão nova com o mesmo `session_id` e o segundo relatório sobrescreve o bom.
    """
    router, saidas = _serie_contada(jumping_jack_poses(20), target_reps=15)

    reps = [e for e in saidas if e.type is EventType.REP_DETECTED]
    fins = [e for e in saidas if e.type is EventType.SESSION_COMPLETED]
    assert len(reps) == 15
    assert SessionCompleted.from_data(fins[0].data).rep_count == 15
    assert router.sessions == {}
    assert SESSAO in router.ended
    assert router.ended[SESSAO].ignored > 0, "os frames depois da meta têm de ser descartados"


def test_estourar_o_teto_termina_em_completed_sem_erro() -> None:
    """Critério 2: fez 10 de 15 e o teto chegou — `completed`, 10 reps, ninguém é punido."""
    router, saidas = _serie_contada(
        [*jumping_jack_poses(10), *still_poses(120)], target_reps=15, duration_s=12
    )

    fins = [e for e in saidas if e.type is EventType.SESSION_COMPLETED]
    assert len(fins) == 1
    payload = SessionCompleted.from_data(fins[0].data)
    assert payload.reason is SessionEndReason.COMPLETED
    assert payload.rep_count == 10
    assert router.sessions == {}, "sessão pendurada come vaga cloud para sempre"


def test_o_teto_do_modo_contado_corre_no_relogio_dos_frames() -> None:
    """Com a parede congelada o teto ainda vence: quem mede o teto é o `ts` do frame.

    O par negativo mora no teste seguinte — nos mesmos frames, o modo livre não fecha nada com
    a parede parada, porque lá a janela é de parede de propósito.
    """
    router, saidas = _serie_contada(
        [*jumping_jack_poses(10), *still_poses(120)], target_reps=15, duration_s=12
    )
    estado_final = [e for e in saidas if e.type is EventType.SESSION_COMPLETED]

    assert estado_final, "o teto por `ts` tem de fechar a sessão mesmo sem a parede andar"
    assert router.sessions == {}


def test_modo_livre_nao_fecha_pelo_ts_dos_frames() -> None:
    """Critério 3 (regressão): o modo livre é byte-a-byte o comportamento de hoje.

    Os mesmos frames que fecham a série contada pelo teto deixam a sessão livre aberta — a
    janela do livre é competitiva e corre no relógio do servidor (SPEC-009), e esta task não
    encostou nisso.
    """
    router = AnalysisRouter()
    router.handle(envelope_started(duration_s=12), now_wall_ms=PAREDE_PARADA)

    saidas = alimentar(router, [*jumping_jack_poses(10), *still_poses(120)])
    saidas.extend(router.tick(now_wall_ms=PAREDE_PARADA))

    assert [e for e in saidas if e.type is EventType.SESSION_COMPLETED] == []
    assert router.sessions[SESSAO].analyzer.summary()["reps"] == 10


def test_modo_livre_ignora_target_reps() -> None:
    """`target_reps` sem modo contado não encerra nada — os dois campos andam juntos."""
    router = AnalysisRouter()
    router.handle(envelope_started(target_reps=3), now_wall_ms=PAREDE_PARADA)

    saidas = alimentar(router, jumping_jack_poses(5))

    assert [e for e in saidas if e.type is EventType.SESSION_COMPLETED] == []
    assert router.sessions[SESSAO].analyzer.summary()["reps"] == 5


def test_modo_contado_sem_meta_degrada_para_livre() -> None:
    """Contrato malformado (`contado` com meta 0) não pode encerrar a série na rep zero.

    A SPEC-023 §2 exige `target_reps > 0` no modo contado. Um `reps >= 0` fecharia a sessão no
    primeiro frame com zero repetição — exatamente a cara de "app quebrado" que a T-112 já
    pagou para aprender.
    """
    router = AnalysisRouter()
    router.handle(
        envelope_started(set_mode=SetMode.CONTADO, target_reps=0), now_wall_ms=PAREDE_PARADA
    )

    saidas = alimentar(router, jumping_jack_poses(3))

    assert [e for e in saidas if e.type is EventType.SESSION_COMPLETED] == []
    assert router.sessions[SESSAO].analyzer.summary()["reps"] == 3


def test_sessao_sem_os_campos_da_spec023_abre_no_modo_livre() -> None:
    """Critério 9 no roteador: evento anterior a esta spec abre nos defaults, não recusa."""
    router = AnalysisRouter()
    router.handle(envelope_started(), now_wall_ms=PAREDE_PARADA)

    estado = router.sessions[SESSAO]
    assert estado.set_mode is SetMode.LIVRE
    assert estado.target_reps == 0
    assert estado.counted is False


def test_a_serie_contada_e_a_mesma_em_qualquer_relogio_de_parede() -> None:
    """Critério 10: replay reproduz o mesmo fim.

    Duas paredes muito distantes (uma delas 30 dias adiante, o desvio que a T-078 mediu em
    produção), os mesmos frames: mesmo motivo, mesma contagem, mesmo `ts` de fim.
    """

    def rodar_com(wall_ms: int) -> tuple[SessionEndReason, int, int]:
        _, saidas = _serie_contada(jumping_jack_poses(15), target_reps=15, wall_ms=wall_ms)
        fim = next(e for e in saidas if e.type is EventType.SESSION_COMPLETED)
        payload = SessionCompleted.from_data(fim.data)
        return payload.reason, payload.rep_count, fim.ts

    assert rodar_com(PAREDE_PARADA) == rodar_com(PAREDE_PARADA + 30 * 86_400_000)


def test_a_meta_devolve_a_vaga_cloud() -> None:
    """Caminho de fim novo = risco novo de vazar vaga (SPEC-009, critério 2).

    Cada caminho de fim esquecido come uma vaga para sempre; este nasceu nesta task.
    """
    semaforo = SemaforoEspiao()
    router = AnalysisRouter(slots=semaforo)
    router.handle(
        envelope_started(set_mode=SetMode.CONTADO, target_reps=2), now_wall_ms=PAREDE_PARADA
    )

    alimentar(router, jumping_jack_poses(3))

    assert semaforo.liberadas == [SESSAO]
