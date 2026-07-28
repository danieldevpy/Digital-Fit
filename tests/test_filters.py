"""Testes do One Euro Filter (T-006 / SPEC-006, item 3)."""

import math

import numpy as np
import pytest

from workers.shared.filters import OneEuroFilter, alpha_for


def test_alpha_cresce_com_dt_maior() -> None:
    """Passo maior ⇒ menos memória do passado (alpha mais perto de 1)."""
    assert alpha_for(1.0, 0.01) < alpha_for(1.0, 0.1) < 1.0


def test_primeiro_valor_passa_direto() -> None:
    filtro = OneEuroFilter(mincutoff=1.0, beta=0.0)

    assert filtro(0.42, 0.0) == pytest.approx(0.42)
    assert filtro.initialized


def test_sinal_constante_converge_para_o_valor() -> None:
    filtro = OneEuroFilter(mincutoff=1.0, beta=0.0)
    filtro(0.0, 0.0)

    for passo in range(1, 60):
        saida = float(filtro(1.0, passo / 15.0))

    assert saida == pytest.approx(1.0, abs=1e-3)


def test_reduz_ruido_de_sinal_parado() -> None:
    rng = np.random.default_rng(11)
    amostras = rng.normal(0.0, 0.01, 200)
    filtro = OneEuroFilter(mincutoff=1.0, beta=0.5)

    saidas = [float(filtro(valor, indice / 15.0)) for indice, valor in enumerate(amostras)]

    # Ignora o transitório inicial do filtro. O número exigido pela SPEC-006 (≥ 60%) é
    # verificado no pipeline completo, em `tests/test_normalize.py`, com os parâmetros de
    # produção; aqui só se afirma que o filtro filtra.
    assert np.std(saidas[20:]) < np.std(amostras[20:]) * 0.5


def test_beta_maior_acompanha_melhor_movimento_rapido() -> None:
    """É a razão de existir do filtro: cutoff adaptativo não atrasa movimento real."""
    tempos = [indice / 15.0 for indice in range(40)]
    rampa = [2.0 * t for t in tempos]  # 2 unidades/s

    lento = OneEuroFilter(mincutoff=1.0, beta=0.0)
    adaptativo = OneEuroFilter(mincutoff=1.0, beta=1.0)
    erro_lento = [abs(float(lento(v, t)) - v) for v, t in zip(rampa, tempos, strict=True)]
    erro_adaptativo = [abs(float(adaptativo(v, t)) - v) for v, t in zip(rampa, tempos, strict=True)]

    assert sum(erro_adaptativo[5:]) < sum(erro_lento[5:]) * 0.7


def test_filtra_array_mantendo_estado_por_canal() -> None:
    filtro = OneEuroFilter(mincutoff=1.0, beta=0.5)
    filtro(np.zeros((33, 3)), 0.0)

    saida = filtro(np.ones((33, 3)), 1 / 15.0)

    assert saida.shape == (33, 3)
    assert np.all(saida > 0.0) and np.all(saida < 1.0)


def test_canais_nao_se_contaminam() -> None:
    filtro = OneEuroFilter(mincutoff=1.0, beta=0.5)
    filtro(np.array([0.0, 0.0]), 0.0)

    saida = filtro(np.array([1.0, 0.0]), 1 / 15.0)

    assert saida[1] == pytest.approx(0.0)
    assert saida[0] > 0.0


def test_tempo_que_nao_avanca_nao_corrompe_estado() -> None:
    filtro = OneEuroFilter(mincutoff=1.0, beta=0.5)
    filtro(0.0, 0.0)
    esperado = float(filtro(1.0, 1 / 15.0))

    repetido = float(filtro(99.0, 1 / 15.0))  # frame duplicado
    atrasado = float(filtro(99.0, 0.0))  # frame fora de ordem

    assert repetido == pytest.approx(esperado)
    assert atrasado == pytest.approx(esperado)


def test_reset_esquece_a_sessao_anterior() -> None:
    filtro = OneEuroFilter(mincutoff=1.0, beta=0.0)
    filtro(10.0, 0.0)

    filtro.reset()

    assert not filtro.initialized
    assert float(filtro(0.0, 0.0)) == pytest.approx(0.0)


@pytest.mark.parametrize(
    "kwargs",
    [{"mincutoff": 0.0}, {"mincutoff": -1.0}, {"dcutoff": 0.0}, {"beta": -0.1}],
)
def test_parametros_invalidos_falham_cedo(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError, match=r"devem ser|negativo"):
        OneEuroFilter(**kwargs)


def test_alpha_bate_com_a_formula_do_artigo() -> None:
    cutoff, dt = 1.5, 1 / 15.0
    tau = 1.0 / (2.0 * math.pi * cutoff)

    assert alpha_for(cutoff, dt) == pytest.approx(1.0 / (1.0 + tau / dt))
