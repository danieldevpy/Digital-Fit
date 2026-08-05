"""Um módulo por exercício, cada um implementando `ExerciseAnalyzer` (SPEC-007).

Exercício novo entra aqui e em mais lugar nenhum — se precisar mexer fora desta pasta, a
interface está errada (SPEC-007, notas técnicas).
"""

from workers.analysis_worker.exercises.abdominal import CrunchAnalyzer, CrunchThresholds
from workers.analysis_worker.exercises.base import (
    EXERCISES,
    AnalysisEvent,
    ExerciseAnalyzer,
    Features,
    Posture,
    SceneHints,
    feed,
    get_analyzer,
)
from workers.analysis_worker.exercises.flexao import PushUpAnalyzer, PushUpThresholds
from workers.analysis_worker.exercises.jumping_jack import (
    JumpingJackAnalyzer,
    JumpingJackThresholds,
)
from workers.analysis_worker.exercises.squat import SquatAnalyzer, SquatThresholds

__all__ = [
    "EXERCISES",
    "AnalysisEvent",
    "CrunchAnalyzer",
    "CrunchThresholds",
    "ExerciseAnalyzer",
    "Features",
    "JumpingJackAnalyzer",
    "JumpingJackThresholds",
    "Posture",
    "PushUpAnalyzer",
    "PushUpThresholds",
    "SceneHints",
    "SquatAnalyzer",
    "SquatThresholds",
    "feed",
    "get_analyzer",
]
