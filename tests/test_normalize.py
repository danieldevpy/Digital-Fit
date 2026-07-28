"""Testes da normalização (T-006 / SPEC-006).

Os três critérios de aceite da spec, um teste cada, mais as invariâncias que o resto do
pipeline assume. O módulo mais crítico para regressão: qualquer mudança aqui move todos os
exercícios (SPEC-006, notas técnicas).
"""

import math

import numpy as np
import pytest

from tests.synthetic_keypoints import (
    ARMS_DOWN,
    ARMS_UP,
    FEET_APART,
    FEET_TOGETHER,
    Pose,
    jumping_jack_poses,
    sequence,
    stick_figure,
    still_poses,
)
from workers.shared.normalize import (
    ANCHOR_LANDMARKS,
    VISIBILITY_THRESHOLD,
    Baseline,
    Normalizer,
    NormFrame,
    NormParams,
    RawFrame,
    normalize,
)

LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_ANKLE, RIGHT_ANKLE = 27, 28

#: Sem filtragem: isola o efeito geométrico da normalização nos testes de invariância.
SEM_FILTRO = NormParams(mincutoff=1e6, beta=0.0, scale_mincutoff=1e6)


# --------------------------------------------------------------------------------------
# Features geométricas — versão de teste, propositalmente independente da SPEC-007 (T-008)
# --------------------------------------------------------------------------------------


def arm_angle(frame: NormFrame) -> float:
    """Abdução média dos braços (graus a partir do braço apontando para baixo)."""
    angulos = []
    for ombro, pulso in ((LEFT_SHOULDER, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_WRIST)):
        dx, dy = frame.points[pulso][:2] - frame.points[ombro][:2]
        angulos.append(math.degrees(math.atan2(abs(dx), dy)))
    return sum(angulos) / 2


def ankle_spread(frame: NormFrame) -> float:
    """Distância entre tornozelos ÷ largura dos ombros (ambos já em torsos)."""
    tornozelos = abs(frame.points[LEFT_ANKLE][0] - frame.points[RIGHT_ANKLE][0])
    ombros = abs(frame.points[LEFT_SHOULDER][0] - frame.points[RIGHT_SHOULDER][0])
    return float(tornozelos / ombros)


def um_frame(pose: Pose, **kwargs) -> NormFrame:
    frames = sequence([pose], **kwargs)
    return normalize(frames, params=SEM_FILTRO)[0]


# --------------------------------------------------------------------------------------
# Critério 1 — invariância a distância da câmera (2 m vs 4 m)
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pose",
    [
        Pose(arm_angle=ARMS_DOWN, ankle_spread=FEET_TOGETHER),
        Pose(arm_angle=ARMS_UP, ankle_spread=FEET_APART),
        Pose(arm_angle=90.0, ankle_spread=1.2),
    ],
    ids=["fechado", "aberto", "meio"],
)
def test_features_nao_mudam_com_a_distancia_da_camera(pose: Pose) -> None:
    """SPEC-006, critério 1: mesma pose a 2 m e a 4 m ⇒ features diferem < 5%."""
    perto = um_frame(pose, torso=0.30)  # ~2 m
    longe = um_frame(pose, torso=0.15)  # ~4 m

    assert arm_angle(longe) == pytest.approx(arm_angle(perto), rel=0.05)
    assert ankle_spread(longe) == pytest.approx(ankle_spread(perto), rel=0.05)


def test_features_nao_mudam_com_a_posicao_no_quadro() -> None:
    pose = Pose(arm_angle=120.0, ankle_spread=1.5)

    centro = um_frame(pose, center=(0.5, 0.55))
    canto = um_frame(pose, center=(0.25, 0.40))

    assert arm_angle(canto) == pytest.approx(arm_angle(centro), rel=0.01)
    assert ankle_spread(canto) == pytest.approx(ankle_spread(centro), rel=0.01)


def test_sequencia_inteira_e_invariante_a_escala() -> None:
    poses = jumping_jack_poses(3)

    perto = normalize(sequence(poses, torso=0.30), params=SEM_FILTRO)
    longe = normalize(sequence(poses, torso=0.15), params=SEM_FILTRO)

    for frame_perto, frame_longe in zip(perto, longe, strict=True):
        assert frame_longe.points == pytest.approx(frame_perto.points, abs=1e-6)


# --------------------------------------------------------------------------------------
# Critério 2 — jitter cai ≥ 60% sem atrasar movimento rápido
# --------------------------------------------------------------------------------------


def _serie_pulso(frames: list[RawFrame], params: NormParams) -> np.ndarray:
    return np.array([frame.points[LEFT_WRIST][1] for frame in normalize(frames, params=params)])


def test_jitter_de_pessoa_parada_cai_pelo_menos_60_porcento() -> None:
    """SPEC-006, critério 2 (primeira metade)."""
    frames = sequence(still_poses(180), jitter=0.004, seed=3)

    cru = _serie_pulso(frames, SEM_FILTRO)
    filtrado = _serie_pulso(frames, NormParams())

    transitorio = 30
    reducao = 1 - float(np.std(filtrado[transitorio:]) / np.std(cru[transitorio:]))
    assert reducao >= 0.60, f"reducao de jitter insuficiente: {reducao:.1%}"


def test_movimento_rapido_nao_atrasa_mais_de_um_frame() -> None:
    """SPEC-006, critério 2 (segunda metade): ~1.5 rep/s, o mais rápido plausível."""
    frames = sequence(jumping_jack_poses(6, frames_per_rep=10), fps=15.0)

    limpo = _serie_pulso(frames, SEM_FILTRO)[15:]
    filtrado = _serie_pulso(frames, NormParams())[15:]

    centrado_limpo = limpo - limpo.mean()
    centrado_filtrado = filtrado - filtrado.mean()
    correlacao = [
        float(np.dot(centrado_limpo[: len(limpo) - atraso], centrado_filtrado[atraso:]))
        for atraso in range(6)
    ]
    atraso_frames = int(np.argmax(correlacao))

    assert atraso_frames <= 1, f"atraso de {atraso_frames} frames"
    # E o movimento continua lá: amplitude preservada dentro de 10%.
    assert float(np.ptp(filtrado)) >= 0.90 * float(np.ptp(limpo))


def test_filtro_nao_mexe_na_visibilidade() -> None:
    """SPEC-006, notas: nunca filtrar `visibility` — só coordenadas."""
    frames = sequence(still_poses(30), jitter=0.004, visibility=0.77)

    saida = normalize(frames)

    for frame in saida:
        assert frame.visibility == pytest.approx(0.77)


# --------------------------------------------------------------------------------------
# Critério 3 — função pura
# --------------------------------------------------------------------------------------


def test_normalize_e_pura_mesma_entrada_mesma_saida() -> None:
    """SPEC-006, critério 3: sem estado escondido entre chamadas."""
    frames = sequence(jumping_jack_poses(2), jitter=0.003)

    primeira = normalize(frames)
    segunda = normalize(frames)

    for a, b in zip(primeira, segunda, strict=True):
        assert a.points == pytest.approx(b.points)
        assert (a.ts, a.seq, a.torso, a.degraded) == (b.ts, b.seq, b.torso, b.degraded)


def test_normalize_nao_altera_a_entrada() -> None:
    frames = sequence(jumping_jack_poses(1))
    copia = [[list(ponto) for ponto in frame.landmarks] for frame in frames]

    normalize(frames)

    assert [[list(p) for p in f.landmarks] for f in frames] == copia


def test_normalizer_mantem_estado_entre_frames() -> None:
    """O worker alimenta frame a frame; o filtro tem de continuar de onde parou."""
    frames = sequence(jumping_jack_poses(2), jitter=0.003)
    normalizer = Normalizer()

    incremental = [normalizer.push(frame) for frame in frames]

    for a, b in zip(incremental, normalize(frames), strict=True):
        assert a.points == pytest.approx(b.points)


# --------------------------------------------------------------------------------------
# Geometria canônica
# --------------------------------------------------------------------------------------


def test_origem_fica_no_quadril_medio() -> None:
    frame = um_frame(Pose(arm_angle=100.0, ankle_spread=1.3), center=(0.3, 0.7))

    quadril_medio = (frame.points[LEFT_HIP] + frame.points[RIGHT_HIP]) / 2

    assert quadril_medio == pytest.approx([0.0, 0.0, 0.0], abs=1e-9)


def test_torso_vale_um_apos_normalizar() -> None:
    frame = um_frame(Pose(), torso=0.22)

    ombro_medio = (frame.points[LEFT_SHOULDER] + frame.points[RIGHT_SHOULDER]) / 2
    quadril_medio = (frame.points[LEFT_HIP] + frame.points[RIGHT_HIP]) / 2

    assert float(np.linalg.norm(ombro_medio[:2] - quadril_medio[:2])) == pytest.approx(
        1.0, abs=1e-6
    )


def test_torso_em_unidades_de_frame_e_preservado_para_quem_precisa_de_escala() -> None:
    """SPEC-003 usa a escala absoluta para julgar distância (TOO_FAR/TOO_CLOSE)."""
    perto = um_frame(Pose(), torso=0.30)
    longe = um_frame(Pose(), torso=0.15)

    assert perto.torso == pytest.approx(0.30, rel=0.02)
    assert longe.torso == pytest.approx(0.15, rel=0.02)


def test_eixo_y_continua_apontando_para_baixo() -> None:
    """Convenção MediaPipe: ombros ficam acima do quadril, logo com y negativo."""
    frame = um_frame(Pose())

    assert frame.points[LEFT_SHOULDER][1] < 0
    assert frame.points[LEFT_ANKLE][1] > 0


# --------------------------------------------------------------------------------------
# Qualidade do frame (degraded) e baseline
# --------------------------------------------------------------------------------------


def test_frame_com_ancoras_invisiveis_e_marcado_degraded() -> None:
    frames = sequence(still_poses(3), visibility=0.2)

    for frame in normalize(frames):
        assert frame.degraded


def test_frame_com_ancoras_visiveis_nao_e_degraded() -> None:
    for frame in normalize(sequence(still_poses(3), visibility=0.9)):
        assert not frame.degraded


def test_apenas_as_ancoras_decidem_degraded() -> None:
    """Rosto e mãos invisíveis não invalidam o frame — âncoras invisíveis, sim."""
    landmarks = stick_figure(Pose())
    for indice in range(33):
        if indice not in ANCHOR_LANDMARKS:
            landmarks[indice][3] = 0.0

    frame = normalize([RawFrame(ts=1000, seq=0, landmarks=landmarks)])[0]

    assert not frame.degraded


def test_limiar_de_visibilidade_e_o_da_convencao() -> None:
    acima = stick_figure(Pose(), visibility=VISIBILITY_THRESHOLD + 0.01)
    abaixo = stick_figure(Pose(), visibility=VISIBILITY_THRESHOLD - 0.01)

    assert not normalize([RawFrame(ts=1000, seq=0, landmarks=acima)])[0].degraded
    assert normalize([RawFrame(ts=1000, seq=0, landmarks=abaixo)])[0].degraded


def test_frame_degradado_nao_polui_o_filtro() -> None:
    """Landmarks 'adivinhados' pelo modelo não devem contaminar os frames bons seguintes."""
    bons = sequence(still_poses(20), jitter=0.001, seed=5)
    ruim = RawFrame(
        ts=bons[-1].ts + 66,
        seq=len(bons),
        landmarks=stick_figure(Pose(arm_angle=170.0), visibility=0.1),
    )
    depois = sequence(still_poses(5), start_ts=ruim.ts + 66, jitter=0.001, seed=6)

    saida = normalize(
        [
            *bons,
            ruim,
            *[RawFrame(f.ts, len(bons) + 1 + i, f.landmarks) for i, f in enumerate(depois)],
        ]
    )

    assert saida[20].degraded
    # O primeiro frame bom depois do ruim segue perto da pose parada, não do salto.
    assert saida[21].points[LEFT_WRIST][1] == pytest.approx(
        saida[19].points[LEFT_WRIST][1], abs=0.05
    )


def test_baseline_fixa_a_escala_da_sessao() -> None:
    """Com baseline (SPEC-004/T-019), a escala não oscila com a medida do frame."""
    frames = sequence(jumping_jack_poses(2), jitter=0.004)

    saida = normalize(frames, baseline=Baseline(torso=0.30, shoulder_width=0.14))

    assert {frame.torso for frame in saida} == {0.30}
    assert {frame.shoulder_width for frame in saida} == {0.14}


def test_sem_baseline_a_escala_vem_do_frame() -> None:
    saida = normalize(sequence(still_poses(5), torso=0.25))

    assert saida[-1].torso == pytest.approx(0.25, rel=0.05)


# --------------------------------------------------------------------------------------
# Contrato de saída e erros
# --------------------------------------------------------------------------------------


def test_to_data_serializa_para_o_campo_norm_do_pose_frame() -> None:
    frame = normalize(sequence(still_poses(1)))[0]

    data = frame.to_data()

    assert set(data) == {"points", "torso", "shoulder_width"}
    assert len(data["points"]) == 33
    assert all(len(ponto) == 3 for ponto in data["points"])


def test_ts_e_seq_atravessam_a_normalizacao() -> None:
    frames = sequence(still_poses(4))

    saida = normalize(frames)

    assert [f.ts for f in saida] == [f.ts for f in frames]
    assert [f.seq for f in saida] == [0, 1, 2, 3]


@pytest.mark.parametrize("landmarks", [[], [[0.0, 0.0, 0.0, 1.0]] * 32, [[0.0, 0.0]] * 33])
def test_forma_errada_de_landmarks_falha_cedo(landmarks: list) -> None:
    with pytest.raises(ValueError, match="33x4"):
        normalize([RawFrame(ts=1000, seq=0, landmarks=landmarks)])


def test_sequencia_vazia_devolve_lista_vazia() -> None:
    assert normalize([]) == []


def test_torso_colapsado_nao_explode_as_coordenadas() -> None:
    """Landmarks empilhados (falha do modelo) não podem virar divisão por zero."""
    landmarks = [[0.5, 0.5, 0.0, 0.9] for _ in range(33)]

    frame = normalize([RawFrame(ts=1000, seq=0, landmarks=landmarks)])[0]

    assert np.all(np.isfinite(frame.points))
