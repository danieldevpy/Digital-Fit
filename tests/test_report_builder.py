"""Consolidação da sessão em relatório (SPEC-010 / T-020).

Dois níveis, deliberadamente separados:

- o `ReportAccumulator` é puro e testado com listas de eventos — é onde vivem cadência,
  janelas e contagens;
- o `ReportWorker` é o encanamento (consumir, gravar, confirmar), testado com o barramento em
  memória e um `sink` de mentira. Os testes de ack e de crash estão aqui: eles são sobre
  *quando* se confirma um evento, não sobre aritmética de cadência.
"""

from __future__ import annotations

import time

import pytest
from api.management.commands.report_builder import GROUP, ReportWorker

from workers.report_builder.builder import CADENCE_WINDOW_MS, ReportAccumulator
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    Code,
    EventType,
    FeedbackIssued,
    Mode,
    Phase,
    RepDetected,
    SceneWarning,
    SessionCalibrated,
    SessionCompleted,
    SessionEndReason,
    SessionReportReady,
    SessionStarted,
    Severity,
    Source,
    Stream,
    make_envelope,
)

BASE_TS = 1_722_100_000_000


def evento(payload, *, ts: int, seq: int = 0, session_id: str = "s-1"):
    return make_envelope(payload, session_id=session_id, ts=ts, seq=seq, source=Source.SYSTEM)


def sessao_completa(
    *,
    reps: int = 20,
    duracao_ms: int = 30_000,
    session_id: str = "s-1",
    exercise: str = "jumping_jack",
) -> list:
    """Uma sessão inteira em eventos: abertura, calibração, N reps espalhadas, fim."""
    eventos = [
        evento(
            SessionStarted(exercise=exercise, mode=Mode.EDGE, duration_s=30),
            ts=BASE_TS,
            session_id=session_id,
        ),
        evento(
            SessionCalibrated(
                torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=12
            ),
            ts=BASE_TS + 1_000,
            session_id=session_id,
        ),
    ]
    inicio = BASE_TS + 1_000
    intervalo = duracao_ms // max(reps, 1)
    for indice in range(reps):
        eventos.append(
            evento(
                RepDetected(rep_count=indice + 1, phase=Phase.CLOSED, duration_ms=intervalo),
                ts=inicio + intervalo * (indice + 1),
                seq=indice + 1,
                session_id=session_id,
            )
        )
    eventos.append(
        evento(
            SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=reps),
            ts=inicio + duracao_ms,
            seq=reps + 1,
            session_id=session_id,
        )
    )
    return eventos


# --------------------------------------------------------------------- acumulador


def test_relatorio_so_sai_no_fim_da_sessao():
    acumulador = ReportAccumulator()
    eventos = sessao_completa()

    saidas = [acumulador.push(envelope) for envelope in eventos]

    assert all(saida is None for saida in saidas[:-1])
    assert saidas[-1] is not None


def test_consolida_reps_duracao_e_cadencia():
    acumulador = ReportAccumulator()
    relatorio = None
    for envelope in sessao_completa(reps=20, duracao_ms=30_000):
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.rep_count == 20
    assert relatorio.exercise == "jumping_jack"
    assert relatorio.mode == "edge"
    assert relatorio.reason == SessionEndReason.COMPLETED.value
    # 30 s de exercício, contados da calibração — não do primeiro evento da sessão.
    assert relatorio.duration_ms == 30_000
    assert relatorio.cadence_rpm == 40.0
    assert relatorio.calibration_samples == 12


def test_duracao_ignora_a_preparacao():
    """O countdown não é treino: a duração começa na calibração (SPEC-004/T-019)."""
    acumulador = ReportAccumulator()
    eventos = sessao_completa(reps=10, duracao_ms=20_000)
    # A sessão abriu 8 s antes de calibrar — pessoa se posicionando.
    eventos[0] = evento(
        SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30), ts=BASE_TS - 8_000
    )

    relatorio = None
    for envelope in eventos:
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.duration_ms == 20_000  # e não 28_000


def test_janelas_de_cadencia_cobrem_a_sessao_inteira_com_buracos():
    """Uma janela vazia é informação: é a pausa que o usuário deu."""
    acumulador = ReportAccumulator()
    inicio = BASE_TS + 1_000
    eventos = [
        evento(
            SessionCalibrated(
                torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=10
            ),
            ts=inicio,
        ),
        # 2 reps na primeira janela, nenhuma na segunda, 1 na terceira.
        evento(RepDetected(rep_count=1, phase=Phase.CLOSED, duration_ms=900), ts=inicio + 1_000),
        evento(RepDetected(rep_count=2, phase=Phase.CLOSED, duration_ms=900), ts=inicio + 4_000),
        evento(RepDetected(rep_count=3, phase=Phase.CLOSED, duration_ms=900), ts=inicio + 12_000),
        evento(
            SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=3), ts=inicio + 15_000
        ),
    ]

    relatorio = None
    for envelope in eventos:
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.cadence_windows == [2, 0, 1]
    assert len(relatorio.cadence_windows) == 15_000 // CADENCE_WINDOW_MS


def test_conta_feedbacks_e_avisos_de_cena_por_codigo():
    acumulador = ReportAccumulator()
    inicio = BASE_TS + 1_000
    eventos = [
        evento(
            SessionCalibrated(
                torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=10
            ),
            ts=inicio,
        ),
        evento(
            FeedbackIssued(
                code=Code.ARMS_TOO_LOW, severity=Severity.WARNING, message="Suba mais os braços"
            ),
            ts=inicio + 2_000,
        ),
        evento(
            FeedbackIssued(
                code=Code.ARMS_TOO_LOW, severity=Severity.WARNING, message="Suba mais os braços"
            ),
            ts=inicio + 6_000,
        ),
        evento(SceneWarning(code=Code.TOO_FAR, severity=Severity.WARNING), ts=inicio + 3_000),
        evento(
            SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=5), ts=inicio + 10_000
        ),
    ]

    relatorio = None
    for envelope in eventos:
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.feedback_counts == {Code.ARMS_TOO_LOW.value: 2}
    assert relatorio.scene_warning_counts == {Code.TOO_FAR.value: 1}


def test_sessao_sem_calibracao_tem_duracao_zero_e_nenhuma_janela():
    """Terminou na preparação: não houve exercício, e o relatório não inventa um."""
    acumulador = ReportAccumulator()
    acumulador.push(
        evento(SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30), ts=BASE_TS)
    )
    relatorio = acumulador.push(
        evento(SessionCompleted(reason=SessionEndReason.NO_DATA, rep_count=0), ts=BASE_TS + 12_000)
    )

    assert relatorio is not None
    assert relatorio.duration_ms == 0
    assert relatorio.cadence_rpm == 0.0
    assert relatorio.cadence_windows == []
    assert relatorio.reason == SessionEndReason.NO_DATA.value


def test_total_de_reps_vem_do_evento_de_fim_nao_da_contagem_de_eventos():
    """Builder que subiu no meio da sessão ainda reporta o total certo."""
    acumulador = ReportAccumulator()
    inicio = BASE_TS + 1_000
    acumulador.push(
        evento(
            SessionCalibrated(
                torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=10
            ),
            ts=inicio,
        )
    )
    # Só viu as duas últimas reps de dezoito.
    acumulador.push(
        evento(RepDetected(rep_count=17, phase=Phase.CLOSED, duration_ms=900), ts=inicio + 25_000)
    )
    acumulador.push(
        evento(RepDetected(rep_count=18, phase=Phase.CLOSED, duration_ms=900), ts=inicio + 27_000)
    )
    relatorio = acumulador.push(
        evento(
            SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=18), ts=inicio + 30_000
        )
    )

    assert relatorio is not None
    assert relatorio.rep_count == 18
    assert sum(relatorio.cadence_windows) == 2  # o gráfico, esse sim, sai incompleto


def test_sessoes_simultaneas_nao_se_misturam():
    acumulador = ReportAccumulator()
    a = sessao_completa(reps=5, duracao_ms=10_000, session_id="s-a", exercise="jumping_jack")
    b = sessao_completa(reps=9, duracao_ms=10_000, session_id="s-b", exercise="jumping_jack")

    relatorios = {}
    # Intercalados, como chegariam de dois usuários ao mesmo tempo.
    for envelope in [item for par in zip(a, b, strict=False) for item in par]:
        saida = acumulador.push(envelope)
        if saida is not None:
            relatorios[saida.session_id] = saida
    for envelope in a[len(b) :] + b[len(a) :]:
        saida = acumulador.push(envelope)
        if saida is not None:
            relatorios[saida.session_id] = saida

    assert relatorios["s-a"].rep_count == 5
    assert relatorios["s-b"].rep_count == 9
    assert acumulador.open_sessions == 0


def test_o_proprio_report_ready_nao_abre_sessao():
    """O sino do builder volta pelo stream; ele não pode ressuscitar a sessão que fechou."""
    acumulador = ReportAccumulator()
    acumulador.push(evento(SessionReportReady(), ts=BASE_TS))
    assert acumulador.open_sessions == 0


# ------------------------------------------------------------------------ worker


class SinkFalho:
    """Sink que recusa a primeira gravação — imita o Postgres fora do ar."""

    def __init__(self) -> None:
        self.recebidos = []
        self.falhar = True

    def __call__(self, relatorio) -> None:
        if self.falhar:
            self.falhar = False
            raise RuntimeError("banco fora do ar")
        self.recebidos.append(relatorio)


def test_worker_grava_e_anuncia_o_relatorio():
    bus = InMemoryBus()
    gravados = []
    worker = ReportWorker(bus, sink=gravados.append)
    bus.feed(Stream.EVENTS_ANALYSIS, *sessao_completa(reps=7, duracao_ms=21_000))

    worker.start()
    worker.run_once()

    assert [r.rep_count for r in gravados] == [7]
    avisos = bus.published_of(EventType.SESSION_REPORT_READY)
    assert len(avisos) == 1
    assert avisos[0].session_id == "s-1"
    # O aviso sai na saída da análise, que é de onde o gateway empurra ao cliente.
    assert bus.published_in(Stream.EVENTS_ANALYSIS) == avisos


def test_eventos_so_sao_confirmados_quando_o_relatorio_esta_gravado():
    """Critério 2 da SPEC-010: crash no meio ⇒ nada confirmado ⇒ nada perdido."""
    bus = InMemoryBus()
    eventos = sessao_completa(reps=4, duracao_ms=12_000)
    worker = ReportWorker(bus, sink=lambda relatorio: None)

    # Só a sessão pela metade: nenhum `session.completed` ainda.
    bus.feed(Stream.EVENTS_ANALYSIS, *eventos[:-1])
    worker.start()
    worker.run_once()

    assert bus.acked == []
    pendentes = bus.consume_pending(Stream.EVENTS_ANALYSIS, group=GROUP, consumer=worker.consumer)
    assert len(pendentes) == len(eventos) - 1


def test_apos_crash_o_relatorio_e_reconstruido_das_pendencias():
    bus = InMemoryBus()
    eventos = sessao_completa(reps=6, duracao_ms=18_000)

    # Processo 1: consome tudo menos o fim e "morre" sem confirmar nada.
    bus.feed(Stream.EVENTS_ANALYSIS, *eventos[:-1])
    ReportWorker(bus, sink=lambda relatorio: None).run_once()
    assert bus.acked == []

    # Processo 2: sobe com o MESMO nome de consumidor, redrena as pendências e recebe o fim.
    gravados = []
    reiniciado = ReportWorker(bus, sink=gravados.append)
    reiniciado.start()
    bus.feed(Stream.EVENTS_ANALYSIS, eventos[-1])
    reiniciado.run_once()

    assert len(gravados) == 1
    relatorio = gravados[0]
    assert relatorio.rep_count == 6
    # Reconstruído inteiro, não só o pedaço pós-restart.
    assert sum(relatorio.cadence_windows) == 6
    assert len(bus.acked) == len(eventos)


def test_falha_ao_gravar_nao_confirma_e_a_sessao_volta():
    bus = InMemoryBus()
    eventos = sessao_completa(reps=3, duracao_ms=9_000)
    sink = SinkFalho()

    bus.feed(Stream.EVENTS_ANALYSIS, *eventos)
    worker = ReportWorker(bus, sink=sink)
    worker.start()
    worker.run_once()

    # Banco recusou: nada confirmado, nenhum aviso publicado.
    assert bus.acked == []
    assert bus.published_of(EventType.SESSION_REPORT_READY) == []

    # Reinício: as pendências voltam e agora o banco aceita.
    reiniciado = ReportWorker(bus, sink=sink)
    reiniciado.start()

    assert [r.rep_count for r in sink.recebidos] == [3]
    assert len(bus.acked) == len(eventos)


def test_sessao_abandonada_e_evacuada_e_confirmada():
    """Sem isso, uma sessão que nunca fecha segura suas mensagens pendentes para sempre."""
    bus = InMemoryBus()
    eventos = sessao_completa(reps=2, duracao_ms=6_000)[:-1]
    bus.feed(Stream.EVENTS_ANALYSIS, *eventos)

    worker = ReportWorker(bus, sink=lambda relatorio: None)
    worker.start()
    worker.run_once()
    assert bus.acked == []

    # Uma hora depois **no relógio do servidor** — que é o único que a evacuação olha. Usar o
    # `ts` dos eventos aqui testaria a comparação errada, justamente a que este código evita.
    velhas = worker._evacuar_velhas(now_ms=int(time.time() * 1000) + 60 * 60_000)

    assert velhas == ["s-1"]
    assert len(bus.acked) == len(eventos)
    assert worker.accumulator.open_sessions == 0


# ------------------------------------------------------------------- persistência


@pytest.mark.django_db
def test_persist_faz_upsert_por_session_id():
    from api.management.commands.report_builder import persist
    from api.models import SessionResult

    acumulador = ReportAccumulator()
    relatorio = None
    for envelope in sessao_completa(reps=11, duracao_ms=22_000):
        relatorio = acumulador.push(envelope) or relatorio
    assert relatorio is not None

    persist(relatorio)
    persist(relatorio)  # reprocessamento após crash, ou replay do stream

    assert SessionResult.objects.count() == 1
    salvo = SessionResult.objects.get(session_id="s-1")
    assert salvo.rep_count == 11
    assert salvo.cadence_rpm == 30.0
    assert sum(salvo.cadence_windows) == 11


@pytest.mark.django_db
def test_relatorio_pela_api(client):
    from api.management.commands.report_builder import persist

    acumulador = ReportAccumulator()
    relatorio = None
    for envelope in sessao_completa(reps=15, duracao_ms=30_000):
        relatorio = acumulador.push(envelope) or relatorio
    assert relatorio is not None
    persist(relatorio)

    resposta = client.get("/api/sessions/s-1/report")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["rep_count"] == 15
    assert corpo["exercise"] == "jumping_jack"
    assert corpo["cadence_rpm"] == 30.0
    assert len(corpo["cadence_windows"]) == 6


@pytest.mark.django_db
def test_relatorio_ainda_nao_pronto_responde_pending(client):
    """404 aqui significa "ainda não", e o cliente precisa saber a diferença."""
    resposta = client.get("/api/sessions/desconhecida/report")

    assert resposta.status_code == 404
    assert resposta.json()["pending"] is True
