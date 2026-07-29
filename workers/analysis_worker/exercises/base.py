"""Interface `ExerciseAnalyzer` — o contrato de todo exercício (SPEC-007).

Um exercício é uma classe com estado de sessão que recebe keypoints canônicos (SPEC-006) e
produz eventos de análise. Nada de I/O aqui dentro: o worker alimenta e publica, o analisador
só raciocina. É isso que permite testar a contagem de repetições com fixtures, sem câmera.

Os eventos produzidos são os payloads do contrato (`workers/shared/events.py`) — o analisador
não monta envelope, porque `session_id`/`seq` são do worker, não dele.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from workers.shared.events import ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import NormFrame

__all__ = [
    "EXERCISES",
    "AnalysisEvent",
    "ExerciseAnalyzer",
    "Features",
    "SceneHints",
    "feed",
    "get_analyzer",
]

#: Features de um frame. `bool` entra junto porque sinais como `wrist_above_shoulder` são
#: booleanos por natureza (SPEC-007).
type Features = dict[str, float | bool]

#: O que uma FSM pode emitir num frame. Fim de sessão é do worker/API (SPEC-009), não daqui.
type AnalysisEvent = ExercisePhase | RepDetected | QualitySignal


class SceneHints(Protocol):
    """Faixas ideais de cena declaradas pelo exercício.

    Consumido de verdade na Fase Evolução da SPEC-003 (distância ótima por exercício); existe
    desde já para que o analisador seja a fonte dessa informação, e não uma tabela solta.
    """

    #: Altura do corpo (cabeça→tornozelo) como fração da altura do frame.
    body_height_range: tuple[float, float]


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


def get_analyzer(slug: str) -> ExerciseAnalyzer:
    """Instancia o analisador de um slug. Slug desconhecido falha alto, não silenciosamente."""
    try:
        analyzer_cls = EXERCISES[slug]
    except KeyError:
        disponiveis = ", ".join(sorted(EXERCISES)) or "nenhum"
        raise ValueError(f"exercicio desconhecido: {slug!r} (disponiveis: {disponiveis})") from None
    return analyzer_cls()
