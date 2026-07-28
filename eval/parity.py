"""Paridade edge × cloud sobre o mesmo vídeo (T-018 / SPEC-005, critério 1).

A pergunta que este módulo responde: **um usuário em modo cloud recebe a mesma contagem que
receberia em modo edge?** Se não recebe, o modo cloud não é um fallback, é outro produto.

## O que é comparado

| | caminho "edge" | caminho "cloud" |
|---|---|---|
| resolução | a do vídeo | reduzida para 320px |
| compressão | nenhuma | JPEG q60 |
| cadência | 15 fps | 10 fps |
| modo do MediaPipe | `VIDEO` (rastreia) | `IMAGE` (sem estado) |

São exatamente as quatro degradações que o modo cloud impõe (SPEC-005, ADR-007), e nenhuma
outra: os dois caminhos usam o MESMO arquivo de modelo e a MESMA FSM depois da extração.

## O que este teste NÃO cobre

O "edge" aqui é o MediaPipe **do Python**, não o do navegador. Uma diferença entre a
implementação JS e a Python passaria despercebida. Cobrir isso exigiria dirigir um browser de
verdade; enquanto não houver, esta é a aproximação honesta — e ela já isola o que muda no
caminho cloud, que é o risco real.

A comparação é de **contagem de repetições**, não de keypoints. Landmarks idênticos seriam
impossíveis por construção (JPEG e modo IMAGE mudam os números), e também não é o que importa:
o produto conta reps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.pipeline import VideoResult, analyze_frames
from eval.sources import MediaPipeExtractor, PoseExtractor, read_video_frames
from workers.shared.normalize import RawFrame

__all__ = [
    "CLOUD_TARGET_FPS",
    "EDGE_TARGET_FPS",
    "CloudPathExtractor",
    "ParityResult",
    "compare_paths",
    "rep_tolerance",
]

#: Cadências de cada modo (SPEC-001). Fazem parte da comparação: menos frames é menos chance
#: de a FSM ver o pico do movimento.
EDGE_TARGET_FPS = 15.0
CLOUD_TARGET_FPS = 10.0

#: Tolerância da SPEC-005: "±1 em 20". Escala com o volume — 40 reps toleram 2.
TOLERANCE_PER_REPS = 20


def rep_tolerance(reps: int) -> int:
    """Quantas reps de diferença ainda são aceitáveis para esta contagem."""
    return max(1, round(abs(reps) / TOLERANCE_PER_REPS))


class CloudPathExtractor:
    """Extractor que reproduz o caminho cloud inteiro a partir de um frame de vídeo.

    Reduz para 320px, comprime em JPEG q60 e extrai com o MESMO extractor que o `pose-worker`
    roda em produção. Não é uma simulação: os bytes que passam pelo MediaPipe aqui são os
    mesmos que passariam se um celular tivesse enviado o frame.
    """

    def __init__(self, *, model_path: Path | None = None, quality: int = 60, max_side: int = 320):
        from workers.pose_worker.extractor import MediaPipeImageExtractor

        self._extractor = MediaPipeImageExtractor(model_path=model_path)
        self._quality = quality
        self._max_side = max_side
        #: Bytes por frame — serve para conferir o orçamento de banda da SPEC-005.
        self.jpeg_sizes: list[int] = []

    def _encode(self, image) -> bytes:
        import cv2

        altura, largura = image.shape[:2]
        maior = max(altura, largura)
        if maior > self._max_side:
            fator = self._max_side / maior
            image = cv2.resize(
                image, (max(1, round(largura * fator)), max(1, round(altura * fator)))
            )
        ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, self._quality])
        if not ok:
            raise ValueError("falha ao codificar o frame em JPEG")
        return buffer.tobytes()

    def extract(self, image, ts_ms: int, seq: int) -> RawFrame | None:
        jpeg = self._encode(image)
        self.jpeg_sizes.append(len(jpeg))
        landmarks = self._extractor.extract(jpeg)
        if landmarks is None:
            return None
        return RawFrame(ts=ts_ms, seq=seq, landmarks=landmarks)

    def close(self) -> None:
        self._extractor.close()


@dataclass(frozen=True, slots=True)
class ParityResult:
    """Resultado da comparação. `passed` é o critério 1 da SPEC-005."""

    video: str
    edge: VideoResult
    cloud: VideoResult
    tolerance: int
    #: Média de bytes por JPEG no caminho cloud. É o orçamento de banda da SPEC-005 medido em
    #: vez de estimado: a 10fps, 15 KB por frame são ~150 KB/s por sessão.
    cloud_jpeg_avg_bytes: int = 0

    @property
    def rep_delta(self) -> int:
        return self.cloud.reps - self.edge.reps

    @property
    def passed(self) -> bool:
        return abs(self.rep_delta) <= self.tolerance

    def to_dict(self) -> dict[str, Any]:
        return {
            "video": self.video,
            "passed": self.passed,
            "tolerance": self.tolerance,
            "rep_delta": self.rep_delta,
            "cloud_jpeg_avg_bytes": self.cloud_jpeg_avg_bytes,
            "edge": self.edge.to_dict(),
            "cloud": self.cloud.to_dict(),
        }

    def summary_line(self) -> str:
        marca = "OK " if self.passed else "FALHA"
        return (
            f"{marca} {self.video}: edge={self.edge.reps} cloud={self.cloud.reps} "
            f"(delta {self.rep_delta:+d}, tolerancia {self.tolerance})"
        )

    def bandwidth_line(self) -> str:
        """Banda do modo cloud, medida. Vazio quando o extractor não reporta tamanhos."""
        if not self.cloud_jpeg_avg_bytes:
            return ""
        kbs = self.cloud_jpeg_avg_bytes * CLOUD_TARGET_FPS / 1024
        return f"  banda cloud: {self.cloud_jpeg_avg_bytes / 1024:.1f} KB/frame (~{kbs:.0f} KB/s)"


def _analisar(
    video: Path,
    extractor: PoseExtractor,
    *,
    target_fps: float,
    exercise: str,
    nome: str,
    expected_reps: int | None,
) -> VideoResult:
    frames: list[RawFrame] = []
    sem_pose = 0
    try:
        for imagem, ts_ms, seq in read_video_frames(video, target_fps=target_fps):
            raw = extractor.extract(imagem, ts_ms, seq)
            if raw is None:
                sem_pose += 1
            else:
                frames.append(raw)
    finally:
        extractor.close()

    return analyze_frames(
        frames,
        exercise=exercise,
        name=nome,
        expected_reps=expected_reps,
        frames_no_pose=sem_pose,
    )


def compare_paths(
    video: Path,
    *,
    exercise: str = "jumping_jack",
    expected_reps: int | None = None,
    edge_extractor: PoseExtractor | None = None,
    cloud_extractor: PoseExtractor | None = None,
    model_path: Path | None = None,
) -> ParityResult:
    """Roda o mesmo vídeo pelos dois caminhos e compara a contagem de reps.

    Os extractors são injetáveis para o teste da própria lógica de comparação rodar sem
    MediaPipe e sem vídeo.
    """
    edge = _analisar(
        video,
        edge_extractor or MediaPipeExtractor(model_path=model_path),
        target_fps=EDGE_TARGET_FPS,
        exercise=exercise,
        nome=f"{video.name} [edge]",
        expected_reps=expected_reps,
    )
    extractor_cloud = cloud_extractor or CloudPathExtractor(model_path=model_path)
    cloud = _analisar(
        video,
        extractor_cloud,
        target_fps=CLOUD_TARGET_FPS,
        exercise=exercise,
        nome=f"{video.name} [cloud]",
        expected_reps=expected_reps,
    )

    tamanhos = getattr(extractor_cloud, "jpeg_sizes", [])

    # A tolerância vem da contagem do caminho de referência (edge), não da média: comparar
    # contra um número que já é suspeito afrouxaria o critério justamente quando ele importa.
    return ParityResult(
        video=str(video),
        edge=edge,
        cloud=cloud,
        tolerance=rep_tolerance(edge.reps),
        cloud_jpeg_avg_bytes=round(sum(tamanhos) / len(tamanhos)) if tamanhos else 0,
    )
