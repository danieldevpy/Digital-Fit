"""Roteador do analysis-worker: envelope entra, envelopes saem (SPEC-007/T-009).

Toda a lógica do worker vive aqui e **não toca em Redis**: recebe um envelope de
`pose.frames`, atualiza o estado da sessão e devolve os envelopes para `events.analysis`. O
`main.py` só liga isso ao barramento.

Uma sessão = um `Normalizer` + um `ExerciseAnalyzer` + um contador de `seq` de saída. Estado em
memória, como o ARCHITECTURE §6 previu; retomada por snapshot é evolução (T-031).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from workers.analysis_worker.exercises import ExerciseAnalyzer, feed, get_analyzer
from workers.analysis_worker.feedback import FeedbackEngine
from workers.analysis_worker.scene import SceneValidator
from workers.shared.events import (
    Envelope,
    EventType,
    EventValidationError,
    Mode,
    PoseFrame,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    Source,
    make_envelope,
)
from workers.shared.normalize import Normalizer, RawFrame

__all__ = ["AnalysisRouter", "SessionState"]

logger = logging.getLogger(__name__)

#: Duração padrão quando a sessão chega sem `session.started` (SPEC-009: sessão de 30 s).
DEFAULT_DURATION_S = 30

#: Sessão sem frame nenhum por 10 s é abortada (SPEC-009, critério 4).
NO_DATA_TIMEOUT_MS = 10_000

#: Margem entre a duração da sessão e o TTL do registro em Redis (30 + 15 = 45 s, SPEC-009).
#: O worker não usa isso para expirar: ele sempre fecha antes, por duração ou por falta de
#: dados. A margem existe para que o token e o registro sobrevivam até o fim do exercício.
TTL_MARGIN_MS = 15_000


@dataclass(slots=True)
class SessionState:
    """Estado de uma sessão ativa no worker."""

    session_id: str
    exercise: str = "jumping_jack"
    mode: Mode = Mode.EDGE
    duration_s: int = DEFAULT_DURATION_S
    analyzer: ExerciseAnalyzer = field(default=None)  # type: ignore[assignment]
    normalizer: Normalizer = field(default_factory=Normalizer)
    scene: SceneValidator = field(default_factory=SceneValidator)
    feedback: FeedbackEngine = field(default_factory=FeedbackEngine)
    first_ts: int | None = None
    last_ts: int | None = None
    frames: int = 0
    out_seq: int = 0
    #: Relógio de parede do servidor — é ele que manda no timer (SPEC-009), não o `ts` do
    #: cliente, que pode vir com o relógio do celular torto.
    #: `None` = instante desconhecido. Não usar 0 como sentinela: 0 é um instante válido e
    #: quebraria qualquer teste de falsidade.
    opened_wall_ms: int | None = None
    first_frame_wall_ms: int | None = None
    last_frame_wall_ms: int | None = None

    def __post_init__(self) -> None:
        if self.analyzer is None:
            self.analyzer = get_analyzer(self.exercise)

    def next_seq(self) -> int:
        """`seq` dos eventos de saída — monotônico por sessão, contado pelo worker."""
        atual = self.out_seq
        self.out_seq += 1
        return atual

    def summary(self) -> dict[str, object]:
        """Consolidado da sessão para o relatório (SPEC-010).

        `quality_signals` é o que a FSM detectou; `feedback_issued` é o que o usuário de fato
        ouviu — os dois diferem pelo throttle, e essa diferença é justamente o que o relatório
        precisa mostrar ("você tentou 12 reps curtas, avisei 3 vezes").
        """
        return {**self.analyzer.summary(), "feedback_issued": dict(self.feedback.counts)}

    def expiry_reason(self, now_wall_ms: int) -> SessionEndReason | None:
        """Por que esta sessão deveria terminar agora — ou `None` se ela segue viva.

        Dois prazos, ambos em relógio do servidor:

        1. os 30 s de exercício correram desde o primeiro frame ⇒ `completed` (é **este** o
           timer autoritativo da SPEC-009; o do HUD é cosmético);
        2. nenhum frame por 10 s ⇒ `no_data` (critério 4 da SPEC-009).

        `timeout` fica no vocabulário para o caminho do TTL em Redis, mas na Fase 0 ele nunca
        dispara aqui: uma das duas regras acima sempre vence antes dos 45 s.
        """
        if (
            self.first_frame_wall_ms is not None
            and now_wall_ms - self.first_frame_wall_ms >= self.duration_s * 1000
        ):
            return SessionEndReason.COMPLETED
        referencia = (
            self.last_frame_wall_ms if self.last_frame_wall_ms is not None else self.opened_wall_ms
        )
        if referencia is not None and now_wall_ms - referencia >= NO_DATA_TIMEOUT_MS:
            return SessionEndReason.NO_DATA
        return None


class AnalysisRouter:
    """Traduz eventos de entrada em eventos de análise, sem I/O."""

    __slots__ = ("_now", "sessions", "slots")

    def __init__(self, *, slots=None) -> None:
        self.sessions: dict[str, SessionState] = {}
        self._now = 0
        #: Semáforo de vagas cloud (SPEC-009). `None` nos testes e em qualquer contexto sem
        #: Redis — a análise nunca depende dele para funcionar.
        self.slots = slots

    def _liberar_vaga(self, session_id: str) -> None:
        """Devolve a vaga cloud da sessão encerrada.

        Chamado para TODA sessão, sem perguntar o modo: liberar uma vaga que não existe é
        no-op, e a alternativa — guardar o modo e lembrar de checá-lo aqui — é exatamente o
        tipo de detalhe que se esquece num caminho de erro e vaza vaga para sempre.
        """
        if self.slots is None:
            return
        try:
            self.slots.release(session_id)
        except Exception:
            # Falha ao liberar não pode impedir o encerramento da sessão: o score de
            # expiração do semáforo recolhe a vaga sozinho mais tarde.
            logger.exception("falha ao liberar vaga cloud de %s", session_id)

    # ------------------------------------------------------------------ entrada

    def handle(self, envelope: Envelope, *, now_wall_ms: int | None = None) -> list[Envelope]:
        """Processa um envelope de `pose.frames` e devolve o que publicar."""
        self._now = now_wall_ms if now_wall_ms is not None else _wall_ms()
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
                opened_wall_ms=self._now,
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
            estado = SessionState(session_id=envelope.session_id, opened_wall_ms=self._now)
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
            estado.first_frame_wall_ms = self._now
        estado.last_ts = envelope.ts
        estado.last_frame_wall_ms = self._now
        estado.frames += 1

        norm = estado.normalizer.push(
            RawFrame(ts=envelope.ts, seq=envelope.seq, landmarks=payload.landmarks)
        )

        # Cena primeiro: um frame ruim ainda deve avisar o usuário, mesmo que a FSM congele
        # nele (é justamente quando o aviso importa).
        avisos = estado.scene.check(norm)
        sinais = feed(estado.analyzer, norm)

        saidas = [self._wrap(estado, payload_evento) for payload_evento in (*avisos, *sinais)]
        # O feedback engine é o último: ele decide o que o HUD vê, com prioridade e throttle.
        saidas.extend(
            self._wrap(estado, mensagem)
            for mensagem in estado.feedback.push([*avisos, *sinais], envelope.ts)
        )
        return saidas

    def _on_session_completed(self, envelope: Envelope) -> list[Envelope]:
        """Fim vindo de fora (API/TTL/cliente): fecha o estado e reemite com o total de reps."""
        estado = self.sessions.pop(envelope.session_id, None)
        if estado is None:
            return []
        self._liberar_vaga(envelope.session_id)
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

    # --------------------------------------------------------------------- timer

    def tick(self, now_wall_ms: int | None = None) -> list[Envelope]:
        """Fecha sessões cujo prazo venceu. Chamado a cada volta do loop do worker.

        É aqui que mora o **timer autoritativo** da SPEC-009: a sessão termina porque o servidor
        decidiu, não porque o cliente avisou.
        """
        agora = now_wall_ms if now_wall_ms is not None else _wall_ms()
        self._now = agora
        saidas: list[Envelope] = []
        for session_id, estado in list(self.sessions.items()):
            motivo = estado.expiry_reason(agora)
            if motivo is None:
                continue
            self.sessions.pop(session_id, None)
            self._liberar_vaga(session_id)
            reps = int(estado.analyzer.summary()["reps"])
            logger.info(
                "sessao %s encerrada pelo servidor (%s) com %s reps", session_id, motivo.value, reps
            )
            saidas.append(self._wrap(estado, SessionCompleted(reason=motivo, rep_count=reps)))
        return saidas

    # -------------------------------------------------------------------- saída

    def _wrap(self, estado: SessionState, payload) -> Envelope:
        """Envelopa um payload da FSM: `session_id` e `seq` são do worker, não do analisador.

        Sem frame nenhum (sessão fechada por `no_data`), o `ts` vem do relógio do servidor: zero
        não é epoch válido e o contrato recusaria o envelope.
        """
        return make_envelope(
            payload,
            session_id=estado.session_id,
            ts=estado.last_ts if estado.last_ts is not None else max(self._now, 1),
            seq=estado.next_seq(),
            source=Source.SYSTEM,
        )


def _wall_ms() -> int:
    """Relógio de parede do servidor em ms."""
    return int(time.time() * 1000)
