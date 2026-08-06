"""Flexão de braço — o exercício 3, e o primeiro do chão (SPEC-007 / SPEC-020 Tier C).

FSM de duas fases, mesma forma dos outros: histerese + debounce, frame `degraded` congela, rep
rasa vira sinal de qualidade em vez de repetição::

        depth < 0.82 da prancha            depth > 0.93 da prancha
  PRANCHA ───────────────────────► EMBAIXO ───────────────────────► PRANCHA
                                                  = 1 repetição válida

**Antes de tudo isso vem um porteiro de postura, e ele existe por um bug de produção.**

A primeira versão contava braço levantado como flexão. O relato de quem testou — "dependendo da
posição ele já contava, quando levantava ele contava" — tem uma causa exata: a altura do ombro
sobre o pulso de quem está **em pé com os braços baixos** é +0,73 torsos, quase idêntica à de
uma prancha (+1,15). Para a FSM, levantar e baixar os braços era descer e subir uma flexão. A
feature media a coisa certa e nunca perguntava *quem* estava sendo medido.

O porteiro pergunta duas coisas, ambas razões no mesmo eixo (imunes ao formato do vídeo):

=========================  ==========  ==========  ==========  =============
situação                   tronco dx/dy  mão↔chão   passa?
=========================  ==========  ==========  ==========  =============
prancha                          2,46        0,13   sim
flexão no fundo                  3,86        0,18   sim
flexão de joelhos                1,56        0,13   sim
em pé, braços baixos             0,00        1,78   não
em pé, braços no alto            0,00        3,78   não
agachado                         0,00        1,23   não
=========================  ==========  ==========  ==========  =============

Os limiares (1,2 e 0,5) ficam no meio de uma folga de ordem de grandeza — a decisão não é
apertada, e é isso que faz o porteiro sobreviver a ruído do modelo e a câmera torta. Frame que
não passa **congela a FSM e descarta a tentativa em curso**: quem começou deitado e terminou de
pé não fez uma repetição incompleta, fez outra coisa.

**Câmera de lado, celular no chão.** É o que a SPEC-020 chama de Tier C: de frente, uma flexão
é um corpo encolhendo contra a lente e não há feature que sobreviva. De lado, o movimento
inteiro acontece no plano da imagem.

**A feature é a altura do ombro sobre a mão, dividida pela altura da própria prancha da
pessoa** — e essa divisão é a decisão que define este módulo.

Duas medições feitas nesta task explicam por quê:

1. **O espaço normalizado não é isotrópico.** O MediaPipe divide `x` pela largura do frame e
   `y` pela altura; num vídeo deitado (16:9) uma distância vertical vale 1,78× o que valeria
   uma horizontal do mesmo tamanho. Medido no corpus: a mesma largura de ombros lê 0,352
   torsos no vídeo em paisagem e 1,188 no vídeo em retrato — razão 3,37, contra 3,16 previstos
   só pelo formato do quadro. Num corpo **deitado** o torso é medido no eixo horizontal e o
   movimento acontece no vertical: qualquer limiar "em torsos" herdaria o formato do vídeo.
2. **Limiar em torsos calibrado no gerador não sobrevive a gente real.** O agachamento é o
   precedente medido (Descoberta `[A/T-106]` no BACKLOG): o boneco sintético diz que quem está
   em pé tem `hip_height` 1,02, gente real do corpus lê 1,31–1,61, e o limiar de 0,72 nunca
   dispara.

A saída para as duas é a mesma: **razão entre duas medidas do mesmo eixo do mesmo corpo**. Aqui
o numerador é a altura atual do ombro sobre o pulso e o denominador é a maior altura que ESTA
pessoa mostrou nesta sessão — a prancha dela. A razão cancela o torso, cancela o formato do
vídeo, cancela a distância da câmera e cancela o tamanho da pessoa. O que sobra é "quanto do
seu próprio braço você dobrou", que é o que a flexão é.

Profundidade medida no gerador (`tests/synthetic_keypoints.py`), com as proporções corporais
tiradas do corpus real:

===============  ===================  ================
cotovelo (real)  altura do ombro      razão da prancha
===============  ===================  ================
172° (prancha)         1,147                1,000
145°                   1,097                0,956
130°                   1,042                0,909
115°                   0,970                0,846
100°                   0,882                0,768
 90° (fundo)           0,814                0,709
===============  ===================  ================

O limiar de descida (0,82) fica em ~107° de cotovelo, um pouco acima dos 90° que NASM e ACE
descrevem como fundo: conta a flexão de quem desce quase tudo, e reserva `PUSHUP_TOO_SHALLOW`
para quem para entre 107° e 127°. Errar para o lado de contar é a escolha certa aqui — um
`beta` que não conta nada não recebe corpus para deixar de ser `beta`.

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

__all__ = ["PushUpAnalyzer", "PushUpThresholds"]

_LEFT_SHOULDER, _RIGHT_SHOULDER = 11, 12
_LEFT_ELBOW, _RIGHT_ELBOW = 13, 14
_LEFT_WRIST, _RIGHT_WRIST = 15, 16
_LEFT_HIP, _RIGHT_HIP = 23, 24
_LEFT_KNEE, _RIGHT_KNEE = 25, 26
_LEFT_ANKLE, _RIGHT_ANKLE = 27, 28

#: Altura de prancha mínima (em torsos) para a referência valer. Abaixo disso o corpo não está
#: numa flexão — está de pé, sentado, ou o modelo perdeu o braço — e dividir por ela produziria
#: profundidades absurdas a partir de ruído.
_MIN_PLANK_HEIGHT = 0.25


@dataclass(frozen=True, slots=True)
class PushUpThresholds:
    """Limiares da flexão. Frozen: mudar isto é mudar comportamento.

    **Calibrados no gerador sintético, não em vídeo de gente fazendo flexão** — a maturidade
    deste exercício nasce `beta` por causa disso (SPEC-020). O que os torna mais defensáveis que
    os do agachamento é a unidade: são frações da prancha da própria pessoa, então não dependem
    das proporções do boneco terem ficado certas.
    """

    #: Fração da prancha abaixo da qual conta como "desceu". ~107° de cotovelo.
    down_depth: float = 0.82
    #: Acima disto voltou à prancha. A folga para 0,82 é a histerese.
    up_depth: float = 0.93
    #: Desceu, mas não o bastante: entre este valor e `down_depth` vira crítica (~107°–127°).
    shallow_depth: float = 0.90
    #: Fase mínima antes de aceitar a transição seguinte (SPEC-007: debounce de 250 ms).
    min_phase_ms: int = 250
    #: Desvio do quadril da linha ombro→tornozelo, em alturas de prancha, que vira crítica.
    #: 0,12 separa com folga o corpo alinhado (0,00) do quadril visivelmente caído (0,20).
    hip_line_tolerance: float = 0.12
    #: **Porteiro 1**: o tronco tem de estar mais deitado que em pé — `|dx| / |dy|` do vetor
    #: ombro→quadril. Medido: 2,4 na prancha, 3,9 no fundo da flexão, 0,0 em pé. O limiar fica
    #: em 1,2 (corpo mais largo que alto, com margem), e a folga para 0,0 é de ordem de
    #: grandeza — é o que faz o porteiro sobreviver a ruído e a câmera torta.
    min_trunk_spread: float = 1.2
    #: **Porteiro 2**: a mão tem de estar no nível do chão — distância vertical do pulso ao
    #: ponto mais baixo da perna, em alturas de prancha. Medido: 0,13 na prancha, 0,18 no
    #: fundo, contra 1,2–3,8 em pé. O limiar em 0,5 aceita flexão de joelhos (onde quem toca o
    #: chão é o joelho, não o pé) e continua recusando qualquer coisa em pé.
    max_hands_to_ground: float = 0.5
    #: Janela da cadência.
    cadence_window_ms: int = 10_000


@dataclass(slots=True)
class PushUpAnalyzer:
    """Um analisador por sessão: guarda fase, contagem, referência da prancha e histórico."""

    slug: str = "flexao"
    thresholds: PushUpThresholds = field(default_factory=PushUpThresholds)

    #: Medidas da calibração (SPEC-004). Não entram no cálculo — a feature é uma razão e
    #: cancela a escala. Existem para o relatório.
    baseline: Baseline | None = None

    phase: Phase = Phase.REST
    rep_count: int = 0

    #: A prancha DESTA pessoa: maior altura ombro→pulso vista na sessão. É o denominador de
    #: `depth`, e por isso o número mais importante do módulo.
    _plank_height: float = 0.0
    _phase_since_ms: int | None = None
    _rep_started_ms: int | None = None
    _rep_timestamps: deque[int] = field(default_factory=deque)
    #: O mais FUNDO que chegou na tentativa atual (menor `depth`).
    _lowest_depth: float = math.inf
    #: Maior desvio do quadril na tentativa atual, com sinal (+ = caindo).
    _worst_hip_line: float = 0.0
    #: Altura do frame anterior, para a referência exigir dois frames seguidos. `None` = ainda
    #: não houve frame anterior, e aí o primeiro vale por si: uma referência que só nascesse no
    #: segundo frame deixaria o primeiro sem medida nenhuma, e semear baixo é inofensivo (a
    #: referência só cresce), enquanto semear alto é o que a persistência existe para impedir.
    _last_plank_height: float | None = None
    _quality_signals: dict[str, int] = field(default_factory=dict)
    _frames_seen: int = 0
    _frames_degraded: int = 0
    #: Frames em que a pessoa não estava em posição de flexão. Não é dado ruim — é gente não
    #: fazendo o exercício —, e por isso conta separado do `degraded` no relatório.
    _frames_off_posture: int = 0

    # ----------------------------------------------------------------- features

    def features(self, frame: NormFrame) -> Features:
        points = frame.points

        shoulder_y = (float(points[_LEFT_SHOULDER][1]) + float(points[_RIGHT_SHOULDER][1])) / 2
        shoulder_x = (float(points[_LEFT_SHOULDER][0]) + float(points[_RIGHT_SHOULDER][0])) / 2
        wrist_y = (float(points[_LEFT_WRIST][1]) + float(points[_RIGHT_WRIST][1])) / 2
        hip_y = (float(points[_LEFT_HIP][1]) + float(points[_RIGHT_HIP][1])) / 2
        hip_x = (float(points[_LEFT_HIP][0]) + float(points[_RIGHT_HIP][0])) / 2
        knee_y = (float(points[_LEFT_KNEE][1]) + float(points[_RIGHT_KNEE][1])) / 2
        ankle_y = (float(points[_LEFT_ANKLE][1]) + float(points[_RIGHT_ANKLE][1])) / 2
        ankle_x = (float(points[_LEFT_ANKLE][0]) + float(points[_RIGHT_ANKLE][0])) / 2

        # y cresce para baixo: ombro acima da mão ⇒ diferença positiva.
        plank_height = wrist_y - shoulder_y

        # Tronco mais deitado que em pé, e mão no nível do chão. Ver `on_floor` abaixo.
        trunk_spread = abs(hip_x - shoulder_x) / max(abs(hip_y - shoulder_y), 1e-6)
        # O ponto mais BAIXO da perna: no apoio de pés é o tornozelo, na flexão de joelhos é o
        # joelho. Usar só o tornozelo recusaria a flexão de joelhos, que é a progressão que
        # mais gente usa para começar.
        ground_y = max(ankle_y, knee_y)
        hands_to_ground = abs(wrist_y - ground_y) / max(abs(plank_height), 1e-6)
        on_floor = (
            trunk_spread >= self.thresholds.min_trunk_spread
            and hands_to_ground <= self.thresholds.max_hands_to_ground
            and plank_height >= _MIN_PLANK_HEIGHT
        )

        # A referência só cresce, e só cresce COM O PORTEIRO ABERTO. Sem essa segunda
        # condição, a pessoa em pé esperando o countdown fixa uma referência que não é prancha
        # nenhuma — e foi assim que a primeira versão contava braço levantado como flexão.
        #
        # `min` com o frame anterior exige que a altura se sustente por DOIS frames: um único
        # frame em que o modelo errou o ombro inflaria a referência para sempre, e a partir daí
        # nenhuma prancha de verdade voltaria a marcar 1,0.
        if on_floor:
            anterior = plank_height if self._last_plank_height is None else self._last_plank_height
            candidata = min(plank_height, anterior)
            if candidata > self._plank_height:
                self._plank_height = candidata
        self._last_plank_height = plank_height

        return {
            "on_floor": on_floor,
            "trunk_spread": trunk_spread,
            "hands_to_ground": hands_to_ground,
            # A feature que decide.
            "depth": self._depth(plank_height),
            "plank_height": plank_height,
            # Desvio do quadril da linha ombro→tornozelo, em alturas de prancha. Positivo =
            # quadril caindo. Também é razão de dois `y`, pela mesma razão que `depth`.
            "hip_line": self._hip_line(
                shoulder_x=shoulder_x,
                shoulder_y=shoulder_y,
                hip_x=hip_x,
                hip_y=hip_y,
                ankle_x=ankle_x,
                ankle_y=ankle_y,
            ),
            # O ângulo que a CÂMERA vê. De lado ele é honesto (o cotovelo dobra no plano da
            # imagem), ao contrário do joelho do agachamento visto de frente — mas quem conta
            # continua sendo `depth`, que não depende de o modelo acertar o cotovelo ocluído.
            "elbow_angle_view": self._elbow_angle_view(points),
            "cadence_10s": self._cadence(frame.ts),
            "degraded": frame.degraded,
        }

    def _depth(self, plank_height: float) -> float:
        """Altura atual como fração da prancha da pessoa. 1.0 = braço estendido."""
        if self._plank_height < _MIN_PLANK_HEIGHT:
            # Sem referência confiável não existe profundidade: devolver 1.0 (= "está na
            # prancha") mantém a FSM em repouso em vez de inventar uma descida.
            return 1.0
        return plank_height / self._plank_height

    def _hip_line(
        self,
        *,
        shoulder_x: float,
        shoulder_y: float,
        hip_x: float,
        hip_y: float,
        ankle_x: float,
        ankle_y: float,
    ) -> float:
        """Quanto o quadril foge da reta ombro→tornozelo, em alturas de prancha."""
        vao = ankle_x - shoulder_x
        if abs(vao) < 1e-6 or self._plank_height < _MIN_PLANK_HEIGHT:
            return 0.0
        # Onde a reta ombro→tornozelo passa na vertical do quadril. `t` é razão de dois `x` e
        # a diferença que sai daqui é `y`: a conta inteira fica imune ao formato do quadro.
        t = (hip_x - shoulder_x) / vao
        linha_y = shoulder_y + t * (ankle_y - shoulder_y)
        return (hip_y - linha_y) / self._plank_height

    @staticmethod
    def _elbow_angle_view(points) -> float:
        """Ângulo ombro–cotovelo–pulso no plano da imagem, média dos dois braços."""

        def um_lado(ombro: int, cotovelo: int, pulso: int) -> float:
            ax = float(points[ombro][0] - points[cotovelo][0])
            ay = float(points[ombro][1] - points[cotovelo][1])
            cx = float(points[pulso][0] - points[cotovelo][0])
            cy = float(points[pulso][1] - points[cotovelo][1])
            na, nc = math.hypot(ax, ay), math.hypot(cx, cy)
            if na == 0.0 or nc == 0.0:
                return 180.0
            cosseno = (ax * cx + ay * cy) / (na * nc)
            return math.degrees(math.acos(max(-1.0, min(1.0, cosseno))))

        return (
            um_lado(_LEFT_SHOULDER, _LEFT_ELBOW, _LEFT_WRIST)
            + um_lado(_RIGHT_SHOULDER, _RIGHT_ELBOW, _RIGHT_WRIST)
        ) / 2

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

        if not feats.get("on_floor"):
            # A pessoa não está em posição de flexão: em pé esperando, levantando do chão,
            # ajeitando o celular. Congela como o `degraded` congela — mas, ao contrário dele,
            # também **descarta a tentativa em curso**: um movimento que começou deitado e
            # terminou de pé não é uma repetição incompleta, é outra coisa.
            #
            # Este porteiro é o conserto do bug relatado em produção: sem ele, a altura do
            # ombro sobre o pulso de quem está EM PÉ com os braços baixos (+0,73 torsos) é
            # quase idêntica à de uma prancha, e levantar os braços virava uma flexão contada.
            self._frames_off_posture += 1
            self._abandon_attempt(ts)
            return []

        if self._phase_since_ms is None:
            self._phase_since_ms = ts
            # Ao contrário do polichinelo e do agachamento, aqui a fase inicial nunca pode ser
            # `PEAK`: no primeiro frame a referência da prancha é o próprio frame, então
            # `depth` vale 1.0 por construção e nada afirma que a pessoa está embaixo. O
            # contrato de `initial_phase` manda devolver repouso justamente quando os features
            # não afirmam a fase sem ambiguidade — é o que acontece.
            if self.initial_phase(feats) is Phase.PEAK:  # pragma: no cover - inalcançável hoje
                self.phase = Phase.PEAK
                self._rep_started_ms = ts
                return [ExercisePhase(phase=Phase.PEAK)]

        depth = float(feats["depth"])
        hip_line = float(feats["hip_line"])
        limiares = self.thresholds
        estavel = ts - self._phase_since_ms >= limiares.min_phase_ms

        if abs(hip_line) > abs(self._worst_hip_line):
            self._worst_hip_line = hip_line

        if self.phase is Phase.REST:
            self._lowest_depth = min(self._lowest_depth, depth)

            if depth < limiares.down_depth and estavel:
                return self._enter(Phase.PEAK, ts)

            # Voltou à prancha sem ter descido o bastante: a tentativa acabou.
            if depth > limiares.up_depth:
                return self._close_partial_attempt()
            return []

        # Fase EMBAIXO: só interessa voltar à prancha — aí nasce a repetição.
        if depth > limiares.up_depth and estavel:
            eventos = self._enter(Phase.REST, ts)
            return [*eventos, *self._count_rep(ts)]
        return []

    def _abandon_attempt(self, ts: int) -> None:
        """Volta ao repouso sem contar e sem criticar.

        Silencioso de propósito: não emite `ExercisePhase` nem sinal de qualidade. Quem saiu da
        posição não fez uma flexão ruim — não fez flexão nenhuma, e criticar a execução de
        alguém que está se levantando do chão é ruído. O `_phase_since_ms` volta para agora,
        para o debounce recomeçar quando a pessoa voltar à prancha.
        """
        self.phase = Phase.REST
        self._phase_since_ms = ts
        self._rep_started_ms = None
        self._lowest_depth = math.inf
        self._worst_hip_line = 0.0

    def _enter(self, phase: Phase, ts: int) -> list[AnalysisEvent]:
        if phase is Phase.PEAK:
            self._rep_started_ms = self._phase_since_ms
        self.phase = phase
        self._phase_since_ms = ts
        self._lowest_depth = math.inf
        return [ExercisePhase(phase=phase)]

    def _count_rep(self, ts: int) -> list[AnalysisEvent]:
        """Fecha a repetição — e critica a postura do corpo durante ela.

        A crítica sai JUNTO com a repetição, e não no lugar dela: quadril caído é uma flexão
        que aconteceu e foi mal feita, ao contrário da rep rasa, que é uma flexão que não
        aconteceu. Contar e criticar diz a verdade sobre as duas.
        """
        self.rep_count += 1
        self._rep_timestamps.append(ts)
        duration_ms = ts - self._rep_started_ms if self._rep_started_ms is not None else 0
        self._rep_started_ms = None

        eventos: list[AnalysisEvent] = [
            RepDetected(rep_count=self.rep_count, phase=Phase.REST, duration_ms=duration_ms)
        ]
        tolerancia = self.thresholds.hip_line_tolerance
        if self._worst_hip_line > tolerancia:
            eventos.append(self._signal(Code.HIPS_SAGGING, self._worst_hip_line))
        elif self._worst_hip_line < -tolerancia:
            eventos.append(self._signal(Code.HIPS_PIKED, self._worst_hip_line))
        self._worst_hip_line = 0.0
        return eventos

    def _close_partial_attempt(self) -> list[AnalysisEvent]:
        """Fecha uma tentativa incompleta. Só reclama de quem chegou perto."""
        limiares = self.thresholds
        eventos: list[AnalysisEvent] = []

        if limiares.down_depth <= self._lowest_depth <= limiares.shallow_depth:
            eventos.append(self._signal(Code.PUSHUP_TOO_SHALLOW, self._lowest_depth))

        self._lowest_depth = math.inf
        self._worst_hip_line = 0.0
        return eventos

    def _signal(self, code: Code, value: float) -> QualitySignal:
        self._quality_signals[code.value] = self._quality_signals.get(code.value, 0) + 1
        return QualitySignal(code=code, value=round(value, 2), rep_index=self.rep_count + 1)

    # ------------------------------------------------------- resto da interface

    def initial_phase(self, feats: Features) -> Phase:
        """Fase do primeiro frame utilizável (T-047, contrato em `base.py`).

        Sempre repouso na prática — ver o comentário em `step()`. O método existe cumprindo o
        contrato, e continuaria correto se um dia a referência da prancha vier da calibração.
        """
        if feats.get("degraded") or not feats.get("on_floor"):
            return Phase.REST
        return Phase.PEAK if float(feats["depth"]) < self.thresholds.down_depth else Phase.REST

    def ready_pose(self, feats: Features) -> bool:
        """Posição inicial da flexão: prancha alta, braço estendido, corpo em linha."""
        if feats.get("degraded") or not feats.get("on_floor"):
            return False
        return (
            float(feats["depth"]) > self.thresholds.up_depth
            and float(feats["plank_height"]) >= _MIN_PLANK_HEIGHT
            and abs(float(feats["hip_line"])) <= self.thresholds.hip_line_tolerance
        )

    def scene_hints(self) -> _PushUpSceneHints:
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
            # Alto aqui significa "a pessoa passou a sessão fora de posição", que é uma coisa
            # muito diferente de dado ruim — e é a primeira pergunta a fazer quando uma sessão
            # de flexão volta com zero repetição.
            "frames_off_posture": self._frames_off_posture,
        }


@dataclass(frozen=True, slots=True)
class _PushUpSceneHints:
    body_height_range: tuple[float, float]
    posture: Posture = Posture.FLOOR


#: Deitado, a extensão do corpo se mede na LARGURA do quadro. A faixa é mais alta que a de quem
#: está em pé (0,40–0,95) porque um corpo deitado ocupa o lado longo do frame quase inteiro: o
#: celular no chão em paisagem enquadra a pessoa de ponta a ponta, e exigir menos de 45% seria
#: aceitar uma gravação em que a flexão cabe num canto da tela.
_SCENE_HINTS = _PushUpSceneHints(body_height_range=(0.45, 0.98))

# Literal pelo mesmo motivo dos outros: com `slots=True` o atributo de classe é o descritor.
EXERCISES["flexao"] = PushUpAnalyzer
