"""Flexão com a câmera de FRENTE — celular em pé no chão (T-108 / SPEC-007 / SPEC-020).

O mesmo exercício da `test_flexao.py`, a outra câmera. O que se testa aqui é o que a
`flexao.py` passou a saber fazer: **descobrir de que lado a lente está e trocar a feature que
conta**, sem perguntar nada ao usuário.

Três blocos existem só neste arquivo, e cada um trava um bug que aconteceu de verdade:

- **Contar de frente.** Antes disto, dois vídeos reais de 50 flexões contavam ZERO: o porteiro
  de postura era `trunk_spread ≥ 1,2`, e de frente o vetor ombro→quadril aponta para a lente,
  o `dx` some e ele nunca abria.
- **Não contar quem está em pé.** A folga que faz o porteiro novo funcionar é medida
  (0,16 em pé contra 0,30 do limiar), e é ela que impede a volta do bug da T-106, em que
  levantar o braço virava repetição.
- **Não dizer "você saiu do quadro" com o enquadramento perfeito.** De frente o tornozelo tem
  visibilidade 0,09 em 100% dos frames, e ele era âncora obrigatória de cena.

O boneco frontal é montado em 3D e projetado em perspectiva (ver `synthetic_keypoints.py`):
de frente a perspectiva não é detalhe de desenho, é o fenômeno que a FSM mede.
"""

import pytest

from tests.synthetic_keypoints import (
    HIPS_ALIGNED,
    HIPS_PIKED,
    HIPS_SAGGED,
    frontal_plank_pose,
    frontal_pushup_poses,
    jumping_jack_poses,
    pushup_poses,
    sequence,
    squat_poses,
    still_poses,
)
from workers.analysis_worker.exercises import PushUpAnalyzer, feed
from workers.analysis_worker.exercises.flexao import View
from workers.analysis_worker.scene import SceneValidator
from workers.shared.events import Code, QualitySignal, RepDetected
from workers.shared.normalize import normalize

#: Frames parados na prancha antes da série. É o que o produto sempre tem (o countdown da
#: SPEC-004) e o que os vídeos do corpus NÃO têm — sem isso a calibração come a primeira
#: repetição, exatamente como já está documentado para o `polichinelo-02`.
COUNTDOWN = 20


def analisar(frames, analyzer: PushUpAnalyzer | None = None):
    analyzer = analyzer or PushUpAnalyzer()
    eventos = []
    for frame in normalize(frames):
        eventos.extend(feed(analyzer, frame))
    return analyzer, eventos


def reps(eventos) -> int:
    return len([e for e in eventos if isinstance(e, RepDetected)])


def codigos(eventos) -> set[str]:
    return {e.code.value for e in eventos if isinstance(e, QualitySignal)}


def com_countdown(poses):
    return [frontal_plank_pose()] * COUNTDOWN + poses


# --------------------------------------------------------------------------------------
# Critério 1 — de frente, flexões limpas contam exatamente
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("quantidade", [1, 6, 20])
def test_flexoes_frontais_limpas_contam_exatamente(quantidade: int) -> None:
    _, eventos = analisar(sequence(com_countdown(frontal_pushup_poses(quantidade))))

    assert reps(eventos) == quantidade


def test_a_vista_frontal_e_descoberta_sozinha() -> None:
    """Ninguém configura nada: a geometria diz de que lado a câmera está."""
    analyzer, _ = analisar(sequence(com_countdown(frontal_pushup_poses(4))))

    assert analyzer.summary()["view"] == View.FRONTAL.value


def test_a_vista_de_perfil_continua_sendo_descoberta_como_perfil() -> None:
    """A capacidade nova não pode reinterpretar o que já funcionava."""
    analyzer, _ = analisar(sequence([*[pushup_poses(1)[0]] * COUNTDOWN, *pushup_poses(4)]))

    assert analyzer.summary()["view"] == View.PROFILE.value


def test_contagem_frontal_nao_depende_da_distancia_da_camera() -> None:
    """A feature é uma razão contra o topo da própria pessoa: escala tem de cancelar."""
    poses = com_countdown(frontal_pushup_poses(6))
    perto = analisar(sequence(poses, torso=0.45))[1]
    longe = analisar(sequence(poses, torso=0.16))[1]

    assert reps(perto) == reps(longe) == 6


def test_contagem_frontal_nao_depende_do_formato_do_quadro() -> None:
    """Retrato e paisagem contam igual — a lição de anisotropia da T-106, na vista nova."""
    poses = com_countdown(frontal_pushup_poses(6))
    retrato = analisar(sequence(poses, center=(0.5, 0.5), torso=0.30))[1]
    paisagem = analisar(sequence(poses, center=(0.5, 0.62), torso=0.30))[1]

    assert reps(retrato) == reps(paisagem) == 6


# --------------------------------------------------------------------------------------
# Critério 2 — quem NÃO está fazendo flexão não conta (o bug da T-106, na vista nova)
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rotulo", "poses"),
    [
        ("em pe, parado", still_poses(60)),
        ("polichinelo", jumping_jack_poses(5)),
        ("agachamento", squat_poses(5)),
    ],
)
def test_de_pe_nunca_conta_flexao(rotulo: str, poses) -> None:
    """A folga que sustenta isto é medida: pulso−quadril chega a 0,16 em pé, o limiar é 0,30."""
    _, eventos = analisar(sequence(poses))

    assert reps(eventos) == 0, rotulo


def test_prancha_parada_nao_conta_nada() -> None:
    """Segurar a posição inicial não é repetição."""
    _, eventos = analisar(sequence([frontal_plank_pose()] * 90))

    assert reps(eventos) == 0


def test_jitter_parado_na_prancha_nao_inventa_repeticao() -> None:
    _, eventos = analisar(sequence([frontal_plank_pose()] * 90, jitter=0.004))

    assert reps(eventos) == 0


def test_levantar_do_chao_no_meio_descarta_a_tentativa_em_curso() -> None:
    """Quem começou deitado e terminou de pé não fez meia flexão — fez outra coisa."""
    poses = [
        *[frontal_plank_pose()] * COUNTDOWN,
        *frontal_pushup_poses(2),
        *still_poses(30),
        *frontal_pushup_poses(2),
    ]
    _, eventos = analisar(sequence(poses))

    assert reps(eventos) == 4


# --------------------------------------------------------------------------------------
# Critério 3 — reps rasas viram crítica, não repetição
# --------------------------------------------------------------------------------------


def test_flexao_que_quase_desce_nao_conta_e_vira_critica() -> None:
    """`amplitude=0.6` põe o fundo em ~123° de cotovelo (0,71 do topo).

    O número não é arbitrário: é o que cai dentro da faixa de crítica frontal (0,63–0,74), o
    equivalente dos 107°–127° que o perfil já usava. Quem para aí tentou uma flexão e não
    chegou — é exatamente de quem o produto tem de reclamar.
    """
    poses = com_countdown(frontal_pushup_poses(5, amplitude=0.6))
    _, eventos = analisar(sequence(poses))

    assert reps(eventos) == 0
    assert Code.PUSHUP_TOO_SHALLOW.value in codigos(eventos)


def test_quem_mal_dobra_o_braco_nao_conta_nem_e_criticado() -> None:
    """`amplitude=0.35` mal tira o braço da extensão (~143°, 0,83 do topo).

    Nem repetição nem crítica, e isso é a resposta certa: `PUSHUP_TOO_SHALLOW` quer dizer
    "faltou pouco", e reclamar de quem sequer tentou descer é ruído — a mesma escolha que o
    perfil faz com a faixa dele.
    """
    _, eventos = analisar(sequence(com_countdown(frontal_pushup_poses(5, amplitude=0.35))))

    assert reps(eventos) == 0
    assert codigos(eventos) == set()


def test_meia_amplitude_nao_e_confundida_com_flexao_inteira() -> None:
    inteiras = analisar(sequence(com_countdown(frontal_pushup_poses(6))))[1]
    rasas = analisar(sequence(com_countdown(frontal_pushup_poses(6, amplitude=0.6))))[1]

    assert reps(inteiras) == 6
    assert reps(rasas) < reps(inteiras)


# --------------------------------------------------------------------------------------
# Critério 4 — a cena para de mentir (o bug visível: "você saiu do quadro")
# --------------------------------------------------------------------------------------


def validador_da_flexao() -> SceneValidator:
    hints = PushUpAnalyzer().scene_hints()
    return SceneValidator(
        posture=hints.posture,
        body_range=hints.body_height_range,
        anchors=hints.frame_anchors,
    )


def test_flexao_frontal_bem_enquadrada_nao_avisa_nada() -> None:
    """O bug dos prints de produção, travado.

    Antes: a cena exigia tornozelo visível, de frente ele tem visibilidade 0,09, e o produto
    dizia "você saiu do quadro" a sessão inteira com o enquadramento perfeito.
    """
    validador = validador_da_flexao()
    frames = normalize(sequence(com_countdown(frontal_pushup_poses(6)), torso=0.30))

    avisos = [aviso for frame in frames for aviso in validador.check(frame)]

    assert avisos == []


def test_o_tornozelo_nao_e_ancora_da_flexao() -> None:
    """A âncora tem de ser o que a lente vê nas duas vistas — e o pé não é."""
    ancoras = PushUpAnalyzer().scene_hints().frame_anchors

    assert 27 not in ancoras and 28 not in ancoras


def test_flexao_frontal_longe_demais_ainda_avisa() -> None:
    """Afrouxar a régua não pode virar régua nenhuma."""
    validador = validador_da_flexao()
    frames = normalize(sequence([frontal_plank_pose()] * 60, torso=0.05))

    avisos = [aviso for frame in frames for aviso in validador.check(frame)]

    assert Code.TOO_FAR.value in {aviso.code.value for aviso in avisos}


# --------------------------------------------------------------------------------------
# Critério 5 — a vista pode ser forçada (o gancho da escolha do usuário)
# --------------------------------------------------------------------------------------


def test_vista_forcada_desliga_a_deteccao() -> None:
    """Fixar a vista é o gancho para o dia em que o usuário puder escolher na tela.

    Forçar PERFIL num vídeo frontal tem de ZERAR a contagem — não porque seja desejável, mas
    porque é a prova de que o parâmetro realmente manda na feature que conta.
    """
    frames = sequence(com_countdown(frontal_pushup_poses(6)))

    automatico = analisar(frames)[1]
    forcado = analisar(frames, PushUpAnalyzer(view=View.PROFILE))[1]

    assert reps(automatico) == 6
    assert reps(forcado) == 0


@pytest.mark.parametrize("hip_offset", [HIPS_ALIGNED, HIPS_SAGGED, HIPS_PIKED])
def test_qualidade_de_postura_nao_e_cobrada_de_frente(hip_offset: float) -> None:
    """`hip_line` se apoia no tornozelo, e de frente ele é um landmark adivinhado.

    Este teste nasceu de uma versão que passava sem provar nada: ele só exercitava o quadril
    ALINHADO, e o `evalctl` mostrou o produto acusando `HIPS_SAGGING` **e** `HIPS_PIKED` na
    mesma série real (35 e 17). Por isso ele agora varre também os dois desalinhamentos: o que
    se quer travar é que de frente o produto **se cale**, não que ele acerte por sorte quando
    não há nada para dizer.

    Contradição na mesma sessão é a assinatura de crítica inventada. Até existir uma feature de
    postura que não dependa do tornozelo, a vista frontal conta e não julga.
    """
    poses = com_countdown(frontal_pushup_poses(6, hip_offset=hip_offset))
    _, eventos = analisar(sequence(poses))

    assert reps(eventos) == 6
    assert Code.HIPS_SAGGING.value not in codigos(eventos)
    assert Code.HIPS_PIKED.value not in codigos(eventos)


def test_de_perfil_a_critica_de_quadril_continua_saindo() -> None:
    """A capacidade nova cala a vista frontal — não pode calar a que já funcionava."""
    poses = [*[pushup_poses(1)[0]] * COUNTDOWN, *pushup_poses(6, hip_offset=HIPS_SAGGED)]
    _, eventos = analisar(sequence(poses))

    assert Code.HIPS_SAGGING.value in codigos(eventos)


def test_pose_de_prontidao_frontal_e_a_prancha() -> None:
    analyzer = PushUpAnalyzer()
    frames = normalize(sequence([frontal_plank_pose()] * 30))
    for frame in frames:
        feats = analyzer.features(frame)

    assert analyzer.ready_pose(feats)


def test_pose_de_prontidao_recusa_quem_esta_em_pe() -> None:
    analyzer = PushUpAnalyzer()
    frames = normalize(sequence(still_poses(30)))
    for frame in frames:
        feats = analyzer.features(frame)

    assert not analyzer.ready_pose(feats)


def test_fundo_da_flexao_frontal_nao_e_pose_de_prontidao() -> None:
    analyzer = PushUpAnalyzer()
    frames = normalize(sequence(com_countdown(frontal_pushup_poses(2))))
    fundo = None
    for frame in frames:
        feats = analyzer.features(frame)
        if fundo is None or float(feats["depth"]) < fundo[0]:
            fundo = (float(feats["depth"]), feats)

    assert not analyzer.ready_pose(fundo[1])
