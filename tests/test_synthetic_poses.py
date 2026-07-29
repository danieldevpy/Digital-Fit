"""Testes do gerador de poses sintéticas (T-052).

O gerador é a base de todos os critérios de aceite da SPEC-007 — se ele mentir, a FSM passa
nos testes e falha em vídeo. Por isso ele próprio tem testes: as invariantes que fazem dele
uma fixture confiável, e não um desenho bonito.
"""

import math

import pytest

from tests.synthetic_keypoints import (
    FEET_SHOULDER_WIDTH,
    KNEE_SQUAT,
    KNEE_STANDING,
    KNEE_STRAIGHT,
    Pose,
    jumping_jack_poses,
    sequence,
    squat_poses,
    standing_pose,
    stick_figure,
)
from workers.shared.events import Landmark

_LEFT_HIP, _LEFT_KNEE, _LEFT_ANKLE = Landmark.LEFT_HIP, Landmark.LEFT_KNEE, Landmark.LEFT_ANKLE
_LEFT_SHOULDER = Landmark.LEFT_SHOULDER


def ponto(landmarks, indice: Landmark) -> tuple[float, float]:
    x, y, _z, _v = landmarks[int(indice)]
    return x, y


def angulo(a: tuple[float, float], vertice: tuple[float, float], c: tuple[float, float]) -> float:
    """Ângulo em `vertice`, em graus — a mesma conta que uma FSM de agachamento faria."""
    ax, ay = a[0] - vertice[0], a[1] - vertice[1]
    cx, cy = c[0] - vertice[0], c[1] - vertice[1]
    cosseno = (ax * cx + ay * cy) / (math.hypot(ax, ay) * math.hypot(cx, cy))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosseno))))


# --------------------------------------------------------------------------------------
# A invariante que protege tudo que já existia
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("pose", [Pose(), *jumping_jack_poses(1)[::4]])
def test_perna_reta_gera_exatamente_o_boneco_de_antes(pose: Pose) -> None:
    """`knee_angle` entrou com default de perna reta justamente para isto.

    Toda fixture do polichinelo — e a bancada inteira que se compara contra elas — depende de
    os números não terem se mexido. Um deslocamento de milésimos aqui reescreveria em silêncio
    o significado de todos os limiares medidos até hoje.
    """
    assert pose.knee_angle == KNEE_STRAIGHT
    ombro = ponto(stick_figure(pose), _LEFT_SHOULDER)
    tornozelo = ponto(stick_figure(pose), _LEFT_ANKLE)

    # Com a perna reta, quadril→tornozelo é a perna inteira e o quadril está em `center`.
    quadril = ponto(stick_figure(pose), _LEFT_HIP)
    assert quadril[1] == pytest.approx(0.55)
    assert ombro[1] == pytest.approx(0.55 - 0.30)
    assert tornozelo[1] > quadril[1]


# --------------------------------------------------------------------------------------
# O que o agachamento precisa: quadril desce, chão fica
# --------------------------------------------------------------------------------------


def test_dobrar_o_joelho_desce_o_quadril() -> None:
    em_pe = stick_figure(standing_pose())
    agachado = stick_figure(Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT))

    # y cresce para baixo: descer é y maior.
    assert ponto(agachado, _LEFT_HIP)[1] > ponto(em_pe, _LEFT_HIP)[1]
    assert ponto(agachado, _LEFT_SHOULDER)[1] > ponto(em_pe, _LEFT_SHOULDER)[1]


def test_os_pes_ficam_no_chao() -> None:
    """O erro que tornaria a fixture inútil: agachar levantando os pés.

    Se o tornozelo subisse junto com o quadril, a altura do corpo no quadro não mudaria e a
    validação de cena (SPEC-003) veria um agachamento como alguém parado — enquanto em vídeo
    real o corpo encolhe visivelmente. A FSM nascida dessa fixture erraria no primeiro vídeo.
    """
    em_pe = stick_figure(standing_pose())
    agachado = stick_figure(Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT))

    assert ponto(agachado, _LEFT_ANKLE)[1] == pytest.approx(ponto(em_pe, _LEFT_ANKLE)[1])
    assert ponto(agachado, _LEFT_ANKLE)[0] == pytest.approx(ponto(em_pe, _LEFT_ANKLE)[0])


def test_o_corpo_encolhe_no_quadro_ao_agachar() -> None:
    """É esta a grandeza que uma câmera frontal enxerga de verdade — ver o teste abaixo.

    Medido: ombro→tornozelo cai a **81%** do valor em pé (0.491 contra 0.607). O número é
    CONSERVADOR de propósito quanto à realidade: um agachamento de verdade também inclina o
    tronco à frente, e de frente isso encurta ainda mais a projeção. O gerador mantém o tronco
    vertical, então mostra MENOS sinal do que o vídeo terá.

    Errar para menos é o lado seguro: a FSM calibrada nesta fixture não fica dependente de um
    encolhimento que o vídeo talvez não entregue. O contrário — fixture generosa — aprovaria
    limiares que reprovariam em produção.
    """

    def altura(pose: Pose) -> float:
        landmarks = stick_figure(pose)
        return ponto(landmarks, _LEFT_ANKLE)[1] - ponto(landmarks, _LEFT_SHOULDER)[1]

    razao = altura(Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT)) / altura(
        standing_pose()
    )

    assert razao == pytest.approx(0.81, abs=0.02)


def test_o_angulo_do_joelho_de_FRENTE_e_muito_menor_que_o_real() -> None:
    """A medição que a T-032 precisa saber ANTES de escolher as features.

    O joelho de um agachamento viaja para a FRENTE. De frente isso quase não se vê — a câmera
    mede um ângulo bem mais aberto que o real. Uma FSM que decidisse "agachou" por
    `knee_angle < 90°` lida do plano da imagem nunca dispararia em vídeo frontal.

    O gerador reproduz essa perda de propósito (`_KNEE_FRONTAL_PROJECTION`). Uma fixture que
    entregasse o ângulo verdadeiro de frente produziria uma FSM aprovada em teste e reprovada
    em vídeo — o pior resultado possível para uma bancada.
    """
    landmarks = stick_figure(Pose(ankle_spread=FEET_SHOULDER_WIDTH, knee_angle=KNEE_SQUAT))

    visto = angulo(
        ponto(landmarks, _LEFT_HIP), ponto(landmarks, _LEFT_KNEE), ponto(landmarks, _LEFT_ANKLE)
    )

    # Medido: 80° reais leem 133° de frente. Um limiar de "agachou" em 90° nunca dispararia.
    assert visto > KNEE_SQUAT + 40, f"de frente parece {visto:.0f}°, real {KNEE_SQUAT:.0f}°"


# --------------------------------------------------------------------------------------
# A sequência de repetições
# --------------------------------------------------------------------------------------


def test_squat_poses_vai_e_volta_e_termina_em_pe() -> None:
    poses = squat_poses(3, frames_per_rep=15)

    assert poses[0].knee_angle == pytest.approx(KNEE_STANDING)
    # Meio da primeira rep = ponto mais baixo.
    assert poses[7].knee_angle < KNEE_STANDING - 80
    # Termina em pé: sem isto a última repetição ficaria eternamente em andamento.
    assert poses[-1].knee_angle == pytest.approx(KNEE_STANDING)


def test_amplitude_menor_e_o_agachamento_raso() -> None:
    """O análogo da rep preguiçosa do polichinelo — é o critério 2 da SPEC-007 para a FSM 2."""
    fundo = min(pose.knee_angle for pose in squat_poses(2))
    raso = min(pose.knee_angle for pose in squat_poses(2, amplitude=0.5))

    assert raso > fundo


def test_squat_poses_atravessa_o_pipeline_de_normalizacao() -> None:
    """Não basta gerar `Pose`: tem de virar frame que a normalização aceita."""
    frames = sequence(squat_poses(2))

    assert len(frames) == 2 * 15 + 2
    assert all(len(frame.landmarks) == 33 for frame in frames)
    assert all(len(ponto_) == 4 for frame in frames for ponto_ in frame.landmarks)


def test_agachamento_nao_mexe_na_abertura_dos_tornozelos() -> None:
    """Agachar não é abrir as pernas — se mexesse, a feature do polichinelo confundiria os dois."""
    espalhamentos = {pose.ankle_spread for pose in squat_poses(3)}

    assert espalhamentos == {FEET_SHOULDER_WIDTH}
