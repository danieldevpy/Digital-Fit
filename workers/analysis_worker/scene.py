"""Validação de cena mínima (SPEC-003, Fase Inicial).

Duas travas, as que dá para checar só com keypoints:

1. **Enquadramento** — os 4 landmarks-âncora (ombros e tornozelos) precisam de `visibility ≥
   0.5`. Falhando por mais de 1 s ⇒ `OUT_OF_FRAME`.
2. **Distância** — a extensão do corpo (cabeça → tornozelo) tem de ficar entre 40% e 95% do
   lado do frame. Fora disso ⇒ `TOO_FAR` / `TOO_CLOSE`.

**Qual lado do frame depende da postura do exercício** (T-106/T-107). Até os exercícios de
chão, "extensão do corpo" era sempre a ALTURA cabeça→tornozelo, porque todo exercício era em
pé. Numa flexão a cabeça e o tornozelo ficam quase na mesma altura: a medida antiga dá ~0, e o
produto pediria "aproxime-se" a sessão inteira com o enquadramento perfeito. Deitado, quem
mede distância é a LARGURA.

Quem declara a postura é o exercício, no `scene_hints()` (`Posture`) — o validador não tem
tabela de slug nenhuma. A faixa também vem de lá, então exercício com enquadramento próprio
não precisa mexer neste arquivo.

Nada aqui **bloqueia** a sessão: na Fase Inicial os warnings orientam o usuário e vão para o
relatório. Bloquear início por cena ruim, luz, tilt de câmera e score de cena são Fase Evolução.

**Debounce** (SPEC-003, notas): 1 s de condição contínua para ligar o warning, 2 s para repetir
o mesmo código. É o que separa "avisar" de "espernear a cada frame".

Roda no worker, sobre o mesmo `NormFrame` da FSM — o mesmo código serve edge e cloud, como a
SPEC-003 exige.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from workers.analysis_worker.exercises.base import Posture
from workers.shared.events import Code, SceneWarning, Severity
from workers.shared.normalize import NormFrame

__all__ = [
    "FRAME_ANCHORS",
    "MAX_BODY_HEIGHT",
    "MIN_BODY_HEIGHT",
    "REPEAT_AFTER_MS",
    "TRIGGER_AFTER_MS",
    "SceneValidator",
]

_NOSE = 0
_LEFT_SHOULDER, _RIGHT_SHOULDER = 11, 12
_LEFT_ANKLE, _RIGHT_ANKLE = 27, 28

#: Âncoras de enquadramento: corpo inteiro visível = ombros e tornozelos (SPEC-003).
FRAME_ANCHORS: tuple[int, ...] = (_LEFT_SHOULDER, _RIGHT_SHOULDER, _LEFT_ANKLE, _RIGHT_ANKLE)

#: Visibilidade mínima por âncora.
MIN_VISIBILITY = 0.5

#: Altura do corpo como fração da altura do frame (proxy grosseiro de distância).
MIN_BODY_HEIGHT = 0.40
MAX_BODY_HEIGHT = 0.95

#: Tempo de condição contínua para emitir, e intervalo mínimo para repetir o mesmo código.
TRIGGER_AFTER_MS = 1_000
REPEAT_AFTER_MS = 2_000

_HINTS: dict[Code, str] = {
    Code.OUT_OF_FRAME: "corpo inteiro precisa aparecer: ombros e tornozelos no quadro",
    Code.TOO_FAR: "aproxime-se da camera",
    Code.TOO_CLOSE: "afaste-se da camera",
}


@dataclass(slots=True)
class _CodeState:
    """Quando a condição começou e quando o aviso saiu pela última vez."""

    since_ms: int | None = None
    last_emitted_ms: int | None = None


@dataclass(slots=True)
class SceneValidator:
    """Um validador por sessão — o debounce é estado.

    Puro: recebe frame normalizado e instante, devolve os avisos que devem sair agora.
    """

    trigger_after_ms: int = TRIGGER_AFTER_MS
    repeat_after_ms: int = REPEAT_AFTER_MS
    #: Postura do exercício em curso, declarada pelo analisador. O default mantém o
    #: comportamento de quem está em pé — nenhuma sessão existente muda de resultado.
    posture: Posture = Posture.STANDING
    #: Faixa aceitável da extensão do corpo. Default = a faixa global da SPEC-003.
    body_range: tuple[float, float] = (MIN_BODY_HEIGHT, MAX_BODY_HEIGHT)
    counts: dict[str, int] = field(default_factory=dict)
    _states: dict[Code, _CodeState] = field(default_factory=dict)

    def check(self, frame: NormFrame) -> list[SceneWarning]:
        """Avisos da cena neste frame (lista vazia quando está tudo bem ou em debounce)."""
        ativos = self._active_codes(frame)
        avisos: list[SceneWarning] = []

        for code in (Code.OUT_OF_FRAME, Code.TOO_FAR, Code.TOO_CLOSE):
            estado = self._states.setdefault(code, _CodeState())
            if code not in ativos:
                estado.since_ms = None
                continue

            if estado.since_ms is None:
                estado.since_ms = frame.ts
            if frame.ts - estado.since_ms < self.trigger_after_ms:
                continue  # condição ainda não durou o suficiente
            if (
                estado.last_emitted_ms is not None
                and frame.ts - estado.last_emitted_ms < self.repeat_after_ms
            ):
                continue  # mesmo código, cedo demais para repetir

            estado.last_emitted_ms = frame.ts
            self.counts[code.value] = self.counts.get(code.value, 0) + 1
            avisos.append(SceneWarning(code=code, severity=Severity.WARNING, hint=_HINTS[code]))

        return avisos

    def _active_codes(self, frame: NormFrame) -> set[Code]:
        """Que problemas a cena tem **neste** frame, antes do debounce."""
        ativos: set[Code] = set()

        if any(float(frame.visibility[indice]) < MIN_VISIBILITY for indice in FRAME_ANCHORS):
            # Fora do quadro é a condição mais grave: sem âncoras, medir distância não faz
            # sentido (a altura do corpo viria de landmarks adivinhados).
            ativos.add(Code.OUT_OF_FRAME)
            return ativos

        minimo, maximo = self.body_range
        extensao = self.body_height(frame, self.posture)
        if extensao < minimo:
            ativos.add(Code.TOO_FAR)
        elif extensao > maximo:
            ativos.add(Code.TOO_CLOSE)
        return ativos

    @staticmethod
    def body_height(frame: NormFrame, posture: Posture = Posture.STANDING) -> float:
        """Extensão cabeça→tornozelo como fração do lado do frame que a postura usa.

        Os pontos vêm em torsos; multiplicar pela escala (`torso`, em unidades de frame) devolve
        a medida na moeda que a SPEC-003 usa. Assim a checagem de distância não precisa dos
        landmarks crus.

        De pé mede-se em `y` (fração da altura do frame); deitado, em `x` (fração da largura) —
        os landmarks do MediaPipe já vêm normalizados por altura e largura respectivamente, então
        cada eixo sai na fração do seu próprio lado sem conversão nenhuma.
        """
        eixo = 0 if posture is Posture.FLOOR else 1
        cabeca = float(frame.points[_NOSE][eixo])
        tornozelos = [
            float(frame.points[_LEFT_ANKLE][eixo]),
            float(frame.points[_RIGHT_ANKLE][eixo]),
        ]
        # Deitado, a cabeça pode estar à esquerda ou à direita dos pés — o sinal depende de
        # para que lado a pessoa deitou, e não diz nada sobre o enquadramento.
        if posture is Posture.FLOOR:
            distante = max(tornozelos, key=lambda valor: abs(valor - cabeca))
            return abs(distante - cabeca) * frame.torso
        return (max(tornozelos) - cabeca) * frame.torso
