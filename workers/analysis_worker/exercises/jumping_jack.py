"""Polichinelo — o exercício 1 (SPEC-007, Fase Inicial).

FSM de duas fases com **histerese** e **debounce**::

    arm_angle > 110° E ankle_spread > 1.4      arm_angle < 40° E ankle_spread < 0.9
  FECHADO ──────────────────────────────► ABERTO ──────────────────────────────► FECHADO
                                                        = 1 repetição válida

No contrato essas duas fases são `Phase.REST` (fechado) e `Phase.PEAK` (aberto): o envelope
fala em repouso e pico porque é o que serve a qualquer exercício por repetição, e "fechado"
só quer dizer alguma coisa para este aqui. Fechado/aberto continua no texto porque é o nome
do movimento; `REST`/`PEAK` é o nome do dado.

- **Histerese**: os limiares de abrir e de fechar são diferentes, então oscilar em cima de um
  limiar não conta duas vezes.
- **Debounce**: cada fase dura no mínimo 250 ms; ruído não vira repetição.
- **Frame `degraded`**: a FSM congela — não conta e não penaliza (SPEC-006/007).
- **Rep parcial**: quem sobe até a faixa intermediária e volta gera sinal de qualidade
  (`ARMS_TOO_LOW`, `LEGS_TOO_CLOSED`) em vez de repetição.

Classe pura, sem I/O. Toda a contagem é testável com fixtures de keypoints.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from workers.analysis_worker.exercises.base import (
    DEFAULT_FRAME_ANCHORS,
    EXERCISES,
    AnalysisEvent,
    Features,
    Posture,
)
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import Baseline, NormFrame

__all__ = ["JumpingJackAnalyzer", "JumpingJackThresholds"]

_LEFT_SHOULDER, _RIGHT_SHOULDER = 11, 12
_LEFT_WRIST, _RIGHT_WRIST = 15, 16
_LEFT_ANKLE, _RIGHT_ANKLE = 27, 28

#: Largura de ombros mínima (em torsos) para dividir com segurança.
_MIN_SHOULDER_WIDTH = 1e-3


@dataclass(frozen=True, slots=True)
class JumpingJackThresholds:
    """Limiares da SPEC-007. Frozen de propósito: mudar isso é mudar comportamento.

    A bancada de avaliação (SPEC-012) varre estes valores contra o corpus rotulado — por isso
    são parâmetro, não constante espalhada pelo código.
    """

    open_arm_angle: float = 110.0
    open_ankle_spread: float = 1.4
    close_arm_angle: float = 40.0
    close_ankle_spread: float = 0.9
    #: Fase mínima antes de aceitar a transição seguinte (SPEC-007: debounce de 250 ms).
    min_phase_ms: int = 250
    #: Faixa de "quase abriu" que vira sinal de qualidade em vez de repetição.
    lazy_arm_angle: float = 70.0
    lazy_ankle_spread: float = 1.1
    #: Janela da cadência.
    cadence_window_ms: int = 10_000


@dataclass(slots=True)
class JumpingJackAnalyzer:
    """Um analisador por sessão: guarda fase, contagem e histórico de repetições."""

    slug: str = "jumping_jack"
    thresholds: JumpingJackThresholds = field(default_factory=JumpingJackThresholds)

    #: Medidas do corpo colhidas no countdown (SPEC-004 / T-019), entregues pelo estado da
    #: sessão. **Não** entram no cálculo de `ankle_spread` — ver o comentário em `features()`,
    #: que registra a medição pela qual isso foi decidido. Existem aqui para o relatório
    #: (SPEC-010) e para o gate de prontidão da Fase Evolução (T-030), que precisa saber onde
    #: os pulsos da pessoa repousam.
    baseline: Baseline | None = None

    phase: Phase = Phase.REST
    rep_count: int = 0

    _phase_since_ms: int | None = None
    _rep_started_ms: int | None = None
    _rep_timestamps: deque[int] = field(default_factory=deque)
    _peak_arm_angle: float = 0.0
    _peak_ankle_spread: float = 0.0
    _quality_signals: dict[str, int] = field(default_factory=dict)
    _frames_seen: int = 0
    _frames_degraded: int = 0

    # ----------------------------------------------------------------- features

    def features(self, frame: NormFrame) -> Features:
        """Features do polichinelo (SPEC-007). Entrada em torsos, saída em graus e razões.

        `cadence_10s` depende do histórico de repetições, não só do frame — é a única feature
        com memória, e é por isso que o analisador tem estado.
        """
        points = frame.points
        # Largura de ombros DESTE frame — e não a medida na calibração, apesar do que o
        # critério 3 da SPEC-004 sugeria. O divisor por frame se autocorrige: com a pessoa em
        # ângulo, a abertura dos pés e a largura dos ombros encurtam JUNTAS em perspectiva, e
        # a razão se mantém. Fixar o divisor numa medida única destrói essa invariância.
        #
        # Medido no corpus (T-019): trocar por `baseline.shoulder_span` levou o vídeo frontal
        # de 20/20 para 18/20, e uma varredura de limiares que consertava o frontal derrubava
        # o vídeo oblíquo de 19/21 para 3/21. Não há fator global que sirva aos dois, porque o
        # problema não é escala — é a perspectiva que o divisor por frame já cancelava.
        shoulder_width = max(
            abs(float(points[_LEFT_SHOULDER][0] - points[_RIGHT_SHOULDER][0])),
            _MIN_SHOULDER_WIDTH,
        )

        arm_angle = (
            self._abduction(points, _LEFT_SHOULDER, _LEFT_WRIST)
            + self._abduction(points, _RIGHT_SHOULDER, _RIGHT_WRIST)
        ) / 2

        ankle_gap = abs(float(points[_LEFT_ANKLE][0] - points[_RIGHT_ANKLE][0]))

        # y cresce para baixo: pulso acima da linha dos ombros ⇒ y menor.
        shoulder_line = (float(points[_LEFT_SHOULDER][1]) + float(points[_RIGHT_SHOULDER][1])) / 2
        wrists_y = (float(points[_LEFT_WRIST][1]) + float(points[_RIGHT_WRIST][1])) / 2

        return {
            "arm_angle": arm_angle,
            "wrist_above_shoulder": wrists_y < shoulder_line,
            "ankle_spread": ankle_gap / shoulder_width,
            "cadence_10s": self._cadence(frame.ts),
            "degraded": frame.degraded,
        }

    @staticmethod
    def _abduction(points, shoulder: int, wrist: int) -> float:
        """Ângulo ombro→pulso contra a vertical: 0° = braço para baixo, 180° = acima da cabeça."""
        dx = float(points[wrist][0] - points[shoulder][0])
        dy = float(points[wrist][1] - points[shoulder][1])
        return math.degrees(math.atan2(abs(dx), dy))

    def _cadence(self, ts: int) -> float:
        """Repetições nos últimos 10 s, extrapoladas para reps/minuto."""
        janela = self.thresholds.cadence_window_ms
        recentes = [t for t in self._rep_timestamps if ts - t <= janela]
        return len(recentes) * 60_000 / janela

    # ---------------------------------------------------------------------- FSM

    def step(self, feats: Features, ts: int) -> list[AnalysisEvent]:
        """Avança um frame. Chamar em ordem de `ts` crescente."""
        self._frames_seen += 1

        if feats.get("degraded"):
            # Estado congela: dado ruim não conta repetição nem gera crítica de execução.
            self._frames_degraded += 1
            return []

        if self._phase_since_ms is None:
            self._phase_since_ms = ts
            # A fase inicial é lida, não assumida (T-047). Se a captura já abre com a pessoa
            # ABERTA, nascer em `CLOSED` perde o ciclo inteiro: o debounce exige 250 ms de
            # estabilidade que um movimento em curso não oferece, e a abertura nunca é aceita.
            if self.initial_phase(feats) is Phase.PEAK:
                self.phase = Phase.PEAK
                # A rep começou antes da câmera. Contar a duração a partir daqui a subestima —
                # é o melhor que este frame permite saber, e é honesto quanto ao que foi visto.
                self._rep_started_ms = ts
                return [ExercisePhase(phase=Phase.PEAK)]

        arm_angle = float(feats["arm_angle"])
        ankle_spread = float(feats["ankle_spread"])
        limiares = self.thresholds
        estavel = ts - self._phase_since_ms >= limiares.min_phase_ms

        if self.phase is Phase.REST:
            self._peak_arm_angle = max(self._peak_arm_angle, arm_angle)
            self._peak_ankle_spread = max(self._peak_ankle_spread, ankle_spread)

            abriu = (
                arm_angle > limiares.open_arm_angle and ankle_spread > limiares.open_ankle_spread
            )
            if abriu and estavel:
                return self._enter(Phase.PEAK, ts)

            # Voltou à posição fechada sem ter aberto: a tentativa acabou. Se chegou perto,
            # vira crítica de execução — reclamar disso é mais útil que ignorar.
            fechou_de_novo = (
                arm_angle < limiares.close_arm_angle and ankle_spread < limiares.close_ankle_spread
            )
            if fechou_de_novo:
                return self._close_partial_attempt()
            return []

        # Fase ABERTO: só interessa voltar a fechar — aí nasce a repetição.
        fechou = arm_angle < limiares.close_arm_angle and ankle_spread < limiares.close_ankle_spread
        if fechou and estavel:
            eventos = self._enter(Phase.REST, ts)
            return [*eventos, self._count_rep(ts)]
        return []

    def _enter(self, phase: Phase, ts: int) -> list[AnalysisEvent]:
        if phase is Phase.PEAK:
            self._rep_started_ms = self._phase_since_ms
        self.phase = phase
        self._phase_since_ms = ts
        self._peak_arm_angle = 0.0
        self._peak_ankle_spread = 0.0
        return [ExercisePhase(phase=phase)]

    def _count_rep(self, ts: int) -> RepDetected:
        self.rep_count += 1
        self._rep_timestamps.append(ts)
        duration_ms = ts - self._rep_started_ms if self._rep_started_ms is not None else 0
        self._rep_started_ms = None
        return RepDetected(rep_count=self.rep_count, phase=Phase.REST, duration_ms=duration_ms)

    def _close_partial_attempt(self) -> list[AnalysisEvent]:
        """Fecha uma tentativa incompleta, emitindo os sinais do que faltou."""
        limiares = self.thresholds
        eventos: list[AnalysisEvent] = []

        if limiares.lazy_arm_angle <= self._peak_arm_angle <= limiares.open_arm_angle:
            eventos.append(self._signal(Code.ARMS_TOO_LOW, self._peak_arm_angle))
        if limiares.lazy_ankle_spread <= self._peak_ankle_spread <= limiares.open_ankle_spread:
            eventos.append(self._signal(Code.LEGS_TOO_CLOSED, self._peak_ankle_spread))

        self._peak_arm_angle = 0.0
        self._peak_ankle_spread = 0.0
        return eventos

    def _signal(self, code: Code, value: float) -> QualitySignal:
        self._quality_signals[code.value] = self._quality_signals.get(code.value, 0) + 1
        return QualitySignal(code=code, value=round(value, 2), rep_index=self.rep_count + 1)

    # ------------------------------------------------------- resto da interface

    def initial_phase(self, feats: Features) -> Phase:
        """Fase do primeiro frame utilizável (T-047, contrato em `base.py`).

        Usa os MESMOS limiares de abertura da transição — e os dois juntos, não um deles. É o
        que separa "está no topo de um polichinelo" de "está parado com os braços erguidos":
        de pé com os pés juntos, `ankle_spread` reprova, a fase adotada é `CLOSED`, e baixar
        os braços não vira repetição. Sem essa exigência dupla, quem calibrasse com o braço
        levantado ganharia uma rep que não fez.
        """
        if feats.get("degraded"):
            return Phase.REST
        limiares = self.thresholds
        aberto = (
            float(feats["arm_angle"]) > limiares.open_arm_angle
            and float(feats["ankle_spread"]) > limiares.open_ankle_spread
        )
        return Phase.PEAK if aberto else Phase.REST

    def ready_pose(self, feats: Features) -> bool:
        """Posição inicial do polichinelo: em pé, braços baixos, pés juntos."""
        if feats.get("degraded"):
            return False
        return (
            float(feats["arm_angle"]) < self.thresholds.close_arm_angle
            and float(feats["ankle_spread"]) < self.thresholds.close_ankle_spread
        )

    def scene_hints(self) -> _JumpingJackSceneHints:
        return _SCENE_HINTS

    def summary(self) -> dict[str, object]:
        """Consolidado para o relatório (SPEC-010)."""
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
class _JumpingJackSceneHints:
    body_height_range: tuple[float, float]
    posture: Posture = Posture.STANDING
    #: Em pe: os ancoras de sempre (ombros e tornozelos).
    frame_anchors: tuple[int, ...] = DEFAULT_FRAME_ANCHORS


#: Fase Inicial usa a faixa global da SPEC-003 (40–95% da altura do frame). A faixa ótima por
#: exercício (60–85% para polichinelo) é Fase Evolução.
_SCENE_HINTS = _JumpingJackSceneHints(body_height_range=(0.40, 0.95))

# Literal, não `JumpingJackAnalyzer.slug`: em dataclass com `slots=True` o atributo de classe
# é o descritor do slot, não o valor default.
EXERCISES["jumping_jack"] = JumpingJackAnalyzer
