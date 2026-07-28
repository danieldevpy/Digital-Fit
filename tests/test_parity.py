"""Testes da paridade edge × cloud (T-018 / SPEC-005, critério 1).

Os extractors são injetados, então a lógica de comparação — decimação diferente por caminho,
tolerância, veredito — é testada sem MediaPipe e sem vídeo de verdade. A passada com vídeo
real depende do corpus (T-038) e roda por `evalctl parity`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.parity import (
    CLOUD_TARGET_FPS,
    EDGE_TARGET_FPS,
    ParityResult,
    compare_paths,
    rep_tolerance,
)
from eval.pipeline import VideoResult
from tests.synthetic_keypoints import jumping_jack_poses, sequence
from workers.shared.normalize import RawFrame


class ExtractorDeLista:
    """Devolve keypoints prontos, ignorando a imagem. Registra o que foi pedido."""

    def __init__(self, frames: list[RawFrame], *, pular: int = 0) -> None:
        self._frames = frames
        self._pular = pular
        self.pedidos = 0
        self.closed = False

    def extract(self, image, ts_ms: int, seq: int) -> RawFrame | None:
        del image
        self.pedidos += 1
        if self._pular and self.pedidos % self._pular == 0:
            return None  # frame em que ninguém foi detectado
        indice = (self.pedidos - 1) % len(self._frames)
        base = self._frames[indice]
        return RawFrame(ts=ts_ms, seq=seq, landmarks=base.landmarks)

    def close(self) -> None:
        self.closed = True


def frames_de(reps: int) -> list[RawFrame]:
    return list(sequence(jumping_jack_poses(reps)))


@pytest.fixture
def video_falso(monkeypatch, tmp_path: Path) -> Path:
    """Substitui a leitura de vídeo por frames sintéticos, respeitando o `target_fps`."""
    caminho = tmp_path / "polichinelo.mp4"
    caminho.write_bytes(b"nao e um mp4 de verdade")

    def leitura(path: Path, *, target_fps: float | None = 15.0):
        del path
        # 20 segundos de vídeo na cadência pedida — é o que muda entre os dois caminhos.
        total = int(20 * (target_fps or 30.0))
        intervalo = 1000.0 / (target_fps or 30.0)
        for i in range(total):
            yield object(), round(i * intervalo), i

    monkeypatch.setattr("eval.parity.read_video_frames", leitura)
    return caminho


# --------------------------------------------------------------------------------------
# Tolerância
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reps", "esperado"),
    [(0, 1), (1, 1), (20, 1), (21, 1), (30, 2), (40, 2), (60, 3)],
)
def test_tolerancia_escala_com_o_volume(reps: int, esperado: int) -> None:
    """ "±1 em 20" da SPEC-005: 40 reps toleram 2, não 1."""
    assert rep_tolerance(reps) == esperado


def test_tolerancia_minima_e_uma_rep() -> None:
    # Com poucas reps a fórmula arredondaria para 0, e uma única rep de diferença — que é
    # ruído normal de detecção — reprovaria o modo cloud inteiro.
    assert rep_tolerance(3) == 1


# --------------------------------------------------------------------------------------
# Veredito
# --------------------------------------------------------------------------------------


def resultado(edge_reps: int, cloud_reps: int) -> ParityResult:
    def vr(nome: str, reps: int) -> VideoResult:
        return VideoResult(name=nome, exercise="jumping_jack", reps=reps)

    return ParityResult(
        video="x.mp4",
        edge=vr("edge", edge_reps),
        cloud=vr("cloud", cloud_reps),
        tolerance=rep_tolerance(edge_reps),
    )


def test_contagem_igual_passa() -> None:
    assert resultado(20, 20).passed is True
    assert resultado(20, 20).rep_delta == 0


def test_uma_rep_de_diferenca_em_vinte_passa() -> None:
    assert resultado(20, 19).passed is True
    assert resultado(20, 21).passed is True


def test_duas_reps_de_diferenca_em_vinte_reprova() -> None:
    assert resultado(20, 18).passed is False
    assert resultado(20, 18).rep_delta == -2


def test_tolerancia_sai_da_contagem_de_referencia_nao_da_media() -> None:
    # Se a tolerância viesse da média, um cloud muito errado aumentaria a própria margem —
    # o critério afrouxaria justamente no caso em que precisa ser rígido.
    assert resultado(20, 60).tolerance == 1
    assert resultado(20, 60).passed is False


def test_resumo_diz_o_que_aconteceu() -> None:
    linha = resultado(20, 18).summary_line()

    assert "FALHA" in linha
    assert "edge=20" in linha
    assert "cloud=18" in linha
    assert "-2" in linha


# --------------------------------------------------------------------------------------
# Comparação de ponta a ponta (com extractors falsos)
# --------------------------------------------------------------------------------------


def test_cada_caminho_roda_na_sua_cadencia(video_falso: Path) -> None:
    """Cadência diferente faz parte da comparação: cloud vê menos frames que edge."""
    edge = ExtractorDeLista(frames_de(20))
    cloud = ExtractorDeLista(frames_de(20))

    compare_paths(video_falso, edge_extractor=edge, cloud_extractor=cloud)

    assert edge.pedidos == int(20 * EDGE_TARGET_FPS)
    assert cloud.pedidos == int(20 * CLOUD_TARGET_FPS)
    assert cloud.pedidos < edge.pedidos


def test_extractors_sao_fechados_mesmo_no_caminho_feliz(video_falso: Path) -> None:
    # Cada extractor segura um grafo do MediaPipe; vazar um por vídeo esgota memória num
    # corpus de 15 vídeos.
    edge = ExtractorDeLista(frames_de(5))
    cloud = ExtractorDeLista(frames_de(5))

    compare_paths(video_falso, edge_extractor=edge, cloud_extractor=cloud)

    assert edge.closed and cloud.closed


def test_frames_sem_pose_sao_contados_e_nao_viram_keypoint(video_falso: Path) -> None:
    edge = ExtractorDeLista(frames_de(10))
    cloud = ExtractorDeLista(frames_de(10), pular=3)  # 1 em cada 3 sem detecção

    resultado = compare_paths(video_falso, edge_extractor=edge, cloud_extractor=cloud)

    assert resultado.cloud.frames_no_pose > 0
    assert resultado.edge.frames_no_pose == 0


def test_relatorio_tem_os_dois_lados(video_falso: Path) -> None:
    saida = compare_paths(
        video_falso,
        edge_extractor=ExtractorDeLista(frames_de(10)),
        cloud_extractor=ExtractorDeLista(frames_de(10)),
    ).to_dict()

    assert set(saida) >= {"video", "passed", "tolerance", "rep_delta", "edge", "cloud"}
    assert saida["edge"]["name"].endswith("[edge]")
    assert saida["cloud"]["name"].endswith("[cloud]")
