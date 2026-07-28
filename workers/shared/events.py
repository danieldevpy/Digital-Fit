"""Contrato de eventos do Digital Fit — **única fonte da verdade** (SPEC-002).

Todo dado que atravessa uma fronteira do sistema (navegador ↔ gateway, gateway ↔ workers,
worker ↔ worker) é um evento com este envelope::

    {"v": 1, "type": "pose.frame", "session_id": "...", "ts": 1722100000123,
     "seq": 142, "source": "edge", "data": {...}}

- `ts`: epoch em **milissegundos**, medido no produtor.
- `seq`: contador monotônico **por sessão** (nunca repete nem retrocede).
- `source`: `edge` (navegador), `cloud` (pose-worker) ou `system` (api/workers).
- `data`: payload do tipo — cada tipo tem uma dataclass neste módulo.

Transporte:

- Cliente ↔ gateway: WebSocket binário com **MessagePack** (`encode_envelope`/`decode_envelope`).
- Interno: **Redis Streams**, envelope inteiro em um campo
  (`to_stream_fields`/`from_stream_fields`).

Regra de ouro (AGENTS.md): mudou ou nasceu evento ⇒ muda aqui primeiro, depois a spec, depois
o DEVLOG (o cliente web lê de lá). Nada aqui importa Django, Redis, numpy ou MediaPipe.

Cobertura desta versão (v1): eventos da **Fase 0** (edge only, sem auth). Ficam para depois,
junto das tasks que os produzem: `frame.raw` (modo cloud, T-015/SPEC-005),
`session.report.ready` (T-020/SPEC-010), `scene.status` e `hold.progress` (Fase Evolução).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any, ClassVar, Protocol, Self, runtime_checkable

import msgpack

__all__ = [
    "CLIENT_PUSH_TYPES",
    "CONSUMER_GROUPS",
    "LANDMARK_COUNT",
    "LANDMARK_NAMES",
    "PROTOCOL_VERSION",
    "STREAM_FOR_TYPE",
    "STREAM_MAXLEN",
    "STREAM_PAYLOAD_FIELD",
    "Code",
    "Envelope",
    "EventPayload",
    "EventType",
    "EventValidationError",
    "ExercisePhase",
    "FeedbackIssued",
    "Landmark",
    "Mode",
    "Phase",
    "PoseFrame",
    "QualitySignal",
    "RepDetected",
    "SceneWarning",
    "SessionCapability",
    "SessionCompleted",
    "SessionEndReason",
    "SessionStarted",
    "Severity",
    "Source",
    "Stream",
    "decode_envelope",
    "encode_envelope",
    "from_stream_fields",
    "make_envelope",
    "to_stream_fields",
]

PROTOCOL_VERSION = 1


class EventValidationError(ValueError):
    """Envelope ou payload fora do contrato.

    O gateway rejeita e loga o evento sem derrubar a conexão (SPEC-002, critério 3).
    """


# ---------------------------------------------------------------------------
# Vocabulário
# ---------------------------------------------------------------------------


class Source(StrEnum):
    """Origem do dado. Downstream não ramifica por `source` (SPEC-005, critério 4)."""

    EDGE = "edge"
    CLOUD = "cloud"
    SYSTEM = "system"
    #: Bancada de avaliação lendo arquivo de vídeo ou fixture (SPEC-012). Existe para que um
    #: resultado de eval nunca se disfarce de sessão real no dataset.
    FILE = "file"


class Mode(StrEnum):
    """Modo de extração de pose da sessão, decidido pelo capability probe (SPEC-001)."""

    EDGE = "edge"
    CLOUD = "cloud"


class EventType(StrEnum):
    """Tipos de evento da Fase 0, em dot.case."""

    SESSION_CAPABILITY = "session.capability"
    SESSION_STARTED = "session.started"
    POSE_FRAME = "pose.frame"
    EXERCISE_PHASE = "exercise.phase"
    REP_DETECTED = "rep.detected"
    QUALITY_SIGNAL = "quality.signal"
    SCENE_WARNING = "scene.warning"
    FEEDBACK_ISSUED = "feedback.issued"
    SESSION_COMPLETED = "session.completed"


class Stream(StrEnum):
    """Streams do Redis (plural do fluxo, conforme `context/conventions.md`)."""

    FRAMES_RAW = "frames.raw"  # só modo cloud (T-015/T-016)
    POSE_FRAMES = "pose.frames"
    EVENTS_ANALYSIS = "events.analysis"


#: Limite aproximado por stream. Quem publica usa `XADD ... MAXLEN ~`; o servidor Redis não
#: é responsável por isso (SPEC-002: "Redis nunca ultrapassa o MAXLEN configurado").
STREAM_MAXLEN = 5000

#: Consumer groups previstos por stream (SPEC-002, notas técnicas).
CONSUMER_GROUPS: dict[Stream, tuple[str, ...]] = {
    Stream.FRAMES_RAW: ("pose-workers",),
    Stream.POSE_FRAMES: ("analysis", "dataset"),
    Stream.EVENTS_ANALYSIS: ("gateway", "report", "dataset"),
}

#: Rota **padrão** de publicação por tipo. `pose.frames` é o fluxo de ENTRADA da análise
#: (frames + metadados da sessão); `events.analysis` é a SAÍDA dela — o que HUD, relatório e
#: dataset consomem. Um produtor pode publicar também em outro stream quando precisar de
#: outra audiência (ex.: API encerrando sessão por TTL), mas nunca inventa stream fora de
#: `Stream`.
STREAM_FOR_TYPE: dict[EventType, Stream] = {
    EventType.SESSION_CAPABILITY: Stream.POSE_FRAMES,
    EventType.SESSION_STARTED: Stream.POSE_FRAMES,
    EventType.POSE_FRAME: Stream.POSE_FRAMES,
    EventType.EXERCISE_PHASE: Stream.EVENTS_ANALYSIS,
    EventType.REP_DETECTED: Stream.EVENTS_ANALYSIS,
    EventType.QUALITY_SIGNAL: Stream.EVENTS_ANALYSIS,
    EventType.SCENE_WARNING: Stream.EVENTS_ANALYSIS,
    EventType.FEEDBACK_ISSUED: Stream.EVENTS_ANALYSIS,
    EventType.SESSION_COMPLETED: Stream.EVENTS_ANALYSIS,
}

#: O que o gateway empurra de volta ao cliente pelo WS (SPEC-002 fase inicial). `pose.frame`
#: nunca volta, e `quality.signal` é insumo do feedback engine — o HUD só vê `feedback.issued`.
CLIENT_PUSH_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.EXERCISE_PHASE,
        EventType.REP_DETECTED,
        EventType.SCENE_WARNING,
        EventType.FEEDBACK_ISSUED,
        EventType.SESSION_COMPLETED,
    }
)


class Landmark(IntEnum):
    """Índices dos 33 landmarks do MediaPipe Pose (SPEC-005 pede a documentação aqui)."""

    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


LANDMARK_COUNT = 33
LANDMARK_NAMES: tuple[str, ...] = tuple(member.name.lower() for member in Landmark)


class Phase(StrEnum):
    """Fase do movimento na FSM (SPEC-007). Polichinelo: fechado ⇄ aberto."""

    CLOSED = "closed"
    OPEN = "open"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"


class Code(StrEnum):
    """Códigos de sinal/feedback da Fase 0 (SPEC-003 e SPEC-008).

    O código é o contrato; a mensagem em pt-BR vive no catálogo YAML do feedback engine
    (T-010) e pode mudar sem quebrar cliente nem dataset.
    """

    # Execução — SPEC-007, viram `quality.signal`
    ARMS_TOO_LOW = "ARMS_TOO_LOW"
    LEGS_TOO_CLOSED = "LEGS_TOO_CLOSED"
    # Cena — SPEC-003, viram `scene.warning`
    OUT_OF_FRAME = "OUT_OF_FRAME"
    TOO_FAR = "TOO_FAR"
    TOO_CLOSE = "TOO_CLOSE"


class SessionEndReason(StrEnum):
    """Por que a sessão terminou (SPEC-009)."""

    COMPLETED = "completed"  # os 30s correram até o fim
    TIMEOUT = "timeout"  # TTL da sessão expirou
    ABORTED = "aborted"  # usuário/cliente encerrou antes
    NO_DATA = "no_data"  # nenhum frame por 10s


# ---------------------------------------------------------------------------
# Payloads (o `data` de cada tipo)
# ---------------------------------------------------------------------------


@runtime_checkable
class EventPayload(Protocol):
    """O que todo payload de evento sabe fazer."""

    TYPE: ClassVar[EventType]

    def to_data(self) -> dict[str, Any]: ...


def _require(data: dict[str, Any], key: str) -> Any:
    try:
        return data[key]
    except (KeyError, TypeError) as exc:
        raise EventValidationError(f"campo obrigatorio ausente em data: {key!r}") from exc


def _as_int(value: Any, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EventValidationError(f"{key} deve ser int, recebido {type(value).__name__}")
    return value


def _as_str(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value:
        raise EventValidationError(f"{key} deve ser str nao vazia")
    return value


def _as_enum[E: StrEnum](enum_cls: type[E], value: Any, key: str) -> E:
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise EventValidationError(f"{key} invalido: {value!r}") from exc


@dataclass(frozen=True, slots=True)
class SessionCapability:
    """Resultado do capability probe, enviado pelo cliente ao preparar a sessão (SPEC-001)."""

    TYPE: ClassVar[EventType] = EventType.SESSION_CAPABILITY

    mode: Mode
    probe_fps: float
    webgl: bool
    ua: str = ""

    def to_data(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "probe_fps": self.probe_fps,
            "webgl": self.webgl,
            "ua": self.ua,
        }

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        return cls(
            mode=_as_enum(Mode, _require(data, "mode"), "mode"),
            probe_fps=float(_require(data, "probe_fps")),
            webgl=bool(_require(data, "webgl")),
            ua=str(data.get("ua", "")),
        )


@dataclass(frozen=True, slots=True)
class SessionStarted:
    """Sessão admitida pela API; abre o estado no analysis-worker (SPEC-009)."""

    TYPE: ClassVar[EventType] = EventType.SESSION_STARTED

    exercise: str
    mode: Mode
    duration_s: int

    def to_data(self) -> dict[str, Any]:
        return {"exercise": self.exercise, "mode": self.mode.value, "duration_s": self.duration_s}

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        return cls(
            exercise=_as_str(_require(data, "exercise"), "exercise"),
            mode=_as_enum(Mode, _require(data, "mode"), "mode"),
            duration_s=_as_int(_require(data, "duration_s"), "duration_s"),
        )


@dataclass(frozen=True, slots=True)
class PoseFrame:
    """33 landmarks `[x, y, z, visibility]` normalizados 0–1 no frame (SPEC-005).

    `norm` é preenchido pela normalização (SPEC-006) **no mesmo evento** — keypoints
    canônicos não criam tipo novo. `degraded` marca frame com âncoras pouco visíveis: a FSM
    congela em vez de contar (SPEC-006/007).
    """

    TYPE: ClassVar[EventType] = EventType.POSE_FRAME

    landmarks: list[list[float]]
    norm: dict[str, Any] | None = None
    degraded: bool = False

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"landmarks": self.landmarks}
        if self.degraded:
            data["degraded"] = True
        if self.norm is not None:
            data["norm"] = self.norm
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        landmarks = _require(data, "landmarks")
        if not isinstance(landmarks, list) or len(landmarks) != LANDMARK_COUNT:
            recebido = len(landmarks) if isinstance(landmarks, list) else type(landmarks).__name__
            raise EventValidationError(
                f"landmarks deve ter {LANDMARK_COUNT} entradas, recebido {recebido}"
            )
        for index, point in enumerate(landmarks):
            if not isinstance(point, list | tuple) or len(point) != 4:
                raise EventValidationError(
                    f"landmark {index} deve ser [x, y, z, visibility], recebido {point!r}"
                )
        return cls(
            landmarks=[[float(value) for value in point] for point in landmarks],
            norm=data.get("norm"),
            degraded=bool(data.get("degraded", False)),
        )


@dataclass(frozen=True, slots=True)
class ExercisePhase:
    """Transição de fase da FSM — habilita a animação de fase no HUD (SPEC-007)."""

    TYPE: ClassVar[EventType] = EventType.EXERCISE_PHASE

    phase: Phase

    def to_data(self) -> dict[str, Any]:
        return {"phase": self.phase.value}

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        return cls(phase=_as_enum(Phase, _require(data, "phase"), "phase"))


@dataclass(frozen=True, slots=True)
class RepDetected:
    """Repetição válida concluída (SPEC-007)."""

    TYPE: ClassVar[EventType] = EventType.REP_DETECTED

    rep_count: int
    phase: Phase
    duration_ms: int

    def to_data(self) -> dict[str, Any]:
        return {
            "rep_count": self.rep_count,
            "phase": self.phase.value,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        return cls(
            rep_count=_as_int(_require(data, "rep_count"), "rep_count"),
            phase=_as_enum(Phase, _require(data, "phase"), "phase"),
            duration_ms=_as_int(_require(data, "duration_ms"), "duration_ms"),
        )


@dataclass(frozen=True, slots=True)
class QualitySignal:
    """Sinal bruto de qualidade de execução, ainda sem tratamento humano (SPEC-007).

    Insumo do feedback engine (SPEC-008), que decide se e quando virar `feedback.issued`.
    """

    TYPE: ClassVar[EventType] = EventType.QUALITY_SIGNAL

    code: Code
    value: float | None = None
    rep_index: int | None = None

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code.value}
        if self.value is not None:
            data["value"] = self.value
        if self.rep_index is not None:
            data["rep_index"] = self.rep_index
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        raw_value = data.get("value")
        raw_index = data.get("rep_index")
        return cls(
            code=_as_enum(Code, _require(data, "code"), "code"),
            value=None if raw_value is None else float(raw_value),
            rep_index=None if raw_index is None else _as_int(raw_index, "rep_index"),
        )


@dataclass(frozen=True, slots=True)
class SceneWarning:
    """Problema de cena detectado por keypoints (SPEC-003). Não bloqueia a sessão na Fase 0."""

    TYPE: ClassVar[EventType] = EventType.SCENE_WARNING

    code: Code
    severity: Severity = Severity.WARNING
    hint: str | None = None

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code.value, "severity": self.severity.value}
        if self.hint is not None:
            data["hint"] = self.hint
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        hint = data.get("hint")
        return cls(
            code=_as_enum(Code, _require(data, "code"), "code"),
            severity=_as_enum(Severity, data.get("severity", Severity.WARNING), "severity"),
            hint=None if hint is None else str(hint),
        )


@dataclass(frozen=True, slots=True)
class FeedbackIssued:
    """Feedback já priorizado e com throttle, pronto para o HUD (SPEC-008)."""

    TYPE: ClassVar[EventType] = EventType.FEEDBACK_ISSUED

    code: Code
    severity: Severity
    message: str
    hint: str | None = None

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.code.value,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.hint is not None:
            data["hint"] = self.hint
        return data

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        hint = data.get("hint")
        return cls(
            code=_as_enum(Code, _require(data, "code"), "code"),
            severity=_as_enum(Severity, _require(data, "severity"), "severity"),
            message=_as_str(_require(data, "message"), "message"),
            hint=None if hint is None else str(hint),
        )


@dataclass(frozen=True, slots=True)
class SessionCompleted:
    """Fim da sessão — o timer de 30s é autoridade do servidor (SPEC-009)."""

    TYPE: ClassVar[EventType] = EventType.SESSION_COMPLETED

    reason: SessionEndReason
    rep_count: int = 0

    def to_data(self) -> dict[str, Any]:
        return {"reason": self.reason.value, "rep_count": self.rep_count}

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        return cls(
            reason=_as_enum(SessionEndReason, _require(data, "reason"), "reason"),
            rep_count=_as_int(data.get("rep_count", 0), "rep_count"),
        )


#: Dataclass de payload por tipo — usada para decodificar `data` já com o envelope validado.
_PAYLOAD_FOR_TYPE: dict[EventType, Any] = {
    EventType.SESSION_CAPABILITY: SessionCapability,
    EventType.SESSION_STARTED: SessionStarted,
    EventType.POSE_FRAME: PoseFrame,
    EventType.EXERCISE_PHASE: ExercisePhase,
    EventType.REP_DETECTED: RepDetected,
    EventType.QUALITY_SIGNAL: QualitySignal,
    EventType.SCENE_WARNING: SceneWarning,
    EventType.FEEDBACK_ISSUED: FeedbackIssued,
    EventType.SESSION_COMPLETED: SessionCompleted,
}


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Envelope:
    """Envelope comum a todos os eventos. Validação leve acontece no `__post_init__`."""

    type: EventType
    session_id: str
    ts: int
    seq: int
    source: Source
    data: dict[str, Any] = field(default_factory=dict)
    v: int = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        self.type = _as_enum(EventType, self.type, "type")
        self.source = _as_enum(Source, self.source, "source")
        self.session_id = _as_str(self.session_id, "session_id")
        self.ts = _as_int(self.ts, "ts")
        self.seq = _as_int(self.seq, "seq")
        if self.v != PROTOCOL_VERSION:
            raise EventValidationError(f"versao de protocolo nao suportada: {self.v!r}")
        if self.ts <= 0:
            raise EventValidationError(f"ts deve ser epoch ms positivo, recebido {self.ts}")
        if self.seq < 0:
            raise EventValidationError(f"seq nao pode ser negativo, recebido {self.seq}")
        if not isinstance(self.data, dict):
            raise EventValidationError(f"data deve ser dict, recebido {type(self.data).__name__}")

    @property
    def stream(self) -> Stream:
        """Stream padrão de publicação deste evento."""
        return STREAM_FOR_TYPE[self.type]

    def to_dict(self) -> dict[str, Any]:
        return {
            "v": self.v,
            "type": self.type.value,
            "session_id": self.session_id,
            "ts": self.ts,
            "seq": self.seq,
            "source": self.source.value,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, raw: Any) -> Self:
        """Valida um mapa cru (vindo do WS ou do stream) e devolve o envelope."""
        if not isinstance(raw, dict):
            raise EventValidationError(f"envelope deve ser mapa, recebido {type(raw).__name__}")
        missing = {"type", "session_id", "ts", "seq", "source"} - raw.keys()
        if missing:
            raise EventValidationError(f"envelope incompleto, faltam: {sorted(missing)}")
        return cls(
            type=raw["type"],
            session_id=raw["session_id"],
            ts=raw["ts"],
            seq=raw["seq"],
            source=raw["source"],
            data=raw.get("data") or {},
            v=raw.get("v", PROTOCOL_VERSION),
        )

    def payload(self) -> EventPayload:
        """Decodifica `data` na dataclass do tipo — a validação do payload acontece aqui."""
        return _PAYLOAD_FOR_TYPE[self.type].from_data(self.data)


def make_envelope(
    payload: EventPayload,
    *,
    session_id: str,
    ts: int,
    seq: int,
    source: Source,
) -> Envelope:
    """Monta o envelope a partir de um payload — forma preferida de criar eventos."""
    return Envelope(
        type=payload.TYPE,
        session_id=session_id,
        ts=ts,
        seq=seq,
        source=source,
        data=payload.to_data(),
    )


# ---------------------------------------------------------------------------
# Serialização
# ---------------------------------------------------------------------------


def encode_envelope(envelope: Envelope) -> bytes:
    """Serializa em MessagePack (WS cliente ↔ gateway e dentro dos streams)."""
    return msgpack.packb(envelope.to_dict(), use_bin_type=True)


def decode_envelope(raw: bytes) -> Envelope:
    """Desserializa e valida; lança `EventValidationError` para tudo fora do contrato."""
    try:
        decoded = msgpack.unpackb(raw, raw=False, strict_map_key=False)
    except EventValidationError:
        raise
    except Exception as exc:
        raise EventValidationError(f"msgpack invalido: {exc}") from exc
    return Envelope.from_dict(decoded)


#: Campo único de cada entrada de stream: o envelope inteiro, empacotado. Um campo só evita
#: conversão campo-a-campo no hot path e mantém WS e stream com a MESMA serialização.
STREAM_PAYLOAD_FIELD = b"e"


def to_stream_fields(envelope: Envelope) -> dict[bytes, bytes]:
    """Campos do `XADD` para este envelope."""
    return {STREAM_PAYLOAD_FIELD: encode_envelope(envelope)}


def from_stream_fields(fields: dict[Any, Any]) -> Envelope:
    """Inverso de `to_stream_fields` (aceita chave em bytes ou str, conforme o cliente Redis)."""
    raw = fields.get(STREAM_PAYLOAD_FIELD, fields.get("e"))
    if raw is None:
        raise EventValidationError(f"entrada de stream sem o campo {STREAM_PAYLOAD_FIELD!r}")
    return decode_envelope(raw)
