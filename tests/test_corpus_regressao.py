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
#: **T-110 mudou um número, e só um.** Ao corrigir a anisotropia do espaço normalizado, cinco
#: das seis contagens ficaram idênticas — polichinelo nas três orientações e agachamento. A
#: flexão v2 caiu de 50 para 43, e a queda é a medida ficando honesta, não regredindo:
#:
#: - A pessoa da v2 para o cotovelo em **91,9°** (paralelo). A v1, que não mudou, desce a 55,2°.
#: - O espaço distorcido lia esse mesmo fundo como 76,6° e o deixava passar como flexão inteira.
#: - As 7 repetições que saíram da contagem **viraram 7 `PUSHUP_TOO_SHALLOW`** — não sumiram
#:   caladas, viraram a crítica que a pessoa precisava ouvir.
#: - Nenhum limiar foi tocado para chegar aqui. Retunar `frontal_down_depth` de 0,63 para 0,74
#:   devolveria o 50, mas 0,74 **é** o limiar de "rasa demais": seria apagar a crítica para
#:   salvar a contagem, ajustando a um rótulo que a Descoberta `[A/T-108]` já declarou
#:   não-confiável (o "50" veio do título do vídeo, não de alguém contando).
#:
#: O aval independente da correção não vem de rótulo nenhum: braço travado no topo é ~180° por
#: anatomia, e a leitura vai de 164,7°→171,2° (v1) e 170,9°→174,5° (v2). A correção move as
#: quatro medidas na direção de uma verdade conhecida de antemão.
#: **T-111 dobrou o corpus de flexão e mudou cinco números — todos para cima, e nenhum por
#: retune de limiar.** Os cinco vídeos novos têm rótulo próprio (contado vale a vale no ângulo
#: de cotovelo cru, com conferência visual), e é contra eles que o conserto foi medido:
#:
#: ===========================  ======  ======  ======
#: fixture                      rótulo  antes   depois
#: ===========================  ======  ======  ======
#: lateral-serie1                   16       0      16
#: lateral-serie2                   16       0      16
#: lateral-serie3 (fadiga)          11       3      11
#: frente-20-militar-lento          20      11      20
#: frente-variantes (5 pegadas)     25      19      26
#: ===========================  ======  ======  ======
#:
#: Os dois defeitos eram o mesmo defeito em vistas diferentes: **grandeza que se move com a
#: repetição usada como porteiro de postura**. De frente, `wrists_below_hips` cai de 1,19 para
#: 0,20 torsos no fundo e fechava a porta ali; de perfil, `plank_height` cai a 0,205 e fazia o
#: mesmo. O porteiro ganhou histerese (entrar forte, permanecer fraco, sair com 400 ms de
#: debounce) e a profundidade passou a ser o ângulo do cotovelo nas DUAS vistas.
#:
#: **Os dois números que já existiam não se mexeram** (v1 52, v2 43), e é isso que separa
#: conserto estrutural de ajuste ao rótulo: a varredura mostra `desce` ∈ {0,60; 0,63; 0,66}
#: com `sobe` = 0,80 dando contagem idêntica nos cinco vídeos novos.
CONTAGENS = {
    "polichinelo-01": 20,
    "polichinelo-02": 13,
    "polichinelo-03": 19,
    "flexão-frente-50-repetições-v1": 52,
    "flexão-frente-50-repetições-v2": 43,
    "flexao-lateral-serie1-16": 16,
    "flexao-lateral-serie2-16": 16,
    "flexao-lateral-serie3-11": 11,
    "flexao-frente-20-repeticoes-estilo-militar-lento": 20,
    "flexão-frente-variantes-de-flexao-5-de-cada": 26,
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


def test_toda_fixture_declara_as_dimensoes_do_frame() -> None:
    """Fixture sem `width`/`height` é medida no espaço anisotrópico — e em silêncio (T-110).

    A ausência das dimensões é tratada como "espaço isotrópico" em todo o pipeline, que é o
    que mantém compatibilidade com produtor antigo. O efeito colateral é que apagar os dois
    campos de uma fixture **não quebra nada**: o teste acima continua verde, medindo a coisa
    errada. Este teste é o que torna esse apagão visível.
    """
    sem_dimensao = []
    for caminho_fixture in sorted(FIXTURES.glob("*.json")):
        fixture = load_fixture(caminho_fixture)
        if fixture.width is None or fixture.height is None:
            sem_dimensao.append(caminho_fixture.name)

    assert not sem_dimensao, (
        f"fixtures sem width/height: {sem_dimensao}. Sem as dimensões do frame de origem, a "
        "normalização não consegue pôr x e y na mesma moeda e a contagem volta a herdar o "
        "formato do vídeo (T-110). Pegue a resolução do mp4 original e declare-a na fixture."
    )


def test_toda_fixture_versionada_esta_no_gate() -> None:
    """O contrário do teste acima: fixture no disco e fora do mapa é gate que ninguém cobra."""
    no_disco = {caminho.stem for caminho in FIXTURES.glob("*.json")}
    fora = no_disco - set(CONTAGENS)

    # A do compilado é a única exceção conhecida, e está declarada no comentário de CONTAGENS.
    assert fora <= {"flexão-frente&lado-v1"}, f"fixtures sem contagem carimbada: {sorted(fora)}"
