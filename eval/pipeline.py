"""Pipeline da bancada: frames → normalização → FSM → resultado (SPEC-012).

**Os módulos são os mesmos do worker** — `workers.shared.normalize` e
`workers.analysis_worker.exercises`. Zero reimplementação: se o harness passa, o worker passa
(SPEC-012, critério 2). A única diferença é a origem dos frames (`source: "file"`).
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from workers.analysis_worker.exercises import feed, get_analyzer
from workers.shared.events import RepDetected, Source
from workers.shared.normalize import Baseline, Normalizer, NormParams, RawFrame

__all__ = ["VideoResult", "analyze_frames", "analyze_video", "commit_hash"]

#: Toda a bancada declara esta origem: um resultado de eval nunca se disfarça de sessão real.
EVAL_SOURCE = Source.FILE


@dataclass(slots=True)
class VideoResult:
    """Resultado de um vídeo (ou de uma fixture) processado pela bancada."""

    name: str
    exercise: str
    reps: int
    expected_reps: int | None = None
    frames: int = 0
    frames_no_pose: int = 0
    frames_degraded: int = 0
    duration_s: float = 0.0
    quality_signals: dict[str, int] = field(default_factory=dict)
    rep_durations_ms: list[int] = field(default_factory=list)
    cadence_rpm: float = 0.0
    conditions: dict[str, object] = field(default_factory=dict)
    error: str | None = None

    @property
    def rep_error(self) -> int | None:
        """Erro absoluto de contagem, quando há rótulo."""
        if self.expected_reps is None:
            return None
        return abs(self.reps - self.expected_reps)

    @property
    def exact(self) -> bool | None:
        erro = self.rep_error
        return None if erro is None else erro == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "exercise": self.exercise,
            "reps": self.reps,
            "expected_reps": self.expected_reps,
            "rep_error": self.rep_error,
            "exact": self.exact,
            "frames": self.frames,
            "frames_no_pose": self.frames_no_pose,
            "frames_degraded": self.frames_degraded,
            "duration_s": round(self.duration_s, 2),
            "cadence_rpm": self.cadence_rpm,
            "quality_signals": self.quality_signals,
            "rep_durations_ms": self.rep_durations_ms,
            "conditions": self.conditions,
            "error": self.error,
        }


def analyze_frames(
    frames: Iterable[RawFrame],
    *,
    exercise: str = "jumping_jack",
    name: str = "frames",
    expected_reps: int | None = None,
    conditions: dict[str, object] | None = None,
    params: NormParams | None = None,
    baseline: Baseline | None = None,
    frames_no_pose: int = 0,
) -> VideoResult:
    """Roda normalização + FSM sobre keypoints já extraídos.

    É o coração da bancada e o mesmo caminho do `analysis-worker`: quem tem keypoints (fixture,
    vídeo ou replay) chega aqui.
    """
    analyzer = get_analyzer(exercise)
    normalizer = Normalizer(params=params or NormParams(), baseline=baseline)

    primeiro_ts: int | None = None
    ultimo_ts: int | None = None
    duracoes: list[int] = []

    for raw in frames:
        if primeiro_ts is None:
            primeiro_ts = raw.ts
        ultimo_ts = raw.ts
        for evento in feed(analyzer, normalizer.push(raw)):
            if isinstance(evento, RepDetected):
                duracoes.append(evento.duration_ms)
            # Sinais de qualidade já são contabilizados no `summary()` do analisador.

    resumo = analyzer.summary()
    duracao_s = 0.0
    if primeiro_ts is not None and ultimo_ts is not None:
        duracao_s = (ultimo_ts - primeiro_ts) / 1000.0

    return VideoResult(
        name=name,
        exercise=exercise,
        reps=int(resumo["reps"]),
        expected_reps=expected_reps,
        frames=int(resumo["frames"]),
        frames_no_pose=frames_no_pose,
        frames_degraded=int(resumo["frames_degraded"]),
        duration_s=duracao_s,
        quality_signals=dict(resumo["quality_signals"]),
        rep_durations_ms=duracoes,
        cadence_rpm=float(resumo["cadence_rpm"]),
        conditions=dict(conditions or {}),
    )


def analyze_video(
    path: Path,
    *,
    exercise: str = "jumping_jack",
    expected_reps: int | None = None,
    conditions: dict[str, object] | None = None,
    target_fps: float | None = 15.0,
    model_path: Path | None = None,
    extractor=None,
) -> VideoResult:
    """Decodifica o vídeo, extrai pose e roda o pipeline.

    `extractor` existe para os testes injetarem uma fonte falsa; em uso normal, MediaPipe.
    """
    from eval.sources import MediaPipeExtractor, read_video_frames

    proprio = extractor is None
    extractor = extractor or MediaPipeExtractor(model_path=model_path)
    sem_pose = 0
    keypoints: list[RawFrame] = []

    try:
        for imagem, ts_ms, seq in read_video_frames(path, target_fps=target_fps):
            raw = extractor.extract(imagem, ts_ms, seq)
            if raw is None:
                sem_pose += 1
                continue
            keypoints.append(raw)
    finally:
        if proprio:
            extractor.close()

    return analyze_frames(
        keypoints,
        exercise=exercise,
        name=path.name,
        expected_reps=expected_reps,
        conditions=conditions,
        frames_no_pose=sem_pose,
    )


def commit_hash() -> str:
    """Hash do commit atual — o `eval.json` precisa saber a que versão o número pertence."""
    try:
        saida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "desconhecido"
    return saida.stdout.strip() or "desconhecido"
