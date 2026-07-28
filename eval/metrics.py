"""Métricas agregadas e comparação entre execuções (SPEC-012, T-039).

Duas perguntas que a bancada precisa responder:

1. *"Quão boa está a contagem hoje?"* → `aggregate()`: MAE de reps, % de vídeos exatos, taxa de
   falso positivo nos negativos e a quebra por condição de gravação (é a tabela que mostra
   "contraluz derruba a acurácia em X%").
2. *"Minha mudança melhorou ou piorou?"* → `compare()`: por vídeo e no agregado, com regressão
   explícita. Mudou o filtro? Roda o corpus e vê o impacto.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Comparison", "Metrics", "aggregate", "compare", "format_comparison", "format_metrics"]


@dataclass(slots=True)
class Metrics:
    """Agregado de um conjunto de vídeos. `None` onde não há rótulo para comparar."""

    videos: int = 0
    labeled: int = 0
    errors: int = 0
    total_reps: int = 0
    total_expected: int = 0
    reps_mae: float | None = None
    exact_rate: float | None = None
    false_positive_rate: float | None = None
    by_condition: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "videos": self.videos,
            "labeled": self.labeled,
            "errors": self.errors,
            "total_reps": self.total_reps,
            "total_expected": self.total_expected,
            "reps_mae": self.reps_mae,
            "exact_rate": self.exact_rate,
            "false_positive_rate": self.false_positive_rate,
            "by_condition": self.by_condition,
        }


def _valid(videos: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Vídeos que rodaram (falha de leitura não polui métrica de acurácia)."""
    return [video for video in videos if not video.get("error")]


def _labeled(videos: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [video for video in _valid(videos) if video.get("expected_reps") is not None]


def _slice_metrics(videos: list[dict[str, Any]]) -> dict[str, Any]:
    """Métricas resumidas de um subconjunto — usado na quebra por condição."""
    rotulados = _labeled(videos)
    erros = [abs(video["reps"] - video["expected_reps"]) for video in rotulados]
    return {
        "videos": len(videos),
        "labeled": len(rotulados),
        "reps_mae": round(sum(erros) / len(erros), 3) if erros else None,
        "exact_rate": (
            round(sum(1 for erro in erros if erro == 0) / len(erros), 3) if erros else None
        ),
    }


def aggregate(videos: list[dict[str, Any]]) -> Metrics:
    """Métricas do relatório inteiro (aceita os dicts de `VideoResult.to_dict()`)."""
    validos = _valid(videos)
    rotulados = _labeled(videos)
    erros = [abs(video["reps"] - video["expected_reps"]) for video in rotulados]

    # Negativo = vídeo rotulado com 0 reps (outro exercício, pessoa parada). Contar qualquer
    # coisa nele é falso positivo — a métrica que impede "melhorar" a contagem inflando reps.
    negativos = [video for video in rotulados if video["expected_reps"] == 0]
    falsos_positivos = [video for video in negativos if video["reps"] > 0]

    chaves_de_condicao = {chave for video in validos for chave in (video.get("conditions") or {})}
    by_condition: dict[str, dict[str, dict[str, Any]]] = {}
    for chave in sorted(chaves_de_condicao):
        grupos: dict[str, list[dict[str, Any]]] = {}
        for video in validos:
            valor = (video.get("conditions") or {}).get(chave)
            if valor is None:
                continue
            grupos.setdefault(str(valor), []).append(video)
        by_condition[chave] = {
            valor: _slice_metrics(grupo) for valor, grupo in sorted(grupos.items())
        }

    return Metrics(
        videos=len(videos),
        labeled=len(rotulados),
        errors=len(videos) - len(validos),
        total_reps=sum(video["reps"] for video in validos),
        total_expected=sum(video["expected_reps"] for video in rotulados),
        reps_mae=round(sum(erros) / len(erros), 3) if erros else None,
        exact_rate=(
            round(sum(1 for erro in erros if erro == 0) / len(erros), 3) if erros else None
        ),
        false_positive_rate=(
            round(len(falsos_positivos) / len(negativos), 3) if negativos else None
        ),
        by_condition=by_condition,
    )


@dataclass(slots=True)
class Comparison:
    """Diferença entre dois relatórios. `regressions` é o que faz o build falhar (T-042)."""

    videos: list[dict[str, Any]] = field(default_factory=list)
    metrics_before: dict[str, Any] = field(default_factory=dict)
    metrics_after: dict[str, Any] = field(default_factory=dict)
    regressions: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    only_in_before: list[str] = field(default_factory=list)
    only_in_after: list[str] = field(default_factory=list)

    @property
    def regressed(self) -> bool:
        return bool(self.regressions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "videos": self.videos,
            "metrics_before": self.metrics_before,
            "metrics_after": self.metrics_after,
            "regressions": self.regressions,
            "improvements": self.improvements,
            "only_in_before": self.only_in_before,
            "only_in_after": self.only_in_after,
            "regressed": self.regressed,
        }


def compare(before: dict[str, Any], after: dict[str, Any]) -> Comparison:
    """Compara dois `eval.json`.

    Regressão é definida pelo **erro de contagem** de cada vídeo rotulado (e por vídeo que
    passou a falhar). Vídeo sem rótulo não pode gerar veredito — só se registra que mudou.
    """
    antes = {video["name"]: video for video in before.get("videos", [])}
    depois = {video["name"]: video for video in after.get("videos", [])}
    comuns = [nome for nome in depois if nome in antes]

    comparacao = Comparison(
        metrics_before=aggregate(list(antes.values())).to_dict(),
        metrics_after=aggregate(list(depois.values())).to_dict(),
        only_in_before=sorted(set(antes) - set(depois)),
        only_in_after=sorted(set(depois) - set(antes)),
    )

    for nome in sorted(comuns):
        a, b = antes[nome], depois[nome]
        linha: dict[str, Any] = {
            "name": nome,
            "reps_before": a.get("reps"),
            "reps_after": b.get("reps"),
            "reps_delta": (b.get("reps") or 0) - (a.get("reps") or 0),
            "expected_reps": b.get("expected_reps"),
            "error_before": a.get("rep_error"),
            "error_after": b.get("rep_error"),
            "status": "igual",
        }

        if b.get("error") and not a.get("error"):
            linha["status"] = "quebrou"
            comparacao.regressions.append(nome)
        elif a.get("error") and not b.get("error"):
            linha["status"] = "voltou a rodar"
            comparacao.improvements.append(nome)
        elif linha["error_before"] is not None and linha["error_after"] is not None:
            if linha["error_after"] > linha["error_before"]:
                linha["status"] = "pior"
                comparacao.regressions.append(nome)
            elif linha["error_after"] < linha["error_before"]:
                linha["status"] = "melhor"
                comparacao.improvements.append(nome)
        elif linha["reps_delta"] != 0:
            linha["status"] = "mudou (sem rotulo)"

        comparacao.videos.append(linha)

    return comparacao


def format_metrics(metrics: Metrics) -> str:
    """Bloco legível das métricas agregadas."""
    linhas = [
        f"videos: {metrics.videos} (rotulados: {metrics.labeled}, com erro: {metrics.errors})",
        f"reps: {metrics.total_reps} contadas / {metrics.total_expected} esperadas",
        f"MAE de reps: {_num(metrics.reps_mae)}",
        f"videos exatos: {_pct(metrics.exact_rate)}",
        f"falso positivo em negativos: {_pct(metrics.false_positive_rate)}",
    ]
    for chave, grupos in metrics.by_condition.items():
        linhas.append(f"\npor {chave}:")
        for valor, resumo in grupos.items():
            linhas.append(
                f"  {valor:<12} videos={resumo['videos']:<3} "
                f"MAE={_num(resumo['reps_mae'])} exatos={_pct(resumo['exact_rate'])}"
            )
    return "\n".join(linhas)


def format_comparison(comparacao: Comparison) -> str:
    """Tabela do `compare`: por vídeo e o veredito no fim."""
    largura = max((len(linha["name"]) for linha in comparacao.videos), default=10)
    cabecalho = f"{'video'.ljust(largura)}  {'antes':>6} {'depois':>6} {'delta':>6}  status"
    linhas = [cabecalho, "-" * len(cabecalho)]
    for linha in comparacao.videos:
        linhas.append(
            f"{linha['name'].ljust(largura)}  {linha['reps_before']!s:>6} "
            f"{linha['reps_after']!s:>6} {linha['reps_delta']:>+6}  {linha['status']}"
        )

    antes = comparacao.metrics_before
    depois = comparacao.metrics_after
    linhas.append("")
    linhas.append(
        f"MAE: {_num(antes.get('reps_mae'))} -> {_num(depois.get('reps_mae'))} | "
        f"exatos: {_pct(antes.get('exact_rate'))} -> {_pct(depois.get('exact_rate'))}"
    )
    if comparacao.only_in_after:
        linhas.append(f"novos no relatorio: {', '.join(comparacao.only_in_after)}")
    if comparacao.only_in_before:
        linhas.append(f"ausentes agora: {', '.join(comparacao.only_in_before)}")
    if comparacao.regressed:
        linhas.append(f"REGRESSAO em: {', '.join(comparacao.regressions)}")
    else:
        linhas.append("sem regressao")
    if comparacao.improvements:
        linhas.append(f"melhorou em: {', '.join(comparacao.improvements)}")
    return "\n".join(linhas)


def _num(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.3f}"


def _pct(valor: float | None) -> str:
    return "-" if valor is None else f"{valor * 100:.1f}%"
