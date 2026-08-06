"""O gate de contagem: os exercícios continuam contando o que contavam (T-042).

Roda a FSM de verdade sobre os keypoints de **gente real**, extraídos uma vez dos vídeos do
corpus e versionados em `eval/fixtures/`. Em todo push, junto com o resto do `pytest`.

## Por que fixture de keypoints, e não o vídeo

Os vídeos são 50 MB e estão fora do git (`.gitignore`), então a CI nunca os viu. Os mesmos
sete vídeos viram 9,7 MB de JSON — **1,9 MB depois da compressão do git** —, e o teste roda
em milissegundos: é JSON → FSM,
sem MediaPipe, sem decodificar vídeo, sem baixar o modelo de 17 MB. É o "subset rápido em todo
push" que a T-042 pede, com o corpus completo (com vídeo e extração) seguindo manual.

**O que este teste pega**: limiar, FSM, normalização, porteiro de postura — a camada onde
mora todo o histórico de regressão deste projeto. O caso concreto: a T-106 consertou "a flexão
contava braço levantado" e, no MESMO commit, apagou a contagem da flexão frontal (51 → 0). Não
havia teste que gritasse, e o produto passou 19 h em produção contando zero. Com este arquivo,
aquele commit teria falhado no push.

**O que ele NÃO pega**: mudança na extração (versão do MediaPipe, do modelo, da normalização
de entrada) — as fixtures congelam a saída do extrator de propósito, para isolar a FSM. Isso é
o `evalctl run` + `evalctl compare` sobre os vídeos, manual. E não pega a perna do navegador,
que é manual por construção (Descoberta `[A/T-040]`).

## Por que o número esperado é o de HOJE, e não a "verdade"

`expected_reps` do manifest é rótulo humano, e nem sempre é confiável: os dois vídeos de
flexão são de rede social e o "50" veio do **título**, não de alguém contando (Descoberta
`[A/T-108]`). Cobrar acurácia contra rótulo herdado seria ajustar o produto a um número que
ninguém verificou.

Então o que se cobra aqui é **o número que a FSM dá hoje**, carimbado e revisado. Se ele
mudar, o teste falha e alguém decide se foi melhora ou regressão — é teste de snapshot, e é
exatamente a pergunta que protege o deploy. A distância entre este número e o rótulo continua
sendo medida pelo `evalctl`, que é onde ela pertence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.pipeline import analyze_frames
from workers.shared.keypoints import load_fixture

FIXTURES = Path(__file__).resolve().parent.parent / "eval" / "fixtures"

#: Contagem carimbada por fixture — o snapshot. Mudou? Alguém tem de olhar e dizer por quê,
#: atualizando este mapa no mesmo commit que muda o comportamento.
#:
#: A terceira flexão (`frente&lado`) está de fora **e é de propósito**: é um compilado de rede
#: social com cortes de câmera e fala, sem série contínua. O manifest já diz que ela serve como
#: teste de robustez de feature e não para acurácia; carimbar o zero que ela dá hoje seria
#: transformar um número ruim em contrato.
CONTAGENS = {
    "polichinelo-01": 20,
    "polichinelo-02": 13,
    "polichinelo-03": 19,
    "flexão-frente-50-repetições-v1": 52,
    "flexão-frente-50-repetições-v2": 50,
    "agachamento-frente-aprox-18-repetiçẽos-v1": 18,
}


def caminho(nome: str) -> Path:
    return FIXTURES / f"{nome}.json"


@pytest.mark.parametrize("nome", sorted(CONTAGENS))
def test_o_exercicio_continua_contando_o_que_contava(nome: str) -> None:
    fixture = load_fixture(caminho(nome))
    esperado = CONTAGENS[nome]

    resultado = analyze_frames(fixture.frames, exercise=fixture.exercise, name=nome)

    assert resultado.reps == esperado, (
        f"{nome} ({fixture.exercise}): contava {esperado}, agora conta {resultado.reps}. "
        "Se a mudança é intencional, atualize CONTAGENS no mesmo commit e diga por quê no "
        "DEVLOG; se não é, você acabou de encontrar uma regressão antes do deploy."
    )


#: Exercícios no ar que **ainda não têm nenhum vídeo de gente real**, declarados aqui para
#: ficarem visíveis em vez de invisíveis.
#:
#: `abdominal` está em produção desde a T-107, `beta`, e tudo o que se sabe dele vem do boneco
#: sintético — o corpus nunca teve um vídeo de abdominal. É exatamente a posição em que a
#: flexão estava antes de contar zero em produção por 19 h. Sai desta lista quando existir um
#: vídeo; até lá, a lista é a dívida escrita.
SEM_MATERIAL_REAL = {"abdominal"}


def test_exercicio_novo_nao_entra_em_producao_sem_video_de_gente_real() -> None:
    """Exercício no ar sem fixture é exercício sem gate — e foi assim que a flexão frontal
    passou 19 h contando zero em produção.

    Não exige corpus completo (isso é a T-096/T-108): exige **um** vídeo, que é a diferença
    entre "medido em gente" e "medido no boneco sintético". O que já está descoberto hoje vive
    em `SEM_MATERIAL_REAL`, para este teste falhar por dívida NOVA e não pela antiga — travar o
    push de todo mundo por causa do abdominal seria transformar um achado em pedágio.
    """
    from workers.analysis_worker.exercises import EXERCISES

    coberto = {load_fixture(caminho(nome)).exercise for nome in CONTAGENS}
    sem_gate = set(EXERCISES) - coberto - SEM_MATERIAL_REAL

    assert not sem_gate, (
        f"exercicios sem fixture de gente real: {sorted(sem_gate)}. "
        "Grave um vídeo, rode `evalctl run <video> --save-keypoints eval/fixtures` e "
        "carimbe a contagem em CONTAGENS."
    )


def test_a_divida_declarada_nao_cresce_sozinha() -> None:
    """`SEM_MATERIAL_REAL` é lista de dívida, não porta de saída: exercício que ganhou vídeo
    tem de sair dela, senão ela vira o lugar onde se esconde exercício sem medição."""
    coberto = {load_fixture(caminho(nome)).exercise for nome in CONTAGENS}

    assert not (SEM_MATERIAL_REAL & coberto), (
        f"exercicio com fixture ainda listado como sem material real: "
        f"{sorted(SEM_MATERIAL_REAL & coberto)}"
    )


def test_toda_fixture_versionada_esta_no_gate() -> None:
    """O contrário do teste acima: fixture no disco e fora do mapa é gate que ninguém cobra."""
    no_disco = {caminho.stem for caminho in FIXTURES.glob("*.json")}
    fora = no_disco - set(CONTAGENS)

    # A do compilado é a única exceção conhecida, e está declarada no comentário de CONTAGENS.
    assert fora <= {"flexão-frente&lado-v1"}, f"fixtures sem contagem carimbada: {sorted(fora)}"
