"""Consolida `events.analysis` em relatório de sessão (SPEC-010, Fase Inicial).

Puro por decisão: envelopes entram, `SessionReport` sai. Sem Redis, sem Django, sem relógio
— o que permite testar "20 reps em 30 s dão cadência 40" com uma lista de eventos, e é a
mesma razão pela qual a FSM não conhece câmera (AGENTS.md).

A SPEC-010 diz que o relatório é **derivável 100% por replay dos eventos**. Isso é uma
propriedade, não um comentário: significa que nada aqui pode consultar o estado da sessão em
Redis nem perguntar nada a outro serviço. Se um número não puder ser calculado do que passou
por `events.analysis`, ele não entra no relatório — entra no backlog como evento que falta.

Tempo: todos os instantes vêm do `ts` do envelope, que na saída da análise é o `ts` do frame
que originou o evento (relógio do cliente). Dentro de uma sessão isso é consistente, que é o
que importa para medir cadência; comparar sessões pelo relógio absoluto seria outra conversa.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field

from workers.shared.events import (
    Envelope,
    EventType,
    EventValidationError,
    FeedbackIssued,
    RepDetected,
    SceneWarning,
    SessionCalibrated,
    SessionCompleted,
    SessionStarted,
)

__all__ = ["CADENCE_WINDOW_MS", "ReportAccumulator", "SessionReport"]

logger = logging.getLogger("report-builder")

#: Janela do gráfico de cadência (SPEC-010: "cadência média e por janela de 5s").
CADENCE_WINDOW_MS = 5_000

#: Teto de sessões acompanhadas ao mesmo tempo. Existe para o builder não virar um vazamento
#: de memória quando uma sessão nunca fecha: sem isso, cada sessão órfã ficaria para sempre.
MAX_SESSIONS = 512


@dataclass(frozen=True, slots=True)
class SessionReport:
    """O que o usuário vê no fim da sessão, e o que vai para o Postgres."""

    session_id: str
    exercise: str
    mode: str
    reason: str
    rep_count: int
    #: Da calibração ao fim — o tempo em que o exercício de fato valeu (SPEC-004/T-019). Não é
    #: o tempo de conexão: o countdown de preparação não é treino e não entra na cadência.
    duration_ms: int
    cadence_rpm: float
    #: Repetições por janela de 5 s, do início do exercício ao fim. É o gráfico da tela.
    cadence_windows: list[int]
    rep_durations_ms: list[int]
    feedback_counts: dict[str, int]
    scene_warning_counts: dict[str, int]
    calibration_samples: int

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "exercise": self.exercise,
            "mode": self.mode,
            "reason": self.reason,
            "rep_count": self.rep_count,
            "duration_ms": self.duration_ms,
            "cadence_rpm": self.cadence_rpm,
            "cadence_windows": list(self.cadence_windows),
            "rep_durations_ms": list(self.rep_durations_ms),
            "feedback_counts": dict(self.feedback_counts),
            "scene_warning_counts": dict(self.scene_warning_counts),
            "calibration_samples": self.calibration_samples,
        }


@dataclass(slots=True)
class _SessionBuffer:
    """O que se sabe de uma sessão ainda em andamento."""

    session_id: str
    exercise: str = "jumping_jack"
    mode: str = "edge"
    #: Instante em que o exercício passou a valer (`session.calibrated`). `None` enquanto a
    #: sessão está em preparação — e uma sessão que termina assim teve duração efetiva zero.
    started_ms: int | None = None
    last_ts: int = 0
    #: Última vez que esta sessão deu sinal, no **relógio do servidor** — e por isso separado
    #: do `last_ts`, que é o relógio do cliente. Só o servidor pode dizer "faz cinco minutos
    #: que não chega nada": comparar `ts` do cliente com o agora do servidor evacuaria na hora
    #: qualquer sessão vinda de um celular com a hora torta, e todo replay da bancada.
    last_seen_ms: int = 0
    rep_count: int = 0
    rep_ts: list[int] = field(default_factory=list)
    rep_durations_ms: list[int] = field(default_factory=list)
    feedback: Counter[str] = field(default_factory=Counter)
    scene: Counter[str] = field(default_factory=Counter)
    calibration_samples: int = 0


class ReportAccumulator:
    """Acumula eventos por sessão e fecha o relatório no `session.completed`.

    Um acumulador serve todas as sessões do processo. `push` devolve o relatório **apenas** no
    evento de fim; nos demais devolve `None`.
    """

    __slots__ = ("_sessions",)

    def __init__(self) -> None:
        self._sessions: dict[str, _SessionBuffer] = {}

    @property
    def open_sessions(self) -> int:
        return len(self._sessions)

    def push(self, envelope: Envelope, *, now_ms: int | None = None) -> SessionReport | None:
        """Consome um envelope de `events.analysis`.

        `now_ms` é o relógio do **servidor** e serve só para a evacuação por idade; quem não
        passa (os testes da consolidação) simplesmente nunca evacua.
        """
        try:
            return self._push(envelope, now_ms)
        except EventValidationError:
            # Um payload torto não pode derrubar o relatório inteiro: o evento é descartado e
            # a sessão segue sendo consolidada com o resto.
            logger.warning(
                "evento fora do contrato ignorado: %s em %s", envelope.type, envelope.session_id
            )
            return None

    def _push(self, envelope: Envelope, now_ms: int | None = None) -> SessionReport | None:
        if envelope.type is EventType.SESSION_REPORT_READY:
            # O próprio sino deste builder volta pelo stream. Ignorar ANTES de tocar no
            # dicionário: criar buffer aqui ressuscitaria a sessão que acabou de fechar, e ela
            # só sairia da memória pela evacuação por idade.
            return None

        if envelope.type is EventType.SESSION_COMPLETED:
            return self._fechar(envelope)

        buffer = self._buffer(envelope.session_id)
        buffer.last_ts = max(buffer.last_ts, envelope.ts)
        if now_ms is not None:
            buffer.last_seen_ms = now_ms

        match envelope.type:
            case EventType.SESSION_STARTED:
                dados = SessionStarted.from_data(envelope.data)
                buffer.exercise = dados.exercise
                buffer.mode = dados.mode.value
            case EventType.SESSION_CALIBRATED:
                dados_cal = SessionCalibrated.from_data(envelope.data)
                buffer.calibration_samples = dados_cal.samples
                # Só a primeira: a calibração acontece uma vez por sessão, e um reenvio não
                # pode reiniciar o relógio da cadência no meio do exercício.
                if buffer.started_ms is None:
                    buffer.started_ms = envelope.ts
            case EventType.REP_DETECTED:
                dados_rep = RepDetected.from_data(envelope.data)
                # `rep_count` é autoritativo do worker — nunca somado aqui. Se um evento se
                # perder, o total continua certo e só o gráfico fica com um buraco.
                buffer.rep_count = dados_rep.rep_count
                buffer.rep_ts.append(envelope.ts)
                buffer.rep_durations_ms.append(dados_rep.duration_ms)
            case EventType.FEEDBACK_ISSUED:
                buffer.feedback[FeedbackIssued.from_data(envelope.data).code.value] += 1
            case EventType.SCENE_WARNING:
                buffer.scene[SceneWarning.from_data(envelope.data).code.value] += 1
            case _:
                # `exercise.phase` e `session.report.ready` (o próprio sino deste builder)
                # passam por aqui sem afetar nada.
                pass
        return None

    def _buffer(self, session_id: str) -> _SessionBuffer:
        buffer = self._sessions.get(session_id)
        if buffer is None:
            if len(self._sessions) >= MAX_SESSIONS:
                # Descarta a mais antiga em vez de crescer sem limite. Perder o gráfico de uma
                # sessão órfã é melhor do que o processo morrer por memória com todas dentro.
                antiga = next(iter(self._sessions))
                logger.warning("teto de %s sessoes atingido; descartando %s", MAX_SESSIONS, antiga)
                del self._sessions[antiga]
            buffer = _SessionBuffer(session_id=session_id)
            self._sessions[session_id] = buffer
        return buffer

    def _fechar(self, envelope: Envelope) -> SessionReport:
        dados = SessionCompleted.from_data(envelope.data)
        buffer = self._sessions.pop(envelope.session_id, None) or _SessionBuffer(
            session_id=envelope.session_id
        )

        fim = max(envelope.ts, buffer.last_ts)
        duracao = max(0, fim - buffer.started_ms) if buffer.started_ms is not None else 0
        # O total vem do evento de fim, não da contagem de `rep.detected` vistos: assim um
        # builder que subiu no meio da sessão ainda reporta o número certo — só o gráfico sai
        # incompleto, e isso é visível.
        reps = dados.rep_count

        return SessionReport(
            session_id=envelope.session_id,
            exercise=buffer.exercise,
            mode=buffer.mode,
            reason=dados.reason.value,
            rep_count=reps,
            duration_ms=duracao,
            cadence_rpm=_cadencia_rpm(reps, duracao),
            cadence_windows=_janelas(buffer.rep_ts, buffer.started_ms, duracao),
            rep_durations_ms=list(buffer.rep_durations_ms),
            feedback_counts=dict(buffer.feedback),
            scene_warning_counts=dict(buffer.scene),
            calibration_samples=buffer.calibration_samples,
        )

    def drop(self, session_id: str) -> None:
        """Esquece uma sessão sem gerar relatório (usado ao evacuar sessões velhas)."""
        self._sessions.pop(session_id, None)

    def stale(self, now_ms: int, *, max_age_ms: int) -> list[str]:
        """Sessões sem evento há tempo demais — nunca vão fechar sozinhas.

        Mede pelo relógio do servidor (`last_seen_ms`). Sessão que nunca foi marcada — porque
        quem alimentou o acumulador não passou `now_ms` — nunca é evacuada: melhor manter na
        memória do que descartar por uma comparação de relógios diferentes.
        """
        return [
            session_id
            for session_id, buffer in self._sessions.items()
            if buffer.last_seen_ms and now_ms - buffer.last_seen_ms >= max_age_ms
        ]


def _cadencia_rpm(reps: int, duracao_ms: int) -> float:
    """Repetições por minuto. Sessão de duração zero não tem cadência — tem zero."""
    if duracao_ms <= 0 or reps <= 0:
        return 0.0
    return round(reps * 60_000 / duracao_ms, 2)


def _janelas(rep_ts: list[int], started_ms: int | None, duracao_ms: int) -> list[int]:
    """Repetições por janela de 5 s, contadas a partir do início do exercício.

    As janelas cobrem a sessão inteira, inclusive as vazias: um gráfico que pula os buracos
    esconderia justamente a pausa que o usuário quer ver.
    """
    if started_ms is None or duracao_ms <= 0:
        return []

    total = max(1, -(-duracao_ms // CADENCE_WINDOW_MS))  # divisão para cima
    janelas = [0] * total
    for ts in rep_ts:
        indice = (ts - started_ms) // CADENCE_WINDOW_MS
        if 0 <= indice < total:
            janelas[indice] += 1
        elif indice >= total:
            # Rep no último milissegundo, depois do fim nominal da última janela: entra na
            # última em vez de sumir do gráfico.
            janelas[-1] += 1
    return janelas
