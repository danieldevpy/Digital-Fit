"""One Euro Filter — suavização de keypoints sem lag perceptível (SPEC-006).

Filtro passa-baixa com **cutoff adaptativo pela velocidade**: parado, filtra forte (mata
jitter); em movimento rápido, abre a banda (não atrasa o movimento). É o comportamento que
um passa-baixa fixo não dá — e é o que a SPEC-006 pede no critério 2.

Referência: Casiez, Roussel & Vogel, "1€ Filter" (CHI 2012).

Implementação vetorizada: um `OneEuroFilter` filtra um escalar ou um array inteiro de
coordenadas (ex.: 33×3) mantendo estado por posição. `visibility` **nunca** é filtrada
(SPEC-006, notas técnicas).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

__all__ = ["OneEuroFilter", "alpha_for"]


def alpha_for(cutoff: float, dt: float) -> float:
    """Fator do passa-baixa exponencial para um `cutoff` (Hz) e um passo `dt` (s)."""
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    """Filtra um sinal (escalar ou array) amostrado em tempos irregulares.

    Parâmetros:
        mincutoff: cutoff (Hz) quando o sinal está parado — quanto menor, mais suave.
        beta: quanto o cutoff cresce com a velocidade (unidades do sinal por segundo).
        dcutoff: cutoff do filtro da derivada (estabiliza a estimativa de velocidade).

    O estado é por posição do array: `filtro(pontos_33x3, t)` mantém 99 canais independentes.
    """

    __slots__ = ("_dx_hat", "_t", "_x_hat", "beta", "dcutoff", "mincutoff")

    def __init__(self, *, mincutoff: float = 1.0, beta: float = 0.0, dcutoff: float = 1.0) -> None:
        if mincutoff <= 0 or dcutoff <= 0:
            raise ValueError("mincutoff e dcutoff devem ser > 0")
        if beta < 0:
            raise ValueError("beta nao pode ser negativo")
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self._t: float | None = None
        self._x_hat: np.ndarray | None = None
        self._dx_hat: np.ndarray | None = None

    def reset(self) -> None:
        """Esquece o estado — usar entre sessões, nunca no meio de uma."""
        self._t = None
        self._x_hat = None
        self._dx_hat = None

    @property
    def initialized(self) -> bool:
        return self._t is not None

    def __call__(self, value: float | Sequence[float] | np.ndarray, t: float) -> np.ndarray:
        """Devolve o valor filtrado no instante `t` (segundos).

        O primeiro valor passa direto (não há velocidade estimável ainda). `t` que não avança
        devolve o último valor filtrado, sem corromper o estado — frame duplicado ou fora de
        ordem não estraga a sequência.
        """
        x = np.asarray(value, dtype=float)

        if self._t is None or self._x_hat is None or self._dx_hat is None:
            self._t = t
            self._x_hat = x.copy()
            self._dx_hat = np.zeros_like(x)
            return self._x_hat.copy()

        dt = t - self._t
        if dt <= 0:
            return self._x_hat.copy()

        # 1) velocidade filtrada (em unidades do sinal por segundo)
        dx = (x - self._x_hat) / dt
        a_d = alpha_for(self.dcutoff, dt)
        self._dx_hat = a_d * dx + (1.0 - a_d) * self._dx_hat

        # 2) cutoff adaptativo: cresce onde o sinal está rápido (por canal)
        cutoff = self.mincutoff + self.beta * np.abs(self._dx_hat)
        tau = 1.0 / (2.0 * math.pi * cutoff)
        a_x = 1.0 / (1.0 + tau / dt)

        # 3) passa-baixa do sinal
        self._x_hat = a_x * x + (1.0 - a_x) * self._x_hat
        self._t = t
        return self._x_hat.copy()
