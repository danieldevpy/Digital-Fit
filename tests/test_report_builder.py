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
    SetMode,
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
    config_version: int = 0,
    set_mode: SetMode = SetMode.LIVRE,
    target_reps: int = 0,
    set_index: int = 0,
    set_total: int = 0,
) -> list:
    """Uma sessão inteira em eventos: abertura, calibração, N reps espalhadas, fim."""
    eventos = [
        evento(
            SessionStarted(
                exercise=exercise,
                mode=Mode.EDGE,
                duration_s=30,
                config_version=config_version,
                set_mode=set_mode,
                target_reps=target_reps,
                set_index=set_index,
                set_total=set_total,
            ),
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
                RepDetected(rep_count=indice + 1, phase=Phase.REST, duration_ms=intervalo),
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


def test_relatorio_carrega_a_versao_de_configuracao_da_abertura():
    """T-075: o carimbo do `session.started` chega inteiro ao relatório."""
    acumulador = ReportAccumulator()
    relatorio = None
    for envelope in sessao_completa(config_version=42):
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.config_version == 42
    assert relatorio.to_dict()["config_version"] == 42


def test_sessao_sem_abertura_diz_versao_zero():
    """Builder que subiu no meio da sessão não viu o carimbo — e não inventa um.

    `0` é "não registrada", e é a mesma escolha já feita para o exercício e o modo: o que
    faltou é dito, não deduzido da configuração de agora (que é justamente o que quebraria a
    promessa de relatório derivável por replay).
    """
    acumulador = ReportAccumulator()
    relatorio = None
    for envelope in sessao_completa(config_version=42)[1:]:  # sem o `session.started`
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.config_version == 0


def test_relatorio_carrega_os_carimbos_de_serie_da_abertura():
    """T-134: os quatro campos da SPEC-023 chegam inteiros ao relatório — consolidação, não
    decisão (quem decide o fim por meta é o analysis-worker, T-135)."""
    acumulador = ReportAccumulator()
    relatorio = None
    for envelope in sessao_completa(
        set_mode=SetMode.CONTADO, target_reps=15, set_index=2, set_total=3
    ):
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.set_mode == "contado"
    assert relatorio.target_reps == 15
    assert relatorio.set_index == 2
    assert relatorio.set_total == 3
    assert relatorio.to_dict()["set_mode"] == "contado"


def test_sessao_sem_abertura_usa_defaults_de_serie():
    """Mesma regra do `config_version`: builder que não viu o `session.started` não inventa
    modo contado nem posição de série — cai no modo livre avulso, que é o default do contrato.
    """
    acumulador = ReportAccumulator()
    relatorio = None
    for envelope in sessao_completa(
        set_mode=SetMode.CONTADO, target_reps=15, set_index=2, set_total=3
    )[1:]:  # sem o `session.started`
        relatorio = acumulador.push(envelope) or relatorio

    assert relatorio is not None
    assert relatorio.set_mode == SetMode.LIVRE.value
    assert relatorio.target_reps == 0
    assert relatorio.set_index == 0
    assert relatorio.set_total == 0


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
        evento(RepDetected(rep_count=1, phase=Phase.REST, duration_ms=900), ts=inicio + 1_000),
        evento(RepDetected(rep_count=2, phase=Phase.REST, duration_ms=900), ts=inicio + 4_000),
        evento(RepDetected(rep_count=3, phase=Phase.REST, duration_ms=900), ts=inicio + 12_000),
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
        evento(RepDetected(rep_count=17, phase=Phase.REST, duration_ms=900), ts=inicio + 25_000)
    )
    acumulador.push(
        evento(RepDetected(rep_count=18, phase=Phase.REST, duration_ms=900), ts=inicio + 27_000)
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
    for envelope in sessao_completa(
        reps=11,
        duracao_ms=22_000,
        set_mode=SetMode.CONTADO,
        target_reps=11,
        set_index=1,
        set_total=3,
    ):
        relatorio = acumulador.push(envelope) or relatorio
    assert relatorio is not None

    persist(relatorio)
    persist(relatorio)  # reprocessamento após crash, ou replay do stream

    assert SessionResult.objects.count() == 1
    salvo = SessionResult.objects.get(session_id="s-1")
    assert salvo.rep_count == 11
    assert salvo.cadence_rpm == 30.0
    assert sum(salvo.cadence_windows) == 11
    # T-134: as colunas aditivas de série chegam ao Postgres, não só ao dataclass em memória.
    assert salvo.set_mode == "contado"
    assert salvo.target_reps == 11
    assert salvo.set_index == 1
    assert salvo.set_total == 3


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
    # T-134: sessão avulsa (sem série) reporta os defaults do contrato, não ausência de campo.
    assert corpo["set_mode"] == "livre"
    assert corpo["target_reps"] == 0
    assert corpo["set_index"] == 0
    assert corpo["set_total"] == 0


@pytest.mark.django_db
def test_relatorio_ainda_nao_pronto_responde_pending(client):
    """404 aqui significa "ainda não", e o cliente precisa saber a diferença."""
    resposta = client.get("/api/sessions/desconhecida/report")

    assert resposta.status_code == 404
    assert resposta.json()["pending"] is True


# ======================================================================================
# Os dois relógios (T-078 / Descoberta [A/T-077]).
# ======================================================================================

#: Um celular adiantado 30 dias. Acima dos 24,8 dias em que `PositiveIntegerField` estoura —
#: é o cenário que matou o processo com `DataError: integer out of range`.
_ADIANTADO_MS = 30 * 24 * 60 * 60 * 1000


def _sessao_com_relogios(desvio_do_servidor_ms: int) -> ReportAccumulator:
    """Sessão normal de 30 s, com o `session.started` da API num relógio deslocado.

    É o desenho real: `api/sessions.py` publica `session.started` com o relógio do SERVIDOR, e
    todo o resto sai do analysis-worker com o `ts` do frame (relógio do cliente).
    """
    acc = ReportAccumulator()
    acc.push(
        evento(
            SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30),
            ts=BASE_TS + desvio_do_servidor_ms,
        )
    )
    acc.push(
        evento(
            SessionCalibrated(
                torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=30
            ),
            ts=BASE_TS,
            seq=1,
        )
    )
    for i in range(20):
        acc.push(
            evento(
                RepDetected(rep_count=i + 1, phase=Phase.REST, duration_ms=1500),
                ts=BASE_TS + 1500 * (i + 1),
                seq=2 + i,
            )
        )
    return acc


def test_o_relogio_do_servidor_nao_entra_na_duracao() -> None:
    """O caso que a Descoberta `[A/T-077]` descreve, medido.

    Antes da T-078 o `session.started` entrava no mesmo `last_ts` dos eventos de frame, e a
    duração virava a diferença entre dois relógios. Com 30 dias de desvio ela estourava o
    `PositiveIntegerField` e matava o report-builder.
    """
    acc = _sessao_com_relogios(_ADIANTADO_MS)

    relatorio = acc.push(
        evento(
            SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=20),
            ts=BASE_TS + 30_000,
            seq=99,
        )
    )

    assert relatorio is not None
    assert relatorio.duration_ms == 30_000
    assert relatorio.cadence_rpm == pytest.approx(40.0)


def test_o_desvio_do_servidor_nao_muda_nada_no_caminho_feliz() -> None:
    """Servidor e cliente em sincronia dão o MESMO número de sempre — a correção não pode ter
    mexido no caso normal, que é a razão de este teste existir ao lado do de cima."""
    alinhado = _sessao_com_relogios(0)
    adiantado = _sessao_com_relogios(_ADIANTADO_MS)
    atrasado = _sessao_com_relogios(-_ADIANTADO_MS)

    fim = evento(
        SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=20),
        ts=BASE_TS + 30_000,
        seq=99,
    )

    duracoes = {acc.push(fim).duration_ms for acc in (alinhado, adiantado, atrasado)}

    assert duracoes == {30_000}


def test_duracao_implausivel_vira_zero_em_vez_de_derrubar_o_processo() -> None:
    """Relógio do CLIENTE andando no meio da sessão — o resíduo que a exclusão não cobre.

    Zero, e não o teto: gravar o teto seria inventar um tempo que ninguém treinou, e a cadência
    derivada dele mentiria com cara de número medido.
    """
    acc = ReportAccumulator()
    acc.push(
        evento(SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=30), ts=BASE_TS)
    )
    acc.push(
        evento(
            SessionCalibrated(
                torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=30
            ),
            ts=BASE_TS,
            seq=1,
        )
    )
    # O celular pulou 30 dias entre a calibração e o fim.
    relatorio = acc.push(
        evento(
            SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=20),
            ts=BASE_TS + _ADIANTADO_MS,
            seq=2,
        )
    )

    assert relatorio.duration_ms == 0
    assert relatorio.cadence_rpm == 0.0
    assert relatorio.cadence_windows == []


def test_o_teto_sai_da_duracao_ADMITIDA_quando_ela_existe() -> None:
    """Sessão de 30 s que reporta 10 minutos é implausível; a mesma duração numa sessão que a
    API admitiu como 600 s é honesta. O teto vem da sessão, não de um palpite."""

    def sessao(duration_s: int, fim_offset_ms: int):
        acc = ReportAccumulator()
        acc.push(
            evento(
                SessionStarted(exercise="jumping_jack", mode=Mode.EDGE, duration_s=duration_s),
                ts=BASE_TS,
            )
        )
        acc.push(
            evento(
                SessionCalibrated(
                    torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=30
                ),
                ts=BASE_TS,
                seq=1,
            )
        )
        return acc.push(
            evento(
                SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=5),
                ts=BASE_TS + fim_offset_ms,
                seq=2,
            )
        )

    dez_minutos = 10 * 60_000

    assert sessao(30, dez_minutos).duration_ms == 0
    assert sessao(600, dez_minutos).duration_ms == dez_minutos


def test_sem_session_started_o_teto_cai_no_absoluto() -> None:
    """Builder que subiu no meio da sessão não sabe a duração admitida — e não pode recusar uma
    sessão honesta por causa disso, nem aceitar 30 dias."""

    def sessao(fim_offset_ms: int):
        acc = ReportAccumulator()
        acc.push(
            evento(
                SessionCalibrated(
                    torso=0.3, shoulder_width=0.2, shoulder_span=1.5, wrist_rest_y=0.8, samples=30
                ),
                ts=BASE_TS,
                seq=1,
            )
        )
        return acc.push(
            evento(
                SessionCompleted(reason=SessionEndReason.COMPLETED, rep_count=5),
                ts=BASE_TS + fim_offset_ms,
                seq=2,
            )
        )

    uma_hora = 60 * 60_000

    assert sessao(uma_hora).duration_ms == uma_hora
    assert sessao(_ADIANTADO_MS).duration_ms == 0


def test_a_duracao_cabe_no_campo_do_postgres() -> None:
    """A guarda que fecha o `DataError` da Descoberta: qualquer saída cabe num
    `PositiveIntegerField` (2³¹ − 1)."""
    from workers.report_builder.builder import TETO_DE_DURACAO_MS

    assert TETO_DE_DURACAO_MS < 2**31 - 1


def test_so_o_session_started_carrega_o_relogio_do_servidor() -> None:
    """Trava de manutenção: um evento novo publicado pela API entraria calado na linha do tempo
    do cliente e traria a T-078 de volta. Este teste obriga a revisar a lista."""
    from workers.report_builder.builder import _EVENTOS_DO_RELOGIO_DO_SERVIDOR

    assert set(_EVENTOS_DO_RELOGIO_DO_SERVIDOR) == {EventType.SESSION_STARTED}
