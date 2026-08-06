"""Validação de cena mínima (T-013 / SPEC-003)."""

import dataclasses

import numpy as np
import pytest

from tests.synthetic_keypoints import (
    Pose,
    jumping_jack_poses,
    plank_pose,
    pushup_poses,
    sequence,
    still_poses,
)
from workers.analysis_worker.exercises import Posture
from workers.analysis_worker.exercises.flexao import PushUpAnalyzer
from workers.analysis_worker.scene import (
    FRAME_ANCHORS,
    MAX_BODY_HEIGHT,
    MIN_BODY_HEIGHT,
    REPEAT_AFTER_MS,
    TRIGGER_AFTER_MS,
    SceneValidator,
)
from workers.shared.events import Code, SceneWarning, Severity
from workers.shared.normalize import RawFrame, normalize

# O boneco tem ~2,37 torsos de cabeça a tornozelo, então torso=0.20 ⇒ ~47% do frame (cena boa),
# torso=0.12 ⇒ ~28% (longe) e torso=0.42 ⇒ ~100% (perto).
TORSO_CENA_BOA = 0.20
TORSO_LONGE = 0.12
TORSO_PERTO = 0.42


def frames_normalizados(poses, **kwargs):
    return normalize(sequence(poses, **kwargs))


def avisos_de(poses, validator: SceneValidator | None = None, **kwargs) -> list[SceneWarning]:
    validator = validator or SceneValidator()
    return [
        aviso for frame in frames_normalizados(poses, **kwargs) for aviso in validator.check(frame)
    ]


def codigos(avisos) -> list[str]:
    return [aviso.code.value for aviso in avisos]


def validador_do_exercicio(analyzer, **kwargs) -> SceneValidator:
    """Validador montado com a régua que o EXERCÍCIO declara (T-108).

    Repetir os números aqui dentro seria testar a cópia, não o produto: foi assim que a
    faixa da flexão continuou parecendo certa num teste enquanto o `scene_hints()` dela
    dizia outra coisa. O que se quer travar é "o exercício declara e o validador obedece".
    """
    hints = analyzer.scene_hints()
    return SceneValidator(
        posture=hints.posture,
        body_range=hints.body_height_range,
        anchors=hints.frame_anchors,
        **kwargs,
    )


def espelha_no_x(frame):
    """O mesmo frame com o corpo deitado para o outro lado."""
    pontos = np.array(frame.points, dtype=float)
    pontos[:, 0] = -pontos[:, 0]
    return dataclasses.replace(frame, points=pontos)


# --------------------------------------------------------------------------------------
# Enquadramento
# --------------------------------------------------------------------------------------


def test_cena_boa_nao_gera_aviso() -> None:
    """Critério 3 da SPEC-003: zero falso positivo em cena padrão (pessoa a 2–3 m)."""
    avisos = avisos_de(jumping_jack_poses(10), torso=TORSO_CENA_BOA)

    assert avisos == []


def test_ancoras_invisiveis_geram_out_of_frame() -> None:
    avisos = avisos_de(still_poses(60), torso=TORSO_CENA_BOA, visibility=0.2)

    assert Code.OUT_OF_FRAME.value in codigos(avisos)


def test_apenas_um_tornozelo_invisivel_ja_e_fora_do_quadro() -> None:
    """Corpo inteiro = ombros **e** tornozelos (SPEC-003)."""
    validator = SceneValidator()
    avisos: list[SceneWarning] = []
    for indice in range(40):
        landmarks = [
            list(ponto) for ponto in sequence(still_poses(1), torso=TORSO_CENA_BOA)[0].landmarks
        ]
        landmarks[27][3] = 0.1  # tornozelo esquerdo sumiu
        frame = normalize([RawFrame(ts=1_000_000 + indice * 66, seq=indice, landmarks=landmarks)])[
            0
        ]
        avisos.extend(validator.check(frame))

    assert codigos(avisos) == [Code.OUT_OF_FRAME.value] * len(avisos)
    assert avisos


def test_rosto_invisivel_nao_e_problema_de_enquadramento() -> None:
    validator = SceneValidator()
    avisos: list[SceneWarning] = []
    for indice in range(40):
        landmarks = [
            list(ponto) for ponto in sequence(still_poses(1), torso=TORSO_CENA_BOA)[0].landmarks
        ]
        for face in range(1, 11):
            landmarks[face][3] = 0.0
        frame = normalize([RawFrame(ts=1_000_000 + indice * 66, seq=indice, landmarks=landmarks)])[
            0
        ]
        avisos.extend(validator.check(frame))

    assert avisos == []


def test_fora_do_quadro_tem_prioridade_sobre_distancia() -> None:
    """Sem âncoras, medir distância seria medir landmarks adivinhados."""
    avisos = avisos_de(still_poses(60), torso=TORSO_LONGE, visibility=0.2)

    assert set(codigos(avisos)) == {Code.OUT_OF_FRAME.value}


# --------------------------------------------------------------------------------------
# Distância
# --------------------------------------------------------------------------------------


def test_pessoa_longe_demais_gera_too_far() -> None:
    avisos = avisos_de(still_poses(60), torso=TORSO_LONGE)

    assert Code.TOO_FAR.value in codigos(avisos)
    assert Code.TOO_CLOSE.value not in codigos(avisos)


def test_pessoa_perto_demais_gera_too_close() -> None:
    avisos = avisos_de(still_poses(60), torso=TORSO_PERTO)

    assert Code.TOO_CLOSE.value in codigos(avisos)
    assert Code.TOO_FAR.value not in codigos(avisos)


def test_altura_do_corpo_e_medida_em_fracao_do_frame() -> None:
    frame_bom = frames_normalizados(still_poses(1), torso=TORSO_CENA_BOA)[0]
    frame_longe = frames_normalizados(still_poses(1), torso=TORSO_LONGE)[0]
    frame_perto = frames_normalizados(still_poses(1), torso=TORSO_PERTO)[0]

    assert MIN_BODY_HEIGHT <= SceneValidator.body_height(frame_bom) <= MAX_BODY_HEIGHT
    assert SceneValidator.body_height(frame_longe) < MIN_BODY_HEIGHT
    assert SceneValidator.body_height(frame_perto) > MAX_BODY_HEIGHT


def test_faixa_de_distancia_e_a_da_spec() -> None:
    assert (MIN_BODY_HEIGHT, MAX_BODY_HEIGHT) == (0.40, 0.95)


def test_polichinelo_em_cena_boa_nao_dispara_distancia() -> None:
    """O movimento muda a altura aparente; isso não pode virar TOO_CLOSE/TOO_FAR."""
    avisos = avisos_de(jumping_jack_poses(20), torso=TORSO_CENA_BOA)

    assert avisos == []


# --------------------------------------------------------------------------------------
# Debounce (critério 1 da SPEC-003)
# --------------------------------------------------------------------------------------


def test_condicao_curta_nao_gera_aviso() -> None:
    """Meio segundo fora do quadro é ruído do modelo, não erro do usuário."""
    validator = SceneValidator()
    frames = frames_normalizados(still_poses(7), torso=TORSO_CENA_BOA, visibility=0.2)  # ~0,47 s

    avisos = [aviso for frame in frames for aviso in validator.check(frame)]

    assert avisos == []


def test_dois_segundos_fora_do_quadro_geram_exatamente_um_aviso() -> None:
    """Critério 1 da SPEC-003: um warning, não spam."""
    validator = SceneValidator()
    frames = frames_normalizados(still_poses(30), torso=TORSO_CENA_BOA, visibility=0.2)  # 2 s

    avisos = [aviso for frame in frames for aviso in validator.check(frame)]

    assert codigos(avisos) == [Code.OUT_OF_FRAME.value]


def test_condicao_longa_repete_no_intervalo_configurado() -> None:
    """6 s fora do quadro: avisa em 1 s e repete a cada 2 s ⇒ 3 avisos."""
    validator = SceneValidator()
    frames = frames_normalizados(still_poses(90), torso=TORSO_CENA_BOA, visibility=0.2)  # 6 s

    avisos = [aviso for frame in frames for aviso in validator.check(frame)]

    assert len(avisos) == 3


def test_condicao_que_resolve_e_volta_reinicia_a_contagem() -> None:
    validator = SceneValidator()
    ruins = frames_normalizados(still_poses(20), torso=TORSO_CENA_BOA, visibility=0.2)
    boas = frames_normalizados(still_poses(20), torso=TORSO_CENA_BOA, start_ts=ruins[-1].ts + 66)
    de_novo = frames_normalizados(
        still_poses(7), torso=TORSO_CENA_BOA, visibility=0.2, start_ts=boas[-1].ts + 66
    )

    avisos = [aviso for frame in [*ruins, *boas, *de_novo] for aviso in validator.check(frame)]

    # O segundo trecho ruim dura menos de 1 s ⇒ não avisa de novo.
    assert len(avisos) == 1


def test_parametros_de_debounce_sao_os_da_spec() -> None:
    assert (TRIGGER_AFTER_MS, REPEAT_AFTER_MS) == (1_000, 2_000)


def test_debounce_e_parametrizavel() -> None:
    imediato = SceneValidator(trigger_after_ms=0, repeat_after_ms=0)
    frames = frames_normalizados(still_poses(3), torso=TORSO_CENA_BOA, visibility=0.2)

    avisos = [aviso for frame in frames for aviso in imediato.check(frame)]

    assert len(avisos) == 3


# --------------------------------------------------------------------------------------
# Conteúdo do aviso e contagem
# --------------------------------------------------------------------------------------


def test_aviso_carrega_severidade_e_dica() -> None:
    aviso = avisos_de(still_poses(30), torso=TORSO_LONGE)[0]

    assert aviso.code is Code.TOO_FAR
    assert aviso.severity is Severity.WARNING
    assert aviso.hint and "aproxime" in aviso.hint.lower()


def test_validador_conta_avisos_para_o_relatorio() -> None:
    """SPEC-003: warnings são anexados ao relatório da sessão."""
    validator = SceneValidator()
    avisos_de(still_poses(90), validator, torso=TORSO_LONGE)

    assert validator.counts == {Code.TOO_FAR.value: 3}


def test_cada_sessao_tem_seu_proprio_debounce() -> None:
    primeiro = SceneValidator()
    segundo = SceneValidator()
    frames = frames_normalizados(still_poses(30), torso=TORSO_CENA_BOA, visibility=0.2)

    for frame in frames:
        primeiro.check(frame)

    assert primeiro.counts
    assert segundo.counts == {}


def test_ancoras_sao_ombros_e_tornozelos() -> None:
    assert set(FRAME_ANCHORS) == {11, 12, 27, 28}


@pytest.mark.parametrize("pose", [Pose(), Pose(arm_angle=170.0, ankle_spread=1.7)])
def test_avisos_nao_dependem_da_fase_do_movimento(pose: Pose) -> None:
    avisos = avisos_de([pose] * 60, torso=TORSO_CENA_BOA)

    assert avisos == []


# --------------------------------------------------------------------------------------
# Corpo deitado — a capacidade que o Tier C exigiu (T-106/T-107, SPEC-003 evolução)
# --------------------------------------------------------------------------------------


def test_corpo_deitado_medido_com_a_regua_de_quem_esta_em_pe_parece_longe_demais() -> None:
    """O bug que a postura existe para consertar, travado como teste.

    Numa flexão a cabeça e o tornozelo ficam quase na mesma ALTURA: a medida de quem está em
    pé dá quase zero e o produto pediria "aproxime-se" a sessão inteira, com o enquadramento
    perfeito. Se um dia alguém remover a postura, é aqui que aparece.
    """
    frame = frames_normalizados([plank_pose()], torso=0.16)[0]

    ancoras = PushUpAnalyzer().scene_hints().frame_anchors
    piso_do_exercicio = PushUpAnalyzer().scene_hints().body_height_range[0]

    assert SceneValidator.body_height(frame, Posture.STANDING) < MIN_BODY_HEIGHT
    assert SceneValidator.body_height(frame, Posture.FLOOR, ancoras) > piso_do_exercicio


def test_flexao_bem_enquadrada_nao_gera_aviso() -> None:
    validator = validador_do_exercicio(PushUpAnalyzer())

    avisos = avisos_de(pushup_poses(6), validator=validator, torso=0.16)

    assert avisos == []


def test_flexao_longe_demais_ainda_gera_too_far() -> None:
    """A trava não sumiu: ela passou a medir no eixo certo."""
    validator = validador_do_exercicio(PushUpAnalyzer())

    avisos = avisos_de([plank_pose()] * 60, validator=validator, torso=0.07)

    assert Code.TOO_FAR.value in codigos(avisos)


def test_deitar_para_o_outro_lado_nao_muda_o_enquadramento() -> None:
    """Cabeça à esquerda ou à direita dos pés é escolha de quem grava, não erro de cena."""
    validator = validador_do_exercicio(PushUpAnalyzer())
    frame = frames_normalizados([plank_pose()], torso=0.16)[0]
    espelhado = espelha_no_x(frame)

    ancoras = PushUpAnalyzer().scene_hints().frame_anchors
    assert SceneValidator.body_height(espelhado, Posture.FLOOR, ancoras) == pytest.approx(
        SceneValidator.body_height(frame, Posture.FLOOR, ancoras), abs=1e-6
    )
    assert validator.check(espelhado) == []


def test_a_postura_padrao_continua_sendo_em_pe() -> None:
    """Nenhuma sessão existente muda de resultado por causa desta capacidade."""
    assert SceneValidator().posture is Posture.STANDING
    assert SceneValidator().body_range == (MIN_BODY_HEIGHT, MAX_BODY_HEIGHT)
