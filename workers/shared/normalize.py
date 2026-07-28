"""Normalização & filtragem de keypoints (SPEC-006).

Fronteira entre "dados de visão" e "dados de movimento": converte landmarks crus (0–1 no
frame) em keypoints **canônicos**, invariantes a posição da câmera, tamanho do corpo e jitter.
Tudo depois daqui raciocina em **torsos** (distância ombro-médio → quadril-médio = 1.0).

Pipeline por frame:

1. **Escala**: comprimento do torso, suavizado (usa `Baseline` da SPEC-004 quando existir).
2. **Recentragem**: origem no ponto médio dos quadris (landmarks 23/24).
3. **Suavização**: One Euro Filter por coordenada, já em torsos — assim os parâmetros do
   filtro significam a mesma coisa para quem está a 2 m e a 4 m da câmera.
4. **Qualidade**: `visibility` média dos âncoras < 0.5 ⇒ `degraded=True`; o frame sai
   normalizado, mas a FSM congela em vez de contar (SPEC-007).

Módulo puro: sem I/O, sem Django, sem MediaPipe. `normalize()` é a função pura testável com
fixtures; `Normalizer` é a mesma coisa com estado explícito, para o worker que recebe frame
a frame.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from workers.shared.filters import OneEuroFilter

__all__ = [
    "ANCHOR_LANDMARKS",
    "DEFAULT_PARAMS",
    "VISIBILITY_THRESHOLD",
    "Baseline",
    "NormFrame",
    "NormParams",
    "Normalizer",
    "RawFrame",
    "normalize",
]

# Índices MediaPipe (ver `Landmark` em events.py). Ficam explícitos aqui para o módulo não
# depender do contrato de transporte — normalização é matemática, não protocolo.
_LEFT_SHOULDER, _RIGHT_SHOULDER = 11, 12
_LEFT_HIP, _RIGHT_HIP = 23, 24
_LEFT_ANKLE, _RIGHT_ANKLE = 27, 28

#: Landmarks de que a normalização e as features dependem: se estes estão invisíveis, o frame
#: não serve (SPEC-006, item 4).
ANCHOR_LANDMARKS: tuple[int, ...] = (
    _LEFT_SHOULDER,
    _RIGHT_SHOULDER,
    _LEFT_HIP,
    _RIGHT_HIP,
    _LEFT_ANKLE,
    _RIGHT_ANKLE,
)

#: Limiar padrão de confiança/visibilidade (`context/conventions.md`).
VISIBILITY_THRESHOLD = 0.5

#: Torso mínimo em unidades de frame. Abaixo disso a escala é ruído (pessoa longe demais ou
#: landmarks colapsados) e dividir por ela explodiria as coordenadas.
_MIN_TORSO = 1e-3


@dataclass(frozen=True, slots=True)
class NormParams:
    """Parâmetros do One Euro. Únicos e globais na Fase Inicial (SPEC-006, item 3).

    `beta` está em torsos por segundo: o pulso de um polichinelo percorre ~3 torsos/s, então
    valores dessa ordem abrem a banda quando o movimento é real.

    Defaults escolhidos por medição na grade (mincutoff × beta) contra os dois critérios da
    SPEC-006, em 10, 15 e 30 fps: jitter cai 61–76% (exigência: ≥ 60%) com atraso ≤ 1 frame no
    movimento rápido. Mexer nestes números é mudança de comportamento: rodar `pytest
    tests/test_normalize.py` antes e depois.
    """

    mincutoff: float = 0.4
    beta: float = 1.5
    dcutoff: float = 1.0
    #: A escala (torso) é suavizada mais forte: ela deveria ser quase constante na sessão.
    scale_mincutoff: float = 0.4
    scale_beta: float = 0.0


DEFAULT_PARAMS = NormParams()


@dataclass(frozen=True, slots=True)
class Baseline:
    """Referências corporais medidas na calibração (SPEC-004 / T-019).

    Sem baseline, a normalização usa o valor instantâneo do frame — que funciona, mas mede o
    corpo enquanto ele se mexe. É por isso que a calibração existe: durante o countdown a
    pessoa está parada e de frente, e é a única hora em que as proporções podem ser medidas
    sem o movimento no meio.

    **Duas unidades convivem aqui, de propósito.** `torso` e `shoulder_width` ficam em unidades
    de frame (0–1), porque quem os consome é a validação de distância (SPEC-003): o tamanho
    APARENTE é justamente o sinal de "longe demais". Já `shoulder_span` e `wrist_rest_y` ficam
    em torsos, porque quem os consome é a FSM (SPEC-007), que raciocina em proporção corporal
    e não pode depender de a pessoa estar perto ou longe.
    """

    #: Distância ombro-médio → quadril-médio, em unidades de frame.
    torso: float | None = None
    #: Largura de ombros em unidades de frame (tamanho aparente).
    shoulder_width: float | None = None
    #: Largura de ombros em TORSOS — a referência da FSM para `ankle_spread`.
    shoulder_span: float | None = None
    #: Altura de repouso dos pulsos em torsos (y cresce para baixo), SPEC-004.
    wrist_rest_y: float | None = None


@dataclass(frozen=True, slots=True)
class RawFrame:
    """Entrada: um `pose.frame` cru — 33 landmarks `[x, y, z, visibility]`, 0–1 no frame."""

    ts: int
    seq: int
    landmarks: Sequence[Sequence[float]]


@dataclass(frozen=True, slots=True)
class NormFrame:
    """Saída: keypoints canônicos em torsos, origem no quadril médio.

    `points` tem 33×3 (x, y, z) já suavizados. `visibility` é a original, nunca filtrada.
    `torso` e `shoulder_width` saem em unidades de frame — quem precisa de escala absoluta
    (validação de distância, SPEC-003) usa esses valores.
    """

    ts: int
    seq: int
    points: np.ndarray
    visibility: np.ndarray
    torso: float
    shoulder_width: float
    degraded: bool

    def to_data(self) -> dict[str, object]:
        """Serializa para `data.norm` do mesmo `pose.frame` (SPEC-006, item 5)."""
        return {
            "points": [[round(value, 5) for value in point] for point in self.points.tolist()],
            "torso": round(self.torso, 5),
            "shoulder_width": round(self.shoulder_width, 5),
        }


class Normalizer:
    """Normaliza uma sequência de frames mantendo o estado dos filtros da sessão.

    Um `Normalizer` por sessão: o estado do One Euro é por sessão e por landmark (SPEC-006).
    """

    __slots__ = ("_baseline", "_last_torso", "_params", "_points_filter", "_scale_filter")

    def __init__(
        self, *, params: NormParams = DEFAULT_PARAMS, baseline: Baseline | None = None
    ) -> None:
        self._params = params
        self._baseline = baseline or Baseline()
        self._points_filter = OneEuroFilter(
            mincutoff=params.mincutoff, beta=params.beta, dcutoff=params.dcutoff
        )
        self._scale_filter = OneEuroFilter(
            mincutoff=params.scale_mincutoff, beta=params.scale_beta, dcutoff=params.dcutoff
        )
        self._last_torso: float | None = None

    def set_baseline(self, baseline: Baseline) -> None:
        """Instala a baseline medida na calibração (SPEC-004).

        A partir daqui a escala para de ser o valor instantâneo do frame e passa a ser a
        medida — o que torna a normalização estável quando a pessoa se aproxima ou gira. O
        filtro de escala fica para trás de propósito: ele existia justamente para suavizar a
        medida instantânea que acabou de deixar de ser usada.
        """
        self._baseline = baseline

    def push(self, frame: RawFrame) -> NormFrame:
        """Normaliza um frame. Chamar em ordem de `ts` crescente."""
        landmarks = np.asarray(frame.landmarks, dtype=float)
        if landmarks.shape != (33, 4):
            raise ValueError(f"landmarks devem ser 33x4, recebido {landmarks.shape}")

        coords = landmarks[:, :3]
        visibility = landmarks[:, 3].copy()
        t = frame.ts / 1000.0

        hip_mid = (coords[_LEFT_HIP] + coords[_RIGHT_HIP]) / 2.0
        shoulder_mid = (coords[_LEFT_SHOULDER] + coords[_RIGHT_SHOULDER]) / 2.0
        shoulder_width = float(
            np.linalg.norm(coords[_LEFT_SHOULDER][:2] - coords[_RIGHT_SHOULDER][:2])
        )

        anchors_visible = float(np.mean(visibility[list(ANCHOR_LANDMARKS)]))
        degraded = anchors_visible < VISIBILITY_THRESHOLD

        torso_raw = float(np.linalg.norm(shoulder_mid[:2] - hip_mid[:2]))
        torso = self._scale(torso_raw, t=t, degraded=degraded)

        centered = (coords - hip_mid) / torso

        # Frame ruim não entra no filtro: landmarks "adivinhados" pelo modelo poluiriam o
        # estado e sujariam os frames bons seguintes. Sai cru, marcado como degraded.
        points = centered if degraded else self._points_filter(centered, t)

        return NormFrame(
            ts=frame.ts,
            seq=frame.seq,
            points=points,
            visibility=visibility,
            torso=torso,
            shoulder_width=self._baseline.shoulder_width or shoulder_width,
            degraded=degraded,
        )

    def _scale(self, torso_raw: float, *, t: float, degraded: bool) -> float:
        """Escala do frame: baseline quando existe, senão o valor instantâneo suavizado."""
        if self._baseline.torso:
            return max(self._baseline.torso, _MIN_TORSO)
        if degraded and self._last_torso is not None:
            # Mantém a última escala boa em vez de aceitar uma medida sem confiança.
            return self._last_torso
        smoothed = float(self._scale_filter(max(torso_raw, _MIN_TORSO), t))
        self._last_torso = max(smoothed, _MIN_TORSO)
        return self._last_torso


def normalize(
    frames: Iterable[RawFrame],
    *,
    params: NormParams = DEFAULT_PARAMS,
    baseline: Baseline | None = None,
) -> list[NormFrame]:
    """Função pura da SPEC-006: `normalize(frames_in) -> frames_out`.

    Mesma entrada ⇒ mesma saída, sem estado compartilhado entre chamadas. É a forma usada por
    testes e pelo `evalctl` (SPEC-012); o worker em tempo real usa `Normalizer`.
    """
    normalizer = Normalizer(params=params, baseline=baseline)
    return [normalizer.push(frame) for frame in frames]
