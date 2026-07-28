"""Fontes de entrada da bancada: vídeo → `pose.frame` (SPEC-012, nível 2).

A extração de pose é uma **interface** (`PoseExtractor`): a implementação de verdade usa o
MediaPipe (mesmo modelo `lite` do modo cloud), e os testes injetam uma falsa com keypoints
sintéticos. Assim a bancada é testável sem 200 MB de dependência e sem vídeo de verdade.

Nada aqui importa MediaPipe ou OpenCV no topo do módulo: o import acontece dentro dos métodos,
para que `evalctl --help` e os testes não paguem por isso.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from workers.shared.normalize import RawFrame

# Reexportados de `workers/shared/pose_model.py`: a bancada e o `pose-worker` TEM de
# resolver o mesmo arquivo (SPEC-005, criterio 1). A direcao da dependencia e
# eval -> workers, nunca o contrario.
from workers.shared.pose_model import (
    MODEL_FILENAME,
    MODEL_URL,
    download_model,
    resolve_model_path,
)

__all__ = [
    "MODEL_FILENAME",
    "MODEL_URL",
    "MediaPipeExtractor",
    "PoseExtractor",
    "VideoInfo",
    "download_model",
    "read_video_frames",
    "resolve_model_path",
    "video_info",
]


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """Metadados do vídeo lido, para o relatório saber sobre o que está falando."""

    path: Path
    fps: float
    frame_count: int
    width: int
    height: int


class PoseExtractor(Protocol):
    """Transforma frames de imagem em landmarks. Um extractor por vídeo (tem estado)."""

    def extract(self, image, ts_ms: int, seq: int) -> RawFrame | None:
        """Landmarks do frame, ou `None` quando nenhuma pessoa foi detectada."""
        ...

    def close(self) -> None: ...


def read_video_frames(path: Path, *, target_fps: float | None = 15.0) -> Iterator[tuple]:
    """Itera `(imagem, ts_ms, seq)` de um vídeo, decimando para `target_fps`.

    Decimação **por tempo**, não por contagem — igual ao frame clock do cliente (SPEC-001), para
    que a bancada veja a mesma cadência que o navegador enviaria.
    """
    import cv2  # import tardio: só quem lê vídeo paga por OpenCV

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"nao foi possivel abrir o video: {path}")

    try:
        source_fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        intervalo_ms = 1000.0 / target_fps if target_fps else 0.0
        proximo_ms = 0.0
        seq = 0
        indice = 0

        while True:
            ok, frame = capture.read()
            if not ok:
                break
            ts_ms = round(indice * 1000.0 / source_fps)
            indice += 1
            if ts_ms + 1e-9 < proximo_ms:
                continue
            proximo_ms += intervalo_ms
            yield frame, ts_ms, seq
            seq += 1
    finally:
        capture.release()


def video_info(path: Path) -> VideoInfo:
    """Metadados sem decodificar o vídeo inteiro."""
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"nao foi possivel abrir o video: {path}")
    try:
        return VideoInfo(
            path=path,
            fps=float(capture.get(cv2.CAP_PROP_FPS) or 0.0),
            frame_count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
            width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
        )
    finally:
        capture.release()


class MediaPipeExtractor:
    """Pose Landmarker (MediaPipe **Tasks**) em CPU, modelo `lite` — SPEC-005.

    Tasks é a mesma API que o cliente web usa no modo edge; usá-la aqui é o que permite comparar
    bancada × navegador × `pose-worker` sem desconfiar do modelo.

    Roda em `RunningMode.VIDEO` (com timestamp por frame, não streaming): a bancada precisa ser
    determinística, senão `evalctl compare` não significa nada (SPEC-012, notas técnicas).
    """

    def __init__(
        self, *, model_path: Path | None = None, min_detection_confidence: float = 0.5
    ) -> None:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        self._model_path = resolve_model_path(model_path)
        opcoes = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(self._model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,  # múltiplas pessoas é Fase Evolução da SPEC-005
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_detection_confidence,
            output_segmentation_masks=False,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(opcoes)
        self._ultimo_ts = -1

    @property
    def version(self) -> str:
        return f"{getattr(self._mp, '__version__', 'desconhecida')} ({self._model_path.name})"

    def extract(self, image, ts_ms: int, seq: int) -> RawFrame | None:
        import cv2

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        # O modo VIDEO exige timestamps estritamente crescentes.
        ts_ms = max(ts_ms, self._ultimo_ts + 1)
        self._ultimo_ts = ts_ms

        resultado = self._landmarker.detect_for_video(mp_image, ts_ms)
        poses = getattr(resultado, "pose_landmarks", None)
        if not poses:
            return None
        return RawFrame(
            ts=ts_ms,
            seq=seq,
            landmarks=[[marco.x, marco.y, marco.z, marco.visibility] for marco in poses[0]],
        )

    def close(self) -> None:
        self._landmarker.close()


#: Modelo `lite` do Pose Landmarker. Fica fora do git (binário) e é baixado uma vez.
#: `download_model` e `resolve_model_path` vivem em `workers/shared/pose_model.py` — a
#: bancada e o `pose-worker` precisam resolver exatamente o mesmo arquivo.
