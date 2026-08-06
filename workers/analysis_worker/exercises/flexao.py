"""Flexão de braço — o exercício 3, e o primeiro do chão (SPEC-007 / SPEC-020 Tier C).

FSM de duas fases, mesma forma dos outros: histerese + debounce, frame `degraded` congela, rep
rasa vira sinal de qualidade em vez de repetição::

           depth < desce                      depth > sobe
  PRANCHA ───────────────────────► EMBAIXO ───────────────────────► PRANCHA
                                                  = 1 repetição válida

`depth` é sempre "que fração do SEU topo você está mostrando agora", mas **o que a alimenta
depende de que lado a câmera está** (0,82/0,93 da altura da prancha de perfil; 0,63/0,80 do
ângulo de cotovelo de frente). A vista é lida da geometria — ver §Duas vistas abaixo.

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

**Duas vistas, medidas — não uma.** Este módulo nasceu só de perfil (celular deitado no chão),
sob a tese de que "de frente uma flexão é um corpo encolhendo contra a lente e não há feature
que sobreviva". A primeira metade da tese é verdadeira e a segunda é falsa: o encolhimento
existe e é violento, mas **ele próprio é a feature**. Medido em dois vídeos de gente real
fazendo flexão de frente (`eval/corpus/flexão-frente-*`), o que a lente vê é isto:

=============================  ============  ==============  ===============
situação                       ombro/tronco  tronco |dx/dy|  pulso − quadril
=============================  ============  ==============  ===============
flexão de PERFIL                       0,12      1,56–3,47       0,48–0,77
flexão de FRENTE                    1,9–48       0,00–1,19       0,25–2,74
em pé (polichinelo real)          0,29–1,26      0,00–0,13     **≤ 0,16**
=============================  ============  ==============  ===============

Três decisões saem dessa tabela, e nenhuma é chute:

1. **O porteiro de chão é `pulso − quadril`**, e vale nas duas vistas. Numa flexão a mão está
   no chão e o quadril está mais longe da lente — e mais longe, num plano que se afasta, é
   mais ALTO na imagem. Quem está em pé nunca passa de 0,16; quem está no chão parte de 0,25.
   O porteiro antigo (`trunk_spread ≥ 1,2`) media a mesma ideia **numa vista só**: de frente o
   vetor ombro→quadril aponta para a lente, o `dx` some, e ele nunca abria — a flexão frontal
   contava 0 de 50. Ele continua valendo, como confirmação do perfil.
2. **A vista se lê em `ombro/tronco`** — largura de ombros dividida pelo comprimento aparente
   do tronco, ambos do mesmo frame. De perfil os ombros se sobrepõem e o tronco aparece
   inteiro (0,12); de frente os ombros abrem e o tronco encolhe contra a lente (≥ 1,9). São
   16× de separação, e o limiar fica em 1,0, no meio do vão.
3. **De frente, quem conta é o ângulo do cotovelo** — não a altura do ombro. A altura que
   sustenta o perfil balança de 0,3 a 2,3 torsos aqui, porque cada repetição muda a distância
   corpo↔lente; o ângulo do cotovelo é imune a escala por construção.

**Em ambas as vistas a feature é uma razão contra o topo da PRÓPRIA pessoa** — a decisão que
define este módulo. De perfil, altura do ombro ÷ maior altura da sessão; de frente, ângulo do
cotovelo ÷ maior ângulo da sessão. Mesma forma, mesma FSM, mesma histerese.

**A feature de perfil é a altura do ombro sobre a mão, dividida pela altura da própria prancha
da pessoa.**

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
import statistics
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum

from workers.analysis_worker.exercises.base import (
    EXERCISES,
    AnalysisEvent,
    Features,
    Posture,
)
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import Baseline, NormFrame

__all__ = ["PushUpAnalyzer", "PushUpThresholds", "View"]


class View(StrEnum):
    """De que lado a câmera está — e, por consequência, que feature sabe contar.

    Não é preferência de enquadramento: é qual eixo do movimento vive no plano da imagem.
    Ver a tabela no topo do módulo; a vista é **lida da geometria**, não perguntada ao usuário.
    """

    #: Celular deitado no chão, pessoa de perfil. O movimento acontece na vertical da imagem.
    PROFILE = "profile"
    #: Celular em pé no chão, pessoa de frente. O corpo encolhe contra a lente, e quem
    #: sobrevive a isso é o ângulo do cotovelo.
    FRONTAL = "frontal"


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

#: Ângulo de cotovelo mínimo (graus) para a referência FRONTAL valer. É o análogo exato do
#: `_MIN_PLANK_HEIGHT`: sem um braço que em algum momento esteve estendido, não existe "topo"
#: contra o qual medir o quanto ele dobrou, e dividir por ruído produziria reps do nada.
_MIN_TOP_ELBOW = 120.0

#: Amostras da vista antes de travar a decisão. Com 16× de separação entre perfil (0,12) e
#: frente (≥ 1,9), poucas bastam — e travar importa mais que decidir devagar: uma vista que
#: oscila no meio da série troca a feature que conta e perde a referência junto.
#:
#: Enquanto não trava, vale o valor **instantâneo**. É de propósito: exigir a janela cheia
#: antes de qualquer decisão congelaria a FSM no primeiro segundo, e a 15 fps isso é uma
#: repetição inteira jogada fora em quem já começa no ritmo.
_VIEW_SAMPLES = 5


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

    # ------------------------------------------------------------------ chão, nas duas vistas

    #: **Porteiro de chão**, válido de perfil E de frente: o pulso tem de estar abaixo do
    #: quadril na imagem, em torsos. A mão está no chão e o quadril está mais longe da lente —
    #: e num plano que se afasta, mais longe é mais alto na imagem. Medido: perfil 0,48–0,77,
    #: frente 0,25–2,74, **em pé no máximo 0,16** (três vídeos reais de polichinelo). O limiar
    #: em 0,30 fica com quase o dobro de folga sobre o pior caso de quem está em pé.
    min_wrists_below_hips: float = 0.30

    # ----------------------------------------------------------------------------- vista

    #: Fronteira da vista: largura de ombros ÷ comprimento aparente do tronco, mesmo frame.
    #: Medido: 0,12 de perfil (ombros sobrepostos), ≥ 1,9 de frente (ombros abertos, tronco
    #: encurtado contra a lente). O limiar em 1,0 fica no meio de um vão de 16×.
    frontal_view_ratio: float = 1.0

    # --------------------------------------------------------------------------- frontal

    #: **Porteiro frontal**: confirma que o corpo continua encurtado contra a lente.
    #:
    #: Deliberadamente frouxo, e igual à fronteira da vista. Quem recusa gente em pé é o
    #: `min_wrists_below_hips` (0,30 contra um máximo medido de 0,16 — quase o dobro de folga);
    #: este aqui só confirma o regime. A versão apertada (1,5, entre o 1,26 de quem está em pé
    #: e o 1,90 do p05 frontal) fechava o porteiro **no topo da repetição**, que é exatamente
    #: onde a FSM precisa dele aberto: o encurtamento é MÍNIMO com o braço estendido, e o
    #: gerador em perspectiva mede 1,40 ali. Dois porteiros apertados na mesma direção não
    #: somam segurança — somam repetições perdidas.
    min_shoulder_to_torso: float = 1.0
    #: Fração do ângulo de cotovelo do topo abaixo da qual conta como "desceu".
    #:
    #: **Dois caminhos independentes chegam neste número, e é isso que o sustenta.**
    #: (1) Equivalência: o `down_depth` do perfil (0,82 de prancha) vale ~107° de cotovelo, e
    #: 107° sobre um topo de ~171° dá 0,63. (2) Medição: nos dois vídeos frontais do corpus,
    #: todo fundo de repetição fica **abaixo de 0,585** e todo topo **acima de 0,859** — a
    #: histerese inteira tem de viver nessa folga, e 0,63 fica dentro dela com margem.
    #:
    #: A varredura registrada no DEVLOG mostra 20 pares (desce, sobe) dentro da folga dando
    #: contagem IDÊNTICA: é platô, não pico. O par que minimizava o erro bruto (0,86) ficava
    #: 0,001 abaixo do menor topo medido — ajuste ao rótulo, não limiar.
    frontal_down_depth: float = 0.63
    #: Acima disto voltou ao topo. A folga para `frontal_down_depth` é a histerese.
    frontal_up_depth: float = 0.80
    #: Desceu, mas não o bastante: entre este valor e `frontal_down_depth` vira crítica.
    #: 0,74 é o equivalente frontal dos 127° que o perfil usa (127 ÷ 171).
    frontal_shallow_depth: float = 0.74


@dataclass(slots=True)
class PushUpAnalyzer:
    """Um analisador por sessão: guarda fase, contagem, referência da prancha e histórico."""

    slug: str = "flexao"
    thresholds: PushUpThresholds = field(default_factory=PushUpThresholds)

    #: Vista da câmera. `None` (o default do produto) = **detectar pela geometria**. Fixar um
    #: valor força a vista e desliga a detecção — é o que os testes usam para exercitar um
    #: caminho de cada vez, e o gancho para o dia em que o usuário puder escolher na tela.
    view: View | None = None

    #: Medidas da calibração (SPEC-004). Não entram no cálculo — a feature é uma razão e
    #: cancela a escala. Existem para o relatório.
    baseline: Baseline | None = None

    phase: Phase = Phase.REST
    rep_count: int = 0

    #: A prancha DESTA pessoa: maior altura ombro→pulso vista na sessão. É o denominador de
    #: `depth` no PERFIL, e por isso o número mais importante daquela vista.
    _plank_height: float = 0.0
    #: O topo DESTA pessoa na vista FRONTAL: maior ângulo de cotovelo visto na sessão. Mesmo
    #: papel do `_plank_height`, mesma persistência de dois frames, outra grandeza.
    _top_elbow: float = 0.0
    _last_elbow: float | None = None
    #: Vista já travada, e as amostras que a decidem. Ver `_VIEW_SAMPLES`.
    _view: View | None = None
    _view_samples: deque[float] = field(default_factory=lambda: deque(maxlen=_VIEW_SAMPLES))
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

        # Porteiro de chão das DUAS vistas: a mão no chão fica abaixo do quadril na imagem,
        # porque o quadril está mais longe da lente e um plano que se afasta sobe no quadro.
        wrists_below_hips = wrist_y - hip_y
        no_chao = wrists_below_hips >= self.thresholds.min_wrists_below_hips

        # Encurtamento: ombros largos contra tronco curto = corpo apontando para a lente. É a
        # grandeza que decide a vista, e é razão de duas medidas do MESMO frame — não herda
        # formato de vídeo nem distância de câmera.
        torso_aparente = math.hypot(shoulder_x - hip_x, shoulder_y - hip_y)
        shoulder_span = math.hypot(
            float(points[_LEFT_SHOULDER][0]) - float(points[_RIGHT_SHOULDER][0]),
            float(points[_LEFT_SHOULDER][1]) - float(points[_RIGHT_SHOULDER][1]),
        )
        shoulder_to_torso = shoulder_span / max(torso_aparente, 1e-6)
        view = self._resolve_view(shoulder_to_torso, no_chao=no_chao)

        elbow_angle = self._elbow_angle_view(points)

        if view is View.FRONTAL:
            on_floor = no_chao and shoulder_to_torso >= self.thresholds.min_shoulder_to_torso
        else:
            # Perfil: o porteiro histórico, intacto. `trunk_spread` continua sendo a
            # confirmação certa aqui — de lado o tronco atravessa a imagem na horizontal.
            on_floor = (
                trunk_spread >= self.thresholds.min_trunk_spread
                and hands_to_ground <= self.thresholds.max_hands_to_ground
                and plank_height >= _MIN_PLANK_HEIGHT
            )

        # As referências só crescem, e só crescem COM O PORTEIRO ABERTO. Sem essa segunda
        # condição, a pessoa em pé esperando o countdown fixa uma referência que não é prancha
        # nenhuma — e foi assim que a primeira versão contava braço levantado como flexão.
        #
        # `min` com o frame anterior exige que a medida se sustente por DOIS frames: um único
        # frame em que o modelo errou o ombro inflaria a referência para sempre, e a partir daí
        # nenhuma prancha de verdade voltaria a marcar 1,0. Vale igual para as duas vistas.
        if on_floor:
            anterior = plank_height if self._last_plank_height is None else self._last_plank_height
            candidata = min(plank_height, anterior)
            if candidata > self._plank_height:
                self._plank_height = candidata

            anterior_cotovelo = elbow_angle if self._last_elbow is None else self._last_elbow
            candidato_cotovelo = min(elbow_angle, anterior_cotovelo)
            if candidato_cotovelo > self._top_elbow:
                self._top_elbow = candidato_cotovelo
        self._last_plank_height = plank_height
        self._last_elbow = elbow_angle

        depth = (
            self._frontal_depth(elbow_angle) if view is View.FRONTAL else self._depth(plank_height)
        )

        return {
            "on_floor": on_floor,
            "view": view.value,
            "trunk_spread": trunk_spread,
            "hands_to_ground": hands_to_ground,
            "wrists_below_hips": wrists_below_hips,
            "shoulder_to_torso": shoulder_to_torso,
            # A feature que decide — em qualquer vista, sempre uma fração do topo da PRÓPRIA
            # pessoa. Só o que a alimenta muda.
            "depth": depth,
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

    def _resolve_view(self, shoulder_to_torso: float, *, no_chao: bool) -> View:
        """Que vista é esta — forçada, já travada, ou lida da geometria agora.

        Só amostra frames **no chão**: quem ainda está em pé esperando o countdown tem uma
        geometria que não diz nada sobre de que lado a câmera está, e deixá-la votar foi
        exatamente o tipo de erro que este módulo já pagou uma vez (a referência de prancha
        fixada em pé, na T-106).

        Antes de travar vale o valor instantâneo — com 16× de separação entre as duas vistas,
        um frame já decide, e esperar custaria repetições de quem começa no ritmo.
        """
        if self.view is not None:
            return self.view
        if self._view is not None:
            return self._view

        instantanea = (
            View.FRONTAL
            if shoulder_to_torso >= self.thresholds.frontal_view_ratio
            else View.PROFILE
        )
        if not no_chao:
            return instantanea

        self._view_samples.append(shoulder_to_torso)
        if len(self._view_samples) >= _VIEW_SAMPLES:
            # Mediana, não média: um frame em que o modelo colapsou o tronco levaria a razão a
            # dezenas (medido: máximo 48), e uma média nunca se recuperaria disso.
            mediana = statistics.median(self._view_samples)
            self._view = (
                View.FRONTAL if mediana >= self.thresholds.frontal_view_ratio else View.PROFILE
            )
            return self._view
        return instantanea

    def _depth(self, plank_height: float) -> float:
        """Altura atual como fração da prancha da pessoa. 1.0 = braço estendido."""
        if self._plank_height < _MIN_PLANK_HEIGHT:
            # Sem referência confiável não existe profundidade: devolver 1.0 (= "está na
            # prancha") mantém a FSM em repouso em vez de inventar uma descida.
            return 1.0
        return plank_height / self._plank_height

    def _frontal_depth(self, elbow_angle: float) -> float:
        """Ângulo de cotovelo como fração do topo da pessoa. 1.0 = braço estendido.

        O análogo exato do `_depth` do perfil, e pelo mesmo motivo: dividir pelo topo DESTA
        pessoa cancela o quanto ela estende o braço, o quanto a lente distorce e o tamanho
        dela no quadro. O que sobra é "quanto do seu próprio braço você dobrou".
        """
        if self._top_elbow < _MIN_TOP_ELBOW:
            return 1.0
        return elbow_angle / self._top_elbow

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
        desce, sobe, _ = self._depth_thresholds(feats)
        estavel = ts - self._phase_since_ms >= limiares.min_phase_ms

        if abs(hip_line) > abs(self._worst_hip_line):
            self._worst_hip_line = hip_line

        if self.phase is Phase.REST:
            self._lowest_depth = min(self._lowest_depth, depth)

            if depth < desce and estavel:
                return self._enter(Phase.PEAK, ts)

            # Voltou à prancha sem ter descido o bastante: a tentativa acabou.
            if depth > sobe:
                return self._close_partial_attempt(feats)
            return []

        # Fase EMBAIXO: só interessa voltar à prancha — aí nasce a repetição.
        if depth > sobe and estavel:
            eventos = self._enter(Phase.REST, ts)
            return [*eventos, *self._count_rep(ts, feats)]
        return []

    def _depth_thresholds(self, feats: Features) -> tuple[float, float, float]:
        """`(desce, sobe, rasa)` da vista deste frame.

        Os dois conjuntos existem porque as grandezas são outras — fração de prancha de um
        lado, fração de ângulo de cotovelo do outro —, e um número calibrado numa não
        significa nada na outra.
        """
        limiares = self.thresholds
        if feats.get("view") == View.FRONTAL.value:
            return (
                limiares.frontal_down_depth,
                limiares.frontal_up_depth,
                limiares.frontal_shallow_depth,
            )
        return limiares.down_depth, limiares.up_depth, limiares.shallow_depth

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

    def _count_rep(self, ts: int, feats: Features) -> list[AnalysisEvent]:
        """Fecha a repetição — e, de PERFIL, critica a postura do corpo durante ela.

        A crítica sai JUNTO com a repetição, e não no lugar dela: quadril caído é uma flexão
        que aconteceu e foi mal feita, ao contrário da rep rasa, que é uma flexão que não
        aconteceu. Contar e criticar diz a verdade sobre as duas.

        **De frente o produto se cala, e isso foi medido.** `hip_line` é o desvio do quadril da
        reta ombro→tornozelo, e de frente o tornozelo tem visibilidade 0,09 em 100% dos frames:
        a reta é traçada sobre um ponto que a lente não vê. O resultado, nos dois vídeos reais,
        era o produto acusando `HIPS_SAGGING` **e** `HIPS_PIKED` na mesma série (35 e 17 num
        vídeo, 27 e 23 no outro) — crítica contraditória é crítica inventada, e mandar alguém
        corrigir o quadril com base em ruído é pior que não dizer nada.

        Criticar postura de frente exige uma feature que não dependa do tornozelo. Não existe
        ainda; até existir, a vista frontal conta e não julga.
        """
        self.rep_count += 1
        self._rep_timestamps.append(ts)
        duration_ms = ts - self._rep_started_ms if self._rep_started_ms is not None else 0
        self._rep_started_ms = None

        eventos: list[AnalysisEvent] = [
            RepDetected(rep_count=self.rep_count, phase=Phase.REST, duration_ms=duration_ms)
        ]
        tolerancia = self.thresholds.hip_line_tolerance
        if feats.get("view") != View.FRONTAL.value:
            if self._worst_hip_line > tolerancia:
                eventos.append(self._signal(Code.HIPS_SAGGING, self._worst_hip_line))
            elif self._worst_hip_line < -tolerancia:
                eventos.append(self._signal(Code.HIPS_PIKED, self._worst_hip_line))
        self._worst_hip_line = 0.0
        return eventos

    def _close_partial_attempt(self, feats: Features) -> list[AnalysisEvent]:
        """Fecha uma tentativa incompleta. Só reclama de quem chegou perto."""
        desce, _, rasa = self._depth_thresholds(feats)
        eventos: list[AnalysisEvent] = []

        if desce <= self._lowest_depth <= rasa:
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
        desce, _, _ = self._depth_thresholds(feats)
        return Phase.PEAK if float(feats["depth"]) < desce else Phase.REST

    def ready_pose(self, feats: Features) -> bool:
        """Posição inicial da flexão: prancha alta, braço estendido, corpo em linha.

        `hip_line` só é exigido de PERFIL: ele mede o desvio do quadril da reta ombro→tornozelo,
        e de frente o tornozelo é justamente o landmark que a lente não vê (medido: visibilidade
        0,09 nos dois vídeos frontais do corpus). Cobrar um alinhamento calculado sobre um ponto
        adivinhado seria recusar a posição inicial de quem está exatamente na posição inicial.
        """
        if feats.get("degraded") or not feats.get("on_floor"):
            return False
        _, sobe, _ = self._depth_thresholds(feats)
        if float(feats["depth"]) <= sobe:
            return False
        if feats.get("view") == View.FRONTAL.value:
            return True
        return (
            float(feats["plank_height"]) >= _MIN_PLANK_HEIGHT
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
            # De que lado a câmera ficou. `None` = a sessão nunca teve frame no chão para
            # decidir, o que por si só já explica um relatório vazio.
            "view": (self.view or self._view).value if (self.view or self._view) else None,
        }


@dataclass(frozen=True, slots=True)
class _PushUpSceneHints:
    body_height_range: tuple[float, float]
    frame_anchors: tuple[int, ...]
    posture: Posture = Posture.FLOOR


#: **Âncoras sem o tornozelo, e isso é medição, não conveniência.** Nos dois vídeos frontais do
#: corpus o tornozelo tem visibilidade 0,09 em 100% dos frames — de frente ele é a parte mais
#: longe e mais de esguelha para a lente. Como a regra antiga exigia os quatro âncoras juntos,
#: uma flexão frontal perfeitamente enquadrada disparava "você saiu do quadro" a sessão inteira.
#:
#: O que sobra é o que a lente vê nas DUAS vistas (medido: 0–4% de frames ruins): nariz, ombros,
#: cotovelos, pulsos e quadris. Não por acaso, é também exatamente o conjunto de que a FSM
#: depende — a cena passa a exigir visível o que a contagem precisa medir, que é a única
#: definição de "fora do quadro" que significa alguma coisa.
_PUSHUP_ANCHORS = (
    _LEFT_SHOULDER,
    _RIGHT_SHOULDER,
    _LEFT_ELBOW,
    _RIGHT_ELBOW,
    _LEFT_WRIST,
    _RIGHT_WRIST,
    _LEFT_HIP,
    _RIGHT_HIP,
)

#: Deitado, a distância se mede pela maior separação entre os âncoras (ver `body_height`), e a
#: faixa vem toda de medição com ESTES âncoras:
#:
#: ============================  =============  ==============
#: situação                      extensão       tem de avisar?
#: ============================  =============  ==============
#: perfil, longe demais (t 0,07)  0,078–0,089   sim, "aproxime-se"
#: perfil, limítrofe (t 0,12)     0,133–0,152   —
#: perfil, bem enquadrado (t 0,16) 0,177–0,203  não
#: perfil, colado (t 0,45)        0,499–0,570   não (ver abaixo)
#: frontal, vídeo real v1         0,655–0,792   não
#: frontal, vídeo real v2         0,733–0,953   não
#: ============================  =============  ==============
#:
#: O piso em 0,12 fica no vão entre "longe demais" (0,089) e "bem enquadrado" (0,177), puxado
#: para baixo de propósito: a SPEC-003 manda os limiares errarem para o lado de NÃO avisar, e
#: um aviso falso a cada frame é pior que um conselho a menos. O teto em 1,10 fica acima do
#: frontal mais próximo já medido.
#:
#: **A faixa é larga porque uma faixa só tem de servir às duas vistas**, e o mesmo corpo à
#: mesma distância mede ~3× mais de frente do que de perfil (0,69 contra 0,20). O preço são as
#: duas pontas: não avisa "afaste-se" de perfil, e o "aproxime-se" de perfil só dispara mais
#: longe do que disparava antes. Estreitar isso exige a vista, e a vista só se conhece depois
#: do primeiro frame no chão — enquanto `scene_hints()` for lido uma vez por sessão
#: (`router.py`), não há onde encaixá-la. Ver a Descoberta [A/T-108] no BACKLOG.
_SCENE_HINTS = _PushUpSceneHints(body_height_range=(0.12, 1.10), frame_anchors=_PUSHUP_ANCHORS)

# Literal pelo mesmo motivo dos outros: com `slots=True` o atributo de classe é o descritor.
EXERCISES["flexao"] = PushUpAnalyzer
