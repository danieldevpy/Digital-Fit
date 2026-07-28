"""Feedback engine: catálogo, prioridade e throttle (T-010 núcleo / SPEC-008).

A exibição no HUD é do Agente B (T-012); aqui se testa a decisão: *qual* feedback sai, *quando*
e *quantas vezes*.
"""

import pytest

from tests.synthetic_keypoints import jumping_jack_poses, sequence, still_poses
from workers.analysis_worker.exercises import feed, get_analyzer
from workers.analysis_worker.feedback import (
    DEFAULT_CATALOG_PATH,
    SCENE_SUPPRESS_MS,
    THROTTLE_MS,
    FeedbackCatalog,
    FeedbackEngine,
)
from workers.shared.events import Code, FeedbackIssued, QualitySignal, SceneWarning, Severity
from workers.shared.normalize import normalize

TS = 1_722_100_000_000


def motor(**kwargs) -> FeedbackEngine:
    return FeedbackEngine(**kwargs)


def sinal_execucao(code: Code = Code.ARMS_TOO_LOW) -> QualitySignal:
    return QualitySignal(code=code, value=95.0, rep_index=1)


def aviso_cena(code: Code = Code.OUT_OF_FRAME) -> SceneWarning:
    return SceneWarning(code=code, severity=Severity.WARNING, hint="dica de cena")


# --------------------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------------------


def test_catalogo_cobre_todos_os_codigos_do_contrato() -> None:
    """Código sem mensagem seria um feedback que nunca aparece."""
    catalogo = FeedbackCatalog.load()

    assert catalogo.missing() == set()


def test_catalogo_traz_mensagem_dica_severidade_e_prioridade() -> None:
    entrada = FeedbackCatalog.load().get(Code.ARMS_TOO_LOW)

    assert entrada is not None
    assert "braços" in entrada.message
    assert entrada.hint
    assert entrada.severity is Severity.INFO
    assert entrada.priority > 0


def test_cena_tem_prioridade_melhor_que_execucao_no_catalogo() -> None:
    catalogo = FeedbackCatalog.load()

    cena = catalogo.get(Code.OUT_OF_FRAME)
    execucao = catalogo.get(Code.ARMS_TOO_LOW)
    assert cena.priority < execucao.priority


def test_catalogo_e_pt_br_e_fica_fora_do_codigo() -> None:
    assert DEFAULT_CATALOG_PATH.name == "catalog.pt-BR.yaml"
    assert DEFAULT_CATALOG_PATH.exists()


def test_codigo_desconhecido_no_catalogo_e_erro(tmp_path) -> None:
    arquivo = tmp_path / "catalog.pt-BR.yaml"
    arquivo.write_text("CODIGO_INVENTADO:\n  message: oi\n", encoding="utf-8")

    with pytest.raises(ValueError, match="codigo desconhecido"):
        FeedbackCatalog.load(arquivo)


def test_entrada_sem_mensagem_e_erro(tmp_path) -> None:
    arquivo = tmp_path / "catalog.pt-BR.yaml"
    arquivo.write_text("ARMS_TOO_LOW:\n  hint: sem mensagem\n", encoding="utf-8")

    with pytest.raises(ValueError, match="sem `message`"):
        FeedbackCatalog.load(arquivo)


def test_catalogo_de_outro_idioma_pode_ser_carregado(tmp_path) -> None:
    """i18n é estrutura de arquivo, não código."""
    arquivo = tmp_path / "catalog.en-US.yaml"
    arquivo.write_text(
        "ARMS_TOO_LOW:\n  message: Extend your arms overhead\n  priority: 20\n", encoding="utf-8"
    )

    catalogo = FeedbackCatalog.load(arquivo)

    assert catalogo.get(Code.ARMS_TOO_LOW).message == "Extend your arms overhead"


# --------------------------------------------------------------------------------------
# Um feedback por vez, com prioridade
# --------------------------------------------------------------------------------------


def test_sinal_vira_feedback_com_o_texto_do_catalogo() -> None:
    saida = motor().push([sinal_execucao()], TS)

    assert len(saida) == 1
    assert isinstance(saida[0], FeedbackIssued)
    assert saida[0].code is Code.ARMS_TOO_LOW
    assert "braços" in saida[0].message


def test_no_maximo_um_feedback_por_vez() -> None:
    """SPEC-008: máximo 1 feedback simultâneo no HUD."""
    saida = motor().push(
        [sinal_execucao(Code.ARMS_TOO_LOW), sinal_execucao(Code.LEGS_TOO_CLOSED)], TS
    )

    assert len(saida) == 1


def test_cena_ganha_de_execucao_quando_os_dois_chegam_juntos() -> None:
    saida = motor().push([sinal_execucao(), aviso_cena()], TS)

    assert saida[0].code is Code.OUT_OF_FRAME


def test_sem_sinal_nao_ha_feedback() -> None:
    assert motor().push([], TS) == []


def test_evento_sem_codigo_e_ignorado() -> None:
    """`rep.detected` alimenta feedback positivo, que é Fase Evolução."""
    from workers.shared.events import Phase, RepDetected

    saida = motor().push([RepDetected(rep_count=1, phase=Phase.CLOSED, duration_ms=900)], TS)

    assert saida == []


def test_severidade_do_aviso_de_cena_e_preservada() -> None:
    saida = motor().push([aviso_cena()], TS)

    assert saida[0].severity is Severity.WARNING


# --------------------------------------------------------------------------------------
# Throttle (critério 1 da SPEC-008)
# --------------------------------------------------------------------------------------


def test_mesmo_codigo_no_maximo_uma_vez_a_cada_quatro_segundos() -> None:
    engine = motor()

    primeiro = engine.push([sinal_execucao()], TS)
    logo_depois = engine.push([sinal_execucao()], TS + THROTTLE_MS - 1)
    depois_da_janela = engine.push([sinal_execucao()], TS + THROTTLE_MS)

    assert len(primeiro) == 1
    assert logo_depois == []
    assert len(depois_da_janela) == 1


def test_rep_pregui_osa_continua_gera_feedback_a_cada_4s_nao_a_cada_rep() -> None:
    """Critério 1 da SPEC-008, com o pipeline real (FSM → engine)."""
    engine = motor()
    analyzer = get_analyzer("jumping_jack")
    emitidos: list[FeedbackIssued] = []

    # 12 reps preguiçosas seguidas: 1 rep/s ⇒ 12 s de sessão.
    for frame in normalize(sequence(jumping_jack_poses(12, amplitude=0.6))):
        sinais = feed(analyzer, frame)
        emitidos.extend(engine.push(sinais, frame.ts))

    assert analyzer.summary()["quality_signals"][Code.ARMS_TOO_LOW.value] == 12, "12 tentativas"
    braços = [msg for msg in emitidos if msg.code is Code.ARMS_TOO_LOW]
    assert 3 <= len(braços) <= 4, f"12 s / 4 s ⇒ 3 a 4 feedbacks, saiu {len(braços)}"


def test_codigos_diferentes_tem_throttle_independente() -> None:
    engine = motor()

    primeiro = engine.push([sinal_execucao(Code.ARMS_TOO_LOW)], TS)
    segundo = engine.push([sinal_execucao(Code.LEGS_TOO_CLOSED)], TS + 100)

    assert primeiro[0].code is Code.ARMS_TOO_LOW
    assert segundo[0].code is Code.LEGS_TOO_CLOSED


def test_throttle_de_um_codigo_deixa_o_proximo_da_fila_passar() -> None:
    engine = motor()
    engine.push([sinal_execucao(Code.ARMS_TOO_LOW)], TS)

    saida = engine.push(
        [sinal_execucao(Code.ARMS_TOO_LOW), sinal_execucao(Code.LEGS_TOO_CLOSED)], TS + 100
    )

    assert saida[0].code is Code.LEGS_TOO_CLOSED


def test_throttle_e_parametrizavel() -> None:
    engine = motor(throttle_ms=0)

    assert engine.push([sinal_execucao()], TS)
    assert engine.push([sinal_execucao()], TS + 1)


# --------------------------------------------------------------------------------------
# Supressão por cena (critério 2 da SPEC-008)
# --------------------------------------------------------------------------------------


def test_out_of_frame_suprime_feedback_de_execucao_enquanto_ativo() -> None:
    engine = motor()

    engine.push([aviso_cena()], TS)
    durante = engine.push([sinal_execucao()], TS + 500)

    assert durante == [], "criticar amplitude de quem esta fora do quadro nao ajuda ninguem"


def test_execucao_volta_a_falar_depois_que_a_cena_resolve() -> None:
    engine = motor()
    engine.push([aviso_cena()], TS)

    depois = engine.push([sinal_execucao()], TS + SCENE_SUPPRESS_MS)

    assert len(depois) == 1
    assert depois[0].code is Code.ARMS_TOO_LOW


def test_cena_repetida_estende_a_supressao() -> None:
    engine = motor()
    engine.push([aviso_cena()], TS)

    engine.push([aviso_cena()], TS + 2_000)  # o validador repete a cada 2 s
    durante = engine.push([sinal_execucao()], TS + 4_000)

    assert durante == []


def test_supressao_nao_impede_o_proprio_aviso_de_cena() -> None:
    engine = motor()
    engine.push([aviso_cena()], TS)

    outro = engine.push([aviso_cena(Code.TOO_FAR)], TS + 500)

    assert outro[0].code is Code.TOO_FAR


# --------------------------------------------------------------------------------------
# Estado da sessão
# --------------------------------------------------------------------------------------


def test_motor_conta_o_que_emitiu_para_o_relatorio() -> None:
    """SPEC-008: todos os feedbacks emitidos entram no estado da sessão."""
    engine = motor(throttle_ms=0)

    engine.push([sinal_execucao()], TS)
    engine.push([sinal_execucao()], TS + 1)
    engine.push([aviso_cena()], TS + 2)

    assert engine.counts == {Code.ARMS_TOO_LOW.value: 2, Code.OUT_OF_FRAME.value: 1}


def test_resumo_da_sessao_separa_o_que_foi_detectado_do_que_foi_dito() -> None:
    """O relatório (SPEC-010) precisa dos dois números: tentativas e avisos."""
    from workers.analysis_worker.router import AnalysisRouter
    from workers.shared.events import Mode, PoseFrame, SessionStarted, Source
    from workers.shared.events import make_envelope as envelopar

    router = AnalysisRouter()
    frames = sequence(jumping_jack_poses(12, amplitude=0.6))
    router.handle(
        envelopar(
            SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
            session_id="s1",
            ts=frames[0].ts,
            seq=0,
            source=Source.SYSTEM,
        )
    )
    for frame in frames:
        router.handle(
            envelopar(
                PoseFrame(landmarks=[list(p) for p in frame.landmarks]),
                session_id="s1",
                ts=frame.ts,
                seq=frame.seq,
                source=Source.EDGE,
            )
        )

    resumo = router.sessions["s1"].summary()

    detectados = resumo["quality_signals"][Code.ARMS_TOO_LOW.value]
    ditos = resumo["feedback_issued"][Code.ARMS_TOO_LOW.value]
    assert detectados == 12
    assert 3 <= ditos <= 4, "o throttle é a diferença entre detectar e falar"


def test_cada_sessao_tem_seu_proprio_throttle() -> None:
    primeiro, segundo = motor(), motor()

    primeiro.push([sinal_execucao()], TS)

    assert segundo.push([sinal_execucao()], TS), "o silencio de uma sessao nao cala outra"


# --------------------------------------------------------------------------------------
# Integração no worker
# --------------------------------------------------------------------------------------


def test_worker_publica_feedback_issued_junto_dos_sinais() -> None:
    from workers.analysis_worker.main import BATCH, run
    from workers.shared.bus import InMemoryBus
    from workers.shared.events import EventType, Mode, PoseFrame, SessionStarted, Source
    from workers.shared.events import make_envelope as envelopar

    bus = InMemoryBus()
    frames = sequence(jumping_jack_poses(6, amplitude=0.6))
    bus.feed(
        __import__("workers.shared.events", fromlist=["Stream"]).Stream.POSE_FRAMES,
        envelopar(
            SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
            session_id="s1",
            ts=frames[0].ts,
            seq=0,
            source=Source.SYSTEM,
        ),
        *[
            envelopar(
                PoseFrame(landmarks=[list(p) for p in frame.landmarks]),
                session_id="s1",
                ts=frame.ts,
                seq=frame.seq,
                source=Source.EDGE,
            )
            for frame in frames
        ],
    )

    run(bus, consumer="teste", max_batches=len(frames) // BATCH + 2)

    sinais = bus.published_of(EventType.QUALITY_SIGNAL)
    feedbacks = bus.published_of(EventType.FEEDBACK_ISSUED)
    assert sinais, "o sinal cru continua no stream (dataset e relatorio precisam dele)"
    assert feedbacks, "e o feedback humano sai para o HUD"
    assert len(feedbacks) < len(sinais), "o throttle e o ponto: menos feedback que sinal"


def test_cena_ruim_no_worker_gera_feedback_de_cena() -> None:
    from workers.analysis_worker.main import BATCH, run
    from workers.shared.bus import InMemoryBus
    from workers.shared.events import EventType, Mode, PoseFrame, SessionStarted, Source, Stream
    from workers.shared.events import make_envelope as envelopar

    bus = InMemoryBus()
    frames = sequence(still_poses(60), visibility=0.2)
    bus.feed(
        Stream.POSE_FRAMES,
        envelopar(
            SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
            session_id="s1",
            ts=frames[0].ts,
            seq=0,
            source=Source.SYSTEM,
        ),
        *[
            envelopar(
                PoseFrame(landmarks=[list(p) for p in frame.landmarks]),
                session_id="s1",
                ts=frame.ts,
                seq=frame.seq,
                source=Source.EDGE,
            )
            for frame in frames
        ],
    )

    run(bus, consumer="teste", max_batches=len(frames) // BATCH + 2)

    feedbacks = bus.published_of(EventType.FEEDBACK_ISSUED)
    assert feedbacks
    from workers.shared.events import FeedbackIssued as Emitido

    assert Emitido.from_data(feedbacks[0].data).code is Code.OUT_OF_FRAME
