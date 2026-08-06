"""Testes da FSM do abdominal (T-107 / SPEC-007 / SPEC-020 Tier C).

Mesmos critérios de aceite dos outros exercícios, sobre o mesmo pipeline real: gerador
sintético → `normalize()` → FSM.

O bloco próprio deste módulo é a **referência do joelho**: é ela que substitui a constante em
torsos, e é ela que decide se o exercício mede alguma coisa. Os testes cobram as duas pontas —
que a razão sobrevive a esticar o quadro (a anisotropia medida em `[A/T-106]`) e que a perna
esticada, onde a referência não existe, não vira contagem.
"""

import pytest

from tests.synthetic_keypoints import (
    THIGH_FEET_CLOSE,
    THIGH_FEET_FAR,
    TRUNK_CRUNCH,
    TRUNK_FLAT,
    CrunchPose,
    Pose,
    crunch_poses,
    jumping_jack_poses,
    lying_pose,
    sequence,
    session_poses,
    squat_poses,
    still_poses,
)
from workers.analysis_worker.exercises import (
    EXERCISES,
    CrunchAnalyzer,
    CrunchThresholds,
    feed,
    get_analyzer,
)
from workers.shared.events import Code, ExercisePhase, Phase, QualitySignal, RepDetected
from workers.shared.normalize import NormFrame, normalize


def analisar(frames, analyzer: CrunchAnalyzer | None = None) -> tuple:
    analyzer = analyzer or CrunchAnalyzer()
    eventos = []
    for frame in normalize(frames):
        eventos.extend(feed(analyzer, frame))
    return analyzer, eventos


def do_tipo(eventos, tipo) -> list:
    return [evento for evento in eventos if isinstance(evento, tipo)]


def codigos(eventos) -> set[str]:
    return {evento.code.value for evento in do_tipo(eventos, QualitySignal)}


def um_frame(pose: CrunchPose, **kwargs) -> NormFrame:
    return normalize(sequence([pose], **kwargs))[0]


# --------------------------------------------------------------------------------------
# Critério 1 — abdominais limpos contam exatamente
# --------------------------------------------------------------------------------------


def test_vinte_abdominais_limpos_contam_exatamente_vinte() -> None:
    analyzer, eventos = analisar(sequence(crunch_poses(20)))

    assert analyzer.rep_count == 20
    assert [evento.rep_count for evento in do_tipo(eventos, RepDetected)] == list(range(1, 21))


@pytest.mark.parametrize("reps", [1, 5, 20])
def test_contagem_bate_para_diferentes_quantidades(reps: int) -> None:
    analyzer, _ = analisar(sequence(crunch_poses(reps)))

    assert analyzer.rep_count == reps


@pytest.mark.parametrize("fps", [10.0, 15.0, 30.0])
def test_contagem_independe_do_fps(fps: float) -> None:
    poses = crunch_poses(10, frames_per_rep=max(int(fps), 8))

    analyzer, _ = analisar(sequence(poses, fps=fps))

    assert analyzer.rep_count == 10


@pytest.mark.parametrize("torso", [0.15, 0.30, 0.45])
def test_contagem_independe_da_distancia_da_camera(torso: float) -> None:
    analyzer, _ = analisar(sequence(crunch_poses(8), torso=torso))

    assert analyzer.rep_count == 8


def test_emite_fase_a_cada_transicao() -> None:
    _, eventos = analisar(sequence(crunch_poses(3)))

    fases = [evento.phase for evento in do_tipo(eventos, ExercisePhase)]

    assert fases == [Phase.PEAK, Phase.REST] * 3


def test_abdominal_limpo_nao_gera_critica_de_execucao() -> None:
    _, eventos = analisar(sequence(crunch_poses(10)))

    assert do_tipo(eventos, QualitySignal) == []


def test_sessao_com_countdown_deitado_conta_tudo() -> None:
    """A sessão real começa parada — e, no abdominal, parada é deitado de joelho dobrado."""
    poses = session_poses(crunch_poses(8), still=lying_pose())

    analyzer, _ = analisar(sequence(poses))

    assert analyzer.rep_count == 8


# --------------------------------------------------------------------------------------
# Critério 2 — rep rasa não conta e gera o sinal certo
# --------------------------------------------------------------------------------------


def test_abdominal_raso_nao_conta_e_avisa() -> None:
    """Subiu, mas as escápulas não saíram do chão: não é crunch, é intenção de crunch."""
    analyzer, eventos = analisar(sequence(crunch_poses(3, amplitude=0.6)))

    assert analyzer.rep_count == 0
    assert codigos(eventos) == {Code.CRUNCH_TOO_SHALLOW.value}
    assert len(do_tipo(eventos, QualitySignal)) == 3  # um por tentativa, não um por frame


def test_sinal_carrega_a_altura_medida_e_o_indice() -> None:
    _, eventos = analisar(sequence(crunch_poses(1, amplitude=0.6)))

    sinal = next(e for e in do_tipo(eventos, QualitySignal) if e.code is Code.CRUNCH_TOO_SHALLOW)
    limiares = CrunchThresholds()

    assert limiares.shallow_lift <= sinal.value <= limiares.up_lift
    assert sinal.rep_index == 1


def test_movimento_minusculo_nao_gera_nem_rep_nem_sinal() -> None:
    """Abaixo da faixa "quase subiu" não há o que criticar — não é tentativa."""
    analyzer, eventos = analisar(sequence(crunch_poses(3, amplitude=0.3)))

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, QualitySignal) == []


def test_rep_valida_depois_de_rasa_conta_normalmente() -> None:
    poses = crunch_poses(2, amplitude=0.6) + crunch_poses(3)

    analyzer, eventos = analisar(sequence(poses))

    assert analyzer.rep_count == 3
    assert Code.CRUNCH_TOO_SHALLOW.value in codigos(eventos)


# --------------------------------------------------------------------------------------
# Critério 3 — nada de falso positivo com pessoa parada
# --------------------------------------------------------------------------------------


def test_pessoa_deitada_com_tremor_nao_conta_nada() -> None:
    frames = sequence([lying_pose()] * 300, jitter=0.006, seed=13)

    analyzer, eventos = analisar(frames)

    assert analyzer.rep_count == 0
    assert do_tipo(eventos, RepDetected) == []


def test_pessoa_parada_encolhida_nao_conta_nada() -> None:
    """Segurar o topo do abdominal não é repetir — a rep nasce na DESCIDA."""
    encolhido = CrunchPose(trunk_angle=TRUNK_CRUNCH)

    analyzer, _ = analisar(sequence([encolhido] * 200, jitter=0.006, seed=17))

    assert analyzer.rep_count == 0


def test_oscilar_no_limiar_nao_conta_duas_vezes() -> None:
    """Histerese: ficar na fronteira da subida não pode virar contagem."""
    limiares = CrunchThresholds()
    fronteira = [CrunchPose(trunk_angle=21.0), CrunchPose(trunk_angle=24.0)] * 40

    analyzer, _ = analisar(sequence(fronteira))

    assert limiares.down_lift < limiares.up_lift  # a folga existe
    assert analyzer.rep_count == 0


def test_debounce_ignora_transicao_mais_rapida_que_250ms() -> None:
    """A 60 fps, subir e descer em 4 frames (66 ms) é ruído, não repetição."""
    analyzer, _ = analisar(sequence(crunch_poses(6, frames_per_rep=4), fps=60.0))

    assert analyzer.rep_count == 0


def test_frames_degradados_congelam_a_fsm() -> None:
    analyzer, _ = analisar(sequence(crunch_poses(5), visibility=0.1))

    assert analyzer.rep_count == 0
    assert analyzer.summary()["frames_degraded"] > 0


# --------------------------------------------------------------------------------------
# Critério 4 — cadência vira crítica JUNTO com a repetição
# --------------------------------------------------------------------------------------


def test_abdominal_no_impulso_conta_a_rep_e_critica() -> None:
    """Subir em meio segundo é balanço, não abdômen — mas a repetição aconteceu."""
    analyzer, eventos = analisar(sequence(crunch_poses(6, frames_per_rep=8), fps=15.0))

    assert analyzer.rep_count == 6
    assert codigos(eventos) == {Code.CRUNCH_TOO_FAST.value}


def test_cadencia_controlada_nao_gera_critica() -> None:
    """~1,3 s por repetição: o ritmo que a execução correta pede."""
    analyzer, eventos = analisar(sequence(crunch_poses(6, frames_per_rep=20), fps=15.0))

    assert analyzer.rep_count == 6
    assert Code.CRUNCH_TOO_FAST.value not in codigos(eventos)


# --------------------------------------------------------------------------------------
# A decisão que define o módulo: razão sobre a altura do JOELHO, não constante em torsos
# --------------------------------------------------------------------------------------


def test_lift_bate_com_a_tabela_do_docstring() -> None:
    """Os números da tabela do módulo, travados."""
    analyzer = CrunchAnalyzer()

    def lift(tronco: float) -> float:
        return float(analyzer.features(um_frame(CrunchPose(trunk_angle=tronco)))["lift"])

    assert lift(TRUNK_FLAT) == pytest.approx(0.097, abs=0.01)
    assert lift(20.0) == pytest.approx(0.474, abs=0.01)
    assert lift(TRUNK_CRUNCH) == pytest.approx(0.694, abs=0.01)
    # Monotônica: mais tronco levantado é sempre mais `lift`, sem inversão no meio da faixa.
    valores = [lift(a) for a in (TRUNK_FLAT, 12.0, 20.0, TRUNK_CRUNCH, 40.0)]
    assert valores == sorted(valores)


def test_a_contagem_nao_muda_com_o_formato_do_quadro() -> None:
    """O teste que existe por causa da anisotropia medida no corpus (ver `[A/T-106]`).

    Deitado, o torso é medido no eixo horizontal e o movimento acontece no vertical: um limiar
    "em torsos" herdaria o formato do vídeo. A razão sobre a altura do joelho não.
    """
    contagens = {
        torso: analisar(sequence(crunch_poses(10), torso=torso))[0].rep_count
        for torso in (0.12, 0.20, 0.30, 0.42)
    }

    assert set(contagens.values()) == {10}, contagens


def test_crunch_cheio_conta_em_qualquer_montagem_de_perna() -> None:
    """O pé mais perto ou mais longe do glúteo muda a referência — mas não o crunch cheio."""
    for coxa in (THIGH_FEET_FAR, THIGH_FEET_CLOSE):
        analyzer, _ = analisar(sequence(crunch_poses(10, thigh_angle=coxa)))

        assert analyzer.rep_count == 10, coxa


def test_a_montagem_da_perna_move_a_referencia_e_isso_esta_medido() -> None:
    """A limitação declarada no docstring, travada em teste para não virar surpresa.

    Pé longe do glúteo abaixa o joelho, e um joelho mais baixo infla o `lift`. É o preço de
    usar o joelho como referência — e o motivo de o Guia mandar aproximar o calcanhar.
    """
    analyzer = CrunchAnalyzer()

    def referencia(coxa: float) -> float:
        pose = CrunchPose(trunk_angle=TRUNK_CRUNCH, thigh_angle=coxa)
        return float(analyzer.features(um_frame(pose))["knee_height"])

    assert referencia(THIGH_FEET_FAR) == pytest.approx(0.601, abs=0.01)
    assert referencia(THIGH_FEET_CLOSE) == pytest.approx(0.808, abs=0.01)


def test_lift_nao_muda_com_a_posicao_no_quadro() -> None:
    """Invariância que a normalização promete e da qual a contagem depende."""
    analyzer = CrunchAnalyzer()
    encolhido = CrunchPose(trunk_angle=TRUNK_CRUNCH)

    canto = analyzer.features(um_frame(encolhido, center=(0.30, 0.35)))
    meio = analyzer.features(um_frame(encolhido, center=(0.5, 0.55)))

    assert float(canto["lift"]) == pytest.approx(float(meio["lift"]), abs=0.01)


@pytest.mark.parametrize(
    ("rotulo", "poses"),
    [
        ("em pé parado", still_poses(120)),
        ("em pé levantando os braços", jumping_jack_poses(10)),
        ("agachando", squat_poses(10)),
        (
            "marcha, joelho alto",
            [Pose(knee_angle=a) for _ in range(12) for a in (172, 120, 90, 120)],
        ),
    ],
)
def test_gente_em_pe_nunca_conta_abdominal(rotulo: str, poses: list) -> None:
    """A mesma classe de erro que derrubou a flexão em produção — medida aqui, não suposta.

    A flexão contava braço levantado como repetição porque a altura ombro→pulso de quem está em
    pé é quase a de uma prancha, e precisou de um porteiro de postura explícito. O abdominal
    **não** tem esse furo, e o motivo é geométrico: em pé o joelho fica sempre ABAIXO do
    quadril, então a referência da contagem sai negativa (−0,52 em pé, −0,32 agachado, −0,37 na
    marcha, contra o mínimo de +0,25) e a feature devolve zero.

    Estes testes existem para transformar essa proteção de acidente em invariante: quem trocar
    a referência do joelho por outra coisa descobre aqui, e não em produção.
    """
    analyzer, eventos = analisar(sequence(poses))

    assert analyzer.rep_count == 0, rotulo
    assert do_tipo(eventos, RepDetected) == [], rotulo


def test_perna_esticada_nao_produz_medida() -> None:
    """Sem joelho dobrado não há referência — e sem referência não há contagem.

    A alternativa seria dividir por um número minúsculo e transformar ruído em repetição.
    """
    analyzer = CrunchAnalyzer()
    esticado = CrunchPose(trunk_angle=TRUNK_CRUNCH, thigh_angle=6.0)

    feats = analyzer.features(um_frame(esticado))

    assert float(feats["lift"]) == 0.0
    assert analyzer.initial_phase(feats) is Phase.REST


def test_deitado_de_joelho_dobrado_e_a_posicao_inicial() -> None:
    analyzer = CrunchAnalyzer()

    assert analyzer.ready_pose(analyzer.features(um_frame(lying_pose()))) is True
    assert (
        analyzer.ready_pose(analyzer.features(um_frame(CrunchPose(trunk_angle=TRUNK_CRUNCH))))
        is False
    )
    # Deitado de perna esticada é uma pessoa deitada, não alguém pronto para abdominal.
    esticado = CrunchPose(trunk_angle=TRUNK_FLAT, thigh_angle=6.0)
    assert analyzer.ready_pose(analyzer.features(um_frame(esticado))) is False


def test_captura_que_comeca_encolhido_le_a_fase_inicial() -> None:
    """T-047: quem começa a captura no topo do abdominal não perde a repetição em curso.

    Diferente da flexão, aqui isto é alcançável: a referência do joelho existe no primeiro
    frame, então "está encolhido" é uma afirmação que os features sabem fazer.
    """
    analyzer = CrunchAnalyzer()
    feats = analyzer.features(um_frame(CrunchPose(trunk_angle=TRUNK_CRUNCH)))

    assert analyzer.initial_phase(feats) is Phase.PEAK


# --------------------------------------------------------------------------------------
# Registro e contrato
# --------------------------------------------------------------------------------------


def test_abdominal_esta_registrado_no_catalogo_do_servidor() -> None:
    assert EXERCISES["abdominal"] is CrunchAnalyzer
    assert isinstance(get_analyzer("abdominal"), CrunchAnalyzer)


def test_summary_traz_o_consolidado_da_sessao() -> None:
    analyzer, _ = analisar(sequence(crunch_poses(5)))

    resumo = analyzer.summary()

    assert resumo["exercise"] == "abdominal"
    assert resumo["reps"] == 5
    assert resumo["cadence_rpm"] > 0
