"""Fixtures de keypoints — nível 1 da pirâmide de teste (SPEC-012).

Uma sessão gravada em JSON: dá para testar normalização, FSM e feedback **sem câmera, sem
vídeo e sem MediaPipe**, em milissegundos. Cada vídeo processado uma vez vira teste rápido
para sempre.

Formato (`schema: 1`)::

    {
      "schema": 1,
      "label": "jj_frontal_boa_luz",
      "exercise": "jumping_jack",
      "expected_reps": 20,
      "source": "file",
      "fps": 15.0,
      "notes": "gravado a 2.5 m, luz boa",
      "width": 576,
      "height": 1024,
      "frames": [{"ts": 1722100000123, "seq": 0, "landmarks": [[x, y, z, v], ... 33]}]
    }

`width`/`height` (T-110) são as dimensões do frame de origem: sem elas a normalização não
consegue pôr `x` e `y` na mesma moeda. Opcionais — fixture sem dimensão continua carregando,
tratada como espaço isotrópico.

`landmarks` são os **crus** (0–1 no frame), nunca os normalizados: normalização é código que
muda, e uma fixture existe para medir mudança de código. Coordenadas com 5 decimais — precisão
muito acima do ruído do modelo e diff estável no git.

Este é o mesmo formato que o gravador do cliente (T-007, Agente B) escreve e que o
`evalctl run --save-keypoints` exporta. Um formato, três produtores.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

from workers.shared.normalize import RawFrame

__all__ = ["SCHEMA_VERSION", "KeypointFixture", "load_fixture", "save_fixture"]

SCHEMA_VERSION = 1

#: Casas decimais guardadas por coordenada.
_PRECISION = 5


@dataclass(slots=True)
class KeypointFixture:
    """Sessão de keypoints gravada, com o rótulo do que se espera dela."""

    label: str
    frames: list[RawFrame]
    exercise: str = "jumping_jack"
    expected_reps: int | None = None
    source: str = "file"
    fps: float | None = None
    notes: str | None = None
    schema: int = SCHEMA_VERSION
    conditions: dict[str, Any] = field(default_factory=dict)
    #: Dimensões do frame de origem (T-110) — a normalização precisa delas para pôr `x` e `y`
    #: na mesma moeda. Ficam no topo, e não por frame, porque um arquivo tem uma resolução só;
    #: é a sessão ao vivo que pode girar o aparelho no meio, e lá elas viajam no `pose.frame`.
    #:
    #: **Não** são lidas de `conditions.resolucao`: os nomes em `conditions` são livres por
    #: contrato (SPEC-012), e derivar geometria de um campo de texto livre é acidente esperando
    #: acontecer. Ausentes ⇒ espaço isotrópico, o comportamento anterior à T-110.
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "label": self.label,
            "exercise": self.exercise,
            "expected_reps": self.expected_reps,
            "source": self.source,
            "fps": self.fps,
            "notes": self.notes,
            "width": self.width,
            "height": self.height,
            "conditions": self.conditions,
            "frames": [
                {
                    "ts": frame.ts,
                    "seq": frame.seq,
                    "landmarks": [
                        [round(float(valor), _PRECISION) for valor in ponto]
                        for ponto in frame.landmarks
                    ],
                }
                for frame in self.frames
            ],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Self:
        schema = int(raw.get("schema", 0))
        if schema != SCHEMA_VERSION:
            raise ValueError(f"fixture de keypoints com schema {schema}, esperado {SCHEMA_VERSION}")
        largura = int(raw["width"]) if raw.get("width") is not None else None
        altura = int(raw["height"]) if raw.get("height") is not None else None
        try:
            frames = [
                RawFrame(
                    ts=int(item["ts"]),
                    seq=int(item["seq"]),
                    landmarks=item["landmarks"],
                    # O frame pode trazer a sua própria dimensão (sessão gravada no navegador,
                    # onde o aparelho gira); o topo é o padrão de quem não traz.
                    width=int(item["width"]) if item.get("width") is not None else largura,
                    height=int(item["height"]) if item.get("height") is not None else altura,
                )
                for item in raw["frames"]
            ]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"frames invalidos na fixture: {exc}") from exc
        return cls(
            label=str(raw.get("label", "sem-rotulo")),
            frames=frames,
            exercise=str(raw.get("exercise", "jumping_jack")),
            expected_reps=(
                int(raw["expected_reps"]) if raw.get("expected_reps") is not None else None
            ),
            source=str(raw.get("source", "file")),
            fps=float(raw["fps"]) if raw.get("fps") is not None else None,
            notes=raw.get("notes"),
            schema=schema,
            conditions=dict(raw.get("conditions") or {}),
            width=largura,
            height=altura,
        )


def save_fixture(path: Path, fixture: KeypointFixture) -> Path:
    """Grava a fixture. Cria a pasta se preciso e devolve o caminho escrito."""
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(fixture.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return destino


def load_fixture(path: Path) -> KeypointFixture:
    """Lê a fixture validando o schema — pytest consome sem conversão nenhuma."""
    dados = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError(f"fixture deve ser objeto JSON: {path}")
    return KeypointFixture.from_dict(dados)
