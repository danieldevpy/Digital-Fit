"""Onde vive o modelo de pose, e como achá-lo (SPEC-005).

Mora em `workers/shared/` porque **três** consumidores precisam do mesmo arquivo e da mesma
regra de resolução: o `pose-worker` (modo cloud), a bancada `evalctl` (SPEC-012) e o script de
setup do cliente web. Se cada um resolvesse o caminho à sua maneira, bastaria um deles achar
outro `.task` para a paridade edge×cloud×bancada deixar de significar qualquer coisa — e o
sintoma seria "a contagem mudou", sem nada apontando para o modelo.

Nada aqui importa MediaPipe: é só caminho de arquivo. Quem carrega o modelo é
`workers/pose_worker/extractor.py`.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "MODEL_DIR",
    "MODEL_FILENAME",
    "MODEL_URL",
    "download_model",
    "resolve_model_path",
]

MODEL_FILENAME = "pose_landmarker_lite.task"

#: Modelo `lite` oficial — o MESMO que o cliente web carrega no modo edge (SPEC-005). Trocar
#: um lado sem o outro quebra o critério 1 da spec (mesmo vídeo, mesma contagem).
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)

#: Diretório padrão: `eval/models/`. Continua sendo o da bancada porque é lá que o
#: `evalctl fetch-model` grava e onde o compose monta o volume para os containers.
MODEL_DIR = Path(__file__).resolve().parents[2] / "eval" / "models"


def resolve_model_path(model_path: Path | None = None) -> Path:
    """Onde está o `.task`: argumento > `DIGITALFIT_POSE_MODEL` > `eval/models/`."""
    if model_path is not None:
        candidato = Path(model_path)
    elif os.environ.get("DIGITALFIT_POSE_MODEL"):
        candidato = Path(os.environ["DIGITALFIT_POSE_MODEL"])
    else:
        candidato = MODEL_DIR / MODEL_FILENAME

    if not candidato.exists():
        raise FileNotFoundError(
            f"modelo de pose nao encontrado em {candidato}.\n"
            f"Baixe uma vez com:  python -m eval.evalctl fetch-model\n"
            f"(ou aponte DIGITALFIT_POSE_MODEL para um {MODEL_FILENAME} existente)"
        )
    return candidato


def download_model(destination: Path | None = None) -> Path:
    """Baixa o modelo `lite` oficial do MediaPipe. Passo explícito, nunca automático."""
    from urllib.request import urlopen

    destino = Path(destination) if destination else MODEL_DIR / MODEL_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    # URL fixa e oficial do MediaPipe — nada aqui vem de entrada do usuario.
    with urlopen(MODEL_URL, timeout=120) as resposta:
        destino.write_bytes(resposta.read())
    return destino
