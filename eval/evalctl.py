"""`evalctl` — bancada de avaliação por linha de comando (SPEC-012).

Roda o pipeline de verdade (normalização + FSM dos workers) sobre vídeos, sem sistema no ar::

    uv run --extra eval python -m eval.evalctl run video.mp4 --exercise jumping_jack
    uv run --extra eval python -m eval.evalctl run eval/corpus/ --report eval/out/eval.json

Com um `manifest.yaml` na pasta do corpus (SPEC-012), cada vídeo já vem com `expected_reps` e
condições de gravação, e o relatório mostra o erro de contagem por vídeo.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from eval.metrics import aggregate, compare, format_comparison, format_metrics
from eval.pipeline import VideoResult, analyze_video, commit_hash

__all__ = ["main"]

REPORT_VERSION = 1
VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")
MANIFEST_NAMES = ("manifest.yaml", "manifest.yml")


@dataclass(frozen=True, slots=True)
class CorpusItem:
    """Um vídeo do corpus, com o rótulo que o manifest declarou."""

    path: Path
    exercise: str
    expected_reps: int | None = None
    conditions: dict[str, object] | None = None


def load_manifest(directory: Path, *, default_exercise: str) -> list[CorpusItem]:
    """Lê `manifest.yaml`; sem manifest, cai para "todos os vídeos da pasta, sem rótulo"."""
    manifest = next(
        (directory / nome for nome in MANIFEST_NAMES if (directory / nome).exists()), None
    )
    if manifest is None:
        return [
            CorpusItem(path=caminho, exercise=default_exercise)
            for caminho in sorted(directory.iterdir())
            if caminho.suffix.lower() in VIDEO_SUFFIXES
        ]

    import yaml  # import tardio: só o corpus precisa de PyYAML

    entradas = yaml.safe_load(manifest.read_text(encoding="utf-8")) or []
    itens: list[CorpusItem] = []
    for entrada in entradas:
        if not isinstance(entrada, dict) or "file" not in entrada:
            raise ValueError(f"entrada invalida em {manifest}: {entrada!r}")
        itens.append(
            CorpusItem(
                path=directory / str(entrada["file"]),
                exercise=str(entrada.get("exercise", default_exercise)),
                expected_reps=(
                    int(entrada["expected_reps"])
                    if entrada.get("expected_reps") is not None
                    else None
                ),
                conditions=dict(entrada.get("conditions") or {}),
            )
        )
    return itens


def collect_items(target: Path, *, exercise: str, expected_reps: int | None) -> list[CorpusItem]:
    """Resolve o alvo do comando: um vídeo ou uma pasta de corpus."""
    if target.is_dir():
        return load_manifest(target, default_exercise=exercise)
    if target.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError(f"nao parece um video: {target}")
    return [CorpusItem(path=target, exercise=exercise, expected_reps=expected_reps)]


def run_items(
    itens: list[CorpusItem],
    *,
    target_fps: float | None,
    model_path: Path | None = None,
    save_keypoints: Path | None = None,
    calibrate: bool = True,
    extractor=None,
) -> list[VideoResult]:
    """Processa cada item, isolando falhas: um vídeo corrompido não derruba o corpus."""
    resultados: list[VideoResult] = []
    for item in itens:
        if not item.path.exists():
            resultados.append(
                VideoResult(
                    name=item.path.name,
                    exercise=item.exercise,
                    reps=0,
                    expected_reps=item.expected_reps,
                    conditions=dict(item.conditions or {}),
                    error="arquivo nao encontrado",
                )
            )
            continue
        try:
            keypoints: list | None = [] if save_keypoints else None
            resultados.append(
                analyze_video(
                    item.path,
                    exercise=item.exercise,
                    expected_reps=item.expected_reps,
                    conditions=item.conditions,
                    target_fps=target_fps,
                    model_path=model_path,
                    extractor=extractor,
                    keypoints_sink=keypoints,
                    calibrate=calibrate,
                )
            )
            if save_keypoints and keypoints:
                _write_fixture(save_keypoints, item, keypoints, target_fps=target_fps)
        except Exception as exc:  # a bancada reporta a falha, não morre com ela
            resultados.append(
                VideoResult(
                    name=item.path.name,
                    exercise=item.exercise,
                    reps=0,
                    expected_reps=item.expected_reps,
                    conditions=dict(item.conditions or {}),
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return resultados


def _write_fixture(
    directory: Path, item: CorpusItem, keypoints: list, *, target_fps: float | None
) -> Path:
    """Exporta os keypoints do vídeo como fixture de nível 1 (SPEC-012, critério 3)."""
    from workers.shared.keypoints import KeypointFixture, save_fixture

    fixture = KeypointFixture(
        label=item.path.stem,
        frames=keypoints,
        exercise=item.exercise,
        expected_reps=item.expected_reps,
        source="file",
        fps=target_fps,
        notes=f"extraido de {item.path.name} por evalctl",
        conditions=dict(item.conditions or {}),
    )
    return save_fixture(Path(directory) / f"{item.path.stem}.json", fixture)


def build_report(resultados: list[VideoResult], *, target_fps: float | None) -> dict[str, object]:
    """Relatório versionado, com a versão do código e do modelo (SPEC-012, notas técnicas)."""
    videos = [resultado.to_dict() for resultado in resultados]
    return {
        "tool": "evalctl",
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit_hash(),
        "model": _model_version(),
        "params": {"target_fps": target_fps},
        "metrics": aggregate(videos).to_dict(),
        "videos": videos,
    }


def _model_version() -> str:
    try:
        import mediapipe

        return f"mediapipe {getattr(mediapipe, '__version__', 'desconhecida')} (pose lite)"
    except ImportError:
        return "mediapipe ausente"


def print_results(resultados: list[VideoResult], stream=None) -> None:
    """Tabela legível: é o que se olha enquanto o corpus roda.

    `stream` é resolvido na chamada, não no import: assim redirecionar `sys.stdout` (teste,
    pipe, log) funciona de verdade.
    """
    stream = stream or sys.stdout
    largura = max((len(r.name) for r in resultados), default=10)
    cabecalho = f"{'video'.ljust(largura)}  {'reps':>5} {'espe':>5} {'erro':>5}  sinais"
    print(cabecalho, file=stream)
    print("-" * len(cabecalho), file=stream)
    for resultado in resultados:
        if resultado.error:
            print(f"{resultado.name.ljust(largura)}  {'ERRO':>5}  {resultado.error}", file=stream)
            continue
        esperado = "-" if resultado.expected_reps is None else str(resultado.expected_reps)
        erro = "-" if resultado.rep_error is None else str(resultado.rep_error)
        sinais = (
            ", ".join(
                f"{codigo} x{contagem}" for codigo, contagem in resultado.quality_signals.items()
            )
            or "-"
        )
        linha = f"{resultado.name.ljust(largura)}  {resultado.reps:>5} {esperado:>5} {erro:>5}"
        print(f"{linha}  {sinais}", file=stream)


def cmd_run(args: argparse.Namespace) -> int:
    itens = collect_items(
        Path(args.target), exercise=args.exercise, expected_reps=args.expected_reps
    )
    if not itens:
        print(f"nenhum video encontrado em {args.target}", file=sys.stderr)
        return 1

    resultados = run_items(
        itens,
        target_fps=args.fps,
        model_path=Path(args.model) if getattr(args, "model", None) else None,
        save_keypoints=Path(args.save_keypoints) if args.save_keypoints else None,
        calibrate=not args.no_calibrate,
    )
    if not args.quiet:
        print_results(resultados)
        print()
        print(format_metrics(aggregate([resultado.to_dict() for resultado in resultados])))

    if args.report:
        destino = Path(args.report)
        destino.parent.mkdir(parents=True, exist_ok=True)
        relatorio = build_report(resultados, target_fps=args.fps)
        destino.write_text(json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8")
        if not args.quiet:
            print(f"\nrelatorio: {destino}")

    # Falha de leitura é erro de execução; contagem errada não é (isso é métrica, T-039).
    return 1 if any(resultado.error for resultado in resultados) else 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compara dois relatórios. Código 1 = regressão (é o gate da T-042 em CI)."""
    antes = json.loads(Path(args.before).read_text(encoding="utf-8"))
    depois = json.loads(Path(args.after).read_text(encoding="utf-8"))
    comparacao = compare(antes, depois)

    if not args.quiet:
        print(format_comparison(comparacao))
    if args.report:
        destino = Path(args.report)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(comparacao.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if not args.quiet:
            print(f"\ncomparacao: {destino}")

    return 1 if comparacao.regressed else 0


def cmd_parity(args: argparse.Namespace) -> int:
    """Paridade edge x cloud (T-018). Código 1 = fora da tolerância da SPEC-005."""
    from eval.parity import compare_paths, load_browser_result

    alvo = Path(args.video)
    if not alvo.exists():
        print(f"video nao encontrado: {alvo}", file=sys.stderr)
        return 2

    navegador = None
    if args.browser:
        origem = Path(args.browser)
        if not origem.exists():
            print(f"json do navegador nao encontrado: {origem}", file=sys.stderr)
            return 2
        try:
            navegador = load_browser_result(origem)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    resultado = compare_paths(
        alvo,
        exercise=args.exercise,
        expected_reps=args.expected_reps,
        model_path=Path(args.model) if args.model else None,
        browser=navegador,
    )

    if not args.quiet:
        print(resultado.summary_line())
        print(
            f"  frames: edge={resultado.edge.frames} cloud={resultado.cloud.frames} "
            f"| sem pose: edge={resultado.edge.frames_no_pose} "
            f"cloud={resultado.cloud.frames_no_pose}"
        )
        if banda := resultado.bandwidth_line():
            print(banda)

    if args.report:
        destino = Path(args.report)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(resultado.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if not args.quiet:
            print(f"relatorio: {destino}")

    return 0 if resultado.passed else 1


def cmd_fetch_model(args: argparse.Namespace) -> int:
    """Baixa o modelo de pose. Passo explícito: a bancada nunca sai buscando rede sozinha."""
    from eval.sources import MODEL_URL, download_model

    destino = download_model(Path(args.output) if args.output else None)
    tamanho_mb = destino.stat().st_size / 1_048_576
    print(f"modelo salvo em {destino} ({tamanho_mb:.1f} MB)\norigem: {MODEL_URL}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalctl", description="Bancada de avaliacao do Digital Fit (SPEC-012)"
    )
    subcomandos = parser.add_subparsers(dest="comando", required=True)

    run = subcomandos.add_parser("run", help="processa um video ou um corpus")
    run.add_argument("target", help="arquivo de video ou pasta com manifest.yaml")
    run.add_argument("--exercise", default="jumping_jack", help="slug do exercicio")
    run.add_argument(
        "--expected-reps", type=int, default=None, help="rotulo de reps (so para 1 video)"
    )
    run.add_argument("--fps", type=float, default=15.0, help="fps de processamento (0 = todos)")
    run.add_argument("--report", default=None, help="caminho do eval.json")
    run.add_argument("--quiet", action="store_true", help="sem tabela no stdout")
    run.add_argument(
        "--no-calibrate",
        action="store_true",
        help="pula a calibracao (SPEC-004); util para comparar com o pipeline anterior",
    )
    run.add_argument("--model", default=None, help="caminho do .task do Pose Landmarker")
    run.add_argument(
        "--save-keypoints",
        default=None,
        metavar="DIR",
        help="exporta os keypoints de cada video como fixture de nivel 1",
    )
    run.set_defaults(func=cmd_run)

    comparar = subcomandos.add_parser(
        "compare", help="compara dois eval.json (codigo 1 se houver regressao)"
    )
    comparar.add_argument("before", help="eval.json de referencia")
    comparar.add_argument("after", help="eval.json novo")
    comparar.add_argument("--report", default=None, help="grava a comparacao em JSON")
    comparar.add_argument("--quiet", action="store_true", help="sem tabela no stdout")
    comparar.set_defaults(func=cmd_compare)

    paridade = subcomandos.add_parser(
        "parity",
        help="paridade edge x cloud no mesmo video (codigo 1 se fora da tolerancia)",
    )
    paridade.add_argument("video", help="arquivo de video")
    paridade.add_argument("--exercise", default="jumping_jack", help="slug do exercicio")
    paridade.add_argument("--expected-reps", type=int, default=None, help="rotulo de reps")
    paridade.add_argument("--report", default=None, help="grava o resultado em JSON")
    paridade.add_argument("--quiet", action="store_true", help="sem saida no stdout")
    paridade.add_argument("--model", default=None, help="caminho do .task do Pose Landmarker")
    paridade.add_argument(
        "--browser",
        default=None,
        help="JSON exportado pelo painel de dev do cliente (T-040): entra como 3a perna",
    )
    paridade.set_defaults(func=cmd_parity)

    fetch = subcomandos.add_parser(
        "fetch-model", help="baixa o modelo pose_landmarker_lite.task (uma vez)"
    )
    fetch.add_argument("--output", default=None, help="destino do arquivo .task")
    fetch.set_defaults(func=cmd_fetch_model)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # `--fps 0` = processar todos os frames do vídeo (sem decimação).
    if getattr(args, "fps", None) is not None and args.fps <= 0:
        args.fps = None
    try:
        return int(args.func(args))
    except (ValueError, OSError) as exc:
        print(f"evalctl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
