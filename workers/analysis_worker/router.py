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

from workers.analysis_worker.calibration import Calibrator
from workers.analysis_worker.exercises import ExerciseAnalyzer, feed, get_analyzer
from workers.analysis_worker.feedback import FeedbackEngine
from workers.analysis_worker.scene import SceneValidator
from workers.shared.events import (
    CameraView,
    Envelope,
    EventType,
    EventValidationError,
    Mode,
    PoseFrame,
    SessionCalibrated,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    SetMode,
    Source,
    make_envelope,
)
from workers.shared.normalize import Baseline, Normalizer, RawFrame

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

#: Por quanto tempo o worker lembra que uma sessão JÁ ACABOU (T-077).
#:
#: O cliente não para de mandar frames no instante em que o servidor encerra: o `session.completed`
#: ainda vai atravessar Redis, gateway e WebSocket, e enquanto isso a câmera segue capturando. Sem
#: esta memória, o primeiro frame atrasado abre uma sessão NOVA com o mesmo `session_id` — que
#: conta as repetições que a pessoa fez depois do fim, morre de `no_data` 10 s depois e emite um
#: segundo `session.completed`. Como o report-builder faz upsert por `session_id` (SPEC-010), esse
#: segundo relatório SOBRESCREVE o bom. Foi exatamente isso, medido em produção: 26 reps viraram 4.
#:
#: 120 s é folga sobre o TTL do ticket (45 s): passado ele nem WebSocket novo se abre para o id.
ENDED_MEMORY_MS = 120_000


@dataclass(slots=True)
class SessionState:
    """Estado de uma sessão ativa no worker."""

    session_id: str
    exercise: str = "jumping_jack"
    mode: Mode = Mode.EDGE
    duration_s: int = DEFAULT_DURATION_S
    #: Vista escolhida por quem treina (T-111), vinda do `session.started`. `None` = ninguém
    #: disse, e o exercício decide sozinho — que é o caminho de todo cliente anterior a esta
    #: task e de toda sessão aberta por `pose.frame` sem admissão.
    view: CameraView | None = None
    analyzer: ExerciseAnalyzer = field(default=None)  # type: ignore[assignment]
    normalizer: Normalizer = field(default_factory=Normalizer)
    scene: SceneValidator = field(default_factory=SceneValidator)
    feedback: FeedbackEngine = field(default_factory=FeedbackEngine)
    #: Mede o corpo antes de o exercício valer (SPEC-004). Enquanto não terminar, os frames
    #: alimentam a calibração e a validação de cena — mas não a contagem.
    calibrator: Calibrator = field(default_factory=Calibrator)
    baseline: Baseline | None = None
    #: Preparação pedida por quem treina (T-049), vinda do `session.started`. `0` = contagem
    #: vale assim que o corpo é medido, que era o comportamento antes da task.
    #:
    #: O default aqui é 0, e não o `DEFAULT_COUNTDOWN_S` do produto, porque este default só é
    #: usado no caminho em que um `pose.frame` abre a sessão SEM admissão. Aí não há cliente
    #: coordenando nada: ninguém está vendo um "3, 2, 1", e engolir 3 s de frames seria perder
    #: dado para preparar uma pessoa que não existe. A preparação é combinada entre cliente e
    #: servidor — sem o combinado, não há preparação.
    countdown_s: int = 0
    #: Como esta série termina (SPEC-023, T-135), vindo do `session.started`. `livre` = a
    #: janela fixa de sempre; é o default de toda sessão anterior a esta task.
    set_mode: SetMode = SetMode.LIVRE
    #: Meta de repetições do modo contado. `0` no modo livre.
    target_reps: int = 0
    #: Instante (relógio do servidor) a partir do qual a FSM vê os frames. Fica no FUTURO
    #: durante o "3, 2, 1".
    counting_from_wall_ms: int | None = None
    #: Instante (relógio do servidor) em que o exercício passou a valer. É daqui que os 30 s
    #: correm, e não do primeiro frame: a preparação é preparação, não treino.
    exercise_started_wall_ms: int | None = None
    #: O mesmo instante, medido no relógio DOS FRAMES (`ts` do cliente). É deste que o teto do
    #: modo contado corre — ver `expiry_reason`.
    exercise_started_ts: int | None = None
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
            self.analyzer = get_analyzer(self.exercise, view=self.view)
        # A cena passa a saber em que postura o corpo vai ficar (T-106): validar uma flexão com
        # a régua de quem está em pé pediria "aproxime-se" a sessão inteira. Os campos são
        # sobrescritos e não recriados para não jogar fora um validador com debounce próprio,
        # que os testes injetam.
        hints = self.analyzer.scene_hints()
        self.scene.posture = hints.posture
        self.scene.body_range = hints.body_height_range
        self.scene.anchors = hints.frame_anchors

    @property
    def counted(self) -> bool:
        """Esta série termina por meta (SPEC-023 §1)?

        Exige as duas coisas. Modo contado com `target_reps = 0` é contrato malformado (a
        §2 pede `> 0`), e a resposta certa é degradar para o comportamento de sempre: um
        `reps >= 0` encerraria a série no primeiro frame, com zero repetição e cara de bug.
        """
        return self.set_mode is SetMode.CONTADO and self.target_reps > 0

    def counting(self, now_wall_ms: int) -> bool:
        """A FSM já pode ver os frames? Falso enquanto mede o corpo e durante a preparação."""
        return self.counting_from_wall_ms is not None and now_wall_ms >= self.counting_from_wall_ms

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

        Três prazos, todos em relógio do servidor:

        1. os 30 s de exercício correram desde a CALIBRAÇÃO ⇒ `completed` (é **este** o timer
           autoritativo da SPEC-009; o do HUD é cosmético). Desde a T-019 a âncora é o fim da
           calibração, não o primeiro frame — o countdown é preparação, e cobrá-lo do treino
           encurtaria a sessão de quem demora a se posicionar;
        2. nenhum frame por 10 s ⇒ `no_data` (critério 4 da SPEC-009);
        3. teto absoluto de vida ⇒ `timeout`, para o caso de a calibração nunca fechar.

        No **modo contado** o prazo 1 deixa de ser a janela e vira o **teto** da série, e ele
        corre no relógio dos FRAMES, não no de parede (SPEC-023, notas técnicas). A troca de
        relógio é a diferença entre os dois modos: a janela do livre é competitiva de
        propósito — 30 s de parede iguais para todo mundo —, enquanto a série contada é o
        oposto ("um aplicativo que não te apressa"), e cortá-la porque a rede engasgou seria
        cobrar de quem treina uma latência que não é dela. Com o `ts` o corte cai onde a
        pessoa realmente estava, e replay do stream reproduz o mesmo fim (critério 10).

        Isso não abre sessão pendurada: sem frame chegando o `ts` para de andar, e aí quem
        fecha é o prazo 2 (`no_data`, 10 s); com frames de `ts` congelado, o prazo 3.
        """
        if self.counted:
            if (
                self.exercise_started_ts is not None
                and self.last_ts is not None
                and self.last_ts - self.exercise_started_ts >= self.duration_s * 1000
            ):
                return SessionEndReason.COMPLETED
        elif (
            self.exercise_started_wall_ms is not None
            and now_wall_ms - self.exercise_started_wall_ms >= self.duration_s * 1000
        ):
            return SessionEndReason.COMPLETED
        referencia = (
            self.last_frame_wall_ms if self.last_frame_wall_ms is not None else self.opened_wall_ms
        )
        if referencia is not None and now_wall_ms - referencia >= NO_DATA_TIMEOUT_MS:
            return SessionEndReason.NO_DATA
        # Teto absoluto do tempo de vida. Antes da T-019 este caminho era inalcançável (uma das
        # duas regras acima sempre vencia); com a calibração ele passou a ser necessário: uma
        # pessoa no quadro mas sempre em frames degradados manteria a sessão calibrando para
        # sempre — frames continuam chegando, então `no_data` nunca dispararia.
        if (
            self.opened_wall_ms is not None
            and now_wall_ms - self.opened_wall_ms >= self.duration_s * 1000 + TTL_MARGIN_MS
        ):
            return SessionEndReason.TIMEOUT
        return None


@dataclass(slots=True)
class _Encerrada:
    """Lápide de uma sessão que já acabou (T-077). Ver `ENDED_MEMORY_MS`."""

    at_wall_ms: int
    #: Frames atrasados descartados. Diagnóstico: um número alto aqui diz que o cliente
    #: continua transmitindo muito depois do fim.
    ignored: int = 0


class AnalysisRouter:
    """Traduz eventos de entrada em eventos de análise, sem I/O."""

    __slots__ = ("_now", "ended", "sessions", "slots")

    def __init__(self, *, slots=None) -> None:
        self.sessions: dict[str, SessionState] = {}
        #: Sessões encerradas há pouco. Existe para que frame atrasado não ressuscite sessão —
        #: a memória é o que separa "chegou antes do `session.started`" (abre) de "chegou depois
        #: do fim" (descarta), dois casos que o `session_id` sozinho não distingue.
        self.ended: dict[str, _Encerrada] = {}
        self._now = 0
        #: Semáforo de vagas cloud (SPEC-009). `None` nos testes e em qualquer contexto sem
        #: Redis — a análise nunca depende dele para funcionar.
        self.slots = slots

    def _marcar_encerrada(self, session_id: str) -> None:
        """Anota o fim. Chamado em TODO caminho que remove a sessão — se um deles esquecer,
        aquele caminho volta a ressuscitar sessão pelo frame seguinte."""
        self.ended[session_id] = _Encerrada(at_wall_ms=self._now)

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
                countdown_s=dados.countdown_s,
                view=dados.view,
                set_mode=dados.set_mode,
                target_reps=dados.target_reps,
                opened_wall_ms=self._now,
            )
        except ValueError as exc:
            # Exercício desconhecido: a sessão não abre, mas o worker segue vivo.
            logger.error("sessao %s recusada: %s", envelope.session_id, exc)
            return []
        self.sessions[envelope.session_id] = estado
        logger.info(
            "sessao %s aberta (%s, %s, %s, %ss%s)",
            estado.session_id,
            estado.exercise,
            estado.mode.value,
            estado.set_mode.value,
            estado.duration_s,
            f", meta {estado.target_reps}" if estado.counted else "",
        )
        return []

    def _on_pose_frame(self, envelope: Envelope) -> list[Envelope]:
        estado = self.sessions.get(envelope.session_id)
        if estado is None:
            encerrada = self.ended.get(envelope.session_id)
            if encerrada is not None:
                # Frame DEPOIS do fim: descartado. Abrir sessão nova aqui era o comportamento
                # anterior, e ele destruía o relatório da sessão boa — ver `ENDED_MEMORY_MS`.
                encerrada.ignored += 1
                if encerrada.ignored == 1:
                    logger.info(
                        "sessao %s ja encerrada: frames atrasados sendo descartados",
                        envelope.session_id,
                    )
                return []
            # Frame ANTES do `session.started`: abre com o padrão da SPEC-009 em vez de
            # descartar — perder repetições por corrida de eventos seria pior.
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
            RawFrame(
                ts=envelope.ts,
                seq=envelope.seq,
                landmarks=payload.landmarks,
                # T-110: as dimensões do frame de origem atravessam o contrato e chegam aqui.
                # Cliente que não as declara continua caindo no espaço isotrópico por omissão,
                # que é como o worker se comportava antes desta task.
                width=payload.width,
                height=payload.height,
            )
        )

        # Cena primeiro: um frame ruim ainda deve avisar o usuário, mesmo que a FSM congele
        # nele (é justamente quando o aviso importa). Roda também durante a calibração — é aí
        # que "entre no quadro" mais precisa ser dito.
        avisos = estado.scene.check(norm)

        calibracao = self._calibrar(estado, norm)

        if not estado.counting(self._now):
            # Duas fases caem aqui: medindo o corpo, e a preparação do "3, 2, 1" (T-049).
            #
            # Os frames continuam sendo normalizados — o One Euro precisa ficar quente, senão
            # o primeiro movimento que vale chegaria cru — e a validação de cena continua
            # falando, que é justamente quando "entre no quadro" mais ajuda. O que não roda é
            # a FSM: um "1" no placar antes do JÁ seria uma repetição que a pessoa não fez, e
            # é para impedir exatamente isso que a espera mora no servidor e não na animação.
            saidas = [*calibracao]
            saidas.extend(self._wrap(estado, aviso) for aviso in avisos)
            saidas.extend(
                self._wrap(estado, mensagem)
                for mensagem in estado.feedback.push(avisos, envelope.ts)
            )
            return saidas

        sinais = feed(estado.analyzer, norm)

        saidas = [*calibracao]
        saidas.extend(self._wrap(estado, payload_evento) for payload_evento in (*avisos, *sinais))
        # O feedback engine é o último: ele decide o que o HUD vê, com prioridade e throttle.
        saidas.extend(
            self._wrap(estado, mensagem)
            for mensagem in estado.feedback.push([*avisos, *sinais], envelope.ts)
        )

        # Meta atingida ⇒ a série acaba AQUI, no frame da N-ésima repetição (SPEC-023 §1).
        # Mora no caminho do frame, e não no `tick`, porque o instante do fim é o da
        # repetição: é dele que sai o "tempo até a meta", e um fim carimbado no `tick`
        # seguinte carregaria o atraso do loop dentro do número que a pessoa vai ler.
        # Quem decide continua sendo o worker, nunca o cliente (notas técnicas da spec).
        #
        # Depois do feedback de propósito: a última repetição tem de chegar ao HUD antes do
        # fim da sessão, senão o placar congela em 14/15 numa série que terminou completa.
        if estado.counted and int(estado.analyzer.summary()["reps"]) >= estado.target_reps:
            saidas.append(self._encerrar(estado, SessionEndReason.TARGET_REACHED))
        return saidas

    def _calibrar(self, estado: SessionState, norm) -> list[Envelope]:
        """Alimenta a calibração enquanto ela não terminou. Devolve `session.calibrated` uma vez.

        Instalar a baseline muda DOIS consumidores: a normalização (que passa a usar a escala
        medida em vez da instantânea) e a FSM (que passa a comparar a abertura dos pés contra
        os ombros medidos). Os dois têm de receber a mesma medida, no mesmo instante — por isso
        isso mora aqui, e não espalhado.
        """
        if estado.baseline is not None:
            return []

        baseline = estado.calibrator.push(norm)
        if baseline is None:
            if estado.calibrator.failed(norm.ts):
                # SPEC-004, critério 2: sem medida não se começa. O countdown recomeça, e o
                # motivo já está sendo dito pelos avisos de cena deste mesmo frame.
                logger.info(
                    "calibracao de %s reiniciada: %s amostras boas, %s descartadas",
                    estado.session_id,
                    estado.calibrator.samples,
                    estado.calibrator.discarded,
                )
                estado.calibrator.reset()
            return []

        estado.baseline = baseline
        estado.normalizer.set_baseline(baseline)
        estado.analyzer.baseline = baseline

        # Preparação (T-049): entre o corpo medido e a contagem valer. Com `countdown_s = 0`
        # os dois instantes coincidem e o comportamento é o de antes da task.
        countdown_ms = estado.countdown_s * 1000
        estado.counting_from_wall_ms = self._now + countdown_ms
        # O relógio dos 30 s começa no "JÁ", não agora (SPEC-009 + SPEC-004): o que veio antes
        # foi a pessoa se posicionando, e cobrar isso do treino dela seria errado. Fica no
        # futuro de propósito — `expired()` compara contra ele e só passa a contar lá.
        estado.exercise_started_wall_ms = estado.counting_from_wall_ms
        # Mesmo instante, no relógio dos frames: a âncora do teto do modo contado. Sai daqui e
        # não do primeiro frame pela mesma razão do par de parede — o que veio antes foi a
        # pessoa se posicionando.
        estado.exercise_started_ts = norm.ts + countdown_ms
        logger.info("sessao %s calibrada, exercicio vale em %s ms", estado.session_id, countdown_ms)

        return [
            self._wrap(
                estado,
                SessionCalibrated(
                    torso=float(baseline.torso or 0.0),
                    shoulder_width=float(baseline.shoulder_width or 0.0),
                    shoulder_span=float(baseline.shoulder_span or 0.0),
                    wrist_rest_y=float(baseline.wrist_rest_y or 0.0),
                    samples=estado.calibrator.samples,
                    countdown_ms=countdown_ms,
                ),
            )
        ]

    def _on_session_completed(self, envelope: Envelope) -> list[Envelope]:
        """Fim vindo de fora (API/TTL/cliente): fecha o estado e reemite com o total de reps."""
        estado = self.sessions.pop(envelope.session_id, None)
        if estado is None:
            return []
        self._marcar_encerrada(envelope.session_id)
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

    def _encerrar(self, estado: SessionState, motivo: SessionEndReason) -> Envelope:
        """Fecha uma sessão por decisão do servidor e devolve o `session.completed`.

        Os três passos — tirar do dicionário, deixar a lápide, devolver a vaga — andam sempre
        juntos: foi separá-los que produziu o bug da T-077. Todo caminho de fim decidido aqui
        dentro (timer, teto, meta) passa por este método.
        """
        self.sessions.pop(estado.session_id, None)
        self._marcar_encerrada(estado.session_id)
        self._liberar_vaga(estado.session_id)
        reps = int(estado.analyzer.summary()["reps"])
        logger.info(
            "sessao %s encerrada pelo servidor (%s) com %s reps",
            estado.session_id,
            motivo.value,
            reps,
        )
        return self._wrap(estado, SessionCompleted(reason=motivo, rep_count=reps))

    # --------------------------------------------------------------------- timer

    def tick(self, now_wall_ms: int | None = None) -> list[Envelope]:
        """Fecha sessões cujo prazo venceu. Chamado a cada volta do loop do worker.

        É aqui que mora o **timer autoritativo** da SPEC-009: a sessão termina porque o servidor
        decidiu, não porque o cliente avisou.
        """
        agora = now_wall_ms if now_wall_ms is not None else _wall_ms()
        self._now = agora
        self._esquecer_encerradas(agora)
        saidas: list[Envelope] = []
        for estado in list(self.sessions.values()):
            motivo = estado.expiry_reason(agora)
            if motivo is None:
                continue
            saidas.append(self._encerrar(estado, motivo))
        return saidas

    def _esquecer_encerradas(self, agora_wall_ms: int) -> None:
        """Poda as lápides vencidas — a memória é limitada por tempo, não por número.

        Um worker de pé por semanas com um `dict` que só cresce vaza memória por uma linha
        esquecida; e um limite por quantidade escolheria quem esquecer pela ordem errada
        (a sessão mais antiga é justamente a que já não recebe frame nenhum).
        """
        for session_id, encerrada in list(self.ended.items()):
            if agora_wall_ms - encerrada.at_wall_ms < ENDED_MEMORY_MS:
                continue
            if encerrada.ignored:
                logger.debug(
                    "sessao %s esquecida apos descartar %s frames atrasados",
                    session_id,
                    encerrada.ignored,
                )
            del self.ended[session_id]

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
