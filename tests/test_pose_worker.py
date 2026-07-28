"""Testes do pose-worker (T-016 / SPEC-005).

O extractor é injetado, então nada aqui carrega MediaPipe: o que se testa é a política —
o que vira `pose.frame`, o que é descartado e por quê.
"""

from __future__ import annotations

import time

import pytest

from workers.pose_worker.main import GROUP, run
from workers.pose_worker.router import MAX_AGE_MS, PoseRouter
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    LANDMARK_COUNT,
    Envelope,
    EventType,
    FrameRaw,
    PoseFrame,
    Source,
    Stream,
    make_envelope,
)

SESSAO = "3f2b9c4e-0000-4000-8000-000000000001"
AGORA = 1_722_100_000_000

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 128

LANDMARKS = [[0.5, 0.5, 0.0, 0.9] for _ in range(LANDMARK_COUNT)]


class ExtractorFalso:
    """Devolve o que o teste mandar. `chamadas` guarda os JPEGs recebidos."""

    def __init__(self, resultado=LANDMARKS, erro: Exception | None = None) -> None:
        self.resultado = resultado
        self.erro = erro
        self.chamadas: list[bytes] = []
        self.closed = False

    def extract(self, jpeg: bytes):
        self.chamadas.append(jpeg)
        if self.erro is not None:
            raise self.erro
        return self.resultado

    def close(self) -> None:
        self.closed = True


def frame_raw(*, ts: int = AGORA, seq: int = 0) -> Envelope:
    return make_envelope(
        FrameRaw(jpeg=JPEG, width=320, height=240),
        session_id=SESSAO,
        ts=ts,
        seq=seq,
        source=Source.CLOUD,
    )


# --------------------------------------------------------------------------------------
# Caminho feliz
# --------------------------------------------------------------------------------------


def test_frame_raw_vira_pose_frame() -> None:
    extractor = ExtractorFalso()
    router = PoseRouter(extractor=extractor)

    saidas = router.handle(frame_raw(seq=7), now_ms=AGORA + 50)

    assert len(saidas) == 1
    assert saidas[0].type is EventType.POSE_FRAME
    assert PoseFrame.from_data(saidas[0].data).landmarks == LANDMARKS
    assert extractor.chamadas == [JPEG]


def test_pose_frame_do_cloud_e_marcado_como_cloud() -> None:
    """Downstream não pode saber a origem, mas o dataset e o relatório precisam registrar."""
    router = PoseRouter(extractor=ExtractorFalso())

    saida = router.handle(frame_raw(), now_ms=AGORA)[0]

    assert saida.source is Source.CLOUD


def test_ts_e_seq_do_frame_original_sao_preservados() -> None:
    # O tempo que interessa à FSM é o da CAPTURA. Se o worker carimbasse o instante em que
    # terminou de processar, a cadência vista pela análise viraria a do servidor sob carga —
    # e os limiares de duração de repetição passariam a medir a fila, não o exercício.
    router = PoseRouter(extractor=ExtractorFalso())

    saida = router.handle(frame_raw(ts=AGORA, seq=42), now_ms=AGORA + 300)[0]

    assert saida.ts == AGORA
    assert saida.seq == 42
    assert saida.session_id == SESSAO


# --------------------------------------------------------------------------------------
# Descarte
# --------------------------------------------------------------------------------------


def test_frame_velho_e_descartado() -> None:
    extractor = ExtractorFalso()
    router = PoseRouter(extractor=extractor)

    saidas = router.handle(frame_raw(), now_ms=AGORA + MAX_AGE_MS + 1)

    assert saidas == []
    assert router.stats.stale == 1
    # O ponto do descarte é economizar CPU: extrair e depois jogar fora não economizaria nada.
    assert extractor.chamadas == []


def test_frame_no_limite_da_idade_ainda_passa() -> None:
    router = PoseRouter(extractor=ExtractorFalso())

    saidas = router.handle(frame_raw(), now_ms=AGORA + MAX_AGE_MS)

    assert len(saidas) == 1


def test_sem_pessoa_no_quadro_nao_produz_evento() -> None:
    # Não inventar `pose.frame` vazio: quem reclama de quadro vazio é a validação de cena
    # (SPEC-003), e um frame com landmarks falsos a faria dizer que está tudo bem.
    router = PoseRouter(extractor=ExtractorFalso(resultado=None))

    assert router.handle(frame_raw(), now_ms=AGORA) == []
    assert router.stats.no_pose == 1


def test_falha_na_extracao_nao_derruba_o_worker() -> None:
    router = PoseRouter(extractor=ExtractorFalso(erro=ValueError("JPEG corrompido")))

    assert router.handle(frame_raw(), now_ms=AGORA) == []
    assert router.stats.failed == 1


def test_jpeg_fora_do_contrato_conta_como_falha_e_nao_estoura() -> None:
    router = PoseRouter(extractor=ExtractorFalso())
    envelope = Envelope(
        type=EventType.FRAME_RAW,
        session_id=SESSAO,
        ts=AGORA,
        seq=0,
        source=Source.CLOUD,
        data={"jpeg": b"nao e jpeg", "width": 320, "height": 240},
    )

    assert router.handle(envelope, now_ms=AGORA) == []
    assert router.stats.failed == 1


def test_tipo_inesperado_no_stream_e_ignorado() -> None:
    router = PoseRouter(extractor=ExtractorFalso())
    envelope = make_envelope(
        PoseFrame(landmarks=LANDMARKS), session_id=SESSAO, ts=AGORA, seq=0, source=Source.EDGE
    )

    assert router.handle(envelope, now_ms=AGORA) == []
    assert router.stats.ignored == 1


def test_relogio_do_cliente_adiantado_nao_descarta() -> None:
    """Frame "do futuro" não é frame velho — descartá-lo mataria a sessão inteira."""
    router = PoseRouter(extractor=ExtractorFalso())

    saidas = router.handle(frame_raw(ts=AGORA + 5_000), now_ms=AGORA)

    assert len(saidas) == 1
    assert router.stats.stale == 0


# --------------------------------------------------------------------------------------
# Loop
# --------------------------------------------------------------------------------------


def test_loop_publica_em_pose_frames_e_da_ack() -> None:
    bus = InMemoryBus()
    entrada = frame_raw(ts=int(time.time() * 1000))  # "agora" real: o loop não injeta relógio
    bus.feed(Stream.FRAMES_RAW, entrada)

    router = run(bus, consumer="teste", extractor=ExtractorFalso(), max_batches=1)

    assert router.stats.processed == 1
    # O `pose.frame` do cloud tem de entrar pelo MESMO stream que o edge usa, senão o
    # analysis-worker precisaria saber a origem — o que a SPEC-005 proíbe (critério 4).
    publicados = bus.published_in(Stream.POSE_FRAMES)
    assert [e.type for e in publicados] == [EventType.POSE_FRAME]
    assert len(bus.acked) == 1


def test_loop_cria_o_consumer_group_declarado_no_contrato() -> None:
    bus = InMemoryBus()

    run(bus, consumer="teste", extractor=ExtractorFalso(), max_batches=1)

    assert (Stream.FRAMES_RAW.value, GROUP) in bus.groups


def test_loop_da_ack_mesmo_no_frame_descartado() -> None:
    # Sem ack, o frame velho ficaria pendente no grupo para sempre e voltaria a cada
    # reivindicação — o descarte tem de ser definitivo.
    bus = InMemoryBus()
    bus.feed(Stream.FRAMES_RAW, frame_raw(ts=1))  # ts de 1970: velhíssimo

    router = run(bus, consumer="teste", extractor=ExtractorFalso(), max_batches=1)

    assert router.stats.stale == 1
    assert len(bus.acked) == 1
    assert bus.published_in(Stream.POSE_FRAMES) == []


def test_run_exige_extractor_ou_router() -> None:
    with pytest.raises(ValueError, match=r"router` ou `extractor"):
        run(InMemoryBus(), consumer="teste", max_batches=1)
