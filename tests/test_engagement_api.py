"""`GET /api/engagement`, o cache e a meta no perfil (T-086 / SPEC-019).

A derivação em si é testada em `test_engagement.py`, sem banco. O que se prova aqui é o que só
existe com banco e cache: a consulta traz as sessões certas, o cache guarda e devolve o mesmo
número, e ele degrada quando o Redis some.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from api import engagement as eng
from api import engagement_cache
from api.models import DailyGoal, Plan, SessionClaim, SessionResult, User
from django.core.cache import cache
from django.utils import timezone

SENHA = "polichinelo-2026"


@pytest.fixture
def usuario(db) -> User:
    return User.objects.create_user(email="ana@exemplo.com", password=SENHA)


@pytest.fixture
def outra_pessoa(db) -> User:
    return User.objects.create_user(email="bruno@exemplo.com", password=SENHA)


def autorizacao(client, email: str = "ana@exemplo.com") -> dict[str, str]:
    resposta = client.post(
        "/api/auth/login",
        data={"email": email, "password": SENHA},
        content_type="application/json",
    )
    assert resposta.status_code == 200, resposta.content
    return {"HTTP_AUTHORIZATION": f"Bearer {resposta.json()['access']}"}


def treino(
    dono: User | None,
    *,
    dias_atras: int = 0,
    reps: int = 10,
    limpa: bool = True,
    exercicio: str = "squat",
) -> SessionResult:
    """Uma sessão gravada como o report-builder grava, com `created_at` recuado à mão.

    `created_at` é `auto_now_add`: sem o `update` toda fixture nasceria hoje, e não haveria
    sequência nenhuma para medir.
    """
    quando = timezone.now() - timedelta(days=dias_atras)
    sid = f"s-{dono.pk if dono else 0}-{dias_atras}-{reps}-{exercicio}"
    SessionClaim.objects.create(session_id=sid, user=dono, device_id="dev-1")
    resultado = SessionResult.objects.create(
        session_id=sid,
        exercise=exercicio,
        mode="edge",
        reason="completed",
        rep_count=reps,
        feedback_counts={} if limpa else {"SQUAT_TOO_SHALLOW": 1},
    )
    SessionResult.objects.filter(pk=resultado.pk).update(created_at=quando)
    resultado.refresh_from_db()
    return resultado


# ======================================================================================
# Critério 8 — anônimo nunca vê número do servidor.
# ======================================================================================


def test_anonimo_recebe_401_e_nao_um_corpo_de_zeros(client, db) -> None:
    """Zeros do servidor seriam indistinguíveis de "nunca treinou" para o cliente.

    O visitante tem fogo fantasma, derivado no aparelho e rotulado como local (T-088) — e a spec
    pede exatamente que ninguém confunda um com o outro.
    """
    resposta = client.get("/api/engagement")

    assert resposta.status_code == 401


def test_o_fogo_de_um_nao_vaza_para_o_outro(client, usuario, outra_pessoa) -> None:
    treino(usuario, dias_atras=0)
    treino(outra_pessoa, dias_atras=0)
    treino(outra_pessoa, dias_atras=1)

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["streak"] == 1


def test_sessao_anonima_do_mesmo_aparelho_nao_entra_no_fogo_de_quem_tem_conta(
    client, usuario
) -> None:
    """Enquanto a T-087 não adotar as claims órfãs, elas não são de ninguém — e o servidor não
    pode fingir que são."""
    treino(None, dias_atras=1)
    treino(usuario, dias_atras=0)

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["streak"] == 1


# ======================================================================================
# A consulta: todas as datas, e só as válidas.
# ======================================================================================


def test_o_fogo_conta_dias_seguidos_do_banco(client, usuario) -> None:
    for atras in (0, 1, 2, 3):
        treino(usuario, dias_atras=atras)

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["streak"] == 4
    assert corpo["today_active"] is True
    assert corpo["best_streak"] == 4


def test_sessao_zerada_no_banco_nao_acende_o_fogo(client, usuario) -> None:
    treino(usuario, dias_atras=0, reps=0)

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["streak"] == 0
    assert corpo["xp"] == 0


def test_o_historico_nao_e_cortado_em_cinquenta_sessoes(client, usuario) -> None:
    """`HISTORY_LIMIT` corta a TELA de histórico; cortar aqui encurtaria a sequência de quem
    treina todo dia — exatamente quem a mecânica existe para premiar."""
    for atras in range(60):
        treino(usuario, dias_atras=atras)

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["streak"] == 60


def test_o_xp_soma_as_sessoes_do_banco(client, usuario) -> None:
    treino(usuario, dias_atras=0, reps=12, limpa=True)
    treino(usuario, dias_atras=1, reps=8, limpa=False)

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["xp"] == (10 + 12 + 10) + (10 + 8)
    assert corpo["level"]["number"] == 1


# ======================================================================================
# Critério 9 — mudar a meta não altera o XP.
# ======================================================================================


def test_meta_diaria_nasce_casual_e_e_editavel_por_rest(client, usuario) -> None:
    cabecalho = autorizacao(client)

    assert client.get("/api/me", **cabecalho).json()["daily_goal"] == DailyGoal.CASUAL

    resposta = client.patch(
        "/api/me",
        data={"daily_goal": "intenso"},
        content_type="application/json",
        **cabecalho,
    )

    assert resposta.status_code == 200
    assert resposta.json()["daily_goal"] == "intenso"
    usuario.refresh_from_db()
    assert usuario.daily_goal == "intenso"


def test_meta_invalida_e_recusada(client, usuario) -> None:
    resposta = client.patch(
        "/api/me",
        data={"daily_goal": "ultra"},
        content_type="application/json",
        **autorizacao(client),
    )

    assert resposta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.daily_goal == DailyGoal.CASUAL


def test_patch_sem_campo_conhecido_nao_finge_que_gravou(client, usuario) -> None:
    resposta = client.patch(
        "/api/me", data={"is_admin": True}, content_type="application/json", **autorizacao(client)
    )

    assert resposta.status_code == 400
    usuario.refresh_from_db()
    assert usuario.is_admin is False


def test_mudar_a_meta_nao_altera_o_xp_total(client, usuario) -> None:
    """Critério de aceite 9, ponta a ponta: lê o XP, troca a meta, relê."""
    treino(usuario, dias_atras=0, reps=15)
    cabecalho = autorizacao(client)

    antes = client.get("/api/engagement", **cabecalho).json()
    client.patch(
        "/api/me", data={"daily_goal": "intenso"}, content_type="application/json", **cabecalho
    )
    depois = client.get("/api/engagement", **cabecalho).json()

    assert antes["xp"] == depois["xp"]
    # E o que a meta MUDA muda mesmo — senão o teste acima passaria com o cache velho.
    assert antes["goal_done_today"] is True
    assert depois["goal_done_today"] is False
    assert depois["goal_target"] == 4


# ======================================================================================
# Critérios 6, 7 e 11 — o cache é otimização, nunca fonte.
# ======================================================================================


def test_recalcular_do_zero_reproduz_o_que_estava_no_cache(client, usuario) -> None:
    """Critério de aceite 6 — a promessa do §Entidade da spec, cobrada."""
    for atras in (0, 1, 2):
        treino(usuario, dias_atras=atras)
    cabecalho = autorizacao(client)

    do_cache_frio = client.get("/api/engagement", **cabecalho).json()
    do_cache_quente = client.get("/api/engagement", **cabecalho).json()
    cache.clear()
    recalculado = client.get("/api/engagement", **cabecalho).json()

    assert do_cache_frio == do_cache_quente == recalculado


def test_a_rota_responde_com_o_cache_fora_do_ar(client, usuario, monkeypatch) -> None:
    """Critério de aceite 7: degrada para consulta direta (P2 da SPEC-018)."""
    treino(usuario, dias_atras=0)

    class CacheQueMorreu:
        def get(self, *_a, **_k):
            raise RuntimeError("redis fora")

        def set(self, *_a, **_k):
            raise RuntimeError("redis fora")

        def delete(self, *_a, **_k):
            raise RuntimeError("redis fora")

    monkeypatch.setattr(engagement_cache, "cache", CacheQueMorreu())

    resposta = client.get("/api/engagement", **autorizacao(client))

    assert resposta.status_code == 200
    assert resposta.json()["streak"] == 1


def test_a_chave_de_ontem_nao_e_servida_hoje(client, usuario) -> None:
    """Critério de aceite 11.

    O payload muda **sozinho** à meia-noite, sem nenhuma escrita para disparar signal. Uma chave
    sem data serviria o fogo de ontem e a meta marcada como batida até a pessoa treinar de novo
    — ou seja, exatamente até deixar de precisar da informação.
    """
    treino(usuario, dias_atras=0)
    ontem = eng.dia_sp(timezone.now()) - timedelta(days=1)
    cache.set(eng.chave_de_cache(usuario.pk, ontem), {"streak": 999}, 3600)

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["streak"] == 1


def test_relatorio_novo_derruba_o_cache_do_dono(client, usuario) -> None:
    cabecalho = autorizacao(client)
    assert client.get("/api/engagement", **cabecalho).json()["streak"] == 0

    treino(usuario, dias_atras=0)

    assert client.get("/api/engagement", **cabecalho).json()["streak"] == 1


def test_relatorio_de_sessao_anonima_nao_quebra_a_invalidacao(client, db) -> None:
    """A sessão sem dono é o caso mais comum do produto — e não tem cache para limpar."""
    treino(None, dias_atras=0)  # não levanta


def test_editar_a_conta_derruba_o_cache(client, usuario) -> None:
    treino(usuario, dias_atras=0)
    cabecalho = autorizacao(client)
    assert client.get("/api/engagement", **cabecalho).json()["goal_target"] == 1

    usuario.daily_goal = "regular"
    usuario.save(update_fields=["daily_goal"])

    assert client.get("/api/engagement", **cabecalho).json()["goal_target"] == 2


# ======================================================================================
# O plano decide as proteções, e o vocabulário não pode divergir.
# ======================================================================================


def test_as_protecoes_vem_do_plano_da_conta(client, usuario, db) -> None:
    """Assinante recebe as 2 da SPEC-018 §A; a conta sem FK recebe a 1 do plano default."""
    cabecalho = autorizacao(client)
    assert client.get("/api/engagement", **cabecalho).json()["protections_month"] == 1

    usuario.plan = Plan.objects.get(slug="subscriber")
    usuario.save(update_fields=["plan"])

    assert client.get("/api/engagement", **cabecalho).json()["protections_month"] == 2


def test_sem_plano_no_banco_as_protecoes_caem_no_piso_do_codigo(client, usuario) -> None:
    """P2 da SPEC-018: tabela vazia devolve o produto de ontem, não capacidade zerada.

    Apaga os planos que a migration 0006 semeou — é o estado de um container novo antes da
    migration de dados, e o de alguém que apagou uma linha no painel.
    """
    Plan.objects.all().delete()
    cache.clear()

    corpo = client.get("/api/engagement", **autorizacao(client)).json()

    assert corpo["protections_month"] == 1  # piso do free, em `config._FLOOR_PLAN`


def test_o_vocabulario_da_meta_nao_diverge_entre_modelo_e_derivacao() -> None:
    """Um nível novo no `DailyGoal` sem o alvo correspondente cairia calado no default.

    Duas listas da mesma coisa em dois arquivos divergem sempre — no dia em que só uma for
    corrigida. Este teste é o que transforma esse dia num teste vermelho.
    """
    assert set(DailyGoal.values) == set(eng.METAS)


# ======================================================================================
# A decomposição de XP no relatório (T-088 / SPEC-019 §Superfícies).
# ======================================================================================


def test_o_relatorio_de_quem_tem_conta_traz_a_decomposicao_do_xp(client, usuario) -> None:
    """A linha "+38 · sessão 10 · reps 18 · limpa 10" é onde o bônus de forma ENSINA que forma
    vale ponto. O número sai do servidor porque a fórmula é versionada — um espelho em
    TypeScript ficaria para trás no dia em que ela mudasse, e nenhum teste compara linguagens."""
    resultado = treino(usuario, dias_atras=0, reps=18, limpa=True)

    corpo = client.get(f"/api/sessions/{resultado.session_id}/report", **autorizacao(client)).json()

    assert corpo["xp"] == {
        "total": 38,
        "session": 10,
        "reps": 18,
        "clean": 10,
        "formula_v": eng.XP_FORMULA_V,
    }


def test_treino_com_correcao_perde_o_bonus_de_limpeza(client, usuario) -> None:
    resultado = treino(usuario, dias_atras=0, reps=18, limpa=False)

    corpo = client.get(f"/api/sessions/{resultado.session_id}/report", **autorizacao(client)).json()

    assert corpo["xp"]["clean"] == 0
    assert corpo["xp"]["total"] == 28


def test_o_visitante_nao_recebe_xp_no_relatorio(client, db) -> None:
    """XP não existe para quem não tem conta (§Planos). A chave some — e não vem zerada, que
    o cliente leria como "não valeu nada"."""
    SessionClaim.objects.create(session_id="anon-1", user=None, device_id="dev-x")
    SessionResult.objects.create(
        session_id="anon-1", exercise="squat", mode="edge", reason="completed", rep_count=12
    )

    corpo = client.get("/api/sessions/anon-1/report").json()

    assert "xp" not in corpo


def test_o_historico_traz_o_xp_de_cada_sessao(client, usuario) -> None:
    treino(usuario, dias_atras=0, reps=5)

    corpo = client.get("/api/sessions?mine", **autorizacao(client)).json()

    assert corpo["results"][0]["xp"]["total"] == 25
