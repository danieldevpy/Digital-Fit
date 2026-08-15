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

## Dois relógios, e por que só um conta o tempo (T-078)

"Todos os instantes vêm do frame" era **falso para um evento**, e o parágrafo acima escondia a
exceção: o `session.started` é publicado pela **API** (`api/sessions.py`), com o relógio do
servidor. Ele entrava no mesmo `last_ts` dos eventos derivados de frame, e a duração saía de uma
subtração entre relógios diferentes — errada em silêncio quando o celular estava adiantado, e
capaz de estourar o `PositiveIntegerField` (2³¹ ms ≈ 24,8 dias) e **matar o processo** com
`DataError: integer out of range`. Descoberta `[A/T-077]`, vista de verdade.

O `source` do envelope **não** separa os dois: `session.started` (API) e `session.completed`
(analysis-worker) são ambos `Source.SYSTEM`. O que os separa é quem publica — e a lista de quem
publica com o relógio do servidor tem um item só, nomeado em `_EVENTOS_DO_RELOGIO_DO_SERVIDOR`.
Há teste que quebra se um segundo entrar no stream sem passar por lá.
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

__all__ = [
    "CADENCE_WINDOW_MS",
    "FOLGA_DE_DURACAO_MS",
    "TETO_DE_DURACAO_MS",
    "ReportAccumulator",
    "SessionReport",
]

logger = logging.getLogger("report-builder")

#: Janela do gráfico de cadência (SPEC-010: "cadência média e por janela de 5s").
CADENCE_WINDOW_MS = 5_000

#: Teto de sessões acompanhadas ao mesmo tempo. Existe para o builder não virar um vazamento
#: de memória quando uma sessão nunca fecha: sem isso, cada sessão órfã ficaria para sempre.
MAX_SESSIONS = 512

#: Eventos que carregam o relógio do **servidor**, e por isso não entram na linha do tempo que
#: mede a duração (T-078).
#:
#: Um item, e é o `session.started` da API. `session.completed` NÃO está aqui de propósito: ele
#: sai do analysis-worker com o `ts` do último frame — só cai no relógio do servidor quando não
#: houve frame nenhum, e nesse caso a calibração também não aconteceu e a duração já é zero.
_EVENTOS_DO_RELOGIO_DO_SERVIDOR = frozenset({EventType.SESSION_STARTED})

#: Folga sobre a duração admitida, para o teto de plausibilidade não recusar sessão honesta.
#:
#: O fim é decidido pelo timer autoritativo do analysis-worker (SPEC-009), mas o `ts` do último
#: frame pode chegar um pouco depois do prazo, e o countdown de preparação entra na conta em
#: algumas rotas. Um minuto cobre tudo isso com sobra e continua a três ordens de grandeza do
#: que um relógio torto produz.
FOLGA_DE_DURACAO_MS = 60_000

#: Teto absoluto, para quando a duração admitida não é conhecida — sessão cujo `session.started`
#: o builder não viu (subiu no meio), ou evento anterior à T-075.
#:
#: Seis horas: qualquer sessão real deste produto dura 30 s, e a maior que a validação do `Plan`
#: aceita são 600 s. O número não precisa ser justo; precisa ser MUITO menor que os 24,8 dias em
#: que o `PositiveIntegerField` estoura, e MUITO maior que qualquer treino.
TETO_DE_DURACAO_MS = 6 * 60 * 60 * 1_000


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
    #: Versão da configuração sob a qual a sessão foi admitida (SPEC-018, T-075). Vem carimbada
    #: no `session.started` — o builder nunca pergunta ao banco, senão o mesmo replay daria
    #: relatórios diferentes em momentos diferentes, e daria em silêncio (SPEC-010).
    config_version: int = 0

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
            "config_version": self.config_version,
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
    #: Último instante visto **na linha do tempo do cliente** (frames). O `session.started` da
    #: API não entra aqui: ele é do relógio do servidor, e misturar os dois é a T-078.
    last_ts: int = 0
    #: Duração admitida pela API (`session.started`), em segundos. `0` = não sei — e aí o teto
    #: de plausibilidade cai no absoluto em vez de num número inventado para esta sessão.
    duration_s: int = 0
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
    #: `0` até o `session.started` chegar — e continua `0` na sessão cujo início o builder não
    #: viu (subiu no meio). Igual a `exercise` e `mode`: o que falta é dito, não inventado.
    config_version: int = 0


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
        # A linha do tempo que mede a duração só avança com evento do relógio do cliente (T-078).
        if envelope.type not in _EVENTOS_DO_RELOGIO_DO_SERVIDOR:
            buffer.last_ts = max(buffer.last_ts, envelope.ts)
        if now_ms is not None:
            buffer.last_seen_ms = now_ms

        match envelope.type:
            case EventType.SESSION_STARTED:
                dados = SessionStarted.from_data(envelope.data)
                buffer.exercise = dados.exercise
                buffer.mode = dados.mode.value
                buffer.config_version = dados.config_version
                buffer.duration_s = dados.duration_s
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
        duracao = _duracao(
            started_ms=buffer.started_ms,
            fim_ms=fim,
            duration_s=buffer.duration_s,
            session_id=envelope.session_id,
        )
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
            config_version=buffer.config_version,
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


def _duracao(*, started_ms: int | None, fim_ms: int, duration_s: int, session_id: str) -> int:
    """Duração efetiva, ou `0` quando o relógio não merece crédito (T-078).

    Duas guardas, e a segunda é a que impede um `DataError` de matar o processo:

    1. Sem calibração não houve exercício — a sessão terminou em preparação, e zero é o número
       certo, não um contorno.
    2. Acima do teto de plausibilidade, o relógio do cliente andou no meio da sessão (troca de
       fuso, sincronização de NTP, hora ajustada à mão). Aí **zero, e não o teto**: gravar o
       teto seria inventar um tempo que ninguém treinou, e a cadência derivada dele mentiria com
       cara de número medido. Zero já significa "não sei" neste campo, e o log diz o resto.

    O teto sai da própria sessão quando ela o declarou (`duration_s` do `session.started`, que a
    API resolve pelo plano), e do absoluto quando não — nunca de um palpite sobre o exercício.
    """
    if started_ms is None:
        return 0

    duracao = max(0, fim_ms - started_ms)
    teto = duration_s * 1_000 + FOLGA_DE_DURACAO_MS if duration_s > 0 else TETO_DE_DURACAO_MS
    if duracao > teto:
        logger.warning(
            "duracao implausivel em %s: %s ms (teto %s ms, calibracao %s, fim %s) — "
            "relogio do cliente andou no meio da sessao; gravando 0",
            session_id,
            duracao,
            teto,
            started_ms,
            fim_ms,
        )
        return 0
    return duracao


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
