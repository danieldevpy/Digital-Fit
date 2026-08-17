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
junto das tasks que os produzem: `scene.status` e `hold.progress` (Fase Evolução).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any, ClassVar, Protocol, Self, runtime_checkable

import msgpack

__all__ = [
    "ANALYSIS_INPUT_TYPES",
    "CLIENT_PUSH_TYPES",
    "CONSUMER_GROUPS",
    "FRAME_RAW_MAX_BYTES",
    "FRAME_RAW_MAX_SIDE",
    "LANDMARK_COUNT",
    "LANDMARK_NAMES",
    "PROTOCOL_VERSION",
    "STREAM_FOR_TYPE",
    "STREAM_MAXLEN",
    "STREAM_PAYLOAD_FIELD",
    "CameraView",
    "Code",
    "Envelope",
    "EventPayload",
    "EventType",
    "EventValidationError",
    "ExercisePhase",
    "FeedbackIssued",
    "FrameRaw",
    "Landmark",
    "Mode",
    "Phase",
    "PoseFrame",
    "QualitySignal",
    "RepDetected",
    "SceneWarning",
    "SessionCalibrated",
    "SessionCapability",
    "SessionCompleted",
    "SessionEndReason",
    "SessionReportReady",
    "SessionStarted",
    "SetMode",
    "Severity",
    "Source",
    "Stream",
    "decode_envelope",
    "encode_envelope",
    "from_stream_fields",
    "make_envelope",
    "parse_camera_view",
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


class SetMode(StrEnum):
    """Como a série termina: em `livre`, quando a janela acaba; em `contado`, quando a meta de
    repetições é atingida (SPEC-023, T-134).

    Eixo **independente** de `Mode`: aquele diz de onde os keypoints saem (navegador ou
    pose-worker), este diz o que decide o fim da série. `session.started` carrega os dois. O
    nome não é `mode` de propósito — colidiria com o `Mode` acima em toda camada que já lê
    `mode` hoje (contrato, `SessionResult.mode`, `to_report()`).
    """

    #: Máximo de repetições numa janela fixa — o que o produto já faz hoje, sem nome até aqui.
    LIVRE = "livre"
    #: Meta de repetições, sem pressa; termina em `target_reached` ou no teto (`completed`).
    CONTADO = "contado"


class CameraView(StrEnum):
    """De que lado a câmera está em relação a quem treina (T-111).

    Não é preferência de enquadramento: é **qual eixo do movimento vive no plano da imagem**, e
    por isso muda a régua com que o exercício é medido. Uma flexão de perfil e uma de frente são
    a mesma flexão e duas geometrias sem nada em comum — de lado o corpo atravessa a imagem na
    horizontal, de frente ele encolhe contra a lente.

    **Viaja no contrato porque é escolha de quem treina, não palpite do modelo.** Dá para
    adivinhar pela geometria (a flexão sabe fazer isso e acerta no corpus inteiro), mas uma
    adivinhação que oscile no meio da série troca a régua com a pessoa em movimento — e o custo
    de errar é a sessão inteira sair zerada, que é a pior coisa que este produto sabe fazer.
    Um toque na pré-configuração resolve, e o valor viaja daqui até a FSM.

    Exercício que não se importa com a vista simplesmente ignora o campo: ele é opcional, e
    ausência significa "ninguém disse", não "de frente".
    """

    #: Celular em pé, pessoa de frente para a lente.
    FRONTAL = "frontal"
    #: Celular deitado no chão, pessoa de perfil.
    PROFILE = "profile"


class EventType(StrEnum):
    """Tipos de evento da Fase 0, em dot.case."""

    SESSION_CAPABILITY = "session.capability"
    SESSION_STARTED = "session.started"
    FRAME_RAW = "frame.raw"  # só modo cloud; morre no pose-worker (SPEC-005)
    POSE_FRAME = "pose.frame"
    SESSION_CALIBRATED = "session.calibrated"  # baseline medida (SPEC-004)
    EXERCISE_PHASE = "exercise.phase"
    REP_DETECTED = "rep.detected"
    QUALITY_SIGNAL = "quality.signal"
    SCENE_WARNING = "scene.warning"
    FEEDBACK_ISSUED = "feedback.issued"
    SESSION_COMPLETED = "session.completed"
    SESSION_REPORT_READY = "session.report.ready"  # relatório persistido (SPEC-010)


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
    # Único tipo cuja rota padrão NÃO é `pose.frames`: imagem não entra no fluxo da análise.
    # O pose-worker (T-016) lê daqui e devolve `pose.frame` — é ali que o vídeo morre.
    EventType.FRAME_RAW: Stream.FRAMES_RAW,
    EventType.POSE_FRAME: Stream.POSE_FRAMES,
    EventType.SESSION_CALIBRATED: Stream.EVENTS_ANALYSIS,
    EventType.EXERCISE_PHASE: Stream.EVENTS_ANALYSIS,
    EventType.REP_DETECTED: Stream.EVENTS_ANALYSIS,
    EventType.QUALITY_SIGNAL: Stream.EVENTS_ANALYSIS,
    EventType.SCENE_WARNING: Stream.EVENTS_ANALYSIS,
    EventType.FEEDBACK_ISSUED: Stream.EVENTS_ANALYSIS,
    EventType.SESSION_COMPLETED: Stream.EVENTS_ANALYSIS,
    EventType.SESSION_REPORT_READY: Stream.EVENTS_ANALYSIS,
}

#: O que a **análise consome**. Quem quiser que o analysis-worker veja um evento publica em
#: `Stream.POSE_FRAMES` explicitamente — inclusive o pedido de encerramento
#: (`session.completed` emitido pela API por TTL ou abort). Publicar o encerramento na rota
#: padrão manda o evento para `events.analysis`, onde o worker **não** escuta: a sessão nunca
#: fecharia. `session.completed` é o único tipo que anda nos dois sentidos — da API é "encerre",
#: do worker é "encerrada, com este total de reps".
ANALYSIS_INPUT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.SESSION_CAPABILITY,
        EventType.SESSION_STARTED,
        EventType.POSE_FRAME,
        EventType.SESSION_COMPLETED,
    }
)

#: O que o gateway empurra de volta ao cliente pelo WS (SPEC-002 fase inicial). `pose.frame`
#: nunca volta, e `quality.signal` é insumo do feedback engine — o HUD só vê `feedback.issued`.
CLIENT_PUSH_TYPES: frozenset[EventType] = frozenset(
    {
        # O cliente precisa deste para encerrar o countdown na hora certa: é o servidor que
        # decide quando o exercicio comecou, e o anel de 30s tem de ancorar no MESMO instante.
        EventType.SESSION_CALIBRATED,
        EventType.EXERCISE_PHASE,
        EventType.REP_DETECTED,
        EventType.SCENE_WARNING,
        EventType.FEEDBACK_ISSUED,
        EventType.SESSION_COMPLETED,
        # Avisa que o relatório já está no banco. Sem ele o cliente teria de adivinhar quando
        # buscar — e o `session.completed` chega ANTES de o relatório existir.
        EventType.SESSION_REPORT_READY,
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
    """Fase do movimento na FSM (SPEC-007) — par NEUTRO, não vocabulário de um exercício.

    Era `closed`/`open`, que é polichinelo e mais nada. Um agachamento não fecha nem abre, e
    somar um par por exercício obrigaria todo consumidor (HUD, relatório, dataset) a virar um
    `switch` sobre `exercise` para saber o que a palavra significa — o oposto de um contrato.

    Toda contagem por repetição tem os mesmos dois extremos, então é isso que o contrato
    nomeia:

    - `REST` — a posição de partida/descanso, onde a repetição nasce e morre.
    - `PEAK`  — o extremo do movimento, onde a amplitude é máxima.

    O que cada uma *parece* é do exercício: polichinelo `REST`=fechado, `PEAK`=aberto;
    agachamento `REST`=em pé, `PEAK`=embaixo. Palavra de tela é do cliente, não daqui.

    Exercício por tempo (prancha) não usa este par — tem `hold.progress` (SPEC-007 Evolução).
    """

    REST = "rest"
    PEAK = "peak"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"


class Code(StrEnum):
    """Códigos de sinal/feedback da Fase 0 (SPEC-003 e SPEC-008).

    O código é o contrato; a mensagem em pt-BR vive no catálogo YAML do feedback engine
    (T-010) e pode mudar sem quebrar cliente nem dataset.
    """

    # Execução — SPEC-007, viram `quality.signal`.
    # Ficam num espaço só, sem prefixo por exercício: o código diz o que a PESSOA fez, e a
    # FSM que o emitiu já é conhecida pelo `exercise` da sessão. Prefixar geraria
    # `JUMPING_JACK_ARMS_TOO_LOW` e um dicionário de mensagens quase duplicado por exercício.
    ARMS_TOO_LOW = "ARMS_TOO_LOW"
    LEGS_TOO_CLOSED = "LEGS_TOO_CLOSED"
    SQUAT_TOO_SHALLOW = "SQUAT_TOO_SHALLOW"
    PUSHUP_TOO_SHALLOW = "PUSHUP_TOO_SHALLOW"
    #: Quadril fora da linha ombro→tornozelo na flexão. Dois códigos e não um com sinal: o que
    #: a pessoa tem de fazer é oposto ("contraia o abdômen" × "abaixe o quadril"), e um código
    #: só obrigaria o texto a falar dos dois casos de uma vez.
    HIPS_SAGGING = "HIPS_SAGGING"
    HIPS_PIKED = "HIPS_PIKED"
    CRUNCH_TOO_SHALLOW = "CRUNCH_TOO_SHALLOW"
    #: Abdominal no impulso. É o erro que a literatura de execução cita como o mais comum do
    #: crunch — subir rápido demais recruta o flexor de quadril no lugar do abdômen.
    CRUNCH_TOO_FAST = "CRUNCH_TOO_FAST"
    # Cena — SPEC-003, viram `scene.warning`
    OUT_OF_FRAME = "OUT_OF_FRAME"
    TOO_FAR = "TOO_FAR"
    TOO_CLOSE = "TOO_CLOSE"


class SessionEndReason(StrEnum):
    """Por que a sessão terminou (SPEC-009)."""

    COMPLETED = "completed"  # os 30s correram até o fim (ou, no modo contado, o teto estourou)
    TIMEOUT = "timeout"  # TTL da sessão expirou
    ABORTED = "aborted"  # usuário/cliente encerrou antes
    NO_DATA = "no_data"  # nenhum frame por 10s
    #: Modo contado: a meta de repetições foi atingida (SPEC-023, T-134). Nunca produzido antes
    #: do deploy desta task — replay de stream gravado antes dela jamais o contém (ressalva do
    #: `_as_enum` estrito, ver módulo `SessionStarted`/PROTOCOL_VERSION nas notas da spec).
    TARGET_REACHED = "target_reached"


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


#: Preparação entre "corpo medido" e "vale agora" (SPEC-004 / T-049).
#:
#: 3 s é o default porque é o tempo do "3, 2, 1" que a SPEC-004 já pedia na Fase Inicial e que
#: a T-019 acabou colapsando: hoje a contagem começa no mesmo frame em que a medida fica
#: pronta, sem aviso nenhum para quem está do outro lado.
DEFAULT_COUNTDOWN_S = 3

#: Teto de 10 s. Não é técnico — é para o campo não virar uma forma de segurar vaga de sessão
#: (SPEC-009) sem treinar: o TTL do ticket é 45 s, e uma preparação longa comeria o slot.
MAX_COUNTDOWN_S = 10


def clamp_countdown_s(valor: Any) -> int:
    """Normaliza a preferência: inteiro entre 0 e `MAX_COUNTDOWN_S`.

    Aceita lixo em silêncio de propósito. É preferência de conforto, não parâmetro de
    medição: recusar a sessão inteira porque alguém mandou `"três"` seria trocar um treino
    por um erro de digitação.
    """
    try:
        segundos = int(valor)
    except (TypeError, ValueError):
        return DEFAULT_COUNTDOWN_S
    return max(0, min(MAX_COUNTDOWN_S, segundos))


def parse_camera_view(valor: Any) -> CameraView | None:
    """Normaliza a vista: valor conhecido vira enum, qualquer outra coisa vira `None`.

    Tolerante de propósito — ver o comentário em `SessionStarted.from_data`.
    """
    if isinstance(valor, CameraView):
        return valor
    if not isinstance(valor, str):
        return None
    try:
        return CameraView(valor.strip().lower())
    except ValueError:
        return None


def _config_version(valor: Any) -> int:
    """Normaliza o carimbo de configuração: inteiro não negativo, `0` para qualquer outra coisa."""
    try:
        versao = int(valor)
    except (TypeError, ValueError):
        return 0
    return max(0, versao)


def _stamp_int(valor: Any) -> int:
    """Normaliza um carimbo inteiro (`target_reps`/`set_index`/`set_total`): não-negativo,
    `0` para qualquer coisa torta — mesmo tratamento de `_config_version` (T-134). São
    carimbo, não parâmetro medido: um valor errado não pode derrubar `session.started`."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 0
    return max(0, numero)


def _as_set_mode(valor: Any) -> SetMode:
    """Modo da série: valor ausente ou desconhecido cai em `livre` — o comportamento de toda
    sessão antes desta task (SPEC-023, critério de aceite 9)."""
    if isinstance(valor, SetMode):
        return valor
    try:
        return SetMode(valor)
    except (ValueError, TypeError):
        return SetMode.LIVRE


@dataclass(frozen=True, slots=True)
class SessionStarted:
    """Sessão admitida pela API; abre o estado no analysis-worker (SPEC-009)."""

    TYPE: ClassVar[EventType] = EventType.SESSION_STARTED

    exercise: str
    mode: Mode
    duration_s: int
    #: Segundos entre o corpo estar medido e a contagem valer (SPEC-004 / T-049). `0` desliga.
    #: Vem da preferência de quem treina e viaja aqui porque quem SEGURA a contagem é o
    #: analysis-worker: fosse só animação no cliente, uma repetição feita durante o "3, 2, 1"
    #: entraria no total — que é exatamente o que o recurso existe para evitar.
    countdown_s: int = DEFAULT_COUNTDOWN_S
    #: De que lado a câmera está, **escolhido por quem treina** na pré-configuração (T-111).
    #: `None` = ninguém disse, e aí cada exercício decide (a flexão cai na detecção geométrica).
    #: Viaja aqui pelo mesmo motivo do `countdown_s`: quem consome é o analysis-worker, e uma
    #: escolha que ficasse só no cliente seria enfeite — a FSM continuaria medindo pela régua
    #: errada.
    view: CameraView | None = None
    #: Versão da configuração (`SiteConfig.version`, SPEC-018) sob a qual esta sessão foi
    #: admitida. Carimbo, não parâmetro: nada na análise lê este número — ele viaja porque o
    #: relatório precisa poder dizer sob qual configuração aquela contagem nasceu, e porque um
    #: worker jamais consulta o banco para descobrir (P1). `0` = configuração não veio do banco
    #: (piso do código, P2) ou evento anterior à T-075.
    config_version: int = 0
    #: Como a série termina — `livre` (janela) ou `contado` (meta), SPEC-023/T-134. Resolvido
    #: pela API na admissão (T-136); aqui é só o carimbo que o analysis-worker lê para saber
    #: se aplica o encerramento por meta. Default `livre` reproduz o comportamento de toda
    #: sessão anterior a esta task.
    set_mode: SetMode = SetMode.LIVRE
    #: Meta de repetições no modo `contado`; `0` no `livre` (SPEC-023 §2).
    target_reps: int = 0
    #: Carimbo de série dentro do treino — `0` = sessão avulsa, todo o passado (SPEC-023 §3).
    set_index: int = 0
    #: De quantas séries o treino é feito; `0` junto com `set_index=0` (SPEC-023 §3).
    set_total: int = 0

    def to_data(self) -> dict[str, Any]:
        return {
            "exercise": self.exercise,
            "mode": self.mode.value,
            "duration_s": self.duration_s,
            "countdown_s": self.countdown_s,
            # `None` viaja como ausência e não como `""`: o campo é opcional dos dois lados, e
            # string vazia obrigaria todo consumidor a saber que ela significa "não sei".
            **({"view": self.view.value} if self.view is not None else {}),
            "config_version": self.config_version,
            "set_mode": self.set_mode.value,
            "target_reps": self.target_reps,
            "set_index": self.set_index,
            "set_total": self.set_total,
        }

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        return cls(
            exercise=_as_str(_require(data, "exercise"), "exercise"),
            mode=_as_enum(Mode, _require(data, "mode"), "mode"),
            duration_s=_as_int(_require(data, "duration_s"), "duration_s"),
            # Ausente = sessão criada antes da T-049 (ou por cliente velho): cai no default,
            # em vez de quebrar a admissão por um campo que não existia.
            countdown_s=clamp_countdown_s(data.get("countdown_s", DEFAULT_COUNTDOWN_S)),
            # Vista desconhecida NÃO derruba a sessão: cai em `None`, que é o mesmo estado de
            # quem não disse nada, e o exercício segue pelo caminho que já tinha. Um
            # `_as_enum` estrito aqui faria um cliente novo com um valor que este worker ainda
            # não conhece perder o treino inteiro — preço alto demais para um campo cuja
            # ausência já é suportada por construção.
            view=parse_camera_view(data.get("view")),
            # Mesma tolerância, mesmo motivo: sessão publicada antes desta task (ou por um
            # replay do stream gravado antes dela) continua abrindo, com a versão desconhecida
            # dita como `0`. Um `_require` aqui recusaria justamente os eventos que a SPEC-010
            # promete poder reprocessar — e um `_as_int` estrito faria um carimbo torto
            # derrubar o `session.started` inteiro, levando junto o exercício e o modo, que é
            # o que o relatório de fato precisa. Metadado não pode custar o relatório.
            config_version=_config_version(data.get("config_version", 0)),
            # Os quatro campos da T-134 seguem a mesma regra: ausentes (evento anterior à
            # SPEC-023, ou replay de stream gravado antes dela) ou tortos caem nos defaults que
            # reproduzem o modo livre de sempre — nunca derrubam o `session.started`.
            set_mode=_as_set_mode(data.get("set_mode", SetMode.LIVRE.value)),
            target_reps=_stamp_int(data.get("target_reps", 0)),
            set_index=_stamp_int(data.get("set_index", 0)),
            set_total=_stamp_int(data.get("set_total", 0)),
        )


#: Maior lado do JPEG no modo cloud (SPEC-005, Fase Inicial: "maior lado 320px").
FRAME_RAW_MAX_SIDE = 320

#: Teto por frame. Um JPEG 320px com qualidade ~60 dá 10–25 KB; 256 KB é folga larga e ainda
#: assim impede que um cliente entupa o barramento — este é o ÚNICO caminho por onde o
#: navegador empurra binário grande, então é o único que precisa de teto.
FRAME_RAW_MAX_BYTES = 256 * 1024

#: Assinatura de arquivo JPEG (SOI + marcador). Barra PNG/WebP/lixo antes de chegar no
#: decoder do pose-worker, onde o erro sairia como stack trace do MediaPipe.
_JPEG_MAGIC = b"\xff\xd8\xff"


@dataclass(frozen=True, slots=True)
class FrameRaw:
    """Frame JPEG reduzido, enviado pelo cliente **apenas** no modo cloud (SPEC-005).

    É a única vez em que imagem trafega no sistema, e ela morre no `pose-worker`: o dado do
    Digital Fit são keypoints, vídeo é insumo descartável (`context/project.md`, decisão 1).
    Por isso este evento não é persistido, não vai para o dataset e não chega ao cliente.

    **`source` deste evento é `cloud`**, embora quem o produza seja o navegador. `source`
    responde "por qual caminho de extração este dado passa", não "qual máquina o gerou" — é
    assim que `pose.frame` já usa o campo (edge = extraído no browser, cloud = extraído no
    pose-worker). Marcar `edge` aqui faria um `frame.raw` parecer do caminho que, por
    definição, nunca produz `frame.raw`.
    """

    TYPE: ClassVar[EventType] = EventType.FRAME_RAW

    jpeg: bytes
    width: int
    height: int

    def to_data(self) -> dict[str, Any]:
        return {"jpeg": self.jpeg, "width": self.width, "height": self.height}

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        jpeg = _require(data, "jpeg")
        if not isinstance(jpeg, bytes | bytearray):
            raise EventValidationError(f"jpeg deve ser binario, recebido {type(jpeg).__name__}")
        jpeg = bytes(jpeg)
        if not jpeg.startswith(_JPEG_MAGIC):
            raise EventValidationError("jpeg nao comeca com a assinatura JPEG")
        if len(jpeg) > FRAME_RAW_MAX_BYTES:
            raise EventValidationError(
                f"jpeg tem {len(jpeg)} bytes, acima do teto de {FRAME_RAW_MAX_BYTES}"
            )

        width = _as_int(_require(data, "width"), "width")
        height = _as_int(_require(data, "height"), "height")
        if width <= 0 or height <= 0:
            raise EventValidationError(f"dimensoes invalidas: {width}x{height}")
        if max(width, height) > FRAME_RAW_MAX_SIDE:
            raise EventValidationError(
                f"maior lado {max(width, height)}px acima de {FRAME_RAW_MAX_SIDE}px "
                "— o cliente deve reduzir antes de enviar (SPEC-005)"
            )
        return cls(jpeg=jpeg, width=width, height=height)


@dataclass(frozen=True, slots=True)
class PoseFrame:
    """33 landmarks `[x, y, z, visibility]` normalizados 0–1 no frame (SPEC-005).

    `norm` é preenchido pela normalização (SPEC-006) **no mesmo evento** — keypoints
    canônicos não criam tipo novo. `degraded` marca frame com âncoras pouco visíveis: a FSM
    congela em vez de contar (SPEC-006/007).

    **`width`/`height` são as dimensões do frame de onde estes landmarks saíram** (T-110), e
    existem porque `x` é dividido pela largura e `y` pela altura: sem elas, o espaço 0–1 é
    anisotrópico e uma distância horizontal não é comparável a uma vertical. Medido: a mesma
    largura de ombros lê 0,348 torsos em paisagem (854×480) e 1,168 em retrato (576×1024).
    Quem corrige é a normalização (SPEC-006); aqui só trafegam.

    **São por frame, não por sessão, de propósito**: o celular gira no meio do treino, e o
    aspecto muda com ele. Carimbar a dimensão na abertura da sessão seria assumir que ninguém
    vira o aparelho.

    Ausentes ⇒ a normalização trata o espaço como isotrópico, que é exatamente o
    comportamento anterior a esta task. É o que mantém fixture antiga e cliente antigo
    lendo o mesmo número de sempre — por isso o campo é aditivo e o `PROTOCOL_VERSION` não sobe.
    """

    TYPE: ClassVar[EventType] = EventType.POSE_FRAME

    landmarks: list[list[float]]
    norm: dict[str, Any] | None = None
    degraded: bool = False
    width: int | None = None
    height: int | None = None

    @property
    def aspect(self) -> float | None:
        """Largura ÷ altura, ou `None` quando o produtor não declarou as dimensões."""
        if self.width is None or self.height is None:
            return None
        return self.width / self.height

    def to_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {"landmarks": self.landmarks}
        if self.degraded:
            data["degraded"] = True
        if self.norm is not None:
            data["norm"] = self.norm
        # Só viajam quando existem: frame sem dimensão declarada continua com o payload de
        # antes, byte a byte.
        if self.width is not None and self.height is not None:
            data["width"] = self.width
            data["height"] = self.height
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
        # As duas dimensões andam juntas: uma sozinha não define aspecto nenhum, e aceitá-la
        # em silêncio produziria um frame que se diz medido sem estar.
        bruto_w, bruto_h = data.get("width"), data.get("height")
        if (bruto_w is None) != (bruto_h is None):
            raise EventValidationError(
                "width e height devem vir juntos ou ausentes — sozinhos nao definem aspecto"
            )
        width = height = None
        if bruto_w is not None:
            width = _as_int(bruto_w, "width")
            height = _as_int(bruto_h, "height")
            if width <= 0 or height <= 0:
                raise EventValidationError(f"dimensoes invalidas: {width}x{height}")

        return cls(
            landmarks=[[float(value) for value in point] for point in landmarks],
            norm=data.get("norm"),
            degraded=bool(data.get("degraded", False)),
            width=width,
            height=height,
        )


@dataclass(frozen=True, slots=True)
class SessionCalibrated:
    """Baseline medida no countdown — a partir daqui o exercício vale (SPEC-004).

    Marca a fronteira entre preparação e exercício: é neste instante que o timer autoritativo
    dos 30 s começa a contar (SPEC-009). Antes disso a pessoa está se posicionando, e cobrar
    esse tempo do treino dela seria errado.

    As medidas seguem em duas unidades — ver `Baseline` em `workers/shared/normalize.py`.
    """

    TYPE: ClassVar[EventType] = EventType.SESSION_CALIBRATED

    torso: float
    shoulder_width: float
    shoulder_span: float
    wrist_rest_y: float
    #: Frames que entraram na mediana. Baixo demais é sinal de calibração no limite.
    samples: int = 0
    #: Quanto falta até a contagem valer (T-049). `0` = vale a partir deste evento, que é o
    #: comportamento de antes da task.
    #:
    #: O evento passou a significar "corpo MEDIDO", não mais "contagem começou" — quem lê
    #: precisa somar isto para saber quando o relógio dos 30 s anda. Não há um segundo evento
    #: para o "JÁ": o cliente já ancorava o anel no relógio dele ao receber este aqui, então um
    #: `session.counting` custaria uma ida ao servidor sem comprar autoridade nenhuma. Quem
    #: segura a contagem de verdade é o worker, que não alimenta a FSM antes do prazo.
    countdown_ms: int = 0

    def to_data(self) -> dict[str, Any]:
        return {
            "torso": self.torso,
            "shoulder_width": self.shoulder_width,
            "shoulder_span": self.shoulder_span,
            "wrist_rest_y": self.wrist_rest_y,
            "samples": self.samples,
            "countdown_ms": self.countdown_ms,
        }

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        return cls(
            torso=float(_require(data, "torso")),
            shoulder_width=float(_require(data, "shoulder_width")),
            shoulder_span=float(_require(data, "shoulder_span")),
            wrist_rest_y=float(_require(data, "wrist_rest_y")),
            samples=_as_int(data.get("samples", 0), "samples"),
            countdown_ms=_as_int(data.get("countdown_ms", 0), "countdown_ms"),
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


@dataclass(frozen=True, slots=True)
class SessionReportReady:
    """O relatório da sessão está persistido e pode ser buscado (SPEC-010).

    **Payload vazio de propósito.** A tentação é mandar reps e cadência junto, já que o
    builder acabou de calculá-los — e aí passariam a existir dois lugares dizendo quantas
    repetições a sessão teve: este evento e o `GET /api/sessions/{id}/report`. Quando os dois
    divergirem (replay, reprocessamento, mudança de fórmula), ninguém saberá qual está certo.

    O evento é um sino, não um relatório: diz "agora existe", e o `session_id` do envelope já
    diz de quem. O conteúdo tem uma fonte só, o banco.
    """

    TYPE: ClassVar[EventType] = EventType.SESSION_REPORT_READY

    def to_data(self) -> dict[str, Any]:
        return {}

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        del data
        return cls()


#: Dataclass de payload por tipo — usada para decodificar `data` já com o envelope validado.
_PAYLOAD_FOR_TYPE: dict[EventType, Any] = {
    EventType.SESSION_CAPABILITY: SessionCapability,
    EventType.SESSION_STARTED: SessionStarted,
    EventType.FRAME_RAW: FrameRaw,
    EventType.POSE_FRAME: PoseFrame,
    EventType.SESSION_CALIBRATED: SessionCalibrated,
    EventType.EXERCISE_PHASE: ExercisePhase,
    EventType.REP_DETECTED: RepDetected,
    EventType.QUALITY_SIGNAL: QualitySignal,
    EventType.SCENE_WARNING: SceneWarning,
    EventType.FEEDBACK_ISSUED: FeedbackIssued,
    EventType.SESSION_COMPLETED: SessionCompleted,
    EventType.SESSION_REPORT_READY: SessionReportReady,
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
