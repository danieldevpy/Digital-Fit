"""Gerador determinístico de keypoints sintéticos — fixtures sem câmera.

Constrói um "boneco" de 33 landmarks no padrão MediaPipe a partir de dois parâmetros que
descrevem um polichinelo: abdução dos braços (graus a partir do corpo estendido para baixo)
e afastamento dos tornozelos (múltiplos da largura de ombros). Isso permite testar
normalização (SPEC-006) e FSM (SPEC-007) variando **distância da câmera, posição no quadro,
fps e ruído** — as três coisas de que a normalização promete ser invariante.

Coordenadas no padrão MediaPipe: `x` para a direita, `y` para **baixo**, ambas 0–1 no frame.
Fixtures gravadas de sessões reais chegam com a T-007 (gravador no cliente) e o corpus de
vídeos com a T-038; estas sintéticas cobrem o que precisa ser exato e reprodutível.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from workers.shared.normalize import RawFrame

# Proporções do boneco, em torsos (ombro-médio → quadril-médio = 1.0).
_SHOULDER_WIDTH = 0.45
_HIP_WIDTH = 0.30
_ARM_LENGTH = 0.75
_LEG_LENGTH = 1.05
_HEAD_OFFSET = 0.32

# Ângulos de braço (graus a partir de "braços colados no corpo, apontando para baixo").
ARMS_DOWN = 12.0
ARMS_UP = 168.0
# Afastamento de tornozelos, em larguras de ombro.
FEET_TOGETHER = 0.55
FEET_APART = 1.75
# Ângulo do joelho (quadril–joelho–tornozelo), em graus. 180° seria trava articular, que
# ninguém faz nem deve fazer; "em pé" é quase reto.
KNEE_STRAIGHT = 180.0
KNEE_STANDING = 172.0
KNEE_SQUAT = 80.0
# Pés na largura dos ombros — a base de um agachamento, mais aberta que "pés juntos".
FEET_SHOULDER_WIDTH = 1.0

#: Quanto do avanço do joelho aparece numa câmera FRONTAL. O joelho de um agachamento viaja
#: sobretudo para a FRENTE (eixo de profundidade), e de frente isso quase não se vê — o que
#: se vê é o joelho abrindo um pouco para fora. Este fator é a projeção desse avanço no
#: plano da imagem, e é baixo de propósito: uma fixture que mostrasse o ângulo do joelho
#: inteiro de frente produziria uma FSM que só funciona em vídeo lateral.
_KNEE_FRONTAL_PROJECTION = 0.35


@dataclass(frozen=True, slots=True)
class Pose:
    """Uma configuração do corpo, independente de escala e posição no quadro.

    Era só polichinelo (braço + tornozelo). `knee_angle` entrou na T-052 para que o segundo
    exercício tenha fixture — sem gerador não há critério de aceite, e os critérios da
    SPEC-007 são todos baseados em fixture.

    O default `KNEE_STRAIGHT` mantém toda pose antiga idêntica ao byte: perna reta é
    exatamente a geometria que existia antes, e é isso que faz a extensão não mexer em
    nenhuma das fixtures do polichinelo.
    """

    arm_angle: float = ARMS_DOWN
    ankle_spread: float = FEET_TOGETHER
    #: Ângulo quadril–joelho–tornozelo. Menor = mais agachado.
    knee_angle: float = KNEE_STRAIGHT


def stick_figure(
    pose: Pose,
    *,
    torso: float = 0.30,
    center: tuple[float, float] = (0.5, 0.55),
    visibility: float = 0.95,
) -> list[list[float]]:
    """33 landmarks `[x, y, z, visibility]` para uma pose.

    `torso` é o comprimento do torso em unidades de frame — é ele que representa a distância
    da câmera (0.30 ≈ pessoa a 2 m; 0.15 ≈ a 4 m). `center` é o quadril médio no quadro.
    """
    cx, cy = center
    shoulder_w = _SHOULDER_WIDTH * torso
    hip_w = _HIP_WIDTH * torso
    arm = _ARM_LENGTH * torso
    leg = _LEG_LENGTH * torso

    # Pernas primeiro: quando o joelho dobra, é o QUADRIL que desce — o chão não se move.
    # `center` continua sendo o quadril de quem está em pé, então nenhuma fixture antiga muda.
    half_gap = pose.ankle_spread * shoulder_w / 2
    # Coxa e canela têm metade da perna cada; o ângulo do joelho encurta a distância
    # quadril→tornozelo por trigonometria do triângulo isósceles.
    hip_to_ankle = leg * math.sin(math.radians(pose.knee_angle) / 2)
    drop = math.sqrt(max(hip_to_ankle**2 - half_gap**2, (0.2 * leg) ** 2))
    drop_em_pe = math.sqrt(max(leg**2 - half_gap**2, (0.2 * leg) ** 2))
    descida = drop_em_pe - drop  # zero com a perna reta

    hip_y = cy + descida
    shoulder_y = hip_y - torso
    ground_y = cy + drop_em_pe

    # Braços: ângulo medido a partir do vetor "para baixo", abrindo para fora.
    theta = math.radians(pose.arm_angle)
    dx, dy = math.sin(theta), math.cos(theta)

    left_shoulder = (cx - shoulder_w / 2, shoulder_y)
    right_shoulder = (cx + shoulder_w / 2, shoulder_y)
    left_wrist = (left_shoulder[0] - arm * dx, left_shoulder[1] + arm * dy)
    right_wrist = (right_shoulder[0] + arm * dx, right_shoulder[1] + arm * dy)
    left_elbow = ((left_shoulder[0] + left_wrist[0]) / 2, (left_shoulder[1] + left_wrist[1]) / 2)
    right_elbow = (
        (right_shoulder[0] + right_wrist[0]) / 2,
        (right_shoulder[1] + right_wrist[1]) / 2,
    )

    # Tornozelos afastados por `ankle_spread` larguras de ombro, apoiados no chão.
    left_hip = (cx - hip_w / 2, hip_y)
    right_hip = (cx + hip_w / 2, hip_y)
    left_ankle = (cx - half_gap, ground_y)
    right_ankle = (cx + half_gap, ground_y)

    # O joelho sai da reta quadril→tornozelo na medida em que a perna dobra. `desvio` é o
    # avanço real do joelho (cateto do triângulo isósceles); só uma fração dele aparece numa
    # câmera frontal, e é essa fração que vai para o x.
    metade = hip_to_ankle / 2
    desvio = math.sqrt(max((leg / 2) ** 2 - metade**2, 0.0)) * _KNEE_FRONTAL_PROJECTION
    left_knee = ((left_hip[0] + left_ankle[0]) / 2 - desvio, (left_hip[1] + left_ankle[1]) / 2)
    right_knee = ((right_hip[0] + right_ankle[0]) / 2 + desvio, (right_hip[1] + right_ankle[1]) / 2)

    nose = (cx, shoulder_y - _HEAD_OFFSET * torso)
    eye_dx, eye_dy = 0.05 * torso, 0.04 * torso
    ear_dx = 0.09 * torso
    mouth_dy = 0.08 * torso
    hand_dx = 0.05 * torso
    heel = 0.06 * torso
    toe = 0.12 * torso

    points: list[tuple[float, float]] = [
        nose,  # 0
        (nose[0] - eye_dx / 2, nose[1] - eye_dy),  # 1 left_eye_inner
        (nose[0] - eye_dx, nose[1] - eye_dy),  # 2 left_eye
        (nose[0] - eye_dx * 1.5, nose[1] - eye_dy),  # 3 left_eye_outer
        (nose[0] + eye_dx / 2, nose[1] - eye_dy),  # 4 right_eye_inner
        (nose[0] + eye_dx, nose[1] - eye_dy),  # 5 right_eye
        (nose[0] + eye_dx * 1.5, nose[1] - eye_dy),  # 6 right_eye_outer
        (nose[0] - ear_dx, nose[1]),  # 7 left_ear
        (nose[0] + ear_dx, nose[1]),  # 8 right_ear
        (nose[0] - eye_dx / 2, nose[1] + mouth_dy),  # 9 mouth_left
        (nose[0] + eye_dx / 2, nose[1] + mouth_dy),  # 10 mouth_right
        left_shoulder,  # 11
        right_shoulder,  # 12
        left_elbow,  # 13
        right_elbow,  # 14
        left_wrist,  # 15
        right_wrist,  # 16
        (left_wrist[0] - hand_dx * dx, left_wrist[1] + hand_dx * dy),  # 17 left_pinky
        (right_wrist[0] + hand_dx * dx, right_wrist[1] + hand_dx * dy),  # 18 right_pinky
        (left_wrist[0] - hand_dx * dx * 1.2, left_wrist[1] + hand_dx * dy * 1.2),  # 19 left_index
        (right_wrist[0] + hand_dx * dx * 1.2, right_wrist[1] + hand_dx * dy * 1.2),  # 20
        (left_wrist[0] - hand_dx * dx * 0.6, left_wrist[1] + hand_dx * dy * 0.6),  # 21 left_thumb
        (right_wrist[0] + hand_dx * dx * 0.6, right_wrist[1] + hand_dx * dy * 0.6),  # 22
        left_hip,  # 23
        right_hip,  # 24
        left_knee,  # 25
        right_knee,  # 26
        left_ankle,  # 27
        right_ankle,  # 28
        (left_ankle[0], left_ankle[1] + heel),  # 29 left_heel
        (right_ankle[0], right_ankle[1] + heel),  # 30 right_heel
        (left_ankle[0] - toe / 2, left_ankle[1] + heel),  # 31 left_foot_index
        (right_ankle[0] + toe / 2, right_ankle[1] + heel),  # 32 right_foot_index
    ]

    return [[x, y, 0.0, visibility] for x, y in points]


def _jitter(landmarks: list[list[float]], sigma: float, rng) -> list[list[float]]:
    """Ruído gaussiano nas coordenadas — imita o tremor do modelo de pose."""
    return [
        [x + rng.gauss(0.0, sigma), y + rng.gauss(0.0, sigma), z, visibility]
        for x, y, z, visibility in landmarks
    ]


def sequence(
    poses: list[Pose],
    *,
    fps: float = 15.0,
    torso: float = 0.30,
    center: tuple[float, float] = (0.5, 0.55),
    visibility: float = 0.95,
    jitter: float = 0.0,
    seed: int = 7,
    start_ts: int = 1_722_100_000_000,
) -> list[RawFrame]:
    """Transforma uma lista de poses em frames com `ts`/`seq` coerentes."""
    rng = random.Random(seed)
    step_ms = 1000.0 / fps
    frames: list[RawFrame] = []
    for index, pose in enumerate(poses):
        landmarks = stick_figure(pose, torso=torso, center=center, visibility=visibility)
        if jitter:
            landmarks = _jitter(landmarks, jitter, rng)
        frames.append(
            RawFrame(ts=start_ts + round(index * step_ms), seq=index, landmarks=landmarks)
        )
    return frames


def still_poses(count: int) -> list[Pose]:
    """Pessoa parada em pé (braços baixos, pés juntos) — base para medir jitter."""
    return [Pose()] * count


#: Frames parados suficientes para a calibração fechar: a SPEC-004 pede mediana de 1 s, e a
#: 15 fps isso são 16 frames. 20 dá folga sem alongar os testes.
COUNTDOWN_FRAMES = 20


def session_poses(poses: list[Pose], *, countdown: int = COUNTDOWN_FRAMES) -> list[Pose]:
    """Poses de uma sessão REAL: countdown parado e depois o exercício.

    Existe porque a T-019 tornou a calibração parte do caminho: o worker mede o corpo no
    primeiro segundo e só então começa a contar. Uma fixture que emenda direto no exercício
    não representa mais nenhuma sessão de verdade — e perderia a primeira repetição, que é
    exatamente o que se veria em produção se o countdown não existisse.
    """
    return [*still_poses(countdown), *poses]


def jumping_jack_poses(
    reps: int, *, frames_per_rep: int = 15, amplitude: float = 1.0
) -> list[Pose]:
    """Poses de `reps` polichinelos contínuos, interpolados por cosseno.

    `amplitude` < 1 encolhe o movimento (rep "preguiçosa"): 0.6 chega a ~105° de braço, abaixo
    do limiar de 110° da SPEC-007.

    A sequência **termina em pé, fechado** (dois frames de sobra): uma gravação real acaba com
    a pessoa parada, e sem isso a última repetição ficaria eternamente "em andamento".
    """
    poses: list[Pose] = []
    for _rep in range(reps):
        for index in range(frames_per_rep):
            # 0 → 1 → 0 ao longo da rep (fechado → aberto → fechado).
            fraction = (1 - math.cos(2 * math.pi * index / frames_per_rep)) / 2 * amplitude
            poses.append(
                Pose(
                    arm_angle=ARMS_DOWN + (ARMS_UP - ARMS_DOWN) * fraction,
                    ankle_spread=FEET_TOGETHER + (FEET_APART - FEET_TOGETHER) * fraction,
                )
            )
    return [*poses, Pose(), Pose()]


def standing_pose(*, feet: float = FEET_SHOULDER_WIDTH) -> Pose:
    """Em pé para agachar: pés na largura dos ombros, joelho quase reto, braços baixos."""
    return Pose(ankle_spread=feet, knee_angle=KNEE_STANDING)


def squat_poses(
    reps: int,
    *,
    frames_per_rep: int = 15,
    amplitude: float = 1.0,
    feet: float = FEET_SHOULDER_WIDTH,
) -> list[Pose]:
    """Poses de `reps` agachamentos contínuos, interpolados por cosseno (T-052).

    Mesma forma de `jumping_jack_poses` de propósito — `amplitude` < 1 é o agachamento raso,
    que é o análogo da rep preguiçosa, e a sequência termina **em pé** para a última repetição
    não ficar eternamente em andamento.

    Os braços ficam parados: o que define um agachamento é a perna. Quem quiser variar o
    braço (à frente, na nuca) monta a `Pose` na mão — não é o caso comum.
    """
    em_pe = standing_pose(feet=feet)
    poses: list[Pose] = []
    for _rep in range(reps):
        for index in range(frames_per_rep):
            fraction = (1 - math.cos(2 * math.pi * index / frames_per_rep)) / 2 * amplitude
            poses.append(
                Pose(
                    ankle_spread=feet,
                    knee_angle=KNEE_STANDING + (KNEE_SQUAT - KNEE_STANDING) * fraction,
                )
            )
    return [*poses, em_pe, em_pe]
