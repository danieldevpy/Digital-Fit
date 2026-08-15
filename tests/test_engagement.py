"""Fogo, meta, XP e níveis (T-086 / SPEC-019).

Organizado pelos **critérios de aceite da spec**, porque são eles que dizem se a task está
pronta. O critério 5 (adoção de sessões do aparelho no cadastro) não está aqui: ele é a T-087,
e testá-lo agora seria testar código que não existe.

A parte de cima do arquivo não toca banco, cache nem relógio — é o que o critério 1 pede, e é o
que permite escrever uma sequência de treino como uma lista de datas em vez de como fixture de
Postgres.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from api import engagement as eng
from api.engagement import (
    FUSO_DO_FOGO,
    LEVELS,
    METAS,
    PROTECOES_TETO,
    SCORING_HOLD,
    SCORING_REPS,
    XP_EXECUCAO_LIMPA,
    XP_FORMULA_V,
    XP_SESSAO_VALIDA,
    XP_TETO_REPS,
    Sessao,
    chave_de_cache,
    dia_sp,
    dias_ativos,
    nivel,
    resumo,
    sessao_valida,
    streak,
    ttl_ate_a_virada,
    xp_da_sessao,
    xp_total,
)

# ======================================================================================
# Ferramentas das fixtures puras — datas viram sessões, sem banco.
# ======================================================================================

#: Meio-dia em São Paulo, para que nenhuma fixture dependa acidentalmente da borda do fuso.
_MEIO_DIA_SP = 12


def sessao_em(dia: date, *, reps: int = 10, limpa: bool = True, exercicio: str = "squat") -> Sessao:
    """Uma sessão válida naquele dia de São Paulo, gravada em UTC como o banco grava."""
    local = datetime(dia.year, dia.month, dia.day, _MEIO_DIA_SP, tzinfo=FUSO_DO_FOGO)
    return Sessao(
        created_at=local.astimezone(UTC),
        exercise=exercicio,
        rep_count=reps,
        feedback_counts={} if limpa else {"SQUAT_TOO_SHALLOW": 2},
    )


def dias(*iso: str) -> set[date]:
    return {date.fromisoformat(texto) for texto in iso}


# ======================================================================================
# Critério 3 — o dia é o de São Paulo, não o do banco.
# ======================================================================================


def test_treino_de_22h30_em_sao_paulo_conta_no_dia_de_sao_paulo() -> None:
    """22h30 de 14/08 em SP é 15/08 01h30 em UTC. O fogo tem de dizer 14.

    É o parágrafo do §Fuso da spec virado em teste: meia-noite UTC é 21 h no Brasil, e "treinei
    às 22h e o app disse que foi amanhã" mata a mecânica no primeiro contato.
    """
    gravado_em_utc = datetime(2026, 8, 15, 1, 30, tzinfo=UTC)

    assert dia_sp(gravado_em_utc) == date(2026, 8, 14)


def test_timestamp_ingenuo_e_lido_como_utc() -> None:
    """`created_at` chega do banco com fuso; sem ele, UTC é a única leitura honesta."""
    assert dia_sp(datetime(2026, 8, 15, 1, 30)) == date(2026, 8, 14)


def test_a_virada_do_dia_cai_na_meia_noite_de_sao_paulo() -> None:
    ultimo_instante = datetime(2026, 8, 14, 23, 59, tzinfo=FUSO_DO_FOGO)
    primeiro_instante = datetime(2026, 8, 15, 0, 1, tzinfo=FUSO_DO_FOGO)

    assert dia_sp(ultimo_instante) == date(2026, 8, 14)
    assert dia_sp(primeiro_instante) == date(2026, 8, 15)


# ======================================================================================
# Critério 2 — sessão de zero repetição não conta para nada.
# ======================================================================================


def test_sessao_de_zero_reps_nao_e_valida() -> None:
    vazia = Sessao(created_at=datetime(2026, 8, 15, 15, tzinfo=UTC), rep_count=0)

    assert sessao_valida(vazia) is False


def test_sessao_de_zero_reps_nao_acende_fogo_nao_da_xp_e_nao_bate_meta() -> None:
    """Senão abrir a câmera por 30 s viraria fazenda de fogo (§Vocabulário)."""
    hoje = date(2026, 8, 15)
    vazia = Sessao(created_at=datetime(2026, 8, 15, 15, tzinfo=UTC), rep_count=0)

    saida = resumo([vazia], hoje=hoje, protecoes_mes=1)

    assert dias_ativos([vazia]) == set()
    assert saida.streak == 0
    assert saida.xp == 0
    assert saida.treinou_hoje is False
    assert saida.meta_batida_hoje is False


def test_hold_e_valido_por_tempo_sustentado_e_nao_por_repeticao() -> None:
    """O ramo `hold` existe escrito e testado antes da T-098 chegar com a coluna.

    A modalidade entra por **parâmetro** justamente para isto: no dia em que o wall sit existir,
    o que muda é o mapa que a view passa, não a regra de validade.
    """
    agora = datetime(2026, 8, 15, 15, tzinfo=UTC)
    firme = Sessao(created_at=agora, exercise="wall_sit", rep_count=0, hold_valid_ms=12_000)
    curta = Sessao(created_at=agora, exercise="wall_sit", rep_count=0, hold_valid_ms=9_000)

    assert sessao_valida(firme, SCORING_HOLD) is True
    assert sessao_valida(curta, SCORING_HOLD) is False
    # E a MESMA sessão, contada como repetição, não vale nada — é o que o mapa decide.
    assert sessao_valida(firme, SCORING_REPS) is False


def test_scoring_ausente_do_mapa_vale_reps() -> None:
    """Todo exercício de hoje. Um default que fosse `hold` zeraria o produto inteiro."""
    sessoes = [sessao_em(date(2026, 8, 15), exercicio="jumping_jack")]

    assert dias_ativos(sessoes, {"wall_sit": SCORING_HOLD}) == dias("2026-08-15")


# ======================================================================================
# Critério 4 — proteções: perdoam, acabam, e renovam na virada do mês.
# ======================================================================================


def test_sequencia_simples_sem_falha() -> None:
    hoje = date(2026, 8, 15)
    ativos = dias("2026-08-15", "2026-08-14", "2026-08-13")

    info = streak(ativos, hoje, protecoes_mes=1)

    assert info.corrente == 3
    assert info.protecoes_usadas_mes == 0


def test_dia_falho_com_protecao_disponivel_nao_apaga_o_fogo() -> None:
    hoje = date(2026, 8, 15)
    # 13/08 faltou, e está no meio da sequência.
    ativos = dias("2026-08-15", "2026-08-14", "2026-08-12", "2026-08-11")

    info = streak(ativos, hoje, protecoes_mes=1)

    # Quatro dias TREINADOS. O dia protegido não entra na conta: ele não foi treinado, só não
    # interrompeu — "número de dias ativos consecutivos" é o que a spec conta.
    assert info.corrente == 4
    assert info.protecoes_usadas_mes == 1


def test_dia_falho_sem_protecao_apaga_o_fogo() -> None:
    hoje = date(2026, 8, 15)
    ativos = dias("2026-08-15", "2026-08-14", "2026-08-12", "2026-08-11")

    info = streak(ativos, hoje, protecoes_mes=0)

    assert info.corrente == 2


def test_dois_dias_falhos_seguidos_consomem_duas_protecoes() -> None:
    hoje = date(2026, 8, 15)
    ativos = dias("2026-08-15", "2026-08-14", "2026-08-11", "2026-08-10")

    com_duas = streak(ativos, hoje, protecoes_mes=2)
    com_uma = streak(ativos, hoje, protecoes_mes=1)

    assert com_duas.corrente == 4
    assert com_duas.protecoes_usadas_mes == 2
    # Com uma só, a segunda falha corta: sobra o pedaço de cá.
    assert com_uma.corrente == 2


def test_a_protecao_cobre_o_dia_falho_da_ponta() -> None:
    """A leitura fixada nesta task (ver o topo de `engagement.py`, nota 1).

    Treinou seg/ter/qua e faltou na quinta: na sexta de manhã, ANTES de treinar, o fogo tem de
    estar de pé. Uma proteção que só agisse entre dois dias treinados seria invisível no único
    momento em que importa — e o efeito dela seria indistinguível do "reacender", que a spec
    deixou como mecânica paga da Fase Evolução.
    """
    sexta = date(2026, 8, 14)
    ativos = dias("2026-08-12", "2026-08-11", "2026-08-10")  # qua, ter, seg

    with_protecao = streak(ativos, sexta, protecoes_mes=1)
    sem_protecao = streak(ativos, sexta, protecoes_mes=0)

    assert with_protecao.corrente == 3
    assert with_protecao.protecoes_usadas_mes == 1
    assert sem_protecao.corrente == 0


def test_hoje_sem_treino_nao_consome_protecao() -> None:
    """O dia não acabou. Cobrar por ele às 00h01 seria punir um treino que ainda pode acontecer."""
    hoje = date(2026, 8, 15)
    ativos = dias("2026-08-14", "2026-08-13")

    info = streak(ativos, hoje, protecoes_mes=1)

    assert info.corrente == 2
    assert info.protecoes_usadas_mes == 0


def test_fogo_apagado_nao_cobra_as_protecoes_que_nao_seguraram_nada() -> None:
    """Gastar proteção sem sustentar sequência tiraria do mês seguinte um perdão não recebido."""
    hoje = date(2026, 8, 15)
    ativos = dias("2026-06-01")  # muito antigo: nada alcança

    info = streak(ativos, hoje, protecoes_mes=2)

    assert info.corrente == 0
    assert info.protecoes_usadas_mes == 0


def test_protecoes_renovam_na_virada_do_mes() -> None:
    """O orçamento é por mês-calendário: o que julho gastou não sai da conta de agosto."""
    hoje = date(2026, 8, 3)
    ativos = dias(
        "2026-08-03", "2026-08-01", "2026-07-30", "2026-07-28", "2026-07-26"
    )  # falharam 02/08, 31/07, 29/07, 27/07

    info = streak(ativos, hoje, protecoes_mes=2)

    # 02/08 gasta 1 de agosto; 31/07 e 29/07 gastam as 2 de julho; 27/07 não tem mais e corta.
    assert info.corrente == 4
    assert info.protecoes_usadas_mes == 1


def test_sem_dia_ativo_nenhum_o_fogo_e_zero() -> None:
    assert streak(set(), date(2026, 8, 15), protecoes_mes=2).corrente == 0


def test_melhor_sequencia_lembra_o_pico_mesmo_com_o_fogo_apagado() -> None:
    hoje = date(2026, 8, 15)
    ativos = dias("2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04", "2026-07-05")

    info = streak(ativos, hoje, protecoes_mes=0)

    assert info.corrente == 0
    assert info.melhor == 5


# ======================================================================================
# Critério 10 — downgrade nunca apaga fogo (o piso do §Downgrade).
# ======================================================================================


def _sequencia_com_duas_protecoes_em_julho() -> tuple[set[date], date]:
    """Corrente que atravessa julho gastando 2 proteções lá, e chega até hoje em agosto."""
    hoje = date(2026, 8, 5)
    ativos = dias(
        "2026-08-05",
        "2026-08-04",
        "2026-08-03",
        "2026-08-02",
        "2026-08-01",
        "2026-07-31",
        "2026-07-29",
        "2026-07-27",
        "2026-07-26",
        "2026-07-25",
    )  # falharam 30/07 e 28/07
    return ativos, hoje


def test_rebaixar_o_plano_nao_encurta_sequencia_de_mes_anterior() -> None:
    """Critério de aceite 10, e o caso que a fórmula literal da spec errava.

    Assinante (2 proteções) atravessou julho gastando as duas. A assinatura vence, o plano cai
    para free (1) — e o fogo de 10 dias **não pode** virar 7 na hora exata em que a pessoa está
    decidindo se renova. Isso não é bug de cálculo: é churn produzido pela mecânica de retenção.
    """
    ativos, hoje = _sequencia_com_duas_protecoes_em_julho()

    como_assinante = streak(ativos, hoje, protecoes_mes=2)
    depois_do_downgrade = streak(ativos, hoje, protecoes_mes=1)

    assert como_assinante.corrente == 10
    assert depois_do_downgrade.corrente == 10


def test_o_beneficio_do_plano_some_para_frente_no_mes_corrente() -> None:
    """A outra metade da regra: para trás o perdão fica, para frente ele acaba.

    Sem isto, "a assinatura acabou" não significaria nada — e o piso viraria um jeito de manter
    duas proteções para sempre.
    """
    hoje = date(2026, 8, 15)
    ativos = dias("2026-08-15", "2026-08-14", "2026-08-11", "2026-08-10")  # falharam 12 e 13

    assert streak(ativos, hoje, protecoes_mes=2).corrente == 4
    assert streak(ativos, hoje, protecoes_mes=1).corrente == 2


def test_o_piso_historico_e_o_teto_do_catalogo_de_planos() -> None:
    """Explicita o número que o piso usa, para que mudar `PROTECOES_TETO` quebre aqui."""
    ativos, hoje = _sequencia_com_duas_protecoes_em_julho()

    assert PROTECOES_TETO == 2
    assert streak(ativos, hoje, protecoes_mes=1, protecoes_historicas=0).corrente == 7


# ======================================================================================
# XP e níveis (§XP) — só lê o SessionResult.
# ======================================================================================


def test_xp_de_uma_sessao_limpa_soma_os_tres_componentes() -> None:
    sessao = sessao_em(date(2026, 8, 15), reps=18, limpa=True)

    assert xp_da_sessao(sessao) == XP_SESSAO_VALIDA + 18 + XP_EXECUCAO_LIMPA


def test_o_bonus_de_execucao_limpa_cai_com_qualquer_aviso() -> None:
    """Feedback OU aviso de cena tira o bônus — os dois medem execução, e o §XP cita os dois."""
    com_feedback = sessao_em(date(2026, 8, 15), reps=10, limpa=False)
    com_cena = Sessao(
        created_at=datetime(2026, 8, 15, 15, tzinfo=UTC),
        rep_count=10,
        scene_warning_counts={"TOO_FAR": 3},
    )

    assert xp_da_sessao(com_feedback) == XP_SESSAO_VALIDA + 10
    assert xp_da_sessao(com_cena) == XP_SESSAO_VALIDA + 10


def test_o_componente_de_reps_tem_teto() -> None:
    maratona = sessao_em(date(2026, 8, 15), reps=120, limpa=False)

    assert xp_da_sessao(maratona) == XP_SESSAO_VALIDA + XP_TETO_REPS


def test_sessao_invalida_nao_da_xp_nenhum() -> None:
    vazia = Sessao(created_at=datetime(2026, 8, 15, 15, tzinfo=UTC), rep_count=0)

    assert xp_da_sessao(vazia) == 0


def test_xp_total_soma_as_sessoes() -> None:
    sessoes = [sessao_em(date(2026, 8, 14), reps=5), sessao_em(date(2026, 8, 15), reps=7)]

    assert xp_total(sessoes) == (XP_SESSAO_VALIDA + 5 + 10) + (XP_SESSAO_VALIDA + 7 + 10)


@pytest.mark.parametrize(
    ("xp", "numero"),
    [(0, 1), (99, 1), (100, 2), (299, 2), (300, 3), (LEVELS[-1], len(LEVELS))],
)
def test_nivel_cai_na_faixa_certa(xp: int, numero: int) -> None:
    assert nivel(xp).numero == numero


def test_o_ultimo_nivel_nao_promete_um_proximo() -> None:
    topo = nivel(LEVELS[-1] + 5_000)

    assert topo.xp_proximo is None
    assert topo.progresso == 1.0


def test_progresso_dentro_da_faixa() -> None:
    meio = nivel(200)  # faixa 100–300

    assert meio.xp_min == 100
    assert meio.xp_proximo == 300
    assert meio.progresso == pytest.approx(0.5)


# ======================================================================================
# O resumo inteiro, e a meta.
# ======================================================================================


def test_meta_conta_as_sessoes_validas_do_dia() -> None:
    hoje = date(2026, 8, 15)
    sessoes = [sessao_em(hoje), sessao_em(hoje)]

    casual = resumo(sessoes, hoje=hoje, protecoes_mes=1, meta="casual")
    intenso = resumo(sessoes, hoje=hoje, protecoes_mes=1, meta="intenso")

    assert casual.meta_alvo == METAS["casual"] and casual.meta_batida_hoje is True
    assert intenso.meta_alvo == METAS["intenso"] and intenso.meta_batida_hoje is False
    assert casual.sessoes_hoje == 2


def test_meta_desconhecida_cai_no_padrao_em_vez_de_quebrar() -> None:
    hoje = date(2026, 8, 15)

    saida = resumo([sessao_em(hoje)], hoje=hoje, protecoes_mes=1, meta="ultra")

    assert saida.meta == "casual"


def test_a_meta_nao_entra_na_conta_do_xp() -> None:
    """Critério 9, no nível da função pura.

    A meta é campo mutável do perfil; se pontuasse, trocá-la reescreveria XP de dias passados.
    """
    hoje = date(2026, 8, 15)
    sessoes = [sessao_em(hoje), sessao_em(hoje - timedelta(days=1))]

    xp_casual = resumo(sessoes, hoje=hoje, protecoes_mes=1, meta="casual").xp
    xp_intenso = resumo(sessoes, hoje=hoje, protecoes_mes=1, meta="intenso").xp

    assert xp_casual == xp_intenso


def test_o_corpo_carrega_a_versao_da_formula_de_xp() -> None:
    hoje = date(2026, 8, 15)

    corpo = resumo([sessao_em(hoje)], hoje=hoje, protecoes_mes=1).to_dict()

    assert corpo["xp_formula_v"] == XP_FORMULA_V


def test_o_corpo_nao_promete_conquistas_que_ainda_nao_existem() -> None:
    """`achievements` é a T-089. Lista vazia seria uma afirmação — e falsa."""
    hoje = date(2026, 8, 15)

    corpo = resumo([sessao_em(hoje)], hoje=hoje, protecoes_mes=1).to_dict()

    assert "achievements" not in corpo


# ======================================================================================
# Chave e TTL do cache — a data na chave é a regra, não detalhe.
# ======================================================================================


def test_a_chave_do_cache_carrega_a_data() -> None:
    assert chave_de_cache(7, date(2026, 8, 15)) == "df:eng:7:2026-08-15"


def test_o_ttl_morre_na_virada_do_dia_em_sao_paulo() -> None:
    quase_meia_noite = datetime(2026, 8, 15, 23, 50, tzinfo=FUSO_DO_FOGO)

    ttl = ttl_ate_a_virada(quase_meia_noite)

    assert 600 <= ttl <= 600 + 120


def test_o_ttl_de_manha_cobre_o_dia_inteiro() -> None:
    manha = datetime(2026, 8, 15, 8, 0, tzinfo=FUSO_DO_FOGO)

    assert ttl_ate_a_virada(manha) > 15 * 3600


def test_o_ttl_e_medido_em_sao_paulo_mesmo_recebendo_utc() -> None:
    """O mesmo instante, escrito nos dois fusos, tem de dar o mesmo TTL."""
    em_sp = datetime(2026, 8, 15, 23, 50, tzinfo=FUSO_DO_FOGO)

    assert ttl_ate_a_virada(em_sp.astimezone(UTC)) == ttl_ate_a_virada(em_sp)


def test_fuso_de_outro_lugar_nao_muda_o_dia_do_fogo() -> None:
    """Toda a mecânica vira em São Paulo, para todo mundo (Fase Inicial)."""
    toquio = ZoneInfo("Asia/Tokyo")
    instante = datetime(2026, 8, 15, 10, 0, tzinfo=toquio)  # 14/08 22h em SP

    assert dia_sp(instante) == date(2026, 8, 14)


def test_o_modulo_puro_nao_importa_django() -> None:
    """A promessa do topo do módulo, cobrada.

    Um `from django...` aqui dentro faria as fixtures precisarem de banco, e o critério 1
    deixaria de ser verdade sem ninguém notar.
    """
    from pathlib import Path

    fonte = Path(eng.__file__).read_text(encoding="utf-8")

    assert "import django" not in fonte
    assert "from django" not in fonte
