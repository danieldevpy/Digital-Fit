"""Abdominal (crunch) — o exercício 4, o segundo do chão (SPEC-007 / SPEC-020 Tier C).

FSM de duas fases, mesma forma dos outros, com o sinal invertido em relação à flexão: aqui o
movimento é subir, e o pico é o valor MÁXIMO::

           lift > 0.52 (~22° de tronco)        lift < 0.22 (~9°)
  DEITADO ────────────────────────────► ENCOLHIDO ──────────────► DEITADO
                                                       = 1 repetição válida

**Câmera de lado, celular no chão** — mesmo enquadramento da flexão (Tier C da SPEC-020).

**A feature é a subida do ombro dividida pela altura do joelho.** Pelo mesmo motivo da flexão:
razão entre duas medidas do mesmo eixo do mesmo corpo, imune ao formato do vídeo e às
proporções do boneco do gerador (a Descoberta `[A/T-106]` no BACKLOG mede o estrago da
alternativa). A diferença é que aqui a referência **não precisa de memória**: o joelho dobrado
com o pé apoiado é uma altura vertical estável que existe em todo frame, inclusive no primeiro
e inclusive com a pessoa parada — coisa que a prancha da flexão não oferece.

É também por isso que o joelho dobrado não é detalhe de execução, é requisito de medição, e o
Guia do exercício diz isso com todas as letras.

`lift` medido no gerador, com o pé na montagem padrão (calcanhar a ~30–45 cm do quadril):

===================  ======
tronco (com o chão)  lift
===================  ======
 4° (deitado)         0,097
16°                   0,382
20°                   0,474
25°                   0,586
30° (crunch cheio)    0,694
40°                   0,892
===================  ======

Os 30° não são gosto: é a amplitude que a literatura de execução (ACE) descreve como o fim do
crunch — escápulas saindo do chão, lombar no chão. Passar muito disso deixa de ser crunch e
recruta flexor de quadril, que é o erro que o `CRUNCH_TOO_FAST` persegue por outro caminho.

**O que este exercício NÃO promete.** A referência do joelho depende de onde a pessoa põe o pé:
medido no gerador, a coxa a 45° (pé longe) dá referência 0,601 torsos e a 72° (pé colado) dá
0,808 — ±15% em volta do padrão. Um crunch cheio conta nas duas montagens; um crunch raso pode
contar como válido para quem deixou o pé longe. Está registrado, e é parte do motivo de o
exercício nascer `beta`.

Classe pura, sem I/O.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from workers.analysis_worker.exercises.base import (
    EXERCISES,
    AnalysisEvent,
    Features,
    Posture,
)
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import Baseline, NormFrame

__all__ = ["CrunchAnalyzer", "CrunchThresholds"]

_NOSE = 0
_LEFT_SHOULDER, _RIGHT_SHOULDER = 11, 12
_LEFT_HIP, _RIGHT_HIP = 23, 24
_LEFT_KNEE, _RIGHT_KNEE = 25, 26

#: Altura de joelho mínima (em torsos) para a referência valer. Abaixo disso a perna está
#: estendida — não é a montagem do crunch — e a razão explodiria a partir de ruído.
_MIN_KNEE_HEIGHT = 0.25


@dataclass(frozen=True, slots=True)
class CrunchThresholds:
    """Limiares do abdominal. Frozen: mudar isto é mudar comportamento.

    Calibrados no gerador sintético (maturidade `beta`, SPEC-020). A unidade é fração da altura
    do joelho da própria pessoa, então não dependem das proporções do boneco.
    """

    #: Acima disto conta como encolhido (~22° de tronco).
    up_lift: float = 0.52
    #: Abaixo disto voltou a deitar. A folga para 0,52 é a histerese.
    down_lift: float = 0.22
    #: Subiu, mas não o bastante: entre este valor e `up_lift` vira crítica (~17°–22°).
    shallow_lift: float = 0.40
    #: Fase mínima antes de aceitar a transição seguinte (SPEC-007: debounce de 250 ms).
    min_phase_ms: int = 250
    #: Repetição mais curta que isto é impulso, não abdômen. Um crunch controlado leva ~2 s;
    #: abaixo de 0,8 s a subida veio do balanço, que é o erro de execução mais citado.
    min_rep_ms: int = 800
    #: Janela da cadência.
    cadence_window_ms: int = 10_000


@dataclass(slots=True)
class CrunchAnalyzer:
    """Um analisador por sessão: guarda fase, contagem e histórico de repetições."""

    slug: str = "abdominal"
    thresholds: CrunchThresholds = field(default_factory=CrunchThresholds)

    #: Medidas da calibração (SPEC-004). Não entram no cálculo — a feature é razão e cancela a
    #: escala. Existem para o relatório.
    baseline: Baseline | None = None

    phase: Phase = Phase.REST
    rep_count: int = 0

    _phase_since_ms: int | None = None
    _rep_started_ms: int | None = None
    _rep_timestamps: deque[int] = field(default_factory=deque)
    #: O mais ALTO que chegou na tentativa atual. Espelha o `_lowest_*` da flexão com o sinal
    #: invertido: lá o movimento encolhe, aqui ele cresce.
    _highest_lift: float = 0.0
    _quality_signals: dict[str, int] = field(default_factory=dict)
    _frames_seen: int = 0
    _frames_degraded: int = 0

    # ----------------------------------------------------------------- features

    def features(self, frame: NormFrame) -> Features:
        points = frame.points

        shoulder_y = (float(points[_LEFT_SHOULDER][1]) + float(points[_RIGHT_SHOULDER][1])) / 2
        hip_y = (float(points[_LEFT_HIP][1]) + float(points[_RIGHT_HIP][1])) / 2
        knee_y = (float(points[_LEFT_KNEE][1]) + float(points[_RIGHT_KNEE][1])) / 2
        nose_y = float(points[_NOSE][1])

        # y cresce para baixo: joelho levantado do chão ⇒ y menor que o do quadril.
        knee_height = hip_y - knee_y
        shoulder_rise = hip_y - shoulder_y

        return {
            # A feature que decide.
            "lift": self._lift(shoulder_rise, knee_height),
            "knee_height": knee_height,
            "shoulder_rise": shoulder_rise,
            # Ângulo do tronco com o chão, para o relatório. De lado ele é honesto, mas quem
            # conta é `lift`, que não depende de o torso ter sido medido no eixo certo.
            "trunk_angle_view": self._trunk_angle_view(shoulder_rise),
            # Quanto a cabeça sobe em relação ao ombro — só relatório. Vira sinal de qualidade
            # no dia em que houver vídeo real para assinar o sentido dele (ver DEVLOG).
            "head_lead": (hip_y - nose_y) / shoulder_rise if shoulder_rise > 0.05 else 0.0,
            "cadence_10s": self._cadence(frame.ts),
            "degraded": frame.degraded,
        }

    @staticmethod
    def _lift(shoulder_rise: float, knee_height: float) -> float:
        """Subida do ombro como fração da altura do joelho. 0 = deitado."""
        if knee_height < _MIN_KNEE_HEIGHT:
            # Perna estendida (ou modelo perdido): sem referência não há medida. Devolver 0
            # mantém a FSM deitada em vez de inventar uma subida.
            return 0.0
        return shoulder_rise / knee_height

    @staticmethod
    def _trunk_angle_view(shoulder_rise: float) -> float:
        """Ângulo do tronco com o chão, em graus.

        O torso vale 1.0 por definição depois da normalização, então a subida do ombro **é** o
        seno do ângulo — não há divisão a fazer.
        """
        return math.degrees(math.asin(max(-1.0, min(1.0, shoulder_rise))))

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
            # Fase lida, não assumida (T-047). Aqui isso é alcançável de verdade, ao contrário
            # da flexão: a referência do joelho existe no primeiro frame, então "está
            # encolhido" é uma afirmação que os features sabem fazer.
            if self.initial_phase(feats) is Phase.PEAK:
                self.phase = Phase.PEAK
                self._rep_started_ms = ts
                return [ExercisePhase(phase=Phase.PEAK)]

        lift = float(feats["lift"])
        limiares = self.thresholds
        estavel = ts - self._phase_since_ms >= limiares.min_phase_ms

        if self.phase is Phase.REST:
            self._highest_lift = max(self._highest_lift, lift)

            if lift > limiares.up_lift and estavel:
                return self._enter(Phase.PEAK, ts)

            # Voltou a deitar sem ter subido o bastante: a tentativa acabou.
            if lift < limiares.down_lift:
                return self._close_partial_attempt()
            return []

        # Fase ENCOLHIDO: só interessa voltar a deitar — aí nasce a repetição.
        if lift < limiares.down_lift and estavel:
            eventos = self._enter(Phase.REST, ts)
            return [*eventos, *self._count_rep(ts)]
        return []

    def _enter(self, phase: Phase, ts: int) -> list[AnalysisEvent]:
        if phase is Phase.PEAK:
            self._rep_started_ms = self._phase_since_ms
        self.phase = phase
        self._phase_since_ms = ts
        self._highest_lift = 0.0
        return [ExercisePhase(phase=phase)]

    def _count_rep(self, ts: int) -> list[AnalysisEvent]:
        """Fecha a repetição — e critica a cadência dela.

        Como o quadril caído da flexão, a pressa sai JUNTO com a repetição e não no lugar dela:
        o abdominal aconteceu, e aconteceu no impulso. Rep que não chega ao topo é outra coisa,
        e essa vira `CRUNCH_TOO_SHALLOW` sem repetição.
        """
        self.rep_count += 1
        self._rep_timestamps.append(ts)
        duration_ms = ts - self._rep_started_ms if self._rep_started_ms is not None else 0
        self._rep_started_ms = None

        eventos: list[AnalysisEvent] = [
            RepDetected(rep_count=self.rep_count, phase=Phase.REST, duration_ms=duration_ms)
        ]
        # `duration_ms > 0` protege a primeira rep de uma sessão que abriu já encolhida: ali a
        # duração é desconhecida, não é zero, e criticar a pressa de uma rep que a câmera não
        # viu começar seria inventar.
        if 0 < duration_ms < self.thresholds.min_rep_ms:
            eventos.append(self._signal(Code.CRUNCH_TOO_FAST, duration_ms / 1000))
        return eventos

    def _close_partial_attempt(self) -> list[AnalysisEvent]:
        """Fecha uma tentativa incompleta. Só reclama de quem chegou perto."""
        limiares = self.thresholds
        eventos: list[AnalysisEvent] = []

        if limiares.shallow_lift <= self._highest_lift <= limiares.up_lift:
            eventos.append(self._signal(Code.CRUNCH_TOO_SHALLOW, self._highest_lift))

        self._highest_lift = 0.0
        return eventos

    def _signal(self, code: Code, value: float) -> QualitySignal:
        self._quality_signals[code.value] = self._quality_signals.get(code.value, 0) + 1
        return QualitySignal(code=code, value=round(value, 2), rep_index=self.rep_count + 1)

    # ------------------------------------------------------- resto da interface

    def initial_phase(self, feats: Features) -> Phase:
        """Fase do primeiro frame utilizável (T-047, contrato em `base.py`)."""
        if feats.get("degraded"):
            return Phase.REST
        return Phase.PEAK if float(feats["lift"]) > self.thresholds.up_lift else Phase.REST

    def ready_pose(self, feats: Features) -> bool:
        """Posição inicial do abdominal: costas no chão e joelho dobrado.

        O joelho entra na condição porque sem ele não há medida — quem deita de perna esticada
        não está pronto para este exercício, está deitado.
        """
        if feats.get("degraded"):
            return False
        return (
            float(feats["lift"]) < self.thresholds.down_lift
            and float(feats["knee_height"]) >= _MIN_KNEE_HEIGHT
        )

    def scene_hints(self) -> _CrunchSceneHints:
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
class _CrunchSceneHints:
    body_height_range: tuple[float, float]
    frame_anchors: tuple[int, ...]
    posture: Posture = Posture.FLOOR


#: Tronco + coxa: os landmarks de que a contagem depende (o joelho é a referência vertical do
#: exercício). O tornozelo sai da lista pela mesma razão que saiu na flexão — num exercício de
#: chão ele é a parte mais longe da lente, e exigi-lo visível transforma enquadramento bom em
#: "você saiu do quadro".
_CRUNCH_ANCHORS = (11, 12, 23, 24, 25, 26)

#: Deitado, a distância é a maior separação entre os âncoras (`SceneValidator.body_height`).
#: Medido no gerador, por distância da câmera (torso = ombro→quadril como fração do frame):
#: 0,102–0,119 em t=0,07 (longe demais, tem de avisar), 0,234–0,271 em t=0,16 (bem
#: enquadrado), 0,659–0,762 em t=0,45 (colado).
#:
#: O piso em 0,15 fica no vão entre longe demais e bem enquadrado; o teto em 1,10 acompanha a
#: flexão. As duas pontas erram para o lado de NÃO avisar, como a SPEC-003 manda.
_SCENE_HINTS = _CrunchSceneHints(body_height_range=(0.15, 1.10), frame_anchors=_CRUNCH_ANCHORS)

# Literal pelo mesmo motivo dos outros: com `slots=True` o atributo de classe é o descritor.
EXERCISES["abdominal"] = CrunchAnalyzer
