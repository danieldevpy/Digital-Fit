"""Calibração da sessão: mede o corpo antes de o exercício valer (SPEC-004 / T-019).

Durante o countdown a pessoa está parada e de frente. É a única janela em que as proporções
do corpo podem ser medidas sem o movimento no meio — e é por isso que a calibração acontece
aí, e não no primeiro frame qualquer.

Para que serve a medida, e para que **não** serve:

- **Serve** como escala da normalização (SPEC-006): a partir dela os keypoints deixam de ser
  divididos por um torso instantâneo que oscila a cada frame.
- **Serve** como conteúdo do `session.calibrated`, que o relatório (SPEC-010) e o gate de
  prontidão (T-030) vão consumir — este último precisa saber onde os pulsos repousam.
- **Não serve** como divisor de `ankle_spread`, apesar de o critério 3 da SPEC-004 pedir isso
  originalmente. Foi implementado, medido contra o corpus e revertido: o divisor por frame se
  autocorrige em perspectiva, e fixá-lo derruba justamente os vídeos em ângulo. O comentário
  em `jumping_jack.features()` guarda os números.

Mediana, nunca média: um frame em que o modelo errou um ombro desloca a média e não desloca a
mediana (SPEC-004, notas técnicas).
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field

from workers.shared.normalize import Baseline, NormFrame

__all__ = ["CALIBRATION_MS", "CALIBRATION_TIMEOUT_MS", "MIN_CALIBRATION_FRAMES", "Calibrator"]

logger = logging.getLogger("analysis-worker")

#: Janela de medição (SPEC-004: "mediana de 1s").
CALIBRATION_MS = 1_000

#: Mínimo de frames bons para aceitar a medida. A 15fps, 1 s dá ~15 frames; exigir 8 tolera
#: perda de metade deles e ainda deixa a mediana significar alguma coisa.
MIN_CALIBRATION_FRAMES = 8

#: Depois disto sem conseguir medir, a calibração falha e o countdown reinicia (SPEC-004,
#: critério 2). Sem esse teto, uma pessoa fora do quadro deixaria a sessão presa para sempre
#: em "calibrando" — sem contar rep e sem dizer o motivo.
CALIBRATION_TIMEOUT_MS = 5_000

_LEFT_SHOULDER, _RIGHT_SHOULDER = 11, 12
_LEFT_WRIST, _RIGHT_WRIST = 15, 16


@dataclass(slots=True)
class Calibrator:
    """Acumula frames bons e devolve a `Baseline` quando tiver o suficiente."""

    window_ms: int = CALIBRATION_MS
    min_frames: int = MIN_CALIBRATION_FRAMES
    timeout_ms: int = CALIBRATION_TIMEOUT_MS

    _torso: list[float] = field(default_factory=list)
    _shoulder_width: list[float] = field(default_factory=list)
    _shoulder_span: list[float] = field(default_factory=list)
    _wrist_y: list[float] = field(default_factory=list)
    _first_ts: int | None = None
    _descartados: int = 0

    @property
    def samples(self) -> int:
        return len(self._torso)

    @property
    def discarded(self) -> int:
        """Frames recusados por qualidade — o número que explica uma calibração que demora."""
        return self._descartados

    def push(self, frame: NormFrame) -> Baseline | None:
        """Consome um frame. Devolve a baseline quando a janela fecha, senão `None`."""
        if self._first_ts is None:
            self._first_ts = frame.ts

        if frame.degraded:
            # Frame degradado é exatamente o que NÃO pode entrar: os landmarks vêm
            # "adivinhados" pelo modelo, e uma proporção medida deles seria inventada.
            self._descartados += 1
            return None

        points = frame.points
        self._torso.append(frame.torso)
        self._shoulder_width.append(frame.shoulder_width)
        self._shoulder_span.append(
            abs(float(points[_LEFT_SHOULDER][0] - points[_RIGHT_SHOULDER][0]))
        )
        self._wrist_y.append((float(points[_LEFT_WRIST][1]) + float(points[_RIGHT_WRIST][1])) / 2.0)

        decorrido = frame.ts - self._first_ts
        if decorrido < self.window_ms or self.samples < self.min_frames:
            return None
        return self._medir()

    def failed(self, ts: int) -> bool:
        """Passou do teto sem conseguir medir? Então o countdown tem de recomeçar."""
        if self._first_ts is None:
            return False
        return ts - self._first_ts >= self.timeout_ms and self.samples < self.min_frames

    def _medir(self) -> Baseline:
        baseline = Baseline(
            torso=statistics.median(self._torso),
            shoulder_width=statistics.median(self._shoulder_width),
            shoulder_span=statistics.median(self._shoulder_span),
            wrist_rest_y=statistics.median(self._wrist_y),
        )
        logger.info(
            "baseline medida em %s frames (%s descartados): torso=%.4f ombros=%.4f "
            "span=%.3f torsos",
            self.samples,
            self._descartados,
            baseline.torso,
            baseline.shoulder_width,
            baseline.shoulder_span,
        )
        return baseline

    def reset(self) -> None:
        """Recomeça a medição do zero (countdown reiniciado)."""
        self._torso.clear()
        self._shoulder_width.clear()
        self._shoulder_span.clear()
        self._wrist_y.clear()
        self._first_ts = None
        self._descartados = 0
