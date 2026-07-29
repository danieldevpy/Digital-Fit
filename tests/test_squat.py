"""Testes da FSM do agachamento (T-032 / SPEC-007).

Mesmos critérios de aceite do polichinelo, sobre o mesmo pipeline real: gerador sintético
(T-052) → `normalize()` → FSM. O que se testa é a contagem que o worker vai produzir.

Um bloco a mais que o polichinelo não tem: os testes que travam a **decisão de qual feature
usar**. O ângulo do joelho lido de frente é enganoso, e é fácil alguém "consertar" este
módulo trocando a altura do quadril por ele. Os testes existem para essa troca falhar alto.
"""

import pytest

from tests.synthetic_keypoints import (
    FEET_SHOULDER_WIDTH,
    KNEE_SQUAT,
    KNEE_STANDING,
    Pose,
    sequence,
    session_poses,
    squat_poses,
    standing_pose,
)
from workers.analysis_worker.exercises import (
    EXERCISES,
    SquatAnalyzer,
    SquatThresholds,
    feed,
    get_analyzer,
)
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import NormFrame, normalize


def analisar(frames, analyzer: SquatAnalyzer | None = None) -> tuple:
    analyzer = analyzer or SquatAnalyzer()
    eventos = []
    for frame in normalize(frames):
        eventos.extend(feed(analyzer, frame))
    return analyzer, eventos


def do_tipo(eventos, tipo) -> list:
    return [evento for evento in eventos if isinstance(evento, tipo)]


def codigos(eventos) -> set[str]:
    return {evento.code.value for evento in do_tipo(eventos, QualitySignal)}


def um_frame(pose: Pose, **kwargs) -> NormFrame:
    return normalize(sequence([pose], **kwargs))[0]


# --------------------------------------------------------------------------------------
# Critério 1 — agachamentos limpos contam exatamente
# --------------------------------------------------------------------------------------


def test_vinte_agachamentos_limpos_contam_exatamente_vinte() -> None:
    analyzer, eventos = analisar(sequence(squat_poses(20)))

    assert analyzer.rep_count == 20
    assert [evento.rep_count for evento in do_tipo(eventos, RepDetected)] == list(range(1, 21))


@pytest.mark.parametrize("reps", [1, 5, 20])
def test_contagem_bate_para_diferentes_quantidades(reps: int) -> None:
    analyzer, _ = analisar(sequence(squat_poses(reps)))

    assert analyzer.rep_count == reps


@pytest.mark.parametrize("fps", [10.0, 15.0, 30.0])
def test_contagem_independe_do_fps(fps: float) -> None:
    poses = squat_poses(10, frames_per_rep=max(int(fps), 8))

    analyzer, _ = analisar(sequence(poses, fps=fps))

    assert analyzer.rep_count == 10


@pytest.mark.parametrize("torso", [0.15, 0.30, 0.45])
def test_contagem_independe_da_distancia_da_camera(torso: float) -> None:
    """A razão é em torsos justamente para isto: 2 m e 4 m contam igual."""
    analyzer, _ = analisar(sequence(squat_poses(8), torso=torso))

    assert analyzer.rep_count == 8


def test_emite_fase_a_cada_transicao() -> None:
    _, eventos = analisar(sequence(squat_poses(3)))

    fases = [evento.phase for evento in do_tipo(eventos, ExercisePhase)]

    assert fases == [Phase.PEAK, Phase.REST] * 3


def test_agachamento_limpo_nao_gera_critica_de_execucao() -> None:
    _, eventos = analisar(sequence(squat_poses(10)))

    assert do_tipo(eventos, QualitySignal) == []


# --------------------------------------------------------------------------------------
# Critério 2 — rep rasa não conta e gera o sinal certo
# --------------------------------------------------------------------------------------


def test_agachamento_raso_nao_conta_e_avisa() -> None:
    """O análogo da rep preguiçosa: desceu, mas a coxa não chegou perto do paralelo."""
    analyzer, eventos = analisar(sequence(squat_poses(3, amplitude=0.7)))

    assert analyzer.rep_count == 0
    assert codigos(eventos) == {Code.SQUAT_TOO_SHALLOW.value}
    assert len(do_tipo(eventos, QualitySignal)) == 3  # um por tentativa, não um por frame


def test_sinal_carrega_a_profundidade_medida_e_o_indice() -> None:
    _, eventos = analisar(sequence(squat_poses(1, amplitude=0.7)))

    sinal = next(e for e in do_tipo(eventos, QualitySignal) if e.code is Code.SQUAT_TOO_SHALLOW)

    assert SquatThresholds().down_hip_height <= sinal.value <= SquatThresholds().shallow_hip_height
    assert sinal.rep_index == 1


def test_movimento_minusculo_nao_gera_nem_rep_nem_sinal() -> None:
    """Abaixo da faixa 'quase desceu' não há o que criticar — não é tentativa."""
    analyzer, eventos = analisar(sequence(squat_poses(3, amplitude=0.25)))

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, QualitySignal) == []


def test_rep_valida_depois_de_rasa_conta_normalmente() -> None:
    poses = squat_poses(2, amplitude=0.7) + squat_poses(3)

    analyzer, eventos = analisar(sequence(poses))

    assert analyzer.rep_count == 3
    assert Code.SQUAT_TOO_SHALLOW.value in codigos(eventos)


# --------------------------------------------------------------------------------------
# Critério 3 — nada de falso positivo com pessoa parada
# --------------------------------------------------------------------------------------


def test_pessoa_em_pe_com_tremor_nao_conta_nada() -> None:
    frames = sequence([standing_pose()] * 300, jitter=0.006, seed=13)

    analyzer, eventos = analisar(frames)

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, RepDetected) == []


def test_pessoa_parada_agachada_nao_conta_nada() -> None:
    """Segurar o agachamento não é repetir — a rep nasce na SUBIDA."""
    agachado = Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT)

    analyzer, _ = analisar(sequence([agachado] * 200, jitter=0.006, seed=17))

    assert analyzer.rep_count == 0


def test_oscilar_no_limiar_nao_conta_duas_vezes() -> None:
    """Histerese: ficar na fronteira da descida não pode virar contagem."""
    limiares = SquatThresholds()
    # Duas poses em volta do limiar de descida (0,72 torsos ≈ 92° de joelho).
    fronteira = [
        Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=94.0),
        Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=90.0),
    ] * 40

    analyzer, _ = analisar(sequence(fronteira))

    assert limiares.down_hip_height < limiares.up_hip_height  # a folga existe
    assert analyzer.rep_count == 0


def test_debounce_ignora_transicao_mais_rapida_que_250ms() -> None:
    """A 60 fps, descer e subir em 4 frames (66 ms) é ruído, não repetição."""
    analyzer, _ = analisar(sequence(squat_poses(6, frames_per_rep=4), fps=60.0))

    assert analyzer.rep_count == 0


def test_ritmo_humano_rapido_ainda_conta() -> None:
    """90 rpm — 1,5 agachamentos por segundo, já mais rápido do que se faz na prática.

    Medido: a contagem é exata até 90 rpm e quebra em 120. E o motivo não é a FSM, é o One
    Euro: a 120 rpm o filtro corta o fundo do movimento (0,727 contra o limiar de 0,72), e o
    agachamento inteiro vira "raso". A 30 fps o mesmo ritmo volta a contar 5 de 8 — mais
    amostras, menos corte —, o que confirma o diagnóstico.

    Os parâmetros do filtro foram medidos para o polichinelo (SPEC-006: "o pulso percorre ~3
    torsos/s"); o quadril de um agachamento anda bem menos, e o filtro trata mais do
    movimento como ruído. Está registrado nas Descobertas: se algum exercício futuro precisar
    de mais banda, o caminho é parâmetro por exercício, não afrouxar o limiar deste aqui.
    """
    analyzer, _ = analisar(sequence(squat_poses(8, frames_per_rep=10), fps=15.0))

    assert analyzer.rep_count == 8


def test_frames_degradados_congelam_a_fsm() -> None:
    analyzer, _ = analisar(sequence(squat_poses(5), visibility=0.1))

    assert analyzer.rep_count == 0
    assert analyzer.summary()["frames_degraded"] > 0


# --------------------------------------------------------------------------------------
# A decisão que define o módulo: altura do quadril, NÃO ângulo do joelho
# --------------------------------------------------------------------------------------


def test_o_angulo_do_joelho_visto_de_frente_NAO_serve_de_criterio() -> None:
    """Trava a decisão da T-032 contra um "conserto" bem-intencionado.

    No fundo de um agachamento de verdade (80° reais de joelho) a câmera frontal lê ~133°.
    Quem trocasse a altura do quadril por `knee_angle_view < 90°` teria uma FSM que jamais
    conta uma repetição — e os testes de contagem acima não pegariam o motivo, só o sintoma.
    """
    analyzer = SquatAnalyzer()
    fundo = Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT)
    feats = analyzer.features(um_frame(fundo))

    assert float(feats["knee_angle_view"]) > 120.0
    # E a feature que de fato decide está bem abaixo do limiar, com folga.
    assert float(feats["hip_height"]) < SquatThresholds().down_hip_height - 0.05


def test_hip_height_e_o_que_a_normalizacao_preserva() -> None:
    """Os números da tabela do docstring do módulo, travados."""
    analyzer = SquatAnalyzer()

    def altura(knee: float) -> float:
        pose = Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=knee)
        return float(analyzer.features(um_frame(pose))["hip_height"])

    assert altura(KNEE_STANDING) == pytest.approx(1.023, abs=0.01)
    assert altura(110.0) == pytest.approx(0.830, abs=0.01)
    assert altura(KNEE_SQUAT) == pytest.approx(0.636, abs=0.01)
    # Monotônica: mais dobrado é sempre mais baixo, sem inversão no meio da faixa.
    alturas = [altura(k) for k in (KNEE_STANDING, 140.0, 110.0, KNEE_SQUAT, 70.0)]
    assert alturas == sorted(alturas, reverse=True)


def test_hip_height_nao_muda_com_a_posicao_no_quadro() -> None:
    """Invariância que a normalização promete e da qual a contagem depende."""
    analyzer = SquatAnalyzer()
    pose = Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT)

    canto = analyzer.features(um_frame(pose, center=(0.25, 0.40)))
    meio = analyzer.features(um_frame(pose, center=(0.5, 0.55)))

    assert float(canto["hip_height"]) == pytest.approx(float(meio["hip_height"]), abs=0.01)


# --------------------------------------------------------------------------------------
# Fase inicial lida (T-047) e resto da interface
# --------------------------------------------------------------------------------------


def test_captura_que_comeca_agachado_nao_perde_a_primeira_rep() -> None:
    poses = squat_poses(2)[7:]  # índice 7 de 15 é o fundo da primeira rep

    analyzer, eventos = analisar(sequence(poses))

    assert analyzer.rep_count == 2
    assert do_tipo(eventos, ExercisePhase)[0].phase is Phase.PEAK


def test_em_pe_a_fase_inicial_e_repouso() -> None:
    analyzer = SquatAnalyzer()
    feats = analyzer.features(um_frame(standing_pose()))

    assert analyzer.initial_phase(feats) is Phase.REST
    assert analyzer.initial_phase({**feats, "degraded": True}) is Phase.REST


def test_sessao_real_com_countdown_conta_certo() -> None:
    """O caminho do produto: parado para calibrar, depois o exercício."""
    analyzer, _ = analisar(sequence(session_poses(squat_poses(6))))

    assert analyzer.rep_count == 6


def test_ready_pose_reconhece_em_pe_e_recusa_agachado() -> None:
    analyzer = SquatAnalyzer()

    assert analyzer.ready_pose(analyzer.features(um_frame(standing_pose())))
    agachado = Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT)
    assert not analyzer.ready_pose(analyzer.features(um_frame(agachado)))


def test_summary_consolida_a_sessao() -> None:
    analyzer, _ = analisar(sequence(squat_poses(4, frames_per_rep=15), fps=15.0))

    resumo = analyzer.summary()

    assert resumo["exercise"] == "squat"
    assert resumo["reps"] == 4
    assert resumo["cadence_rpm"] == pytest.approx(60.0, rel=0.25)


def test_registro_resolve_o_exercicio_por_slug() -> None:
    assert isinstance(get_analyzer("squat"), SquatAnalyzer)
    assert "squat" in EXERCISES


def test_cada_sessao_tem_seu_proprio_estado() -> None:
    primeiro, _ = analisar(sequence(squat_poses(3)))

    assert primeiro.rep_count == 3
    assert SquatAnalyzer().rep_count == 0


def test_limiares_sao_parametrizaveis_para_a_bancada() -> None:
    exigente = SquatAnalyzer(thresholds=SquatThresholds(down_hip_height=0.40))

    analyzer, _ = analisar(sequence(squat_poses(5)), exigente)

    assert analyzer.rep_count == 0
