"""Schema e escrita do Parquet do dataset (SPEC-010, critério 3).

Este é o único arquivo do repositório que conhece pyarrow, e o único que decide o formato em
disco. O schema é **contrato com o futuro**: cada arquivo gravado hoje será lido por um
treino que ainda não existe, então mudar coluna aqui é mudança quebrante — `SCHEMA_VERSION`
sobe junto e `docs/DATASET.md` diz o que mudou.

Formato longo (uma linha por frame), não uma coluna de lista: `pandas.read_parquet` devolve
direto um `DataFrame` de 138 colunas em que `df[COORD_COLUMNS].to_numpy()` já é a matriz
`(n_frames, 132)` que um modelo temporal consome. Guardar `landmarks` como lista de listas
economizaria nomes e custaria um `explode` em todo notebook que tocasse o corpus.
"""

from __future__ import annotations

import os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from workers.dataset_writer.collector import SessionFrames
from workers.shared.events import LANDMARK_COUNT, LANDMARK_NAMES

__all__ = [
    "AXES",
    "COORD_COLUMNS",
    "SCHEMA",
    "SCHEMA_VERSION",
    "build_table",
    "session_path",
    "write_session",
]

#: Sobe quando o schema muda de forma que quebre quem lê o corpus antigo.
SCHEMA_VERSION = 1

#: Sufixos das 4 componentes de cada landmark. `v` é `visibility` (0–1), não uma coordenada —
#: entra junto porque quem treina precisa saber de qual ponto pode confiar.
AXES: tuple[str, ...] = ("x", "y", "z", "v")

#: As 132 colunas de keypoint, em ordem de landmark (ver `Landmark` em events.py). Os nomes
#: vêm do contrato de eventos: se um landmark for renomeado lá, o dataset acompanha sozinho.
COORD_COLUMNS: tuple[str, ...] = tuple(f"{nome}_{eixo}" for nome in LANDMARK_NAMES for eixo in AXES)

#: Colunas de identificação, antes das coordenadas — `df.head()` tem de ser legível.
_META_FIELDS: list[tuple[str, pa.DataType]] = [
    # Não está na lista da SPEC-010, e entra de propósito: um treino concatena centenas destes
    # arquivos, e sem `session_id` na linha não há como dizer onde uma sequência termina e a
    # próxima começa — o nome do arquivo se perde no `concat`.
    ("session_id", pa.string()),
    ("seq", pa.int32()),
    ("ts", pa.int64()),  # epoch ms do produtor (relógio do cliente)
    ("exercise", pa.string()),
    ("source", pa.string()),  # edge | cloud | file — de qual caminho de extração veio
    ("degraded", pa.bool_()),
]

#: `float32` e não `float64`: o MediaPipe entrega precisão simples, então o dobro de bytes
#: guardaria zeros. Um arquivo de 30 s fica em ~250 KB, como a spec previu.
SCHEMA = pa.schema(
    [pa.field(nome, tipo) for nome, tipo in _META_FIELDS]
    + [pa.field(nome, pa.float32()) for nome in COORD_COLUMNS],
    metadata={
        b"digitalfit.schema_version": str(SCHEMA_VERSION).encode(),
        b"digitalfit.landmark_count": str(LANDMARK_COUNT).encode(),
        b"digitalfit.spec": b"SPEC-010",
    },
)


def build_table(frames: SessionFrames) -> pa.Table:
    """Converte a sessão em tabela Arrow no schema acima."""
    linhas = frames.rows
    colunas: dict[str, list] = {
        "session_id": [frames.session_id] * len(linhas),
        "seq": [linha.seq for linha in linhas],
        "ts": [linha.ts for linha in linhas],
        "exercise": [frames.exercise] * len(linhas),
        "source": [linha.source for linha in linhas],
        "degraded": [linha.degraded for linha in linhas],
    }
    for indice, nome in enumerate(COORD_COLUMNS):
        landmark, eixo = divmod(indice, len(AXES))
        colunas[nome] = [linha.landmarks[landmark][eixo] for linha in linhas]
    return pa.Table.from_pydict(colunas, schema=SCHEMA)


def session_path(root: Path | str, session_id: str, *, day: str) -> Path:
    """`{root}/{day}/{session_id}.parquet`, com `day` no formato `YYYY-MM-DD`."""
    return Path(root) / day / f"{session_id}.parquet"


def write_session(frames: SessionFrames, *, root: Path | str, day: str) -> Path | None:
    """Grava a sessão e devolve o caminho. Sessão sem frames **não** gera arquivo.

    Esse `None` é o critério 3 da SPEC-010, não uma otimização: uma sessão abortada antes do
    primeiro frame produziria um Parquet de zero linhas, e um corpus salpicado de arquivos
    vazios faz todo script de treino ter de checar isso.
    """
    if not frames.rows:
        return None

    destino = session_path(root, frames.session_id, day=day)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Grava fora do lugar e move: `os.replace` é atômico no mesmo filesystem, então um crash no
    # meio da escrita deixa o arquivo anterior intacto em vez de um Parquet truncado que só vai
    # explodir meses depois, dentro de um treino.
    temporario = destino.with_suffix(".parquet.tmp")
    # zstd: ~2× melhor que snappy em coluna de float e lido por qualquer pyarrow/pandas atual.
    pq.write_table(build_table(frames), temporario, compression="zstd")
    os.replace(temporario, destino)
    return destino
