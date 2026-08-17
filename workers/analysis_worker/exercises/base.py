"""Interface `ExerciseAnalyzer` — o contrato de todo exercício (SPEC-007).

Um exercício é uma classe com estado de sessão que recebe keypoints canônicos (SPEC-006) e
produz eventos de análise. Nada de I/O aqui dentro: o worker alimenta e publica, o analisador
só raciocina. É isso que permite testar a contagem de repetições com fixtures, sem câmera.

Os eventos produzidos são os payloads do contrato (`workers/shared/events.py`) — o analisador
não monta envelope, porque `session_id`/`seq` são do worker, não dele.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from workers.shared.events import CameraView, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import NormFrame

__all__ = [
    "DEFAULT_FRAME_ANCHORS",
    "EXERCISES",
    "AnalysisEvent",
    "ExerciseAnalyzer",
    "Features",
    "Posture",
    "SceneHints",
    "feed",
    "get_analyzer",
]

#: Âncoras de enquadramento de quem está EM PÉ: ombros e tornozelos (SPEC-003). Mora aqui, e
#: não no validador de cena, porque quem declara âncora é o exercício — e um exercício não pode
#: importar o validador sem inverter a direção da dependência.
DEFAULT_FRAME_ANCHORS: tuple[int, ...] = (11, 12, 27, 28)


class Posture(StrEnum):
    """Em que eixo o corpo se estende durante o exercício (SPEC-003 / SPEC-020 Tier C).

    A validação de cena mede distância pela altura cabeça→tornozelo. Isso vale para quem está
    **em pé** e é falso para quem está **deitado**: uma pessoa em prancha tem cabeça e
    tornozelo quase na mesma altura, a medida dá ~0, e o produto avisaria "aproxime-se" a
    sessão inteira enquanto o enquadramento está perfeito.

    Quem sabe a resposta é o exercício, não o validador — por isso a postura é declarada no
    `scene_hints()` do analisador. É o eixo técnico que a SPEC-020 chama de Tier C.
    """

    #: Corpo na vertical: a distância se lê na altura (o enquadramento de sempre).
    STANDING = "standing"
    #: Corpo na horizontal, celular deitado no chão: a distância se lê na largura.
    FLOOR = "floor"


#: Features de um frame. `bool` entra junto porque sinais como `wrist_above_shoulder` são
#: booleanos por natureza (SPEC-007).
type Features = dict[str, float | bool]

#: O que uma FSM pode emitir num frame. Fim de sessão é do worker/API (SPEC-009), não daqui.
type AnalysisEvent = ExercisePhase | RepDetected | QualitySignal


class SceneHints(Protocol):
    """Faixas ideais de cena declaradas pelo exercício.

    Nasceu como declaração sem consumidor ("Fase Evolução da SPEC-003"); a chegada dos
    exercícios de chão (T-106/T-107) a tornou consumida de verdade — o validador de cena lê
    daqui a postura e a faixa, em vez de aplicar a regra de quem está em pé a todo mundo.
    """

    #: Extensão do corpo como fração do frame. De pé é a ALTURA cabeça→tornozelo; deitado é a
    #: maior distância entre as âncoras (ver `frame_anchors` e `SceneValidator.body_height`).
    body_height_range: tuple[float, float]

    #: Em que eixo o corpo se estende. Ver `Posture`.
    posture: Posture

    #: Landmarks que precisam estar visíveis para a cena valer — e, deitado, também os que
    #: medem a distância. O default histórico (ombros + tornozelos) é a régua de quem está em
    #: pé, e ela **mente** num exercício de chão filmado de frente: medido nos dois vídeos
    #: frontais do corpus, o tornozelo tem visibilidade 0,09 em 100% dos frames, porque é a
    #: parte mais longe e mais de esguelha para a lente. O produto passava a sessão inteira
    #: dizendo "você saiu do quadro" com o enquadramento perfeito.
    #:
    #: Quem sabe quais landmarks importam é o exercício, pela mesma razão que já vale para a
    #: postura: o validador não tem — e não deve ter — tabela de slug nenhuma.
    frame_anchors: tuple[int, ...]


@runtime_checkable
class ExerciseAnalyzer(Protocol):
    """Contrato desde o dia 1 (SPEC-007). Um analisador por sessão — tem estado."""

    slug: str

    def features(self, frame: NormFrame) -> Features:
        """Grandezas do frame que a FSM entende (ângulos, razões, flags)."""
        ...

    def step(self, feats: Features, ts: int) -> list[AnalysisEvent]:
        """Avança a FSM um frame e devolve o que aconteceu. `ts` em epoch ms."""
        ...

    def initial_phase(self, feats: Features) -> Phase:
        """Em que fase a FSM começa, LIDA do primeiro frame utilizável (T-047).

        Está no contrato — e não escondida dentro de cada FSM — porque a alternativa (nascer
        numa fase constante) custou uma repetição de verdade: no `polichinelo-02.mp4` a
        gravação abre com a pessoa já ABERTA, a FSM assumia `CLOSED`, e a primeira abertura
        nunca era aceita porque o debounce exigia estabilidade que o movimento em curso não
        dava. Todo exercício novo tem de responder a esta pergunta antes de contar.

        Regra da resposta: só adotar uma fase que os features afirmem **sem ambiguidade**
        (os mesmos limiares da transição). Frame intermediário ou `degraded` devolve a fase
        de repouso — o palpite errado aqui vira repetição fantasma, e é pior que a rep
        perdida que este método existe para evitar.
        """
        ...

    def ready_pose(self, feats: Features) -> bool:
        """Está na posição inicial? (usado pelo gate de prontidão, SPEC-004 evolução)"""
        ...

    def scene_hints(self) -> SceneHints:
        """Faixas de cena ideais para este exercício (SPEC-003 evolução)."""
        ...

    def summary(self) -> dict[str, object]:
        """Consolidado da sessão para o relatório (SPEC-010)."""
        ...


def feed(analyzer: ExerciseAnalyzer, frame: NormFrame) -> list[AnalysisEvent]:
    """`features` + `step` num passo — o que worker, `evalctl` e testes realmente querem."""
    return analyzer.step(analyzer.features(frame), frame.ts)


#: Exercícios disponíveis por slug. O usuário escolhe o exercício na Fase 0 — nada de detecção
#: automática ainda (SPEC-007).
EXERCISES: dict[str, type[ExerciseAnalyzer]] = {}


def get_analyzer(slug: str, *, view: CameraView | None = None) -> ExerciseAnalyzer:
    """Instancia o analisador de um slug. Slug desconhecido falha alto, não silenciosamente.

    `view` é a vista escolhida por quem treina (T-111), e chega da sessão. **Quem decide se ela
    significa alguma coisa é o exercício**: um analisador que declare o atributo `view` a
    recebe, e os outros a ignoram sem nem saber que ela existe. É de propósito que o
    despacho more aqui e não no `router.py` — a regra auditada da SPEC-007 é que exercício não
    pode obrigar mudança fora de `exercises/`, e um `if slug == "flexao"` no worker seria a
    primeira pedra desse caminho.
    """
    try:
        analyzer_cls = EXERCISES[slug]
    except KeyError:
        disponiveis = ", ".join(sorted(EXERCISES)) or "nenhum"
        raise ValueError(f"exercicio desconhecido: {slug!r} (disponiveis: {disponiveis})") from None
    analyzer = analyzer_cls()
    if view is not None and hasattr(analyzer, "view"):
        analyzer.view = view  # type: ignore[attr-defined]
    return analyzer
