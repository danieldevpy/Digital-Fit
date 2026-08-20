"""Acumula `pose.frame` por sessão até a sessão fechar (SPEC-010, Fase Inicial).

Puro por decisão: envelopes entram, `SessionFrames` sai. Sem Redis, sem pyarrow, sem
filesystem — o que permite testar "sessão abortada sem frames não gera arquivo" com uma lista
de eventos, que é literalmente o critério 3 da spec.

**O que este módulo NÃO faz, de propósito:** normalizar. A SPEC-006 transforma landmarks
crus em keypoints canônicos (torsos, recentragem, One Euro), e seria tentador aplicar isso
aqui — "sequências normalizadas" está na spec. Mas os landmarks do `pose.frame` já vêm
normalizados 0–1 no frame, e assar a canonicalização de hoje no arquivo congelaria os
parâmetros do filtro dentro do dataset para sempre: mudar o `mincutoff` amanhã invalidaria
todo o corpus gravado até aqui. O dataset guarda o dado de entrada; a normalização é
reproduzível a partir dele, e é assim que ela continua sendo uma decisão revisável.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from workers.shared.events import (
    Envelope,
    EventType,
    EventValidationError,
    PoseFrame,
    SessionCapability,
    SessionStarted,
)

__all__ = [
    "FLUSH_GRACE_MS",
    "MAX_FRAMES",
    "STALE_MS",
    "FrameCollector",
    "FrameRow",
    "SessionFrames",
]

logger = logging.getLogger("dataset-writer")

#: Espera entre ver o `session.completed` e fechar o arquivo.
#:
#: Existe porque os dois streams são independentes: os frames chegam por `pose.frames` e o
#: encerramento autoritativo por `events.analysis` (é o analysis-worker que o emite, com o
#: total de reps). Nada garante que este processo já leu os últimos frames quando o
#: encerramento aparece — fechar na hora cortaria a cauda da sessão em silêncio, e um dataset
#: com o fim de cada série faltando é pior que um dataset menor.
FLUSH_GRACE_MS = 1_500

#: Sessão sem nenhum evento por tanto tempo não vai fechar sozinha (o worker que emitiria o
#: `session.completed` morreu antes). Aqui a evacuação **grava** o arquivo, ao contrário do
#: report-builder, que descarta: um relatório de sessão que não terminou seria errado, mas
#: keypoints continuam sendo keypoints — o valor deles não depende de a sessão ter fim limpo.
STALE_MS = 5 * 60_000

#: Teto de frames por sessão. 30 s a 15 fps são ~450; 3000 é ~3,5 min de captura e serve só
#: para uma sessão que nunca fecha não consumir memória sem limite.
MAX_FRAMES = 3_000

#: Teto de sessões acompanhadas ao mesmo tempo, pela mesma razão.
MAX_SESSIONS = 64

#: Quando os frames chegam antes do `session.started` — writer que subiu no meio de uma
#: sessão. O arquivo sai assim mesmo: keypoints sem rótulo de exercício ainda treinam
#: detecção de movimento, e mentir o rótulo padrão contaminaria o corpus.
UNKNOWN_EXERCISE = "unknown"


@dataclass(frozen=True, slots=True)
class FrameRow:
    """Uma linha do Parquet, ainda em Python puro."""

    seq: int
    ts: int
    #: 33 × `[x, y, z, visibility]`, como vieram no evento.
    landmarks: list[list[float]]
    degraded: bool
    source: str


@dataclass(frozen=True, slots=True)
class SessionFrames:
    """Uma sessão pronta para virar arquivo."""

    session_id: str
    exercise: str
    rows: list[FrameRow]
    #: De que lado e de que jeito o celular olhava (SPEC-027 §Eventos, T-176). Vazio quando o
    #: cliente não soube dizer — cliente antigo, ou origem em arquivo.
    facing: str = ""
    orientation: str = ""

    def __len__(self) -> int:
        return len(self.rows)


@dataclass(slots=True)
class _SessionBuffer:
    session_id: str
    exercise: str = UNKNOWN_EXERCISE
    rows: list[FrameRow] = field(default_factory=list)
    facing: str = ""
    orientation: str = ""
    #: Relógio do **servidor** — nunca o `ts` do envelope, que é do cliente. Comparar um com o
    #: outro evacuaria na hora toda sessão de celular com a hora torta (mesma lição da T-016).
    last_seen_ms: int = 0
    #: Instante (relógio do servidor) em que o arquivo deve ser fechado. `None` = sessão em
    #: andamento.
    close_at_ms: int | None = None
    #: Já avisou que bateu o teto — o log sai uma vez por sessão, não uma vez por frame.
    truncated: bool = False


class FrameCollector:
    """Bufferiza frames por sessão e entrega a sessão inteira quando ela fecha.

    Um coletor serve todas as sessões do processo. `push` nunca devolve nada: o fechamento é
    assíncrono (existe uma carência) e sai por `due()`, chamado a cada volta do loop.
    """

    __slots__ = ("_sessions",)

    def __init__(self) -> None:
        self._sessions: dict[str, _SessionBuffer] = {}

    @property
    def open_sessions(self) -> int:
        return len(self._sessions)

    def push(self, envelope: Envelope, *, now_ms: int) -> None:
        """Consome um envelope de `pose.frames` ou de `events.analysis`."""
        try:
            self._push(envelope, now_ms)
        except EventValidationError:
            # Frame torto não derruba a sessão inteira: descarta a linha e segue gravando o
            # resto. Um buraco no meio da sequência é visível pelo `seq`, que não é reindexado.
            logger.warning(
                "evento fora do contrato ignorado: %s em %s", envelope.type, envelope.session_id
            )

    def _push(self, envelope: Envelope, now_ms: int) -> None:
        if envelope.type is EventType.SESSION_COMPLETED:
            self._fechar(envelope.session_id, now_ms)
            return
        if envelope.type not in (
            EventType.POSE_FRAME,
            EventType.SESSION_STARTED,
            EventType.SESSION_CAPABILITY,
        ):
            # Todo o resto de `events.analysis` (reps, feedback, o sino do relatório) passa
            # aqui sem efeito: o dataset é a sequência de keypoints, não a saída da análise.
            return

        buffer = self._buffer(envelope.session_id)
        buffer.last_seen_ms = now_ms

        if envelope.type is EventType.SESSION_STARTED:
            buffer.exercise = SessionStarted.from_data(envelope.data).exercise
            return

        if envelope.type is EventType.SESSION_CAPABILITY:
            # Procedência da imagem (SPEC-027 §Eventos). Entra pela mesma porta do `exercise`:
            # é atributo da SESSÃO, repetido em toda linha do arquivo, e não um evento a mais
            # na sequência de keypoints.
            #
            # Sem isto o rótulo `landscape_forced` morreria no stream do Redis e nunca chegaria
            # ao corpus — e é no corpus que ele precisa existir, porque a razão de ele existir
            # é poder EXCLUIR essas sessões de uma calibração futura.
            capability = SessionCapability.from_data(envelope.data)
            buffer.facing = capability.facing
            buffer.orientation = capability.orientation
            return

        # Frame chegando com a sessão já marcada para fechar entra normalmente: é exatamente a
        # cauda que a carência de `FLUSH_GRACE_MS` existe para salvar.
        if len(buffer.rows) >= MAX_FRAMES:
            if not buffer.truncated:
                logger.warning(
                    "sessao %s passou de %s frames; o excedente nao entra no arquivo",
                    envelope.session_id,
                    MAX_FRAMES,
                )
                buffer.truncated = True
            return

        frame = PoseFrame.from_data(envelope.data)
        buffer.rows.append(
            FrameRow(
                seq=envelope.seq,
                ts=envelope.ts,
                landmarks=frame.landmarks,
                degraded=frame.degraded,
                source=envelope.source.value,
            )
        )

    def _fechar(self, session_id: str, now_ms: int) -> None:
        """Marca a sessão para fechar depois da carência.

        Sessão desconhecida **não** cria buffer: `session.completed` chega duas vezes quando o
        encerramento parte da API (uma em `pose.frames`, pedindo; outra em `events.analysis`,
        confirmando), e uma sessão já gravada não pode renascer vazia e sobrescrever o próprio
        arquivo com zero linhas.
        """
        buffer = self._sessions.get(session_id)
        if buffer is None:
            return
        buffer.last_seen_ms = now_ms
        if buffer.close_at_ms is None:
            buffer.close_at_ms = now_ms + FLUSH_GRACE_MS

    def _buffer(self, session_id: str) -> _SessionBuffer:
        buffer = self._sessions.get(session_id)
        if buffer is None:
            if len(self._sessions) >= MAX_SESSIONS:
                antiga = next(iter(self._sessions))
                logger.warning("teto de %s sessoes atingido; descartando %s", MAX_SESSIONS, antiga)
                del self._sessions[antiga]
            buffer = _SessionBuffer(session_id=session_id)
            self._sessions[session_id] = buffer
        return buffer

    def due(self, now_ms: int) -> list[SessionFrames]:
        """Sessões prontas para virar arquivo: fechadas com a carência vencida, ou abandonadas.

        Devolve e esquece — quem chama é responsável por gravar.
        """
        prontas: list[SessionFrames] = []
        for session_id, buffer in list(self._sessions.items()):
            fechada = buffer.close_at_ms is not None and now_ms >= buffer.close_at_ms
            abandonada = buffer.close_at_ms is None and now_ms - buffer.last_seen_ms >= STALE_MS
            if not (fechada or abandonada):
                continue
            if abandonada:
                logger.info(
                    "sessao %s sem eventos ha %s ms; gravando o que tem", session_id, STALE_MS
                )
            del self._sessions[session_id]
            prontas.append(
                SessionFrames(
                    session_id=session_id,
                    exercise=buffer.exercise,
                    rows=list(buffer.rows),
                    facing=buffer.facing,
                    orientation=buffer.orientation,
                )
            )
        return prontas

    def drain(self) -> list[SessionFrames]:
        """Fecha tudo que está aberto, sem carência nem log de abandono (shutdown limpo).

        Um SIGTERM no meio de uma sessão perderia a captura inteira se o buffer morresse com o
        processo — e um restart de deploy é justamente quando há sessão em andamento.
        """
        prontas = [
            SessionFrames(
                session_id=sid,
                exercise=buf.exercise,
                rows=list(buf.rows),
                facing=buf.facing,
                orientation=buf.orientation,
            )
            for sid, buf in self._sessions.items()
        ]
        self._sessions.clear()
        return prontas
