"""Agachamento — o exercício 2 (SPEC-007, Fase Evolução / T-032).

FSM de duas fases, mesma forma do polichinelo: histerese + debounce, frame `degraded` congela,
rep rasa vira sinal de qualidade em vez de repetição::

      hip_height < 0.72 torsos            hip_height > 0.90 torsos
  EM PÉ ────────────────────────► AGACHADO ────────────────────────► EM PÉ
                                                    = 1 repetição válida

**A feature NÃO é o ângulo do joelho, e essa é a decisão que define este módulo.**

O joelho de um agachamento viaja para a FRENTE, e uma câmera frontal — o enquadramento que a
SPEC-003 pede em todo o produto — quase não vê esse eixo. Medido no gerador de fixtures
(T-052), 80° reais de joelho leem **133°** no plano da imagem:

===========  =================  ==========================
joelho real  visto de frente    quadril→tornozelo (torsos)
===========  =================  ==========================
172° (em pé)      177°                    1,023
110°              152°                    0,830
 80° (fundo)      133°                    0,636
 70°              124°                    0,559
===========  =================  ==========================

Uma FSM com limiar em `knee_angle < 90°` lido da imagem **nunca dispararia**. O que a câmera
enxerga bem é a **altura do quadril**: a distância quadril→tornozelo cai de 1,02 para 0,64
torsos, monotônica e com folga enorme para qualquer limiar razoável.

E ela sobrevive à normalização (SPEC-006), que é o segundo requisito: a origem fica no
quadril médio, então a descida ABSOLUTA no quadro se perde — o que resta, e é o que se usa
aqui, é a perna encolhendo em relação ao próprio torso da pessoa.

Divisor por frame (o torso deste frame, que a normalização já aplicou) e não a medida da
calibração: é a lição medida na T-019. Com a pessoa em ângulo, torso e perna encurtam JUNTOS
em perspectiva e a razão se mantém; fixar o divisor destrói essa invariância.

Os números da tabela saem do gerador da T-052 passando pela normalização real; os testes em
`tests/test_squat.py` os travam.

Classe pura, sem I/O.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from workers.analysis_worker.exercises.base import EXERCISES, AnalysisEvent, Features
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import Baseline, NormFrame

__all__ = ["SquatAnalyzer", "SquatThresholds"]

_LEFT_HIP, _RIGHT_HIP = 23, 24
_LEFT_KNEE, _RIGHT_KNEE = 25, 26
_LEFT_ANKLE, _RIGHT_ANKLE = 27, 28


@dataclass(frozen=True, slots=True)
class SquatThresholds:
    """Limiares do agachamento. Frozen: mudar isto é mudar comportamento.

    **Estes números foram calibrados no gerador sintético, NÃO em vídeo de gente agachando.**
    O corpus (T-038) só tem polichinelo. São honestos quanto à geometria e conservadores
    quanto à realidade — o gerador não inclina o tronco à frente, e vídeo real inclina, o que
    encurta ainda mais a projeção e faz o sinal ser MAIOR do que o testado aqui.

    Errar para menos é o lado seguro, mas não substitui medição: gravar agachamentos e varrer
    estes valores contra eles é o que fecha a conta (ver Descobertas no BACKLOG).
    """

    #: Quadril→tornozelo, em torsos, abaixo do qual conta como agachado. 0,72 fica em torno de
    #: 90° de joelho — coxa aproximadamente paralela ao chão, o critério clássico.
    down_hip_height: float = 0.72
    #: Acima disto voltou a ficar em pé. A folga para 0,72 é a histerese.
    up_hip_height: float = 0.90
    #: Desceu, mas não o bastante: entre este valor e `down_hip_height` vira crítica.
    shallow_hip_height: float = 0.88
    #: Fase mínima antes de aceitar a transição seguinte (SPEC-007: debounce de 250 ms).
    min_phase_ms: int = 250
    #: Janela da cadência.
    cadence_window_ms: int = 10_000


@dataclass(slots=True)
class SquatAnalyzer:
    """Um analisador por sessão: guarda fase, contagem e histórico de repetições."""

    slug: str = "squat"
    thresholds: SquatThresholds = field(default_factory=SquatThresholds)

    #: Medidas da calibração (SPEC-004). Não entram no cálculo — ver o docstring do módulo
    #: sobre divisor por frame. Existem para o relatório e para o gate de prontidão (T-030).
    baseline: Baseline | None = None

    phase: Phase = Phase.REST
    rep_count: int = 0

    _phase_since_ms: int | None = None
    _rep_started_ms: int | None = None
    _rep_timestamps: deque[int] = field(default_factory=deque)
    #: O mais FUNDO que chegou na tentativa atual. Espelha o `_peak_*` do polichinelo com o
    #: sinal invertido: lá o movimento cresce, aqui ele encolhe.
    _lowest_hip_height: float = math.inf
    _quality_signals: dict[str, int] = field(default_factory=dict)
    _frames_seen: int = 0
    _frames_degraded: int = 0

    # ----------------------------------------------------------------- features

    def features(self, frame: NormFrame) -> Features:
        points = frame.points

        hip_y = (float(points[_LEFT_HIP][1]) + float(points[_RIGHT_HIP][1])) / 2
        ankle_y = (float(points[_LEFT_ANKLE][1]) + float(points[_RIGHT_ANKLE][1])) / 2
        knee_y = (float(points[_LEFT_KNEE][1]) + float(points[_RIGHT_KNEE][1])) / 2

        return {
            # A feature que decide. y cresce para baixo, então isto é positivo em pé.
            "hip_height": ankle_y - hip_y,
            # Quanto o joelho está acima do tornozelo — útil ao relatório e à T-033 (form
            # score), não à contagem.
            "knee_height": ankle_y - knee_y,
            # O ângulo que a CÂMERA vê, não o do corpo. O nome tem `view` de propósito: ele
            # existe para o relatório e para a bancada poder mostrar a diferença, e usá-lo
            # como critério de profundidade é o erro que este módulo foi escrito para evitar.
            "knee_angle_view": self._knee_angle_view(points),
            "cadence_10s": self._cadence(frame.ts),
            "degraded": frame.degraded,
        }

    @staticmethod
    def _knee_angle_view(points) -> float:
        """Ângulo quadril–joelho–tornozelo no plano da imagem, média das duas pernas."""

        def um_lado(quadril: int, joelho: int, tornozelo: int) -> float:
            ax = float(points[quadril][0] - points[joelho][0])
            ay = float(points[quadril][1] - points[joelho][1])
            cx = float(points[tornozelo][0] - points[joelho][0])
            cy = float(points[tornozelo][1] - points[joelho][1])
            na, nc = math.hypot(ax, ay), math.hypot(cx, cy)
            if na == 0.0 or nc == 0.0:
                return 180.0
            cosseno = (ax * cx + ay * cy) / (na * nc)
            return math.degrees(math.acos(max(-1.0, min(1.0, cosseno))))

        return (
            um_lado(_LEFT_HIP, _LEFT_KNEE, _LEFT_ANKLE)
            + um_lado(_RIGHT_HIP, _RIGHT_KNEE, _RIGHT_ANKLE)
        ) / 2

    def _cadence(self, ts: int) -> float:
        janela = self.thresholds.cadence_window_ms
        recentes = [t for t in self._rep_timestamps if ts - t <= janela]
        return len(recentes) * 60_000 / janela

    # ---------------------------------------------------------------------- FSM

    def step(self, feats: Features, ts: int) -> list[AnalysisEvent]:
        self._frames_seen += 1

        if feats.get("degraded"):
            self._frames_degraded += 1
            return []

        if self._phase_since_ms is None:
            self._phase_since_ms = ts
            # Fase lida, não assumida (T-047): quem começa a captura já agachado não perde a
            # repetição que está fazendo.
            if self.initial_phase(feats) is Phase.PEAK:
                self.phase = Phase.PEAK
                self._rep_started_ms = ts
                return [ExercisePhase(phase=Phase.PEAK)]

        hip_height = float(feats["hip_height"])
        limiares = self.thresholds
        estavel = ts - self._phase_since_ms >= limiares.min_phase_ms

        if self.phase is Phase.REST:
            self._lowest_hip_height = min(self._lowest_hip_height, hip_height)

            if hip_height < limiares.down_hip_height and estavel:
                return self._enter(Phase.PEAK, ts)

            # Voltou a ficar em pé sem ter descido o bastante: a tentativa acabou.
            if hip_height > limiares.up_hip_height:
                return self._close_partial_attempt()
            return []

        # Fase AGACHADO: só interessa voltar a subir — aí nasce a repetição.
        if hip_height > limiares.up_hip_height and estavel:
            eventos = self._enter(Phase.REST, ts)
            return [*eventos, self._count_rep(ts)]
        return []

    def _enter(self, phase: Phase, ts: int) -> list[AnalysisEvent]:
        if phase is Phase.PEAK:
            self._rep_started_ms = self._phase_since_ms
        self.phase = phase
        self._phase_since_ms = ts
        self._lowest_hip_height = math.inf
        return [ExercisePhase(phase=phase)]

    def _count_rep(self, ts: int) -> RepDetected:
        self.rep_count += 1
        self._rep_timestamps.append(ts)
        duration_ms = ts - self._rep_started_ms if self._rep_started_ms is not None else 0
        self._rep_started_ms = None
        return RepDetected(rep_count=self.rep_count, phase=Phase.REST, duration_ms=duration_ms)

    def _close_partial_attempt(self) -> list[AnalysisEvent]:
        """Fecha uma tentativa incompleta. Só reclama de quem chegou perto."""
        limiares = self.thresholds
        eventos: list[AnalysisEvent] = []

        if limiares.down_hip_height <= self._lowest_hip_height <= limiares.shallow_hip_height:
            eventos.append(self._signal(Code.SQUAT_TOO_SHALLOW, self._lowest_hip_height))

        self._lowest_hip_height = math.inf
        return eventos

    def _signal(self, code: Code, value: float) -> QualitySignal:
        self._quality_signals[code.value] = self._quality_signals.get(code.value, 0) + 1
        return QualitySignal(code=code, value=round(value, 2), rep_index=self.rep_count + 1)

    # ------------------------------------------------------- resto da interface

    def initial_phase(self, feats: Features) -> Phase:
        """Fase do primeiro frame utilizável (T-047, contrato em `base.py`)."""
        if feats.get("degraded"):
            return Phase.REST
        return (
            Phase.PEAK
            if float(feats["hip_height"]) < self.thresholds.down_hip_height
            else Phase.REST
        )

    def ready_pose(self, feats: Features) -> bool:
        """Posição inicial do agachamento: em pé, perna estendida."""
        if feats.get("degraded"):
            return False
        return float(feats["hip_height"]) > self.thresholds.up_hip_height

    def scene_hints(self) -> _SquatSceneHints:
        return _SCENE_HINTS

    def summary(self) -> dict[str, object]:
        cadencia = 0.0
        if self._rep_timestamps and self.rep_count:
            duracao_ms = self._rep_timestamps[-1] - self._rep_timestamps[0]
            if duracao_ms > 0:
                cadencia = (self.rep_count - 1) * 60_000 / duracao_ms
        return {
            "exercise": self.slug,
            "reps": self.rep_count,
            "phase": self.phase.value,
            "cadence_rpm": round(cadencia, 1),
            "quality_signals": dict(self._quality_signals),
            "frames": self._frames_seen,
            "frames_degraded": self._frames_degraded,
        }


@dataclass(frozen=True, slots=True)
class _SquatSceneHints:
    body_height_range: tuple[float, float]


#: Mesma faixa global da SPEC-003 que o polichinelo usa. A faixa ótima por exercício é Fase
#: Evolução da SPEC-003 — e no agachamento ela terá um detalhe próprio: a pessoa ENCOLHE ~20%
#: ao descer, então o enquadramento tem de caber quem está em pé, não quem está agachado.
_SCENE_HINTS = _SquatSceneHints(body_height_range=(0.40, 0.95))

# Literal pelo mesmo motivo do polichinelo: com `slots=True` o atributo de classe é o descritor.
EXERCISES["squat"] = SquatAnalyzer
