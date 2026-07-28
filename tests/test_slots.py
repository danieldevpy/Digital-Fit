"""Testes do semáforo de slots cloud (T-017 / SPEC-009).

Usa `fakeredis` quando disponível; senão, um Redis de verdade em `REDIS_URL`. O que se testa
são os quatro critérios da spec, com atenção especial ao 2 — liberar a vaga em TODOS os
finais, inclusive quando o dono da vaga simplesmente morre.
"""

from __future__ import annotations

import pytest

from workers.shared.slots import GRACE_MS, CloudSlots

TTL_MS = 45_000
AGORA = 1_722_100_000_000


@pytest.fixture
def redis_falso():
    """Redis em memória. `fakeredis` executa Lua de verdade, que é o ponto do teste."""
    fakeredis = pytest.importorskip("fakeredis", reason="fakeredis nao instalado")
    return fakeredis.FakeStrictRedis()


@pytest.fixture
def slots(redis_falso) -> CloudSlots:
    return CloudSlots(redis_falso, limit=3)


# --------------------------------------------------------------------------------------
# Critério 1: a 4ª sessão é negada; vaga volta quando alguma termina
# --------------------------------------------------------------------------------------


def test_tres_sessoes_entram_a_quarta_e_negada(slots: CloudSlots) -> None:
    for i in range(3):
        assert slots.acquire(f"s{i}", ttl_ms=TTL_MS, now_ms=AGORA) is True

    assert slots.acquire("s3", ttl_ms=TTL_MS, now_ms=AGORA) is False
    assert slots.active(now_ms=AGORA) == 3
    assert slots.available(now_ms=AGORA) == 0


def test_vaga_liberada_admite_a_proxima(slots: CloudSlots) -> None:
    for i in range(3):
        slots.acquire(f"s{i}", ttl_ms=TTL_MS, now_ms=AGORA)

    assert slots.release("s1") is True

    assert slots.acquire("s3", ttl_ms=TTL_MS, now_ms=AGORA) is True
    assert slots.active(now_ms=AGORA) == 3


# --------------------------------------------------------------------------------------
# Critério 2: liberação em TODOS os finais
# --------------------------------------------------------------------------------------


def test_vaga_de_sessao_morta_volta_sozinha(slots: CloudSlots) -> None:
    """O caso que o contador INCR/DECR não cobre.

    Worker crashou: ninguém chamou `release`. Sem expiração por membro, a vaga estaria
    ocupada para sempre e o modo cloud morreria depois de três crashes — sem nada em log
    dizendo por quê.
    """
    for i in range(3):
        slots.acquire(f"s{i}", ttl_ms=TTL_MS, now_ms=AGORA)

    depois = AGORA + TTL_MS + GRACE_MS + 1

    assert slots.active(now_ms=depois) == 0
    assert slots.acquire("nova", ttl_ms=TTL_MS, now_ms=depois) is True


def test_vaga_nao_e_recolhida_antes_do_prazo(slots: CloudSlots) -> None:
    # A sessão dura 30s e o TTL é 45s; recolher a vaga durante o exercício deixaria uma 4ª
    # sessão entrar enquanto três ainda gravam.
    slots.acquire("s0", ttl_ms=TTL_MS, now_ms=AGORA)

    assert slots.active(now_ms=AGORA + TTL_MS - 1) == 1


def test_liberar_sessao_que_nunca_teve_vaga_e_no_op(slots: CloudSlots) -> None:
    # É o que permite o worker chamar `release` para toda sessão sem saber o modo dela.
    assert slots.release("sessao-edge") is False
    assert slots.active(now_ms=AGORA) == 0


def test_liberar_duas_vezes_nao_devolve_vaga_a_mais(slots: CloudSlots) -> None:
    slots.acquire("s0", ttl_ms=TTL_MS, now_ms=AGORA)

    assert slots.release("s0") is True
    assert slots.release("s0") is False
    assert slots.active(now_ms=AGORA) == 0


# --------------------------------------------------------------------------------------
# Concorrência e idempotência
# --------------------------------------------------------------------------------------


def test_mesma_sessao_pedindo_duas_vezes_nao_gasta_duas_vagas(slots: CloudSlots) -> None:
    """Retry de rede não pode virar vazamento."""
    assert slots.acquire("s0", ttl_ms=TTL_MS, now_ms=AGORA) is True
    assert slots.acquire("s0", ttl_ms=TTL_MS, now_ms=AGORA) is True

    assert slots.active(now_ms=AGORA) == 1


def test_pedido_repetido_estende_o_prazo(slots: CloudSlots) -> None:
    slots.acquire("s0", ttl_ms=TTL_MS, now_ms=AGORA)
    quase_vencendo = AGORA + TTL_MS

    slots.acquire("s0", ttl_ms=TTL_MS, now_ms=quase_vencendo)

    assert slots.active(now_ms=quase_vencendo + TTL_MS) == 1


def test_limite_e_configuravel(redis_falso) -> None:
    solo = CloudSlots(redis_falso, limit=1)

    assert solo.acquire("a", ttl_ms=TTL_MS, now_ms=AGORA) is True
    assert solo.acquire("b", ttl_ms=TTL_MS, now_ms=AGORA) is False


def test_semaforos_com_chaves_diferentes_nao_se_misturam(redis_falso) -> None:
    a = CloudSlots(redis_falso, limit=1, key="slots:cloud")
    b = CloudSlots(redis_falso, limit=1, key="slots:outro")

    assert a.acquire("x", ttl_ms=TTL_MS, now_ms=AGORA) is True
    assert b.acquire("y", ttl_ms=TTL_MS, now_ms=AGORA) is True
