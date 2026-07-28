"""Métricas agregadas, `evalctl compare` e fixtures de keypoints (T-039 / SPEC-012)."""

import json
from pathlib import Path

import pytest

from eval.evalctl import build_report, main
from eval.metrics import aggregate, compare, format_comparison, format_metrics
from eval.pipeline import analyze_frames
from tests.synthetic_keypoints import jumping_jack_poses, sequence, still_poses
from workers.shared.keypoints import (
    SCHEMA_VERSION,
    KeypointFixture,
    load_fixture,
    save_fixture,
)
from workers.shared.normalize import RawFrame


def video(
    name: str,
    reps: int,
    expected: int | None = None,
    *,
    error: str | None = None,
    **conditions,
) -> dict:
    """Um dict no formato de `VideoResult.to_dict()`, sem precisar processar vídeo."""
    rep_error = None if expected is None else abs(reps - expected)
    return {
        "name": name,
        "exercise": "jumping_jack",
        "reps": reps,
        "expected_reps": expected,
        "rep_error": rep_error,
        "exact": None if rep_error is None else rep_error == 0,
        "conditions": conditions,
        "error": error,
    }


# --------------------------------------------------------------------------------------
# Agregado
# --------------------------------------------------------------------------------------


def test_mae_e_taxa_de_exatos() -> None:
    metrics = aggregate([video("a.mp4", 20, 20), video("b.mp4", 18, 20), video("c.mp4", 15, 14)])

    assert metrics.videos == 3
    assert metrics.labeled == 3
    assert metrics.reps_mae == pytest.approx(1.0)  # (0 + 2 + 1) / 3
    assert metrics.exact_rate == pytest.approx(1 / 3, abs=1e-3)  # arredondado a 3 casas
    assert metrics.total_reps == 53
    assert metrics.total_expected == 54


def test_falso_positivo_conta_so_os_negativos() -> None:
    """Negativo = rótulo 0 reps. É a métrica que impede 'melhorar' inflando contagem."""
    metrics = aggregate(
        [
            video("jj.mp4", 20, 20),
            video("negativo_parado.mp4", 3, 0),
            video("negativo_agachamento.mp4", 0, 0),
        ]
    )

    assert metrics.false_positive_rate == pytest.approx(0.5)


def test_sem_negativos_nao_ha_taxa_de_falso_positivo() -> None:
    assert aggregate([video("a.mp4", 5, 5)]).false_positive_rate is None


def test_video_com_erro_de_leitura_nao_polui_a_acuracia() -> None:
    metrics = aggregate([video("ok.mp4", 20, 20), video("quebrado.mp4", 0, 20, error="boom")])

    assert metrics.errors == 1
    assert metrics.reps_mae == pytest.approx(0.0)
    assert metrics.exact_rate == pytest.approx(1.0)


def test_videos_sem_rotulo_nao_geram_metrica_de_erro() -> None:
    metrics = aggregate([video("sem_rotulo.mp4", 7)])

    assert metrics.labeled == 0
    assert metrics.reps_mae is None
    assert metrics.exact_rate is None


def test_quebra_por_condicao_mostra_onde_a_acuracia_cai() -> None:
    """A tabela que responde 'contraluz derruba a acurácia em quanto?'."""
    metrics = aggregate(
        [
            video("a.mp4", 20, 20, light="good"),
            video("b.mp4", 19, 20, light="good"),
            video("c.mp4", 12, 20, light="backlit"),
            video("d.mp4", 10, 20, light="backlit"),
        ]
    )

    boa = metrics.by_condition["light"]["good"]
    contraluz = metrics.by_condition["light"]["backlit"]
    assert boa["reps_mae"] == pytest.approx(0.5)
    assert contraluz["reps_mae"] == pytest.approx(9.0)
    assert contraluz["exact_rate"] == pytest.approx(0.0)


def test_quebra_cobre_todas_as_condicoes_declaradas() -> None:
    metrics = aggregate([video("a.mp4", 20, 20, light="good", distance="2.5m", angle="frontal")])

    assert set(metrics.by_condition) == {"angle", "distance", "light"}


def test_agregado_de_lista_vazia_nao_explode() -> None:
    metrics = aggregate([])

    assert metrics.videos == 0
    assert metrics.reps_mae is None
    assert "MAE" in format_metrics(metrics)


def test_relatorio_do_run_inclui_metricas() -> None:
    relatorio = build_report(
        [analyze_frames(sequence(jumping_jack_poses(5)), name="jj.mp4", expected_reps=5)],
        target_fps=15.0,
    )

    assert relatorio["metrics"]["labeled"] == 1
    assert relatorio["metrics"]["reps_mae"] == pytest.approx(0.0)


# --------------------------------------------------------------------------------------
# compare
# --------------------------------------------------------------------------------------


def relatorio(*videos: dict) -> dict:
    return {"tool": "evalctl", "report_version": 1, "videos": list(videos)}


def test_compare_detecta_regressao_por_video() -> None:
    comparacao = compare(
        relatorio(video("a.mp4", 20, 20), video("b.mp4", 20, 20)),
        relatorio(video("a.mp4", 20, 20), video("b.mp4", 17, 20)),
    )

    assert comparacao.regressed
    assert comparacao.regressions == ["b.mp4"]
    linha = next(linha for linha in comparacao.videos if linha["name"] == "b.mp4")
    assert linha["status"] == "pior"
    assert linha["reps_delta"] == -3


def test_compare_reconhece_melhora() -> None:
    comparacao = compare(relatorio(video("a.mp4", 15, 20)), relatorio(video("a.mp4", 20, 20)))

    assert not comparacao.regressed
    assert comparacao.improvements == ["a.mp4"]
    assert comparacao.videos[0]["status"] == "melhor"


def test_compare_nao_marca_regressao_quando_nada_muda() -> None:
    igual = relatorio(video("a.mp4", 20, 20))

    comparacao = compare(igual, igual)

    assert not comparacao.regressed
    assert comparacao.videos[0]["status"] == "igual"
    assert "sem regressao" in format_comparison(comparacao)


def test_video_que_passou_a_falhar_e_regressao() -> None:
    comparacao = compare(
        relatorio(video("a.mp4", 20, 20)),
        relatorio(video("a.mp4", 0, 20, error="nao foi possivel abrir")),
    )

    assert comparacao.regressions == ["a.mp4"]
    assert comparacao.videos[0]["status"] == "quebrou"


def test_video_que_voltou_a_rodar_e_melhora() -> None:
    comparacao = compare(
        relatorio(video("a.mp4", 0, 20, error="boom")), relatorio(video("a.mp4", 20, 20))
    )

    assert not comparacao.regressed
    assert comparacao.videos[0]["status"] == "voltou a rodar"


def test_mudanca_em_video_sem_rotulo_nao_da_veredito() -> None:
    """Sem rótulo não há como dizer se ficou melhor — só que mudou."""
    comparacao = compare(relatorio(video("a.mp4", 10)), relatorio(video("a.mp4", 14)))

    assert not comparacao.regressed
    assert comparacao.videos[0]["status"] == "mudou (sem rotulo)"


def test_compare_lista_videos_que_entraram_e_sairam() -> None:
    comparacao = compare(relatorio(video("antigo.mp4", 5, 5)), relatorio(video("novo.mp4", 5, 5)))

    assert comparacao.only_in_before == ["antigo.mp4"]
    assert comparacao.only_in_after == ["novo.mp4"]
    assert comparacao.videos == []


def test_compare_carrega_o_agregado_dos_dois_lados() -> None:
    comparacao = compare(relatorio(video("a.mp4", 10, 20)), relatorio(video("a.mp4", 20, 20)))

    assert comparacao.metrics_before["reps_mae"] == pytest.approx(10.0)
    assert comparacao.metrics_after["reps_mae"] == pytest.approx(0.0)


def test_cli_compare_sai_com_um_em_regressao(tmp_path: Path, capsys) -> None:
    antes = tmp_path / "v1.json"
    depois = tmp_path / "v2.json"
    antes.write_text(json.dumps(relatorio(video("a.mp4", 20, 20))), encoding="utf-8")
    depois.write_text(json.dumps(relatorio(video("a.mp4", 12, 20))), encoding="utf-8")

    codigo = main(["compare", str(antes), str(depois)])

    assert codigo == 1
    assert "REGRESSAO" in capsys.readouterr().out


def test_cli_compare_sai_com_zero_sem_regressao(tmp_path: Path) -> None:
    caminho = tmp_path / "v.json"
    caminho.write_text(json.dumps(relatorio(video("a.mp4", 20, 20))), encoding="utf-8")

    assert main(["compare", str(caminho), str(caminho), "--quiet"]) == 0


def test_cli_compare_grava_json(tmp_path: Path) -> None:
    caminho = tmp_path / "v.json"
    caminho.write_text(json.dumps(relatorio(video("a.mp4", 20, 20))), encoding="utf-8")
    destino = tmp_path / "out" / "diff.json"

    main(["compare", str(caminho), str(caminho), "--report", str(destino), "--quiet"])

    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert dados["regressed"] is False


# --------------------------------------------------------------------------------------
# Fixtures de keypoints (`--save-keypoints`)
# --------------------------------------------------------------------------------------


def test_fixture_sobrevive_ao_round_trip(tmp_path: Path) -> None:
    frames = sequence(jumping_jack_poses(2))
    original = KeypointFixture(
        label="jj_2reps",
        frames=frames,
        expected_reps=2,
        fps=15.0,
        conditions={"light": "good"},
    )

    caminho = save_fixture(tmp_path / "jj.json", original)
    recuperada = load_fixture(caminho)

    assert recuperada.label == "jj_2reps"
    assert recuperada.expected_reps == 2
    assert recuperada.fps == 15.0
    assert recuperada.conditions == {"light": "good"}
    assert len(recuperada.frames) == len(frames)
    assert recuperada.frames[0].ts == frames[0].ts


def test_fixture_gravada_conta_as_mesmas_reps(tmp_path: Path) -> None:
    """SPEC-012, critério 3: pytest consome a fixture sem conversão nenhuma."""
    frames = sequence(jumping_jack_poses(7))
    caminho = save_fixture(
        tmp_path / "jj.json", KeypointFixture(label="jj_7", frames=frames, expected_reps=7)
    )

    fixture = load_fixture(caminho)
    resultado = analyze_frames(
        fixture.frames,
        exercise=fixture.exercise,
        name=fixture.label,
        expected_reps=fixture.expected_reps,
    )

    assert resultado.reps == 7
    assert resultado.exact is True


def test_fixture_guarda_landmarks_crus_nao_normalizados(tmp_path: Path) -> None:
    frames = sequence(still_poses(1))
    caminho = save_fixture(tmp_path / "p.json", KeypointFixture(label="parado", frames=frames))

    dados = json.loads(caminho.read_text(encoding="utf-8"))

    ponto = dados["frames"][0]["landmarks"][0]
    assert len(ponto) == 4
    assert all(0.0 <= valor <= 1.0 for valor in ponto[:2]), "coordenadas devem ser 0-1 do frame"
    assert dados["schema"] == SCHEMA_VERSION


def test_schema_desconhecido_e_recusado(tmp_path: Path) -> None:
    caminho = tmp_path / "futuro.json"
    caminho.write_text(json.dumps({"schema": 99, "frames": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="schema 99"):
        load_fixture(caminho)


def test_fixture_sem_frames_validos_e_recusada(tmp_path: Path) -> None:
    caminho = tmp_path / "ruim.json"
    caminho.write_text(
        json.dumps({"schema": SCHEMA_VERSION, "frames": [{"seq": 0}]}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="frames invalidos"):
        load_fixture(caminho)


def test_save_keypoints_exporta_fixture_por_video(tmp_path: Path, monkeypatch) -> None:
    from tests.test_evalctl import FakeExtractor

    video_path = tmp_path / "jj_frontal_boa_luz.mp4"
    video_path.write_bytes(b"x")
    monkeypatch.setattr(
        "eval.sources.read_video_frames",
        lambda path, *, target_fps=15.0: ((object(), seq * 66, seq) for seq in range(200)),
    )
    monkeypatch.setattr(
        "eval.sources.MediaPipeExtractor",
        lambda **kwargs: FakeExtractor(sequence(jumping_jack_poses(6))),
    )
    destino = tmp_path / "fixtures"

    codigo = main(
        [
            "run",
            str(video_path),
            "--expected-reps",
            "6",
            "--save-keypoints",
            str(destino),
            "--quiet",
        ]
    )

    assert codigo == 0
    fixture = load_fixture(destino / "jj_frontal_boa_luz.json")
    assert fixture.label == "jj_frontal_boa_luz"
    assert fixture.expected_reps == 6
    assert fixture.source == "file"
    # E a fixture reproduz a contagem do vídeo original.
    assert analyze_frames(fixture.frames, expected_reps=6).reps == 6


def test_fixture_de_frames_avulsos_pode_ser_montada_a_mao() -> None:
    """Formato simples o suficiente para o gravador do cliente (T-007) escrever direto."""
    bruto = {
        "schema": 1,
        "label": "do-navegador",
        "exercise": "jumping_jack",
        "frames": [{"ts": 1000, "seq": 0, "landmarks": [[0.5, 0.5, 0.0, 0.9]] * 33}],
    }

    fixture = KeypointFixture.from_dict(bruto)

    assert isinstance(fixture.frames[0], RawFrame)
    assert fixture.frames[0].seq == 0
