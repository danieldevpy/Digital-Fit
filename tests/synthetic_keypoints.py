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

    Esta é a pose de quem está **em pé, de frente**. Os corpos deitados vistos de lado são a
    `PushUpPose` e a `CrunchPose` — geometria diferente demais para caber num parâmetro a
    mais (T-106/T-107).
    """

    arm_angle: float = ARMS_DOWN
    ankle_spread: float = FEET_TOGETHER
    #: Ângulo quadril–joelho–tornozelo. Menor = mais agachado.
    knee_angle: float = KNEE_STRAIGHT


def stick_figure(
    pose: Pose | PushUpPose | CrunchPose,
    *,
    torso: float = 0.30,
    center: tuple[float, float] = (0.5, 0.55),
    visibility: float = 0.95,
) -> list[list[float]]:
    """33 landmarks `[x, y, z, visibility]` para uma pose.

    `torso` é o comprimento do torso em unidades de frame — é ele que representa a distância
    da câmera (0.30 ≈ pessoa a 2 m; 0.15 ≈ a 4 m). `center` é o quadril médio no quadro.

    Despacha por tipo de pose: `PushUpPose` e `CrunchPose` montam o corpo deitado visto de
    lado (T-106/T-107). O despacho fica aqui, e não numa função separada, para `sequence()` —
    e portanto toda fixture, todo teste e o `evalctl` — continuar funcionando sem saber que
    existem duas geometrias.
    """
    if isinstance(pose, PushUpPose):
        return _pushup_figure(pose, torso=torso, center=center, visibility=visibility)
    if isinstance(pose, CrunchPose):
        return _crunch_figure(pose, torso=torso, center=center, visibility=visibility)

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


# ======================================================================================
# Corpo deitado, visto de lado (T-106 flexão / T-107 abdominal)
# ======================================================================================
#
# **Proporções próprias, e MEDIDAS — não as do boneco em pé.** O boneco de cima tem braço de
# 0.75 torsos e perna de 1.05; gente de verdade, medida no corpus da bancada pelo caminho
# real (vídeo → MediaPipe → `normalize()`), tem isto:
#
# ======================  =========================  ==============  ==========
# medida (em torsos)      corpus real (3 vídeos)     boneco em pé    aqui
# ======================  =========================  ==============  ==========
# ombro→pulso                    0.89 / 1.35 / 1.11       0.75          1.15
# quadril→tornozelo              1.33 / 1.85 / 1.50       1.05          1.65
# ombro→nariz                    0.32 / 0.37 / 0.48       0.32          0.37
# `hip_height` em pé             1.31 / 1.61 / 1.44       1.02           —
# ======================  =========================  ==============  ==========
#
# O boneco em pé não foi corrigido aqui de propósito: mexer nele muda toda fixture do
# polichinelo e do agachamento, e o efeito dessa divergência no agachamento virou Descoberta
# própria no BACKLOG (`[A/T-106]`) — o limiar de 0.72 torsos do `squat` foi calibrado contra
# 1.02 e gente real lê 1.44. Corrigir isso é task, não efeito colateral desta.
#
# A lição que os dois exercícios daqui absorveram: **feature de exercício novo é razão entre
# duas medidas do MESMO eixo do MESMO corpo**, nunca uma constante em torsos. Assim o
# gerador errar a proporção do boneco não vira limiar errado em produção.

#: Proporções do corpo deitado, em torsos. Ver a tabela acima.
_LAT_UPPER_ARM = 0.60
_LAT_FOREARM = 0.55
_LAT_THIGH = 0.85
_LAT_SHIN = 0.80
_LAT_NECK = 0.37
#: Altura do tornozelo com a ponta do pé no chão (prancha) — o pé tem espessura.
_LAT_ANKLE_LIFT = 0.15
#: Quanto o ombro/quadril de trás aparece atrás do da frente. Numa vista lateral perfeita os
#: dois lados coincidiriam e `shoulder_width` seria zero — o que não acontece em vídeo real e
#: deixaria a calibração medindo uma largura de ombros nula.
_LAT_SPLIT = 0.12
#: Visibilidade do lado de trás: o corpo esconde metade de si numa vista lateral. Fica acima
#: do limiar de `degraded` (0.5) porque o MediaPipe estima o lado ocluído em vez de desistir —
#: é o que se vê nos vídeos do corpus.
_LAT_FAR_VISIBILITY = 0.62

# Ângulos do cotovelo (ombro–cotovelo–pulso) da flexão, em graus. O topo não trava o
# cotovelo; o fundo é o padrão de execução que a literatura de treino usa (NASM/ACE): descer
# até ~90° de cotovelo, ou até o peito quase tocar o chão, o que vier primeiro.
ELBOW_TOP = 172.0
ELBOW_BOTTOM = 90.0
#: Desvio do quadril da linha ombro→tornozelo, em torsos. Positivo = quadril CAINDO (o erro
#: clássico da flexão); negativo = quadril empinado.
HIPS_ALIGNED = 0.0
HIPS_SAGGED = 0.22
HIPS_PIKED = -0.22

# Ângulos do tronco do abdominal, em graus a partir do chão. Deitado não é exatamente 0: o
# ombro tem espessura e fica um pouco acima do quadril.
TRUNK_FLAT = 4.0
#: Amplitude de um crunch bem executado: ~30° de flexão de tronco, com as escápulas saindo do
# chão. Passar muito disso deixa de ser crunch e vira abdominal completo (o quadril entra).
TRUNK_CRUNCH = 30.0
#: Ângulo da coxa com o chão na montagem do abdominal (joelho dobrado, pé apoiado). 58° põe o
#: joelho a 0.72 torsos do chão, que é o que a trigonometria dá para "calcanhar a 30–45 cm do
#: quadril" num corpo de 1,75 m.
THIGH_ANGLE = 58.0
#: Montagens extremas de perna, para medir o quanto a referência do joelho balança: pé longe
#: (coxa baixa) e pé colado no glúteo (coxa alta).
THIGH_FEET_FAR = 45.0
THIGH_FEET_CLOSE = 72.0


@dataclass(frozen=True, slots=True)
class PushUpPose:
    """Uma flexão vista de lado, celular no chão (T-106).

    Dois parâmetros, que são exatamente os dois eixos que a FSM julga: quanto o cotovelo
    dobrou (a repetição) e quanto o quadril saiu da linha do corpo (a qualidade).

    As mãos ficam no chão e o ombro desce sobre elas — é assim que uma flexão se parece de
    lado, e é por isso que a altura do ombro sobre o pulso é a feature que conta.
    """

    #: Ângulo ombro–cotovelo–pulso. Menor = mais fundo.
    elbow_angle: float = ELBOW_TOP
    #: Desvio perpendicular do quadril da linha ombro→tornozelo, em torsos. + = caindo.
    hip_offset: float = HIPS_ALIGNED
    #: Flexão de joelhos — a progressão com que quase todo mundo começa. Quem toca o chão
    #: passa a ser o JOELHO, e o pé sobe para trás; a linha do corpo vai do ombro ao joelho.
    #: Existe como fixture porque o porteiro de postura da FSM promete aceitar esta variação,
    #: e promessa sem fixture é chute (T-106).
    on_knees: bool = False


@dataclass(frozen=True, slots=True)
class CrunchPose:
    """Um abdominal (crunch) visto de lado, celular no chão (T-107).

    O quadril fica no chão e o tronco sobe — o que separa um crunch de um abdominal completo.
    O joelho dobrado com o pé apoiado não é enfeite: é ele que dá a **referência vertical**
    que a FSM usa para não depender de constante em torsos.
    """

    #: Ângulo do tronco (quadril→ombro) com o chão. Maior = mais alto.
    trunk_angle: float = TRUNK_FLAT
    #: Ângulo da coxa com o chão. Define a altura do joelho, a referência da feature.
    thigh_angle: float = THIGH_ANGLE


def _lateral_landmarks(
    *,
    nose: tuple[float, float],
    shoulder: tuple[float, float],
    elbow: tuple[float, float],
    wrist: tuple[float, float],
    hip: tuple[float, float],
    knee: tuple[float, float],
    ankle: tuple[float, float],
    axis: tuple[float, float],
    torso: float,
    visibility: float,
) -> list[list[float]]:
    """Monta os 33 landmarks a partir das articulações de UM lado, vistas de perfil.

    O lado de trás nasce deslocado ao longo do eixo do corpo (`axis`), metade para cada lado,
    para que a MÉDIA dos dois lados caia exatamente na articulação — que é o que toda feature
    lê — e mesmo assim `shoulder_width` não seja zero.
    """
    dx, dy = axis[0] * _LAT_SPLIT * torso / 2, axis[1] * _LAT_SPLIT * torso / 2

    def par(ponto: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
        """(perto, longe) — a média dos dois é `ponto`."""
        return (ponto[0] - dx, ponto[1] - dy), (ponto[0] + dx, ponto[1] + dy)

    l_shoulder, r_shoulder = par(shoulder)
    l_elbow, r_elbow = par(elbow)
    l_wrist, r_wrist = par(wrist)
    l_hip, r_hip = par(hip)
    l_knee, r_knee = par(knee)
    l_ankle, r_ankle = par(ankle)

    # Face: o rosto olha na direção do eixo do corpo (para onde a cabeça aponta).
    olho = 0.05 * torso
    orelha = 0.09 * torso
    mao = 0.06 * torso
    pe = 0.10 * torso

    pontos: list[tuple[float, float]] = [
        nose,  # 0
        (nose[0] - olho / 2, nose[1] - olho),  # 1 left_eye_inner
        (nose[0] - olho, nose[1] - olho),  # 2 left_eye
        (nose[0] - olho * 1.5, nose[1] - olho),  # 3 left_eye_outer
        (nose[0] + olho / 2, nose[1] - olho),  # 4 right_eye_inner
        (nose[0] + olho, nose[1] - olho),  # 5 right_eye
        (nose[0] + olho * 1.5, nose[1] - olho),  # 6 right_eye_outer
        (nose[0] - orelha, nose[1]),  # 7 left_ear
        (nose[0] + orelha, nose[1]),  # 8 right_ear
        (nose[0] - olho / 2, nose[1] + olho),  # 9 mouth_left
        (nose[0] + olho / 2, nose[1] + olho),  # 10 mouth_right
        l_shoulder,  # 11
        r_shoulder,  # 12
        l_elbow,  # 13
        r_elbow,  # 14
        l_wrist,  # 15
        r_wrist,  # 16
        (l_wrist[0], l_wrist[1] + mao),  # 17 left_pinky
        (r_wrist[0], r_wrist[1] + mao),  # 18 right_pinky
        (l_wrist[0] + mao / 2, l_wrist[1] + mao),  # 19 left_index
        (r_wrist[0] + mao / 2, r_wrist[1] + mao),  # 20 right_index
        (l_wrist[0] - mao / 2, l_wrist[1] + mao / 2),  # 21 left_thumb
        (r_wrist[0] - mao / 2, r_wrist[1] + mao / 2),  # 22 right_thumb
        l_hip,  # 23
        r_hip,  # 24
        l_knee,  # 25
        r_knee,  # 26
        l_ankle,  # 27
        r_ankle,  # 28
        (l_ankle[0] - pe / 2, l_ankle[1] + pe / 2),  # 29 left_heel
        (r_ankle[0] - pe / 2, r_ankle[1] + pe / 2),  # 30 right_heel
        (l_ankle[0] + pe, l_ankle[1] + pe / 2),  # 31 left_foot_index
        (r_ankle[0] + pe, r_ankle[1] + pe / 2),  # 32 right_foot_index
    ]

    # Índices ímpares do MediaPipe são o lado esquerdo; aqui o esquerdo é o lado de PERTO da
    # câmera. O lado de trás vem com visibilidade menor, como em vídeo real.
    longe = {12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32}
    return [
        [x, y, 0.0, (visibility * _LAT_FAR_VISIBILITY if i in longe else visibility)]
        for i, (x, y) in enumerate(pontos)
    ]


def _pushup_figure(
    pose: PushUpPose,
    *,
    torso: float,
    center: tuple[float, float],
    visibility: float,
) -> list[list[float]]:
    """Flexão de lado: mãos no chão, cabeça à esquerda, pés à direita.

    `center` continua sendo o quadril — a mesma convenção do boneco em pé, para que
    `sequence()` e as fixtures não precisem saber qual geometria estão usando.
    """
    cx, cy = center
    braco_sup = _LAT_UPPER_ARM * torso
    antebraco = _LAT_FOREARM * torso
    perna = (_LAT_THIGH + _LAT_SHIN) * torso
    corpo = torso + perna  # ombro→tornozelo com o corpo em prancha

    # Distância ombro→pulso pelo ângulo do cotovelo (lei dos cossenos).
    theta = math.radians(pose.elbow_angle)
    ombro_pulso = math.sqrt(
        braco_sup**2 + antebraco**2 - 2 * braco_sup * antebraco * math.cos(theta)
    )

    # O ombro fica sobre a mão: numa flexão o que desce é o corpo, a mão não anda.
    wrist = (cx - torso * 1.05, cy)
    shoulder = (wrist[0], wrist[1] - ombro_pulso)

    # Cotovelo: interseção dos círculos (ombro, braço) e (pulso, antebraço), escolhendo a
    # solução que aponta para os PÉS — é para lá que o cotovelo vai numa flexão.
    if ombro_pulso < 1e-6:
        elbow = (shoulder[0] + braco_sup, shoulder[1])
    else:
        a = (braco_sup**2 - antebraco**2 + ombro_pulso**2) / (2 * ombro_pulso)
        h = math.sqrt(max(braco_sup**2 - a**2, 0.0))
        # Do ombro em direção ao pulso (para baixo), depois perpendicular (para os pés).
        base = (shoulder[0], shoulder[1] + a)
        elbow = (base[0] + h, base[1])

    # Corpo em prancha: reta do ombro até o ponto de apoio, que fica quase no chão. No apoio
    # de pés a linha vai até o tornozelo; de joelhos ela termina no JOELHO, e o pé sobe atrás.
    chao = wrist[1]
    corpo = torso + (_LAT_THIGH * torso if pose.on_knees else perna)
    apoio_y = chao - _LAT_ANKLE_LIFT * torso
    dy_corpo = apoio_y - shoulder[1]
    dx_corpo = math.sqrt(max(corpo**2 - dy_corpo**2, (0.3 * corpo) ** 2))

    eixo = (dx_corpo / corpo, dy_corpo / corpo)  # ombro → apoio, unitário
    perpendicular = (-eixo[1], eixo[0])  # gira 90°: y+ = para o chão no trecho horizontal
    desvio = pose.hip_offset * torso

    fracao_quadril = torso / corpo
    hip = (
        shoulder[0] + eixo[0] * corpo * fracao_quadril + perpendicular[0] * desvio,
        shoulder[1] + eixo[1] * corpo * fracao_quadril + perpendicular[1] * desvio,
    )
    if pose.on_knees:
        # O joelho é o apoio: fim da linha do corpo, no chão. A canela sobe para trás a 45°,
        # que é como o pé fica numa flexão de joelhos.
        knee = (shoulder[0] + eixo[0] * corpo, shoulder[1] + eixo[1] * corpo)
        recuo = _LAT_SHIN * torso * math.cos(math.radians(45))
        ankle = (knee[0] - recuo, knee[1] - recuo)
    else:
        ankle = (shoulder[0] + dx_corpo, apoio_y)
        # Joelho na reta quadril→tornozelo, na proporção coxa/perna.
        fracao_joelho = _LAT_THIGH / (_LAT_THIGH + _LAT_SHIN)
        knee = (
            hip[0] + (ankle[0] - hip[0]) * fracao_joelho,
            hip[1] + (ankle[1] - hip[1]) * fracao_joelho,
        )
    # Cabeça no prolongamento do tronco, para além do ombro.
    nose = (shoulder[0] - eixo[0] * _LAT_NECK * torso, shoulder[1] - eixo[1] * _LAT_NECK * torso)

    return _lateral_landmarks(
        nose=nose,
        shoulder=shoulder,
        elbow=elbow,
        wrist=wrist,
        hip=hip,
        knee=knee,
        ankle=ankle,
        axis=eixo,
        torso=torso,
        visibility=visibility,
    )


def _crunch_figure(
    pose: CrunchPose,
    *,
    torso: float,
    center: tuple[float, float],
    visibility: float,
) -> list[list[float]]:
    """Abdominal de lado: costas no chão, cabeça à esquerda, joelhos dobrados à direita."""
    cx, cy = center
    hip = (cx, cy)  # o quadril não sai do chão num crunch — é o que o define
    chao = cy

    # Tronco: sobe do quadril em direção à cabeça (para a esquerda).
    alpha = math.radians(pose.trunk_angle)
    eixo = (-math.cos(alpha), -math.sin(alpha))  # quadril → ombro, unitário
    shoulder = (hip[0] + eixo[0] * torso, hip[1] + eixo[1] * torso)

    # Cabeça no prolongamento do tronco. O boneco NÃO modela queixo colado no peito: num corpo
    # deitado a cabeça flexionada gira o nariz por cima do peito, e o sinal disso na projeção
    # lateral muda de sentido conforme onde a cabeça pivota. Sinal de qualidade que o gerador
    # não sabe assinar com segurança não vira limiar — por isso o erro de execução que o
    # `abdominal` critica é a CADÊNCIA (relógio, não geometria), e não o pescoço.
    nose = (shoulder[0] + eixo[0] * _LAT_NECK * torso, shoulder[1] + eixo[1] * _LAT_NECK * torso)

    # Perna: coxa sobe do quadril, canela desce até o pé apoiado no chão.
    beta = math.radians(pose.thigh_angle)
    knee = (
        hip[0] + _LAT_THIGH * torso * math.cos(beta),
        hip[1] - _LAT_THIGH * torso * math.sin(beta),
    )
    queda = chao - knee[1]
    avanco = math.sqrt(max((_LAT_SHIN * torso) ** 2 - queda**2, (0.2 * _LAT_SHIN * torso) ** 2))
    ankle = (knee[0] + avanco, chao)

    # Braços ao lado do corpo (mão na nuca deixaria o pulso em cima do rosto e não muda
    # nenhuma feature do crunch): cotovelo e pulso apoiados perto do quadril.
    elbow = (shoulder[0] + 0.35 * torso, chao - 0.05 * torso)
    wrist = (shoulder[0] + 0.85 * torso, chao - 0.05 * torso)

    return _lateral_landmarks(
        nose=nose,
        shoulder=shoulder,
        elbow=elbow,
        wrist=wrist,
        hip=hip,
        knee=knee,
        ankle=ankle,
        axis=eixo,
        torso=torso,
        visibility=visibility,
    )


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


def session_poses(
    poses: list[Pose], *, countdown: int = COUNTDOWN_FRAMES, still: Pose | None = None
) -> list[Pose]:
    """Poses de uma sessão REAL: countdown parado e depois o exercício.

    `still` é a pose do countdown. O default (em pé, braços baixos) só serve a quem treina em
    pé — quem vai fazer flexão passa o countdown na prancha, e quem vai fazer abdominal passa
    deitado. Sem esse parâmetro, uma fixture de exercício de chão começaria com a pessoa em pé
    e mediria a calibração de um corpo que não é o do exercício.

    Existe porque a T-019 tornou a calibração parte do caminho: o worker mede o corpo no
    primeiro segundo e só então começa a contar. Uma fixture que emenda direto no exercício
    não representa mais nenhuma sessão de verdade — e perderia a primeira repetição, que é
    exatamente o que se veria em produção se o countdown não existisse.
    """
    return [*(still_poses(countdown) if still is None else [still] * countdown), *poses]


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


def plank_pose(*, hip_offset: float = HIPS_ALIGNED, on_knees: bool = False) -> PushUpPose:
    """Prancha alta: braço estendido, corpo alinhado. É a posição inicial da flexão."""
    return PushUpPose(elbow_angle=ELBOW_TOP, hip_offset=hip_offset, on_knees=on_knees)


def pushup_poses(
    reps: int,
    *,
    frames_per_rep: int = 15,
    amplitude: float = 1.0,
    hip_offset: float = HIPS_ALIGNED,
    on_knees: bool = False,
) -> list[PushUpPose]:
    """Poses de `reps` flexões contínuas, interpoladas por cosseno (T-106).

    Mesma forma das outras: `amplitude` < 1 é a flexão que não desce (o análogo da rep
    preguiçosa), e a sequência termina **na prancha** para a última repetição não ficar
    eternamente em andamento.

    `hip_offset` vale para a série inteira — quadril caindo é erro de postura sustentado, não
    de um frame.
    """
    topo = plank_pose(hip_offset=hip_offset, on_knees=on_knees)
    poses: list[PushUpPose] = []
    for _rep in range(reps):
        for index in range(frames_per_rep):
            fraction = (1 - math.cos(2 * math.pi * index / frames_per_rep)) / 2 * amplitude
            poses.append(
                PushUpPose(
                    elbow_angle=ELBOW_TOP + (ELBOW_BOTTOM - ELBOW_TOP) * fraction,
                    hip_offset=hip_offset,
                    on_knees=on_knees,
                )
            )
    return [*poses, topo, topo]


def lying_pose(*, thigh_angle: float = THIGH_ANGLE) -> CrunchPose:
    """Deitado de costas, joelhos dobrados. É a posição inicial do abdominal."""
    return CrunchPose(trunk_angle=TRUNK_FLAT, thigh_angle=thigh_angle)


def crunch_poses(
    reps: int,
    *,
    frames_per_rep: int = 15,
    amplitude: float = 1.0,
    thigh_angle: float = THIGH_ANGLE,
) -> list[CrunchPose]:
    """Poses de `reps` abdominais contínuos, interpolados por cosseno (T-107).

    `thigh_angle` é a montagem da perna, e existe como parâmetro porque é a única variação de
    montagem que mexe na feature: o joelho é a referência vertical do exercício. Pé longe do
    glúteo abaixa a referência e infla o `lift` — o teste de sensibilidade mede quanto.
    """
    deitado = lying_pose(thigh_angle=thigh_angle)
    poses: list[CrunchPose] = []
    for _rep in range(reps):
        for index in range(frames_per_rep):
            fraction = (1 - math.cos(2 * math.pi * index / frames_per_rep)) / 2 * amplitude
            poses.append(
                CrunchPose(
                    trunk_angle=TRUNK_FLAT + (TRUNK_CRUNCH - TRUNK_FLAT) * fraction,
                    thigh_angle=thigh_angle,
                )
            )
    return [*poses, deitado, deitado]
