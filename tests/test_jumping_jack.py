"""Testes da FSM do polichinelo (T-008 / SPEC-007).

Os frames passam pelo pipeline real: gerador sintético → `normalize()` → FSM. Assim o que se
testa é a contagem que o worker vai produzir, não uma versão idealizada dela.
"""

import time

import pytest

from tests.synthetic_keypoints import Pose, jumping_jack_poses, sequence, still_poses
from workers.analysis_worker.exercises import (
    EXERCISES,
    JumpingJackAnalyzer,
    JumpingJackThresholds,
    feed,
    get_analyzer,
)
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import Baseline, NormFrame, normalize


def analisar(frames, analyzer: JumpingJackAnalyzer | None = None) -> tuple:
    """Roda a FSM sobre frames crus e devolve `(analyzer, eventos)`."""
    analyzer = analyzer or JumpingJackAnalyzer()
    eventos = []
    for frame in normalize(frames):
        eventos.extend(feed(analyzer, frame))
    return analyzer, eventos


def do_tipo(eventos, tipo) -> list:
    return [evento for evento in eventos if isinstance(evento, tipo)]


def codigos(eventos) -> set[str]:
    return {evento.code.value for evento in do_tipo(eventos, QualitySignal)}


# --------------------------------------------------------------------------------------
# Critério 1 — 20 polichinelos limpos = 20 repetições
# --------------------------------------------------------------------------------------


def test_vinte_polichinelos_limpos_contam_exatamente_vinte() -> None:
    frames = sequence(jumping_jack_poses(20))

    analyzer, eventos = analisar(frames)

    assert analyzer.rep_count == 20
    assert len(do_tipo(eventos, RepDetected)) == 20
    assert [evento.rep_count for evento in do_tipo(eventos, RepDetected)] == list(range(1, 21))


@pytest.mark.parametrize("reps", [1, 5, 20])
def test_contagem_bate_para_diferentes_quantidades(reps: int) -> None:
    analyzer, _ = analisar(sequence(jumping_jack_poses(reps)))

    assert analyzer.rep_count == reps


@pytest.mark.parametrize("fps", [10.0, 15.0, 30.0])
def test_contagem_independe_do_fps(fps: float) -> None:
    poses = jumping_jack_poses(10, frames_per_rep=max(int(fps), 8))

    analyzer, _ = analisar(sequence(poses, fps=fps))

    assert analyzer.rep_count == 10


@pytest.mark.parametrize("torso", [0.15, 0.30, 0.45])
def test_contagem_independe_da_distancia_da_camera(torso: float) -> None:
    analyzer, _ = analisar(sequence(jumping_jack_poses(8), torso=torso))

    assert analyzer.rep_count == 8


def test_emite_fase_a_cada_transicao() -> None:
    _, eventos = analisar(sequence(jumping_jack_poses(3)))

    fases = [evento.phase for evento in do_tipo(eventos, ExercisePhase)]

    assert fases == [Phase.OPEN, Phase.CLOSED] * 3


def test_duracao_da_rep_e_plausivel() -> None:
    """1 rep/s a 15 fps: cada rep leva ~1 s de ponta a ponta."""
    _, eventos = analisar(sequence(jumping_jack_poses(5, frames_per_rep=15), fps=15.0))

    duracoes = [evento.duration_ms for evento in do_tipo(eventos, RepDetected)]

    assert all(500 <= duracao <= 1500 for duracao in duracoes), duracoes


def test_polichinelo_limpo_nao_gera_critica_de_execucao() -> None:
    _, eventos = analisar(sequence(jumping_jack_poses(10)))

    assert do_tipo(eventos, QualitySignal) == []


# --------------------------------------------------------------------------------------
# Critério 2 — reps preguiçosas não contam e geram os sinais certos
# --------------------------------------------------------------------------------------


def test_reps_pregui_osas_nao_contam_e_geram_sinais() -> None:
    """SPEC-007: pico de braço em 70–110° e de tornozelo em 1.1–1.4 é rep parcial."""
    frames = sequence(jumping_jack_poses(3, amplitude=0.6))

    analyzer, eventos = analisar(frames)

    assert analyzer.rep_count == 0
    assert codigos(eventos) == {Code.ARMS_TOO_LOW.value, Code.LEGS_TOO_CLOSED.value}
    assert len(do_tipo(eventos, QualitySignal)) == 6  # 2 sinais por tentativa


def test_um_sinal_por_tentativa_nao_um_por_frame() -> None:
    frames = sequence(jumping_jack_poses(3, amplitude=0.6))

    _, eventos = analisar(frames)

    bracos = [
        evento for evento in do_tipo(eventos, QualitySignal) if evento.code is Code.ARMS_TOO_LOW
    ]
    assert len(bracos) == 3


def test_sinal_carrega_o_pico_medido_e_o_indice_da_rep() -> None:
    _, eventos = analisar(sequence(jumping_jack_poses(1, amplitude=0.6)))

    braco = next(e for e in do_tipo(eventos, QualitySignal) if e.code is Code.ARMS_TOO_LOW)

    assert 70.0 <= braco.value <= 110.0
    assert braco.rep_index == 1


def test_movimento_minusculo_nao_gera_nem_rep_nem_sinal() -> None:
    """Abaixo da faixa 'quase abriu' não há o que criticar — não é tentativa de rep."""
    analyzer, eventos = analisar(sequence(jumping_jack_poses(3, amplitude=0.2)))

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, QualitySignal) == []


def test_rep_valida_depois_de_preguicosa_conta_normalmente() -> None:
    poses = jumping_jack_poses(2, amplitude=0.6) + jumping_jack_poses(3)

    analyzer, eventos = analisar(sequence(poses))

    assert analyzer.rep_count == 3
    assert Code.ARMS_TOO_LOW.value in codigos(eventos)


# --------------------------------------------------------------------------------------
# Critério 3 — jitter parado não gera falso positivo
# --------------------------------------------------------------------------------------


def test_pessoa_parada_com_tremor_nao_conta_nada() -> None:
    frames = sequence(still_poses(300), jitter=0.006, seed=13)

    analyzer, eventos = analisar(frames)

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, RepDetected) == []


def test_pessoa_parada_de_bracos_abertos_nao_conta_nada() -> None:
    frames = sequence([Pose(arm_angle=160.0, ankle_spread=1.6)] * 200, jitter=0.006, seed=17)

    analyzer, _ = analisar(frames)

    assert analyzer.rep_count == 0


def test_oscilar_no_limiar_nao_conta_duas_vezes() -> None:
    """Histerese: entrar e sair da fronteira de abertura não pode virar contagem dupla."""
    fronteira = [
        Pose(arm_angle=112.0, ankle_spread=1.42),
        Pose(arm_angle=108.0, ankle_spread=1.38),
    ] * 40

    analyzer, _ = analisar(sequence(fronteira))

    assert analyzer.rep_count == 0


def test_debounce_ignora_transicao_mais_rapida_que_250ms() -> None:
    """A 60 fps, abrir e fechar em 2 frames (33 ms) é ruído, não repetição."""
    poses = jumping_jack_poses(6, frames_per_rep=4)  # ~15 rep/s

    analyzer, _ = analisar(sequence(poses, fps=60.0))

    assert analyzer.rep_count == 0


def test_ritmo_humano_rapido_ainda_conta() -> None:
    """O debounce não pode matar polichinelo rápido de verdade (~2 rep/s)."""
    poses = jumping_jack_poses(8, frames_per_rep=8)

    analyzer, _ = analisar(sequence(poses, fps=16.0))

    assert analyzer.rep_count == 8


# --------------------------------------------------------------------------------------
# Critério 4 — custo por frame
# --------------------------------------------------------------------------------------


def test_step_roda_em_menos_de_um_milissegundo() -> None:
    """SPEC-007, critério 4 — garante o orçamento de ~1–2% de CPU por sessão."""
    frames = normalize(sequence(jumping_jack_poses(30)))
    analyzer = JumpingJackAnalyzer()
    features = [analyzer.features(frame) for frame in frames]

    inicio = time.perf_counter()
    for frame, feats in zip(frames, features, strict=True):
        analyzer.step(feats, frame.ts)
    por_frame_ms = (time.perf_counter() - inicio) / len(frames) * 1000

    assert por_frame_ms < 1.0, f"{por_frame_ms:.3f} ms por frame"


# --------------------------------------------------------------------------------------
# Frames degradados
# --------------------------------------------------------------------------------------


def test_frames_degradados_congelam_a_fsm() -> None:
    """SPEC-007: frame ruim não conta nem penaliza."""
    frames = sequence(jumping_jack_poses(5), visibility=0.1)

    analyzer, eventos = analisar(frames)

    assert analyzer.rep_count == 0
    assert eventos == []
    assert analyzer.summary()["frames_degraded"] == len(frames)


def test_rep_atravessada_por_frames_ruins_nao_e_perdida() -> None:
    """Sair do quadro no meio da série não deve zerar o que já foi contado."""
    boas = sequence(jumping_jack_poses(3))
    ruins = sequence(still_poses(10), visibility=0.1, start_ts=boas[-1].ts + 66)
    depois = sequence(jumping_jack_poses(2), start_ts=ruins[-1].ts + 66)

    analyzer, _ = analisar([*boas, *ruins, *depois])

    assert analyzer.rep_count == 5


# --------------------------------------------------------------------------------------
# Features
# --------------------------------------------------------------------------------------


def um_frame(pose: Pose, **kwargs) -> NormFrame:
    return normalize(sequence([pose], **kwargs))[0]


def test_arm_angle_zero_com_bracos_para_baixo_e_180_acima_da_cabeca() -> None:
    analyzer = JumpingJackAnalyzer()

    baixo = analyzer.features(um_frame(Pose(arm_angle=0.0)))
    alto = analyzer.features(um_frame(Pose(arm_angle=180.0)))

    assert baixo["arm_angle"] == pytest.approx(0.0, abs=1.0)
    assert alto["arm_angle"] == pytest.approx(180.0, abs=1.0)


@pytest.mark.parametrize("angulo", [15.0, 45.0, 90.0, 135.0, 170.0])
def test_arm_angle_acompanha_a_pose(angulo: float) -> None:
    feats = JumpingJackAnalyzer().features(um_frame(Pose(arm_angle=angulo)))

    assert feats["arm_angle"] == pytest.approx(angulo, abs=1.0)


def test_wrist_above_shoulder_so_e_verdadeiro_com_bracos_acima() -> None:
    analyzer = JumpingJackAnalyzer()

    assert analyzer.features(um_frame(Pose(arm_angle=170.0)))["wrist_above_shoulder"] is True
    assert analyzer.features(um_frame(Pose(arm_angle=20.0)))["wrist_above_shoulder"] is False


@pytest.mark.parametrize("spread", [0.55, 1.0, 1.75])
def test_ankle_spread_e_medido_em_larguras_de_ombro(spread: float) -> None:
    feats = JumpingJackAnalyzer().features(um_frame(Pose(ankle_spread=spread)))

    assert feats["ankle_spread"] == pytest.approx(spread, rel=0.02)


def test_ankle_spread_nao_muda_com_a_distancia_da_camera() -> None:
    analyzer = JumpingJackAnalyzer()
    pose = Pose(ankle_spread=1.5)

    perto = analyzer.features(um_frame(pose, torso=0.30))
    longe = analyzer.features(um_frame(pose, torso=0.15))

    assert longe["ankle_spread"] == pytest.approx(perto["ankle_spread"], rel=0.01)


def test_cadencia_reflete_as_reps_da_janela() -> None:
    """10 reps em 10 s ⇒ 60 rep/min."""
    analyzer, _ = analisar(sequence(jumping_jack_poses(10, frames_per_rep=15), fps=15.0))
    ultimo = normalize(sequence(still_poses(1), start_ts=analyzer._rep_timestamps[-1]))[0]

    cadencia = analyzer.features(ultimo)["cadence_10s"]

    assert cadencia == pytest.approx(60.0, rel=0.2)


def test_features_com_baseline_continuam_coerentes() -> None:
    """Com baseline de escala (T-019) a contagem não muda — só fica mais estável."""
    frames = sequence(jumping_jack_poses(6), jitter=0.003)
    analyzer = JumpingJackAnalyzer()

    for frame in normalize(frames, baseline=Baseline(torso=0.30, shoulder_width=0.135)):
        feed(analyzer, frame)

    assert analyzer.rep_count == 6


# --------------------------------------------------------------------------------------
# Resto da interface (SPEC-007) e registro
# --------------------------------------------------------------------------------------


def test_ready_pose_reconhece_a_posicao_inicial() -> None:
    analyzer = JumpingJackAnalyzer()

    fechado = analyzer.features(um_frame(Pose()))
    aberto = analyzer.features(um_frame(Pose(arm_angle=170.0, ankle_spread=1.7)))

    assert analyzer.ready_pose(fechado)
    assert not analyzer.ready_pose(aberto)


def test_ready_pose_e_falso_em_frame_degradado() -> None:
    analyzer = JumpingJackAnalyzer()
    feats = analyzer.features(um_frame(Pose(), visibility=0.1))

    assert not analyzer.ready_pose(feats)


def test_scene_hints_declara_faixa_de_altura_do_corpo() -> None:
    minimo, maximo = JumpingJackAnalyzer().scene_hints().body_height_range

    assert 0.0 < minimo < maximo <= 1.0


def test_summary_consolida_a_sessao() -> None:
    analyzer, _ = analisar(sequence(jumping_jack_poses(4, frames_per_rep=15), fps=15.0))

    resumo = analyzer.summary()

    assert resumo["exercise"] == "jumping_jack"
    assert resumo["reps"] == 4
    assert resumo["cadence_rpm"] == pytest.approx(60.0, rel=0.25)
    assert resumo["frames_degraded"] == 0
    assert resumo["quality_signals"] == {}


def test_summary_conta_sinais_de_qualidade() -> None:
    analyzer, _ = analisar(sequence(jumping_jack_poses(2, amplitude=0.6)))

    assert analyzer.summary()["quality_signals"] == {
        Code.ARMS_TOO_LOW.value: 2,
        Code.LEGS_TOO_CLOSED.value: 2,
    }


def test_registro_resolve_o_exercicio_por_slug() -> None:
    analyzer = get_analyzer("jumping_jack")

    assert isinstance(analyzer, JumpingJackAnalyzer)
    assert "jumping_jack" in EXERCISES


def test_slug_desconhecido_falha_alto() -> None:
    with pytest.raises(ValueError, match="exercicio desconhecido"):
        get_analyzer("levitacao")


def test_cada_sessao_tem_seu_proprio_estado() -> None:
    """Dois analisadores não compartilham contagem — um por sessão."""
    primeiro, _ = analisar(sequence(jumping_jack_poses(3)))
    segundo = JumpingJackAnalyzer()

    assert primeiro.rep_count == 3
    assert segundo.rep_count == 0


def test_limiares_sao_parametrizaveis_para_a_bancada() -> None:
    """SPEC-012 varre limiares contra o corpus; por isso são parâmetro, não constante."""
    exigente = JumpingJackAnalyzer(thresholds=JumpingJackThresholds(open_arm_angle=160.0))

    analyzer, _ = analisar(sequence(jumping_jack_poses(5, amplitude=0.85)), exigente)

    assert analyzer.rep_count == 0
