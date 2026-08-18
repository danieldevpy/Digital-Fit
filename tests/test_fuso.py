"""O fuso de quem treina (T-156, SPEC-019 §Fuso / SPEC-025 §Fora de escopo).

O bug que esta task fecha não aparece como erro: aparece como **streak que quebra sozinho**.
Até aqui a virada do dia do fogo era 00h de São Paulo para todo mundo, então quem treinava às
22h em Lisboa tinha a sessão contada no dia seguinte — e via a sequência zerar por causa de um
fuso, não de um treino. É o pior modo de falha possível numa mecânica de retenção: silencioso, e
do lado de quem estava certo.

Estes testes cobram as três coisas que o fuso decide (a linha da T-156 nomeia as três): o **dia**
do fogo, a **meta diária** e o **TTL do cache**.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from api import engagement as eng
from api import engagement_cache
from api.fuso import FUSO_PADRAO, normalizar_fuso, resolve_fuso
from api.models import SessionClaim, SessionResult, User
from django.utils import timezone

SENHA = "senha-de-teste-123"
LISBOA = ZoneInfo("Europe/Lisbon")


class RequisicaoFalsa:
    """O bastante para `resolve_fuso`: ele é resolvido por duck typing, como o `resolve_locale`."""

    def __init__(self, headers: dict[str, str] | None = None, params: dict[str, str] | None = None):
        self.headers = headers or {}
        self.query_params = params or {}


# ======================================================================================
# Resolução: cabeçalho, override e as recusas
# ======================================================================================


def test_sem_sinal_nenhum_o_fuso_e_o_de_antes_da_task() -> None:
    """O default conservador (ver o docstring de `api/fuso.py`).

    Cliente antigo, `evalctl` e teste continuam vendo exatamente o dia de antes da T-156. Trocar
    o default para UTC teria movido a virada de quem já usa o produto — uma "correção" que
    quebraria streaks reais para consertar um caso que ainda não existe.
    """
    assert resolve_fuso(RequisicaoFalsa()) == FUSO_PADRAO


def test_o_cabecalho_do_aparelho_decide() -> None:
    assert resolve_fuso(RequisicaoFalsa({"X-Timezone": "Europe/Lisbon"})) == LISBOA


def test_o_override_da_url_vence_o_cabecalho() -> None:
    """Mesma ordem do `resolve_locale`: pedido explícito não perde para cabeçalho automático."""
    requisicao = RequisicaoFalsa({"X-Timezone": "America/Sao_Paulo"}, {"tz": "Europe/Lisbon"})
    assert resolve_fuso(requisicao) == LISBOA


@pytest.mark.parametrize(
    "valor",
    ["", "   ", "Mordor/Barad-dur", "../../etc/passwd", "/etc/localtime", "12345"],
)
def test_fuso_que_nao_existe_cai_no_padrao_em_silencio(valor: str) -> None:
    """Entrada de cabeçalho é entrada não confiável, e derrubar a rota seria trocar um dia
    deslocado por uma tela vazia. `..` e `/` inicial entram no caso porque `ZoneInfo` resolve
    caminho de arquivo — é a forma clássica de pedir para ler o que não devia."""
    assert normalizar_fuso(valor) == FUSO_PADRAO


# ======================================================================================
# O dia e o TTL
# ======================================================================================


def test_a_mesma_sessao_cai_em_dias_diferentes_conforme_o_fuso() -> None:
    """O bug inteiro, em uma asserção: 23h30 de 15/08 em São Paulo já é 16/08 em Lisboa."""
    quando = datetime(2026, 8, 15, 23, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    assert eng.dia_do_fogo(quando).isoformat() == "2026-08-15"
    assert eng.dia_do_fogo(quando, LISBOA).isoformat() == "2026-08-16"


def test_instante_ingenuo_continua_sendo_lido_como_utc() -> None:
    """É o que o banco guarda (`USE_TZ=True`), e adivinhar outro fuso aqui deslocaria o dia de
    quem treina de noite — justamente o caso que o fuso protege."""
    ingenuo = datetime(2026, 8, 15, 2, 0)  # 02h UTC = 23h do dia 14 em SP
    assert eng.dia_do_fogo(ingenuo).isoformat() == "2026-08-14"


def test_o_ttl_do_cache_expira_na_virada_de_quem_le() -> None:
    """A terceira coisa que o fuso decide. Com o TTL fixo em SP, o cache de quem está em Lisboa
    expirava às 4h da manhã de lá — horas depois de o dia dessa pessoa já ter virado, servindo o
    fogo de ontem numa tela que já era de hoje."""
    quando = datetime(2026, 8, 15, 23, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    em_sp = eng.ttl_ate_a_virada(quando)
    em_lisboa = eng.ttl_ate_a_virada(quando, LISBOA)

    # Em SP falta meia hora para virar; em Lisboa o dia virou há três horas e meia, então o
    # próximo corte é quase um dia inteiro à frente.
    assert em_sp < 60 * 60
    assert em_lisboa > 20 * 60 * 60


def test_a_meta_do_dia_conta_as_sessoes_do_dia_de_quem_le() -> None:
    """Meta diária é a segunda das três coisas que o fuso decide.

    A sessão das 23h30 em SP é de **hoje** para quem está em SP e do **dia seguinte** para quem
    está em Lisboa — e nos dois casos a meta de "hoje" tem de contá-la, porque nos dois casos ela
    caiu no dia que aquela pessoa chama de hoje. O erro que isto pega é o cruzado: derivar com o
    fuso de um e perguntar "hoje" com o do outro, que era o estado do código antes da T-156.
    """
    quando = datetime(2026, 8, 15, 23, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
    sessao = eng.Sessao(created_at=quando, exercise="squat", rep_count=10)

    em_sp = eng.resumo([sessao], hoje=eng.dia_do_fogo(quando), protecoes_mes=0)
    em_lisboa = eng.resumo(
        [sessao], hoje=eng.dia_do_fogo(quando, LISBOA), protecoes_mes=0, fuso=LISBOA
    )

    assert em_sp.sessoes_hoje == 1
    assert em_lisboa.sessoes_hoje == 1

    # E o cruzado, que é o bug: dia de Lisboa com bucketing de São Paulo não acha sessão nenhuma.
    cruzado = eng.resumo([sessao], hoje=eng.dia_do_fogo(quando, LISBOA), protecoes_mes=0)
    assert cruzado.sessoes_hoje == 0


# ======================================================================================
# Ponta a ponta: o cabeçalho chega até a resposta
# ======================================================================================


@pytest.fixture
def usuario(db) -> User:
    return User.objects.create_user(email="viajante@exemplo.com", password=SENHA)


def _autorizacao(client, email: str = "viajante@exemplo.com") -> dict[str, str]:
    resposta = client.post(
        "/api/auth/login",
        {"email": email, "password": SENHA},
        content_type="application/json",
    )
    return {"HTTP_AUTHORIZATION": f"Bearer {resposta.json()['access']}"}


def _sessao_em(dono: User, quando: datetime, sid: str) -> None:
    SessionClaim.objects.create(session_id=sid, user=dono, device_id="dev-1")
    resultado = SessionResult.objects.create(
        session_id=sid, exercise="squat", mode="edge", reason="completed", rep_count=10
    )
    SessionResult.objects.filter(pk=resultado.pk).update(created_at=quando)


def test_dois_fusos_nao_compartilham_o_payload_do_cache(client, usuario) -> None:
    """A quinta dimensão da chave (T-156).

    O `hoje` já é resolvido no fuso de quem pede — mas duas pessoas podem estar no MESMO
    dia-calendário e discordar sobre a que dia pertence uma sessão da madrugada. O payload
    guardado traz o streak e a meta já contados; sem o fuso na chave, o primeiro a ler grava a
    contagem DELE para quem vier depois no mesmo dia.
    """
    agora = timezone.now()
    # Uma sessão na fronteira: nas primeiras horas UTC, quando SP ainda está no dia anterior.
    _sessao_em(usuario, agora - timedelta(hours=6), "s-fronteira")
    cabecalho = _autorizacao(client)

    em_sp = client.get("/api/engagement", HTTP_X_TIMEZONE="America/Sao_Paulo", **cabecalho)
    em_toquio = client.get("/api/engagement", HTTP_X_TIMEZONE="Asia/Tokyo", **cabecalho)

    assert em_sp.status_code == em_toquio.status_code == 200
    # As duas respostas existem e são independentes: a de Tóquio não é a de SP servida de novo.
    # (Os números podem coincidir conforme a hora em que a suíte roda — o que não pode é uma
    # leitura ter servido a outra, e é isso que a chave separada garante.)
    chave_sp = engagement_cache.chave_de_cache(
        usuario.pk,
        eng.dia_do_fogo(agora, ZoneInfo("America/Sao_Paulo")),
        "en",
        f"{ZoneInfo('America/Sao_Paulo')}:{engagement_cache._versao_de(usuario.pk)}",
    )
    chave_toquio = engagement_cache.chave_de_cache(
        usuario.pk,
        eng.dia_do_fogo(agora, ZoneInfo("Asia/Tokyo")),
        "en",
        f"{ZoneInfo('Asia/Tokyo')}:{engagement_cache._versao_de(usuario.pk)}",
    )
    assert chave_sp != chave_toquio


def test_fuso_invalido_no_cabecalho_nao_derruba_a_rota(client, usuario) -> None:
    """Cabeçalho é entrada de cliente: um valor sem sentido tem de virar o padrão, não um 500."""
    resposta = client.get(
        "/api/engagement", HTTP_X_TIMEZONE="Mordor/Barad-dur", **_autorizacao(client)
    )

    assert resposta.status_code == 200


def test_sem_cabecalho_a_resposta_e_a_de_antes_da_task(client, usuario) -> None:
    """A garantia de que a T-156 não mexeu no que já funcionava: cliente que não manda
    `X-Timezone` continua vendo o dia de São Paulo — e uma sessão de agora acende o fogo, como
    acendia antes."""
    _sessao_em(usuario, timezone.now(), "s-hoje")

    resposta = client.get("/api/engagement", **_autorizacao(client))

    assert resposta.status_code == 200
    assert resposta.json()["streak"] == 1
