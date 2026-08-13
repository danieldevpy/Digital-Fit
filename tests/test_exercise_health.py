"""Saúde do exercício em produção (T-104 / SPEC-020).

O critério de `validado` — "taxa de sessões zero-rep < 20% por uma semana" — é o que estes
testes protegem, e o primeiro deles é o que mais importa: **`no_data` não entra na taxa**.

Não é sutileza de estatística. Treze sessões de agachamento com zero repetição, todas
`no_data`, foram lidas por semanas como "o agachamento não conta", viraram uma task de alta
prioridade contra um bug inexistente e quase custaram uma mexida a esmo nos limiares do
`squat.py` (T-133). Se alguém um dia simplificar este módulo somando os quatro motivos num
número só, é aqui que a conta volta.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from api.exercise_health import LIMITE_ZERO, MINIMO_PARA_VEREDITO, coletar
from api.models import Exercise, SessionResult
from django.core.management import CommandError, call_command
from django.utils import timezone


def sessao(
    exercise: str,
    *,
    reason: str = "completed",
    reps: int = 10,
    cadencia: float = 20.0,
    dias_atras: int = 0,
    sufixo: str = "",
) -> SessionResult:
    resultado = SessionResult.objects.create(
        session_id=f"s-{exercise}-{reason}-{reps}-{dias_atras}-{sufixo}-{timezone.now().timestamp()}",
        exercise=exercise,
        mode="edge",
        reason=reason,
        rep_count=reps,
        duration_ms=30_000,
        cadence_rpm=cadencia,
    )
    if dias_atras:
        # `auto_now_add` ignora o que se passa no create; para testar a janela é preciso
        # reescrever depois.
        novo = timezone.now() - timezone.timedelta(days=dias_atras)
        SessionResult.objects.filter(pk=resultado.pk).update(created_at=novo)
        resultado.refresh_from_db()
    return resultado


def por_slug(saude: list, slug: str):
    return next(linha for linha in saude if linha.slug == slug)


def executar(*args: str) -> str:
    saida = StringIO()
    call_command("exercise_health", *args, stdout=saida)
    return saida.getvalue()


@pytest.mark.django_db
def test_no_data_nao_entra_na_taxa_de_zero() -> None:
    """O teste que existe por causa da T-133.

    Dez sessões que morreram sem frame e duas que correram até o fim contando bem: a taxa é
    zero. Se `no_data` entrasse, este exercício apareceria com 83% e seria rebaixado por um
    problema que não é dele.
    """
    for i in range(10):
        sessao("squat", reason="no_data", reps=0, cadencia=0, sufixo=str(i))
    sessao("squat", reps=15, sufixo="a")
    sessao("squat", reps=15, sufixo="b")

    linha = por_slug(coletar(), "squat")

    assert linha.total == 12
    assert linha.completas == 2
    assert linha.zeradas == 0
    assert linha.taxa_zero == 0.0
    assert linha.sem_dado == 10


@pytest.mark.django_db
def test_zero_de_sessao_completa_e_o_que_conta() -> None:
    for i in range(3):
        sessao("squat", reps=0, cadencia=0, sufixo=str(i))
    sessao("squat", reps=15, sufixo="ok")

    linha = por_slug(coletar(), "squat")

    assert linha.zeradas == 3
    assert linha.taxa_zero == pytest.approx(0.75)
    assert linha.veredito == "poucas"  # 4 completas, abaixo do mínimo


@pytest.mark.django_db
def test_veredito_atencao_acima_do_limite_da_spec() -> None:
    # 2 zeradas em 6 completas = 33%, acima dos 20% da SPEC-020.
    for i in range(2):
        sessao("squat", reps=0, cadencia=0, sufixo=f"z{i}")
    for i in range(4):
        sessao("squat", reps=12, sufixo=f"ok{i}")

    linha = por_slug(coletar(), "squat")

    assert linha.completas >= MINIMO_PARA_VEREDITO
    assert linha.taxa_zero is not None and linha.taxa_zero > LIMITE_ZERO
    assert linha.veredito == "atencao"


@pytest.mark.django_db
def test_poucas_sessoes_nao_viram_veredito() -> None:
    """Duas sessões com um zero dariam 50%. Rebaixar um exercício por isso seria decidir no
    ruído — e a spec pede uma SEMANA de produção, não duas sessões."""
    sessao("squat", reps=0, cadencia=0, sufixo="z")
    sessao("squat", reps=12, sufixo="ok")

    assert por_slug(coletar(), "squat").veredito == "poucas"


@pytest.mark.django_db
def test_exercicio_do_catalogo_sem_sessao_aparece_zerado() -> None:
    """Ausência é resposta. Um exercício que ninguém abriu é notícia."""
    linha = por_slug(coletar(), "abdominal")

    assert linha.total == 0
    assert linha.veredito == "sem sessao"
    assert linha.taxa_zero is None
    assert linha.cadencia_mediana is None


@pytest.mark.django_db
def test_a_janela_recorta_por_dias() -> None:
    sessao("squat", reps=12, dias_atras=30, sufixo="velha")
    sessao("squat", reps=12, sufixo="nova")

    assert por_slug(coletar(dias=7), "squat").total == 1
    assert por_slug(coletar(dias=60), "squat").total == 2


@pytest.mark.django_db
def test_cadencia_e_mediana_e_ignora_sessao_zerada() -> None:
    """Mediana e não média: uma sessão lenta não move a mediana, e uma sessão zerada tem
    cadência 0 que arrastaria qualquer das duas para baixo sem significar nada."""
    sessao("squat", reps=12, cadencia=20.0, sufixo="a")
    sessao("squat", reps=12, cadencia=30.0, sufixo="b")
    sessao("squat", reps=12, cadencia=100.0, sufixo="c")
    sessao("squat", reps=0, cadencia=0.0, sufixo="zero")

    assert por_slug(coletar(), "squat").cadencia_mediana == 30.0


@pytest.mark.django_db
def test_slug_que_saiu_do_catalogo_continua_aparecendo() -> None:
    """O exercício foi removido do catálogo; as sessões dele não foram. Sumir com a linha
    apagaria justamente o histórico que motivou a remoção."""
    sessao("exercicio-extinto", reps=5)

    linha = por_slug(coletar(), "exercicio-extinto")

    assert linha.no_catalogo is False
    assert linha.maturity is None
    assert linha.total == 1


@pytest.mark.django_db
def test_comando_imprime_as_duas_colunas_de_zero_separadas() -> None:
    sessao("squat", reason="no_data", reps=0, cadencia=0, sufixo="nd")
    sessao("squat", reps=15, sufixo="ok")

    saida = executar()

    assert "zeradas" in saida
    assert "sem dado" in saida
    # A legenda é parte da entrega: sem ela as duas colunas são fáceis de confundir.
    assert "FORA da taxa" in saida
    assert f"< {LIMITE_ZERO * 100:.0f}%" in saida


@pytest.mark.django_db
def test_comando_em_json_da_os_mesmos_numeros() -> None:
    sessao("squat", reps=15, sufixo="ok")

    dados = json.loads(executar("--json"))

    assert dados["dias"] == 7
    assert dados["limite_zero"] == LIMITE_ZERO
    squat = next(e for e in dados["exercicios"] if e["exercise"] == "squat")
    assert squat["completas"] == 1
    assert squat["taxa_zero"] == 0.0


@pytest.mark.django_db
def test_comando_recusa_janela_invalida() -> None:
    with pytest.raises(CommandError):
        call_command("exercise_health", "--dias", "0")


@pytest.mark.django_db
def test_exercicio_desligado_continua_na_tabela() -> None:
    """Ele foi desligado porque alguém viu um número aqui. Esconder a linha apaga a prova."""
    Exercise.objects.filter(slug="squat").update(enabled=False)
    sessao("squat", reps=12, sufixo="ok")

    saida = executar()

    assert "(off)" in saida
