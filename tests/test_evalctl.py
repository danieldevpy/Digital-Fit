"""Testes da bancada de avaliação (T-037 / SPEC-012).

A extração de pose é injetada (extractor falso alimentado por keypoints sintéticos), então
estes testes rodam em milissegundos, sem MediaPipe, sem OpenCV e sem vídeo — que é justamente
o nível 1 da pirâmide da SPEC-012.
"""

import json
import sys
from pathlib import Path

import pytest

from eval.evalctl import build_report, collect_items, load_manifest, main, print_results, run_items
from eval.pipeline import EVAL_SOURCE, analyze_frames, analyze_video, commit_hash
from tests.synthetic_keypoints import (
    jumping_jack_poses,
    sequence,
    session_poses,
    still_poses,
)
from workers.shared.events import Code, Source


class FakeExtractor:
    """Devolve keypoints prontos, um por chamada — o dublê do MediaPipe."""

    def __init__(self, frames) -> None:
        self._frames = list(frames)
        self.closed = False

    def extract(self, image, ts_ms: int, seq: int):
        del image
        if seq >= len(self._frames):
            return None
        raw = self._frames[seq]
        # Respeita o relógio de quem decodificou o vídeo.
        return type(raw)(ts=ts_ms, seq=seq, landmarks=raw.landmarks)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def video_falso(tmp_path: Path, monkeypatch) -> Path:
    """Um arquivo com extensão de vídeo + um leitor falso que devolve N frames."""
    caminho = tmp_path / "jj_frontal.mp4"
    caminho.write_bytes(b"nao-e-um-video-de-verdade")

    def read_video_frames(path, *, target_fps=15.0):
        del path
        intervalo = round(1000 / (target_fps or 30.0))
        for seq in range(600):
            yield object(), seq * intervalo, seq

    monkeypatch.setattr("eval.sources.read_video_frames", read_video_frames)
    return caminho


# --------------------------------------------------------------------------------------
# Pipeline sobre keypoints (o caminho que worker e bancada compartilham)
# --------------------------------------------------------------------------------------


def test_analyze_frames_conta_as_reps_do_video() -> None:
    resultado = analyze_frames(
        sequence(session_poses(jumping_jack_poses(12))), name="jj_12.mp4", expected_reps=12
    )

    assert resultado.reps == 12
    assert resultado.rep_error == 0
    assert resultado.exact is True
    # +1,3 s do countdown: a sessão real inclui a preparação (T-019).
    assert resultado.duration_s == pytest.approx(13.4, abs=0.5)


def test_analyze_frames_reporta_erro_de_contagem() -> None:
    resultado = analyze_frames(sequence(session_poses(jumping_jack_poses(10))), expected_reps=12)

    assert resultado.reps == 10
    assert resultado.rep_error == 2
    assert resultado.exact is False


def test_sem_rotulo_nao_ha_erro_a_calcular() -> None:
    resultado = analyze_frames(sequence(session_poses(jumping_jack_poses(3))))

    assert resultado.rep_error is None
    assert resultado.exact is None


def test_video_negativo_de_pessoa_parada_da_zero_reps() -> None:
    """SPEC-012, critério 4."""
    resultado = analyze_frames(
        sequence(still_poses(300), jitter=0.006), name="negativo_parado.mp4", expected_reps=0
    )

    assert resultado.reps == 0
    assert resultado.exact is True


def test_reps_pregui_osas_aparecem_como_sinais_no_resultado() -> None:
    resultado = analyze_frames(
        sequence(session_poses(jumping_jack_poses(4, amplitude=0.6))), expected_reps=0
    )

    assert resultado.reps == 0
    assert resultado.quality_signals[Code.ARMS_TOO_LOW.value] == 4


def test_resultado_traz_duracoes_e_cadencia() -> None:
    resultado = analyze_frames(
        sequence(session_poses(jumping_jack_poses(5, frames_per_rep=15)), fps=15.0)
    )

    assert len(resultado.rep_durations_ms) == 5
    assert resultado.cadence_rpm == pytest.approx(60.0, rel=0.25)


def test_frames_degradados_sao_contados_no_relatorio() -> None:
    resultado = analyze_frames(sequence(still_poses(20), visibility=0.1))

    assert resultado.frames_degraded == 20
    assert resultado.reps == 0


# --------------------------------------------------------------------------------------
# Critério 2 — bancada e worker usam o MESMO módulo
# --------------------------------------------------------------------------------------


def test_bancada_usa_os_modulos_do_worker() -> None:
    """SPEC-012, critério 2: verificável por import, sem código duplicado."""
    import eval.pipeline as pipeline

    assert pipeline.get_analyzer.__module__.startswith("workers.analysis_worker")
    assert pipeline.Normalizer.__module__ == "workers.shared.normalize"


def test_bancada_declara_origem_file_no_contrato() -> None:
    assert EVAL_SOURCE is Source.FILE
    assert Source("file") is Source.FILE


def test_importar_o_pipeline_nao_puxa_mediapipe_nem_opencv() -> None:
    """`evalctl --help` e os testes não podem pagar 200 MB de dependência."""
    codigo = (
        "import sys; import eval.pipeline, eval.evalctl; "
        "assert 'mediapipe' not in sys.modules, 'mediapipe importado'; "
        "assert 'cv2' not in sys.modules, 'cv2 importado'"
    )
    import subprocess

    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr


# --------------------------------------------------------------------------------------
# Leitura de vídeo (com extractor e leitor injetados)
# --------------------------------------------------------------------------------------


def test_analyze_video_processa_do_arquivo_ate_o_resultado(video_falso: Path) -> None:
    extractor = FakeExtractor(sequence(session_poses(jumping_jack_poses(8))))

    resultado = analyze_video(video_falso, expected_reps=8, extractor=extractor)

    assert resultado.name == "jj_frontal.mp4"
    assert resultado.reps == 8
    assert resultado.exact is True
    assert not extractor.closed, "extractor injetado e fechado por quem o criou"


def test_frames_sem_pose_detectada_sao_contados(video_falso: Path) -> None:
    """Vídeo em que a pessoa sai do quadro: o relatório mostra quantos frames vieram vazios."""
    extractor = FakeExtractor(sequence(session_poses(jumping_jack_poses(3))))

    resultado = analyze_video(video_falso, extractor=extractor)

    assert resultado.frames_no_pose > 0
    assert resultado.frames == len(sequence(session_poses(jumping_jack_poses(3))))


# --------------------------------------------------------------------------------------
# Manifest do corpus
# --------------------------------------------------------------------------------------


def escrever_manifest(directory: Path, conteudo: str) -> Path:
    (directory / "manifest.yaml").write_text(conteudo, encoding="utf-8")
    for nome in ("jj_frontal_boa_luz.mp4", "negativo_parado.mp4"):
        (directory / nome).write_bytes(b"x")
    return directory


def test_manifest_traz_rotulo_e_condicoes(tmp_path: Path) -> None:
    pasta = escrever_manifest(
        tmp_path,
        """
        - file: jj_frontal_boa_luz.mp4
          exercise: jumping_jack
          expected_reps: 20
          conditions: {light: good, distance: 2.5m, angle: frontal}
        - file: negativo_parado.mp4
          expected_reps: 0
        """,
    )

    itens = load_manifest(pasta, default_exercise="jumping_jack")

    assert [item.path.name for item in itens] == [
        "jj_frontal_boa_luz.mp4",
        "negativo_parado.mp4",
    ]
    assert itens[0].expected_reps == 20
    assert itens[0].conditions == {"light": "good", "distance": "2.5m", "angle": "frontal"}
    assert itens[1].exercise == "jumping_jack"  # herda o default
    assert itens[1].expected_reps == 0


def test_pasta_sem_manifest_processa_os_videos_sem_rotulo(tmp_path: Path) -> None:
    (tmp_path / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.mov").write_bytes(b"x")
    (tmp_path / "leia-me.txt").write_text("nao e video")

    itens = load_manifest(tmp_path, default_exercise="jumping_jack")

    assert [item.path.name for item in itens] == ["a.mp4", "b.mov"]
    assert all(item.expected_reps is None for item in itens)


def test_manifest_invalido_falha_com_mensagem_util(tmp_path: Path) -> None:
    (tmp_path / "manifest.yaml").write_text("- sem_o_campo_file: 1", encoding="utf-8")

    with pytest.raises(ValueError, match="entrada invalida"):
        load_manifest(tmp_path, default_exercise="jumping_jack")


def test_collect_items_recusa_arquivo_que_nao_e_video(tmp_path: Path) -> None:
    arquivo = tmp_path / "planilha.xlsx"
    arquivo.write_bytes(b"x")

    with pytest.raises(ValueError, match="nao parece um video"):
        collect_items(arquivo, exercise="jumping_jack", expected_reps=None)


# --------------------------------------------------------------------------------------
# Robustez: um vídeo ruim não derruba o corpus
# --------------------------------------------------------------------------------------


def test_video_inexistente_vira_erro_no_relatorio(tmp_path: Path) -> None:
    itens = collect_items(tmp_path, exercise="jumping_jack", expected_reps=None)
    itens = [*itens, *collect_items(tmp_path, exercise="jumping_jack", expected_reps=None)]
    from eval.evalctl import CorpusItem

    resultados = run_items(
        [CorpusItem(path=tmp_path / "fantasma.mp4", exercise="jumping_jack")], target_fps=15.0
    )

    assert resultados[0].error == "arquivo nao encontrado"
    assert resultados[0].reps == 0


def test_falha_de_leitura_nao_interrompe_os_demais(tmp_path: Path, monkeypatch) -> None:
    from eval.evalctl import CorpusItem

    bom = tmp_path / "bom.mp4"
    ruim = tmp_path / "ruim.mp4"
    for caminho in (bom, ruim):
        caminho.write_bytes(b"x")

    def read_video_frames(path, *, target_fps=15.0):
        del target_fps
        if Path(path).name == "ruim.mp4":
            raise ValueError("nao foi possivel abrir o video")
        for seq in range(200):
            yield object(), seq * 66, seq

    monkeypatch.setattr("eval.sources.read_video_frames", read_video_frames)

    resultados = run_items(
        [
            CorpusItem(path=ruim, exercise="jumping_jack"),
            CorpusItem(path=bom, exercise="jumping_jack", expected_reps=5),
        ],
        target_fps=15.0,
        extractor=FakeExtractor(sequence(session_poses(jumping_jack_poses(5)))),
    )

    assert "nao foi possivel abrir" in (resultados[0].error or "")
    assert resultados[1].reps == 5
    assert resultados[1].error is None


def test_exercicio_desconhecido_e_reportado_por_video(tmp_path: Path, monkeypatch) -> None:
    from eval.evalctl import CorpusItem

    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    monkeypatch.setattr(
        "eval.sources.read_video_frames",
        lambda path, *, target_fps=15.0: iter([(object(), 0, 0)]),
    )

    resultados = run_items(
        [CorpusItem(path=video, exercise="levitacao")],
        target_fps=15.0,
        extractor=FakeExtractor(sequence(still_poses(1))),
    )

    assert "exercicio desconhecido" in (resultados[0].error or "")


# --------------------------------------------------------------------------------------
# Relatório e CLI
# --------------------------------------------------------------------------------------


def test_relatorio_carrega_versao_commit_e_modelo() -> None:
    relatorio = build_report(
        [analyze_frames(sequence(session_poses(jumping_jack_poses(2))))], target_fps=15.0
    )

    assert relatorio["tool"] == "evalctl"
    assert relatorio["report_version"] == 1
    assert relatorio["commit"] == commit_hash()
    assert "mediapipe" in str(relatorio["model"])
    assert relatorio["params"] == {"target_fps": 15.0}
    assert len(relatorio["videos"]) == 1


def test_relatorio_e_json_serializavel() -> None:
    relatorio = build_report(
        [analyze_frames(sequence(session_poses(jumping_jack_poses(2))))], target_fps=None
    )

    texto = json.dumps(relatorio)

    assert json.loads(texto)["videos"][0]["reps"] == 2


def test_cli_run_escreve_o_eval_json(tmp_path: Path, monkeypatch, capsys) -> None:
    video = tmp_path / "jj.mp4"
    video.write_bytes(b"x")
    monkeypatch.setattr(
        "eval.sources.read_video_frames",
        lambda path, *, target_fps=15.0: ((object(), seq * 66, seq) for seq in range(200)),
    )
    monkeypatch.setattr(
        "eval.sources.MediaPipeExtractor",
        lambda **kwargs: FakeExtractor(sequence(session_poses(jumping_jack_poses(6)))),
    )
    destino = tmp_path / "out" / "eval.json"

    codigo = main(["run", str(video), "--expected-reps", "6", "--report", str(destino)])

    assert codigo == 0
    relatorio = json.loads(destino.read_text(encoding="utf-8"))
    assert relatorio["videos"][0]["reps"] == 6
    assert relatorio["videos"][0]["exact"] is True
    assert "jj.mp4" in capsys.readouterr().out


def test_cli_run_em_pasta_vazia_reclama(tmp_path: Path, capsys) -> None:
    codigo = main(["run", str(tmp_path)])

    assert codigo == 1
    assert "nenhum video encontrado" in capsys.readouterr().err


def test_cli_com_alvo_invalido_retorna_codigo_dois(tmp_path: Path, capsys) -> None:
    arquivo = tmp_path / "doc.pdf"
    arquivo.write_bytes(b"x")

    codigo = main(["run", str(arquivo)])

    assert codigo == 2
    assert "nao parece um video" in capsys.readouterr().err


def test_fps_zero_significa_todos_os_frames(tmp_path: Path, monkeypatch) -> None:
    """`--fps 0` desliga a decimação; o relatório tem de refletir isso."""
    video = tmp_path / "jj.mp4"
    video.write_bytes(b"x")
    vistos: list[float | None] = []

    def read_video_frames(path, *, target_fps=15.0):
        vistos.append(target_fps)
        return iter(())

    monkeypatch.setattr("eval.sources.read_video_frames", read_video_frames)
    monkeypatch.setattr("eval.sources.MediaPipeExtractor", lambda **kwargs: FakeExtractor([]))

    main(["run", str(video), "--fps", "0", "--quiet"])

    assert vistos == [None]


def test_tabela_mostra_erro_por_video(capsys) -> None:
    resultados = [
        analyze_frames(
            sequence(session_poses(jumping_jack_poses(20))), name="jj_bom.mp4", expected_reps=20
        ),
        analyze_frames(
            sequence(session_poses(jumping_jack_poses(2, amplitude=0.6))),
            name="jj_lento.mp4",
            expected_reps=2,
        ),
    ]

    print_results(resultados)

    saida = capsys.readouterr().out
    assert "jj_bom.mp4" in saida
    assert Code.ARMS_TOO_LOW.value in saida
