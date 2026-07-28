"""Roteador do analysis-worker: envelope entra, envelopes saem (SPEC-007/T-009).

Toda a lógica do worker vive aqui e **não toca em Redis**: recebe um envelope de
`pose.frames`, atualiza o estado da sessão e devolve os envelopes para `events.analysis`. O
`main.py` só liga isso ao barramento.

Uma sessão = um `Normalizer` + um `ExerciseAnalyzer` + um contador de `seq` de saída. Estado em
memória, como o ARCHITECTURE §6 previu; retomada por snapshot é evolução (T-031).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from workers.analysis_worker.exercises import ExerciseAnalyzer, feed, get_analyzer
from workers.shared.events import (
    Envelope,
    EventType,
    EventValidationError,
    Mode,
    PoseFrame,
    SessionCompleted,
    SessionStarted,
    Source,
    make_envelope,
)
from workers.shared.normalize import Normalizer, RawFrame

__all__ = ["AnalysisRouter", "SessionState"]

logger = logging.getLogger(__name__)

#: Duração padrão quando a sessão chega sem `session.started` (SPEC-009: sessão de 30 s).
DEFAULT_DURATION_S = 30


@dataclass(slots=True)
class SessionState:
    """Estado de uma sessão ativa no worker."""

    session_id: str
    exercise: str = "jumping_jack"
    mode: Mode = Mode.EDGE
    duration_s: int = DEFAULT_DURATION_S
    analyzer: ExerciseAnalyzer = field(default=None)  # type: ignore[assignment]
    normalizer: Normalizer = field(default_factory=Normalizer)
    first_ts: int | None = None
    last_ts: int | None = None
    frames: int = 0
    out_seq: int = 0

    def __post_init__(self) -> None:
        if self.analyzer is None:
            self.analyzer = get_analyzer(self.exercise)

    def next_seq(self) -> int:
        """`seq` dos eventos de saída — monotônico por sessão, contado pelo worker."""
        atual = self.out_seq
        self.out_seq += 1
        return atual

    def summary(self) -> dict[str, object]:
        return self.analyzer.summary()


class AnalysisRouter:
    """Traduz eventos de entrada em eventos de análise, sem I/O."""

    __slots__ = ("sessions",)

    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}

    # ------------------------------------------------------------------ entrada

    def handle(self, envelope: Envelope) -> list[Envelope]:
        """Processa um envelope de `pose.frames` e devolve o que publicar."""
        match envelope.type:
            case EventType.SESSION_STARTED:
                return self._on_session_started(envelope)
            case EventType.POSE_FRAME:
                return self._on_pose_frame(envelope)
            case EventType.SESSION_COMPLETED:
                return self._on_session_completed(envelope)
            case EventType.SESSION_CAPABILITY:
                return []  # telemetria do cliente: interessa a report/dataset, não à FSM
            case _:
                logger.debug("evento ignorado pelo analysis-worker: %s", envelope.type)
                return []

    def _on_session_started(self, envelope: Envelope) -> list[Envelope]:
        dados = SessionStarted.from_data(envelope.data)
        if envelope.session_id in self.sessions:
            logger.warning("session.started repetido para %s; reiniciando", envelope.session_id)
        try:
            estado = SessionState(
                session_id=envelope.session_id,
                exercise=dados.exercise,
                mode=dados.mode,
                duration_s=dados.duration_s,
            )
        except ValueError as exc:
            # Exercício desconhecido: a sessão não abre, mas o worker segue vivo.
            logger.error("sessao %s recusada: %s", envelope.session_id, exc)
            return []
        self.sessions[envelope.session_id] = estado
        logger.info(
            "sessao %s aberta (%s, %s, %ss)",
            estado.session_id,
            estado.exercise,
            estado.mode.value,
            estado.duration_s,
        )
        return []

    def _on_pose_frame(self, envelope: Envelope) -> list[Envelope]:
        estado = self.sessions.get(envelope.session_id)
        if estado is None:
            # Frame antes do `session.started` (ou depois do fim): abre com o padrão da SPEC-009
            # em vez de descartar — perder repetições por corrida de eventos seria pior.
            estado = SessionState(session_id=envelope.session_id)
            self.sessions[envelope.session_id] = estado
            logger.info(
                "sessao %s aberta por pose.frame (sem session.started)", envelope.session_id
            )

        try:
            payload = PoseFrame.from_data(envelope.data)
        except EventValidationError:
            logger.warning("pose.frame invalido em %s, seq=%s", envelope.session_id, envelope.seq)
            return []

        if estado.first_ts is None:
            estado.first_ts = envelope.ts
        estado.last_ts = envelope.ts
        estado.frames += 1

        norm = estado.normalizer.push(
            RawFrame(ts=envelope.ts, seq=envelope.seq, landmarks=payload.landmarks)
        )
        return [
            self._wrap(estado, payload_evento) for payload_evento in feed(estado.analyzer, norm)
        ]

    def _on_session_completed(self, envelope: Envelope) -> list[Envelope]:
        """Fim vindo de fora (API/TTL/cliente): fecha o estado e reemite com o total de reps."""
        estado = self.sessions.pop(envelope.session_id, None)
        if estado is None:
            return []
        try:
            motivo = SessionCompleted.from_data(envelope.data).reason
        except EventValidationError:
            logger.warning("session.completed sem motivo valido em %s", envelope.session_id)
            return []
        logger.info(
            "sessao %s encerrada (%s) com %s reps",
            envelope.session_id,
            motivo.value,
            estado.analyzer.summary()["reps"],
        )
        return [
            self._wrap(
                estado,
                SessionCompleted(reason=motivo, rep_count=int(estado.analyzer.summary()["reps"])),
            )
        ]

    # -------------------------------------------------------------------- saída

    def _wrap(self, estado: SessionState, payload) -> Envelope:
        """Envelopa um payload da FSM: `session_id` e `seq` são do worker, não do analisador."""
        return make_envelope(
            payload,
            session_id=estado.session_id,
            ts=estado.last_ts or 0,
            seq=estado.next_seq(),
            source=Source.SYSTEM,
        )
