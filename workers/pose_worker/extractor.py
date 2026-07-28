"""Extração de pose no servidor: bytes JPEG → 33 landmarks (SPEC-005, modo cloud).

A extração é uma **interface** (`PoseExtractor`). A implementação real carrega MediaPipe; os
testes injetam uma falsa. É o que permite testar o worker inteiro — descarte por idade,
roteamento, ack — sem 200 MB de dependência e sem imagem de verdade.

Nada aqui importa MediaPipe no topo do módulo: quem só quer a interface (ou o `--help`) não
paga o carregamento.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from workers.shared.pose_model import resolve_model_path

__all__ = ["MediaPipeImageExtractor", "PoseExtractor"]

#: Landmarks de uma pessoa: `[x, y, z, visibility]` × 33, igual ao contrato de `pose.frame`.
Landmarks = list[list[float]]


class PoseExtractor(Protocol):
    def extract(self, jpeg: bytes) -> Landmarks | None:
        """Landmarks do JPEG, ou `None` quando nenhuma pessoa foi detectada."""
        ...

    def close(self) -> None: ...


class MediaPipeImageExtractor:
    """Pose Landmarker (MediaPipe Tasks) em CPU, modelo `lite`, **sem estado entre frames**.

    Roda em `RunningMode.IMAGE`, e não em `VIDEO` como a bancada (`eval/sources.py`). A
    diferença é deliberada e vem de como o worker recebe trabalho: os frames chegam por um
    consumer group, então dois frames seguidos da MESMA sessão podem cair em réplicas
    diferentes. Modo VIDEO pressupõe uma sequência contínua com timestamps crescentes por
    instância — premissa que o consumer group quebra. Manter rastreamento aqui significaria
    ou prender sessão a réplica (perdendo a tolerância a falha que o grupo dá de graça), ou
    misturar o rastreamento de sessões distintas, que é pior: o estado de uma pessoa
    influenciaria os landmarks de outra.

    IMAGE mode custa detecção completa a cada frame — que é exatamente o que o orçamento da
    SPEC-005 já previa (≤80ms por frame de 320px em 1 vCPU). Em troca, o mesmo JPEG produz
    sempre o mesmo resultado, que é o que dá sentido ao teste de paridade da T-018.
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
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,  # múltiplas pessoas é Fase Evolução da SPEC-005
            min_pose_detection_confidence=min_detection_confidence,
            output_segmentation_masks=False,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(opcoes)

    @property
    def version(self) -> str:
        return f"{getattr(self._mp, '__version__', 'desconhecida')} ({self._model_path.name})"

    def extract(self, jpeg: bytes) -> Landmarks | None:
        import cv2
        import numpy as np

        # `imdecode` devolve BGR (convenção do OpenCV) e `None` para bytes corrompidos —
        # o contrato já checou a assinatura, mas assinatura certa não garante imagem íntegra.
        bgr = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("JPEG nao pode ser decodificado")

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        resultado = self._landmarker.detect(mp_image)
        poses = getattr(resultado, "pose_landmarks", None)
        if not poses:
            return None
        return [[marco.x, marco.y, marco.z, marco.visibility] for marco in poses[0]]

    def close(self) -> None:
        self._landmarker.close()
