"""dataset-writer: Parquet por sessão (SPEC-010 / T-021).

Três níveis, deliberadamente separados:

- o `FrameCollector` é puro e testado com listas de eventos — carência, abandono, tetos;
- o Parquet é testado **lendo com pandas**, porque é essa a promessa do critério 3;
- o `DatasetWriter` é o encanamento (dois streams, ack, shutdown), com barramento em memória.
"""

from __future__ import annotations

import pandas as pd
import pytest

from workers.dataset_writer.collector import (
    FLUSH_GRACE_MS,
    MAX_FRAMES,
    STALE_MS,
    UNKNOWN_EXERCISE,
    FrameCollector,
)
from workers.dataset_writer.main import GROUP, DatasetWriter
from workers.dataset_writer.parquet import (
    COORD_COLUMNS,
    SCHEMA_VERSION,
    build_table,
    write_session,
)
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    LANDMARK_COUNT,
    Mode,
    PoseFrame,
    SessionCapability,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    Source,
    Stream,
    make_envelope,
)

BASE_TS = 1_722_100_000_000
#: Relógio do servidor nos testes — propositalmente longe do `ts` do cliente, para que
#: qualquer comparação indevida entre os dois apareça como falha.
BASE_NOW = 1_800_000_000_000


def landmarks(valor: float = 0.5) -> list[list[float]]:
    return [[valor, valor + 0.1, valor + 0.2, 0.9] for _ in range(LANDMARK_COUNT)]


def frame(*, seq: int, ts: int, session_id: str = "s-1", degraded: bool = False, valor=0.5):
    return make_envelope(
        PoseFrame(landmarks=landmarks(valor), degraded=degraded),
        session_id=session_id,
        ts=ts,
        seq=seq,
        source=Source.EDGE,
    )


def abertura(*, session_id: str = "s-1", exercise: str = "jumping_jack"):
    return make_envelope(
        SessionStarted(exercise=exercise, mode=Mode.EDGE, duration_s=30),
        session_id=session_id,
        ts=BASE_TS,
        seq=0,
        source=Source.SYSTEM,
    )


def enquadramento(
    *, session_id: str = "s-1", facing: str = "environment", orientation: str = "landscape"
):
    """`session.capability` como o servidor publica (SPEC-027 §Eventos)."""
    return make_envelope(
        SessionCapability(
            mode=Mode.EDGE,
            probe_fps=18.0,
            webgl=True,
            ua="teste",
            facing=facing,
            orientation=orientation,
        ),
        session_id=session_id,
        ts=BASE_TS,
        seq=1,
        source=Source.SYSTEM,
    )


def fim(*, session_id: str = "s-1", reason=SessionEndReason.COMPLETED, reps: int = 10):
    return make_envelope(
        SessionCompleted(reason=reason, rep_count=reps),
        session_id=session_id,
        ts=BASE_TS + 30_000,
        seq=99,
        source=Source.SYSTEM,
    )


def sessao_no_coletor(coletor: FrameCollector, *, n_frames: int = 3, session_id: str = "s-1"):
    coletor.push(abertura(session_id=session_id), now_ms=BASE_NOW)
    for i in range(n_frames):
        coletor.push(frame(seq=i + 1, ts=BASE_TS + i * 66, session_id=session_id), now_ms=BASE_NOW)


# ---------------------------------------------------------------- coletor (puro)


def test_sessao_fecha_com_os_frames_e_o_exercicio():
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=5)
    coletor.push(fim(), now_ms=BASE_NOW)

    prontas = coletor.due(BASE_NOW + FLUSH_GRACE_MS)
    assert len(prontas) == 1
    assert prontas[0].session_id == "s-1"
    assert prontas[0].exercise == "jumping_jack"
    assert [linha.seq for linha in prontas[0].rows] == [1, 2, 3, 4, 5]
    assert coletor.open_sessions == 0


def test_carencia_segura_a_cauda_da_sessao():
    """O `session.completed` vem por outro stream e pode ultrapassar os últimos frames."""
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=2)
    coletor.push(fim(), now_ms=BASE_NOW)

    # Ainda dentro da carência: nada fecha, e o frame atrasado entra.
    assert coletor.due(BASE_NOW + FLUSH_GRACE_MS - 1) == []
    coletor.push(frame(seq=3, ts=BASE_TS + 200), now_ms=BASE_NOW + 100)

    prontas = coletor.due(BASE_NOW + FLUSH_GRACE_MS)
    assert [linha.seq for linha in prontas[0].rows] == [1, 2, 3]


def test_segundo_completed_nao_estende_a_carencia():
    """Encerramento pela API chega duas vezes: em `pose.frames` e em `events.analysis`."""
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=1)
    coletor.push(fim(reason=SessionEndReason.ABORTED), now_ms=BASE_NOW)
    coletor.push(fim(reason=SessionEndReason.ABORTED), now_ms=BASE_NOW + 500)

    assert len(coletor.due(BASE_NOW + FLUSH_GRACE_MS)) == 1


def test_completed_de_sessao_ja_gravada_nao_ressuscita_a_sessao():
    """Senão o segundo `session.completed` gravaria um arquivo vazio por cima do bom."""
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=2)
    coletor.push(fim(), now_ms=BASE_NOW)
    assert len(coletor.due(BASE_NOW + FLUSH_GRACE_MS)) == 1

    coletor.push(fim(), now_ms=BASE_NOW + 10_000)
    assert coletor.due(BASE_NOW + 20_000) == []
    assert coletor.open_sessions == 0


def test_sessao_abortada_sem_frames_nao_vira_sessao_pronta():
    """Critério 3 da SPEC-010, na origem: sem frame não há o que gravar."""
    coletor = FrameCollector()
    coletor.push(abertura(), now_ms=BASE_NOW)
    coletor.push(fim(reason=SessionEndReason.ABORTED, reps=0), now_ms=BASE_NOW)

    prontas = coletor.due(BASE_NOW + FLUSH_GRACE_MS)
    assert len(prontas) == 1
    assert prontas[0].rows == []


def test_sessao_abandonada_e_gravada_e_nao_descartada():
    """Diferente do report-builder: keypoints valem mesmo sem o fim limpo da sessão."""
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=4)

    assert coletor.due(BASE_NOW + STALE_MS - 1) == []
    prontas = coletor.due(BASE_NOW + STALE_MS)
    assert len(prontas[0].rows) == 4


def test_frame_antes_do_session_started_nao_ganha_exercicio_inventado():
    coletor = FrameCollector()
    coletor.push(frame(seq=1, ts=BASE_TS), now_ms=BASE_NOW)
    coletor.push(fim(), now_ms=BASE_NOW)

    assert coletor.due(BASE_NOW + FLUSH_GRACE_MS)[0].exercise == UNKNOWN_EXERCISE


def test_teto_de_frames_trunca_sem_derrubar_a_sessao():
    coletor = FrameCollector()
    coletor.push(abertura(), now_ms=BASE_NOW)
    for i in range(MAX_FRAMES + 10):
        coletor.push(frame(seq=i + 1, ts=BASE_TS + i), now_ms=BASE_NOW)
    coletor.push(fim(), now_ms=BASE_NOW)

    assert len(coletor.due(BASE_NOW + FLUSH_GRACE_MS)[0].rows) == MAX_FRAMES


def test_frame_fora_do_contrato_e_descartado_sem_matar_a_sessao():
    coletor = FrameCollector()
    coletor.push(abertura(), now_ms=BASE_NOW)
    torto = frame(seq=1, ts=BASE_TS)
    torto.data["landmarks"] = [[0.0, 0.0, 0.0, 0.0]]  # 1 landmark em vez de 33
    coletor.push(torto, now_ms=BASE_NOW)
    coletor.push(frame(seq=2, ts=BASE_TS + 66), now_ms=BASE_NOW)
    coletor.push(fim(), now_ms=BASE_NOW)

    # O buraco fica visível: o `seq` não é reindexado.
    assert [linha.seq for linha in coletor.due(BASE_NOW + FLUSH_GRACE_MS)[0].rows] == [2]


def test_drain_fecha_o_que_estiver_aberto_sem_carencia():
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=3, session_id="a")
    sessao_no_coletor(coletor, n_frames=2, session_id="b")

    prontas = coletor.drain()
    assert sorted(sessao.session_id for sessao in prontas) == ["a", "b"]
    assert coletor.open_sessions == 0


# ------------------------------------------------------------------- Parquet


def test_parquet_legivel_por_pandas_com_o_schema_documentado(tmp_path):
    """Critério 3 da SPEC-010, verificado como a spec o escreveu: com pandas."""
    coletor = FrameCollector()
    coletor.push(abertura(), now_ms=BASE_NOW)
    for i in range(3):
        coletor.push(
            frame(seq=i + 1, ts=BASE_TS + i * 66, degraded=(i == 1), valor=0.1 * i),
            now_ms=BASE_NOW,
        )
    coletor.push(fim(), now_ms=BASE_NOW)
    sessao = coletor.due(BASE_NOW + FLUSH_GRACE_MS)[0]

    caminho = write_session(sessao, root=tmp_path, day="2026-07-28")
    assert caminho == tmp_path / "2026-07-28" / "s-1.parquet"

    df = pd.read_parquet(caminho)
    assert len(df) == 3
    assert list(df["seq"]) == [1, 2, 3]
    assert list(df["exercise"]) == ["jumping_jack"] * 3
    assert list(df["source"]) == ["edge"] * 3
    assert list(df["degraded"]) == [False, True, False]
    assert list(df["session_id"]) == ["s-1"] * 3
    # 132 colunas de keypoint: a matriz que o treino consome sai sem transformação nenhuma.
    assert len(COORD_COLUMNS) == LANDMARK_COUNT * 4
    assert df[list(COORD_COLUMNS)].to_numpy().shape == (3, 132)
    # A ordem das componentes é [x, y, z, visibility] — trocar isso é mudar o dataset.
    assert df["nose_x"][0] == pytest.approx(0.0)
    assert df["nose_y"][0] == pytest.approx(0.1)
    assert df["nose_v"][0] == pytest.approx(0.9)


def test_sessao_sem_frames_nao_gera_arquivo(tmp_path):
    coletor = FrameCollector()
    coletor.push(abertura(), now_ms=BASE_NOW)
    coletor.push(fim(reason=SessionEndReason.ABORTED, reps=0), now_ms=BASE_NOW)
    sessao = coletor.due(BASE_NOW + FLUSH_GRACE_MS)[0]

    assert write_session(sessao, root=tmp_path, day="2026-07-28") is None
    assert list(tmp_path.rglob("*.parquet")) == []


def test_regravar_a_mesma_sessao_substitui_o_arquivo(tmp_path):
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=2)
    coletor.push(fim(), now_ms=BASE_NOW)
    sessao = coletor.due(BASE_NOW + FLUSH_GRACE_MS)[0]

    caminho = write_session(sessao, root=tmp_path, day="2026-07-28")
    write_session(sessao, root=tmp_path, day="2026-07-28")

    assert len(list(tmp_path.rglob("*.parquet"))) == 1
    # Nenhum `.tmp` sobrando: a escrita é fora do lugar e movida por cima.
    assert list(tmp_path.rglob("*.tmp")) == []
    assert len(pd.read_parquet(caminho)) == 2


def test_metadados_do_arquivo_carregam_a_versao_do_schema(tmp_path):
    coletor = FrameCollector()
    sessao_no_coletor(coletor, n_frames=1)
    coletor.push(fim(), now_ms=BASE_NOW)
    tabela = build_table(coletor.due(BASE_NOW + FLUSH_GRACE_MS)[0])

    assert tabela.schema.metadata[b"digitalfit.schema_version"] == str(SCHEMA_VERSION).encode()
    assert tabela.schema.metadata[b"digitalfit.landmark_count"] == b"33"
    del tmp_path


# ------------------------------------------------------------ loop (encanamento)


class SinkFake:
    """Coleta as sessões gravadas sem tocar em disco."""

    def __init__(self, *, falha: bool = False) -> None:
        self.sessoes = []
        self.falha = falha

    def __call__(self, sessao):
        if self.falha:
            raise OSError("disco cheio")
        self.sessoes.append(sessao)
        return f"/tmp/{sessao.session_id}.parquet" if sessao.rows else None


def test_le_frames_de_pose_frames_e_o_fim_de_events_analysis():
    """As duas metades da sessão vêm de streams diferentes — ler um só perderia uma delas."""
    bus = InMemoryBus()
    bus.feed(
        Stream.POSE_FRAMES, abertura(), frame(seq=1, ts=BASE_TS), frame(seq=2, ts=BASE_TS + 66)
    )
    bus.feed(Stream.EVENTS_ANALYSIS, fim())
    sink = SinkFake()

    writer = DatasetWriter(bus, consumer="t", sink=sink)
    writer.run(max_batches=1)  # o `drain` do fim do run fecha a sessão

    assert len(sink.sessoes) == 1
    assert [linha.seq for linha in sink.sessoes[0].rows] == [1, 2]
    assert writer.written == 1
    assert writer.frames == 2


def test_ack_e_imediato_nos_dois_streams():
    """Ao contrário do report-builder: aqui segurar o PEL de `pose.frames` seria teatro."""
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, abertura(), frame(seq=1, ts=BASE_TS))
    bus.feed(Stream.EVENTS_ANALYSIS, fim())

    DatasetWriter(bus, consumer="t", sink=SinkFake()).run(max_batches=1)

    assert len(bus.acked) == 3
    assert bus.consume_pending(Stream.POSE_FRAMES, group=GROUP, consumer="t") == []
    assert bus.consume_pending(Stream.EVENTS_ANALYSIS, group=GROUP, consumer="t") == []


def test_grupos_sao_criados_nos_dois_streams():
    bus = InMemoryBus()
    DatasetWriter(bus, consumer="t", sink=SinkFake()).run(max_batches=1)

    assert (Stream.POSE_FRAMES.value, GROUP) in bus.groups
    assert (Stream.EVENTS_ANALYSIS.value, GROUP) in bus.groups


def test_falha_ao_gravar_nao_derruba_o_writer():
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, abertura(), frame(seq=1, ts=BASE_TS))
    bus.feed(Stream.EVENTS_ANALYSIS, fim())

    writer = DatasetWriter(bus, consumer="t", sink=SinkFake(falha=True))
    writer.run(max_batches=1)

    assert writer.written == 0


def test_shutdown_grava_a_sessao_em_andamento():
    """Deploy no meio da captura não pode virar sessão perdida."""
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, abertura(), frame(seq=1, ts=BASE_TS))
    sink = SinkFake()

    writer = DatasetWriter(bus, consumer="t", sink=sink)
    writer.run(max_batches=1)

    assert [linha.seq for linha in sink.sessoes[0].rows] == [1]


def test_consume_com_block_ms_zero_volta_na_hora():
    """A armadilha do Redis: `BLOCK 0` bloqueia para SEMPRE.

    O writer lê dois streams por volta e passa `block_ms=0` no segundo. Se a tradução de 0
    para "sem BLOCK" se perder no `RedisBus`, este teste trava — que é bem melhor do que o
    processo travar em produção sem gravar nada.
    """
    fakeredis = pytest.importorskip("fakeredis", reason="fakeredis nao instalado")
    from workers.shared.bus import RedisBus

    bus = RedisBus(fakeredis.FakeStrictRedis())
    bus.ensure_group(Stream.EVENTS_ANALYSIS, GROUP)

    assert bus.consume(Stream.EVENTS_ANALYSIS, group=GROUP, consumer="t", block_ms=0) == []

    bus.publish(fim(), stream=Stream.EVENTS_ANALYSIS)
    lote = bus.consume(Stream.EVENTS_ANALYSIS, group=GROUP, consumer="t", block_ms=0)
    assert [envelope.session_id for _, envelope in lote] == ["s-1"]


def test_eventos_da_analise_nao_viram_linha(tmp_path):
    """`rep.detected` e afins passam pelo mesmo stream e não são keypoints."""
    from workers.shared.events import Phase, RepDetected

    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, abertura(), frame(seq=1, ts=BASE_TS))
    bus.feed(
        Stream.EVENTS_ANALYSIS,
        make_envelope(
            RepDetected(rep_count=1, phase=Phase.PEAK, duration_ms=800),
            session_id="s-1",
            ts=BASE_TS + 100,
            seq=5,
            source=Source.SYSTEM,
        ),
        fim(),
    )

    writer = DatasetWriter(bus, consumer="t", root=tmp_path)
    writer.run(max_batches=1)

    assert writer.frames == 1
    assert len(pd.read_parquet(next(tmp_path.rglob("*.parquet")))) == 1


# --------------------------------------------------------------------------------------
# Enquadramento no corpus (SPEC-027 §Eventos, T-176)
# --------------------------------------------------------------------------------------


def test_enquadramento_vira_coluna_em_toda_linha(tmp_path):
    """O rótulo tem de chegar ao ARQUIVO, não parar no stream.

    `landscape_forced` existe para permitir EXCLUIR essas sessões de uma calibração futura, e
    quem calibra lê parquet — não lê Redis. Repetido na linha (e não só nos metadados do
    arquivo) porque o corpus se lê com `concat` de centenas de arquivos, e metadado de arquivo
    não sobrevive ao `concat`: foi essa a lição que pôs `session_id` na linha.
    """
    bus = InMemoryBus()
    bus.feed(
        Stream.POSE_FRAMES,
        abertura(),
        enquadramento(facing="environment", orientation="landscape_forced"),
        frame(seq=2, ts=BASE_TS),
        frame(seq=3, ts=BASE_TS + 100),
    )
    bus.feed(Stream.EVENTS_ANALYSIS, fim())

    DatasetWriter(bus, consumer="t", root=tmp_path).run(max_batches=1)

    df = pd.read_parquet(next(tmp_path.rglob("*.parquet")))
    assert list(df["facing"]) == ["environment", "environment"]
    assert list(df["orientation"]) == ["landscape_forced", "landscape_forced"]


def test_sessao_sem_capability_grava_vazio_e_nao_inventa(tmp_path):
    """Cliente antigo (ou origem em arquivo) não recebe procedência fabricada.

    Vazio é uma resposta: "esta sessão não soube dizer". Carimbar `user`/`portrait` por padrão
    poria no corpus uma afirmação que ninguém fez — e o corpus é o produto.
    """
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, abertura(), frame(seq=1, ts=BASE_TS))
    bus.feed(Stream.EVENTS_ANALYSIS, fim())

    DatasetWriter(bus, consumer="t", root=tmp_path).run(max_batches=1)

    df = pd.read_parquet(next(tmp_path.rglob("*.parquet")))
    assert list(df["facing"]) == [""]
    assert list(df["orientation"]) == [""]


def test_capability_nao_vira_linha_de_keypoint(tmp_path):
    """Ele é ATRIBUTO da sessão, como o `exercise` — não um frame a mais."""
    bus = InMemoryBus()
    bus.feed(Stream.POSE_FRAMES, abertura(), enquadramento(), frame(seq=2, ts=BASE_TS))
    bus.feed(Stream.EVENTS_ANALYSIS, fim())

    writer = DatasetWriter(bus, consumer="t", root=tmp_path)
    writer.run(max_batches=1)

    assert writer.frames == 1
    assert len(pd.read_parquet(next(tmp_path.rglob("*.parquet")))) == 1
