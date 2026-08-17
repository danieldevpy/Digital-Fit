"""A série resolvida na admissão (SPEC-023 §4, T-136).

Os critérios de aceite que esta task fecha:

- **2b** — plano com `session_max_s = 30` (o Free de hoje) não admite modo contado: a série é
  recusada com motivo legível, e não cortada no meio;
- **4** — forjar `target_reps` ou o teto no cliente não muda nada: a meta e o teto que valem são
  os que o servidor resolveu (mesma prova da quota, SPEC-016 §4);
- **9**, na metade que é da API — corpo sem `set_mode`/`target_reps`/`set_index`/`set_total`
  (todo cliente anterior a esta spec) abre a sessão nos defaults, sem recusa.

O critério 4 é o que mais fácil se finge de testar. Um teste que só chame o endpoint pelo
caminho normal prova que o caminho normal funciona — não que não existe outro. Os daqui atacam
o que um cliente adulterado tentaria: meta gigante, meta zero, teto no corpo, modo contado sem
plano que o suporte e carimbo de série inventado. Em todos, o que se verifica é o **evento**,
porque é ele que o analysis-worker lê: o que não chega ao `session.started` não existe.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from api.config import COUNTED_MIN_CEILING_S, PLAN_SUBSCRIBER, capabilities_for, config_payload
from api.models import Plan, SessionClaim, User
from api.sessions import (
    COUNTED_UNAVAILABLE,
    DEFAULT_DURATION_S,
    CountedUnavailable,
    SessionRequest,
    SetPlan,
    create_session,
    resolve_set,
)

from tests.synthetic_keypoints import jumping_jack_poses, sequence, session_poses
from tests.test_analysis_worker import PAREDE_PARADA, envelope_pose
from tests.test_auth import SENHA, autorizacao
from tests.test_sessions import AGORA, FakeBus, FakeRedis
from workers.analysis_worker.router import AnalysisRouter
from workers.shared.bus import InMemoryBus
from workers.shared.events import (
    EventType,
    Mode,
    SessionCompleted,
    SessionEndReason,
    SessionStarted,
    SetMode,
    Stream,
)

#: Teto da assinatura depois da migration `0021`. Escrito aqui como número, e não importado do
#: piso: o teste existe para dizer QUAL é o número, e um teste que o importa da fonte que ele
#: verifica não verifica nada.
TETO_DA_ASSINATURA_S = 180


@pytest.fixture
def conta(db) -> User:
    """Conta sem plano atribuído — ou seja, `free`, que é o `is_default` da tabela."""
    return User.objects.create_user(email="ana@exemplo.com", password=SENHA, name="Ana")


@pytest.fixture
def assinante(conta) -> User:
    """A "flag manual no banco" da SPEC-016, enquanto não há checkout (T-036).

    Recarregado do banco: `update()` não toca no objeto em memória, e quem passasse o `conta`
    velho para `capabilities_for` leria o plano de antes — um teste verde pelo motivo errado.
    """
    User.objects.filter(pk=conta.pk).update(plan=Plan.objects.get(slug=PLAN_SUBSCRIBER))
    return User.objects.get(pk=conta.pk)


def admissao_falsa(monkeypatch) -> InMemoryBus:
    """Como a `test_sessions.admissao_falsa`, mas **repassando os kwargs da view**.

    A diferença é o ponto de metade destes testes: o que a view resolve (`set_plan`,
    `duration_s`) só chega ao evento se ela passar adiante, e um dublê que engula os kwargs
    provaria o contrário do que se quer provar — o teste passaria com a resolução no chão.
    """
    redis = FakeRedis()
    bus = InMemoryBus()
    monkeypatch.setattr("api.views.bus", lambda: FakeBus(redis))
    monkeypatch.setattr(
        "api.views.create_session",
        lambda pedido, **kwargs: create_session(
            pedido,
            **{**kwargs, "redis_client": redis, "event_bus": bus},
        ),
    )
    return bus


def abertura(bus: InMemoryBus) -> SessionStarted:
    """O `session.started` que a admissão publicou — o que o worker vai ler."""
    envelope = next(
        e for e in bus.published_in(Stream.POSE_FRAMES) if e.type is EventType.SESSION_STARTED
    )
    return SessionStarted.from_data(envelope.data)


def treinar(client, monkeypatch, corpo: dict, headers: dict | None = None):
    bus = admissao_falsa(monkeypatch)
    resposta = client.post(
        "/api/sessions", data=corpo, content_type="application/json", **(headers or {})
    )
    return resposta, bus


# --------------------------------------------------------------------------------------
# A regra, sem HTTP — `resolve_set` é função pura sobre o plano
# --------------------------------------------------------------------------------------


def caps_com(**mudancas):
    """Capacidades do visitante (piso do código, sem banco) com um campo trocado."""
    return replace(capabilities_for(None), **mudancas)


def test_modo_livre_nao_passa_por_nada_disto() -> None:
    """SPEC-023 §1: o modo livre é byte-a-byte o comportamento de hoje.

    Ele sai antes da régua do contado, então nem plano curto nem meta no corpo o alcançam —
    e é por isso que esta task não pôde quebrá-lo.
    """
    pedido = SessionRequest.parse({"exercise": "jumping_jack", "target_reps": 15})

    serie = resolve_set(pedido, caps_com(session_max_s=30))

    assert serie.set_mode is SetMode.LIVRE
    assert serie.duration_s == DEFAULT_DURATION_S
    # Meta pedida no modo livre é ruído: o número que viaja é `0`, e o worker não tem o que
    # encerrar por meta. Carregá-la "por via das dúvidas" seria plantar uma meta silenciosa
    # dentro do único modo que a spec prometeu não mudar.
    assert serie.target_reps == 0


def test_plano_de_30s_nao_tem_onde_a_serie_contada_acontecer() -> None:
    """Critério 2b, na régua: `session_max_s = 30` recusa, e a recusa carrega o teto."""
    pedido = SessionRequest.parse({"exercise": "jumping_jack", "set_mode": "contado"})

    with pytest.raises(CountedUnavailable) as recusa:
        resolve_set(pedido, caps_com(session_max_s=30))

    assert recusa.value.ceiling_s == 30
    # Motivo legível, não código: quem lê é gente. O texto diz o teto que o plano tem e o que
    # dá para fazer com ele — recusa sem saída é a que vira suporte.
    assert "modo contado" in str(recusa.value)
    assert "modo livre" in str(recusa.value)


def test_a_regua_e_o_dobro_da_janela_livre() -> None:
    """A fronteira exata, para que mudá-la exija mudar um teste que diz por quê."""
    assert COUNTED_MIN_CEILING_S == 60

    pedido = SessionRequest.parse({"exercise": "jumping_jack", "set_mode": "contado"})

    with pytest.raises(CountedUnavailable):
        resolve_set(pedido, caps_com(session_max_s=COUNTED_MIN_CEILING_S - 1))
    assert resolve_set(pedido, caps_com(session_max_s=COUNTED_MIN_CEILING_S)).duration_s == 60


def test_o_teto_da_serie_contada_e_o_session_max_s_do_plano() -> None:
    """SPEC-023 §4: sem coluna nova. O teto é o número que o plano já tinha."""
    pedido = SessionRequest.parse({"exercise": "jumping_jack", "set_mode": "contado"})

    serie = resolve_set(pedido, caps_com(session_max_s=TETO_DA_ASSINATURA_S))

    assert serie.set_mode is SetMode.CONTADO
    assert serie.duration_s == TETO_DA_ASSINATURA_S
    # E NÃO a janela: `duration_s()` do plano continua entregando 30 s, que é o que o modo
    # livre usa. Confundir os dois daria à série contada o teto de que ela provou não precisar.
    assert caps_com(session_max_s=TETO_DA_ASSINATURA_S).duration_s() == DEFAULT_DURATION_S


@pytest.mark.parametrize(
    ("pedida", "resolvida"),
    [
        (999, 30),  # teto dos steppers (`reps_max`)
        (1, 5),  # piso dos steppers (`reps_min`)
        (0, 15),  # não pediu: o default do painel
        (20, 20),  # dentro da faixa: o que a pessoa escolheu
    ],
)
def test_a_meta_que_vale_e_a_do_servidor(pedida: int, resolvida: int) -> None:
    """Critério 4, na régua: o corpo pede, o plano limita.

    A faixa é a MESMA dos steppers do painel (SPEC-018) — ter uma régua para desenhar o
    montador e outra para admitir a série é o que transforma um cliente adulterado numa meta
    de 500 repetições.
    """
    pedido = SessionRequest.parse(
        {"exercise": "jumping_jack", "set_mode": "contado", "target_reps": pedida}
    )

    serie = resolve_set(pedido, caps_com(session_max_s=TETO_DA_ASSINATURA_S))

    assert serie.target_reps == resolvida


@pytest.mark.parametrize("bruto", ["contadoo", "", None, 42, "CONTADO"])
def test_modo_de_serie_invalido_cai_no_livre_em_vez_de_derrubar(bruto) -> None:
    """Mesma tolerância do worker (`parse_set_mode`) e da vista (T-111).

    Um cliente novo com um valor que este servidor ainda não conhece perde a escolha, não o
    treino. `"CONTADO"` entra na lista porque maiúscula é erro de digitação de cliente, não
    valor novo.
    """
    pedido = SessionRequest.parse({"exercise": "jumping_jack", "set_mode": bruto})

    assert pedido.set_mode is SetMode.LIVRE
    assert resolve_set(pedido, caps_com()).set_mode is SetMode.LIVRE


@pytest.mark.parametrize(
    ("indice", "total", "esperado"),
    [
        (2, 3, (2, 3)),
        (4, 3, (0, 0)),  # série 4 de 3 não existe
        (1, 0, (0, 0)),  # índice sem total não diz nada
        (0, 3, (0, 0)),  # total sem índice, idem
        (-1, 3, (0, 0)),  # negativo já morre no `parse`
    ],
)
def test_carimbo_incoerente_vira_sessao_avulsa(indice, total, esperado) -> None:
    """§3: o carimbo é leitura, não escrita — e leitura errada é pior que leitura nenhuma.

    O servidor não é dono do treino na Fase Inicial (não há tabela, não há entidade), então ele
    não tem o que validar aqui além da coerência interna. "Série 4 de 3" viraria uma linha de
    relatório que mente; `0/0` é como toda sessão avulsa do passado se apresenta.
    """
    pedido = SessionRequest.parse(
        {"exercise": "jumping_jack", "set_index": indice, "set_total": total}
    )

    serie = resolve_set(pedido, caps_com())

    assert (serie.set_index, serie.set_total) == esperado


# --------------------------------------------------------------------------------------
# Critério 2b — a recusa pelo caminho real do HTTP
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_o_free_recebe_recusa_legivel_em_vez_de_serie_cortada(client, conta, monkeypatch) -> None:
    """Critério 2b inteiro: 403 com motivo, e **nenhuma sessão nascida**.

    O outro desfecho possível seria admitir a série com teto de 30 s e deixar a pessoa fazer 8
    de 15 — com o relatório dizendo que ela terminou. É o desfecho que a §4 chama de cortar no
    meio, e ele é pior justamente por ser silencioso.
    """
    resposta, bus = treinar(
        client,
        monkeypatch,
        {"exercise": "jumping_jack", "set_mode": "contado", "target_reps": 15},
        autorizacao(client),
    )

    assert resposta.status_code == 403
    corpo = resposta.json()
    assert corpo["code"] == COUNTED_UNAVAILABLE
    assert corpo["session_max_s"] == 30
    assert "modo contado" in corpo["detail"]
    # Sessão nenhuma: sem evento, sem posse, sem contador gasto. Recusar depois de consumir a
    # quota cobraria da pessoa um treino que ela não chegou a fazer.
    assert bus.published_in(Stream.POSE_FRAMES) == []
    assert SessionClaim.objects.count() == 0


@pytest.mark.django_db
def test_o_assinante_treina_contado_e_o_teto_e_o_do_plano(client, assinante, monkeypatch) -> None:
    """O outro lado do cadeado (SPEC-016): quem tem teto generoso entra, e o teto viaja."""
    resposta, bus = treinar(
        client,
        monkeypatch,
        {"exercise": "jumping_jack", "set_mode": "contado", "target_reps": 15},
        autorizacao(client),
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["set_mode"] == SetMode.CONTADO.value
    assert corpo["target_reps"] == 15
    # O ticket e o evento dizem o MESMO teto: o HUD conta para cima até onde o worker corta.
    assert corpo["duration_s"] == TETO_DA_ASSINATURA_S

    dados = abertura(bus)
    assert dados.set_mode is SetMode.CONTADO
    assert dados.target_reps == 15
    assert dados.duration_s == TETO_DA_ASSINATURA_S


@pytest.mark.django_db
def test_o_piso_do_codigo_e_a_linha_do_banco_dizem_o_mesmo_teto(assinante) -> None:
    """P2 da SPEC-018: com o Postgres fora, o assinante não perde o modo que acabou de pagar.

    Este é o par da migration `0021`. Se um dos dois números mudar sozinho, o modo contado
    passa a existir ou sumir dependendo de o banco estar de pé — que é a pior forma de uma
    capacidade se comportar.
    """
    assert Plan.objects.get(slug=PLAN_SUBSCRIBER).session_max_s == TETO_DA_ASSINATURA_S

    from api.config import _FLOOR_PLAN

    assert _FLOOR_PLAN[PLAN_SUBSCRIBER]["session_max_s"] == TETO_DA_ASSINATURA_S


@pytest.mark.django_db
def test_o_painel_manda_no_teto_e_nao_o_codigo(client, assinante, monkeypatch) -> None:
    """SPEC-018, critério 1: baixar o teto no painel tira o modo contado, sem deploy."""
    Plan.objects.filter(slug=PLAN_SUBSCRIBER).update(session_max_s=30)
    Plan.objects.get(slug=PLAN_SUBSCRIBER).save()  # dispara a invalidação do snapshot

    resposta, _ = treinar(
        client,
        monkeypatch,
        {"exercise": "jumping_jack", "set_mode": "contado"},
        autorizacao(client),
    )

    assert resposta.status_code == 403
    assert resposta.json()["code"] == COUNTED_UNAVAILABLE


@pytest.mark.django_db
def test_o_config_diz_se_o_plano_tem_modo_contado(conta, assinante) -> None:
    """A UI reflete a trava em vez de descobri-la batendo nela (mesmo papel do `GET /quota`).

    E lê um booleano pronto, não a régua: duas implementações da mesma comparação divergiriam,
    e a divergência apareceria como um montador que oferece a meta e uma admissão que a recusa.
    """
    assert config_payload(None)["session"]["counted"] is False
    assert config_payload(assinante)["session"]["counted"] is True


# --------------------------------------------------------------------------------------
# Critério 4 — forjar o cliente não muda a meta nem o teto
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_meta_forjada_no_corpo_chega_limitada_ao_worker(client, assinante, monkeypatch) -> None:
    """O caminho inteiro, porque é ele que vale: corpo → `resolve_set` → `session.started`.

    Provar o clamp só na função pura deixaria de fora a pergunta que interessa — se a view
    passa adiante o que resolveu. Um `create_session` chamado com o corpo cru passaria naquele
    teste e entregaria 999 ao worker.
    """
    resposta, bus = treinar(
        client,
        monkeypatch,
        {"exercise": "jumping_jack", "set_mode": "contado", "target_reps": 999},
        autorizacao(client),
    )

    assert resposta.status_code == 201
    assert resposta.json()["target_reps"] == 30
    assert abertura(bus).target_reps == 30


@pytest.mark.django_db
def test_teto_e_duracao_no_corpo_sao_ignorados(client, assinante, monkeypatch) -> None:
    """O corpo não tem onde escrever o teto — e mandá-lo assim mesmo não abre porta nenhuma."""
    resposta, bus = treinar(
        client,
        monkeypatch,
        {
            "exercise": "jumping_jack",
            "set_mode": "contado",
            "duration_s": 600,
            "session_max_s": 600,
        },
        autorizacao(client),
    )

    assert resposta.status_code == 201
    assert abertura(bus).duration_s == TETO_DA_ASSINATURA_S


@pytest.mark.django_db
def test_modo_contado_sem_plano_nao_vira_livre_em_silencio(client, conta, monkeypatch) -> None:
    """A recusa é dita, não contornada.

    Degradar para livre seria "gentil" e mentiroso: a pessoa pediu 15 repetições sem pressa e
    receberia 30 s de janela, com o relatório contando outra coisa. Quem escolhe o que fazer
    depois da recusa é o cliente (T-137), com o motivo na mão.
    """
    resposta, _ = treinar(
        client,
        monkeypatch,
        {"exercise": "jumping_jack", "set_mode": "contado"},
        autorizacao(client),
    )

    assert resposta.status_code == 403


@pytest.mark.django_db
def test_a_meta_forjada_nao_encerra_a_serie_onde_o_cliente_quis(
    client, assinante, monkeypatch
) -> None:
    """A costura inteira: `POST /api/sessions` → `session.started` → analysis-worker.

    Este é o critério 4 provado onde ele importa. Os testes acima mostram o número certo no
    ticket e no evento; só este mostra que é **por esse número que a série termina** — o
    cliente pediu 999 e a série fecha na 30ª repetição, que é a meta que o servidor resolveu.

    A parede fica parada (a razão está na `test_analysis_worker.PAREDE_PARADA`): com ela
    congelada nenhuma regra de relógio de parede pode fechar a sessão, então o fim que aparecer
    aqui só pode ter vindo da meta.
    """
    _, bus = treinar(
        client,
        monkeypatch,
        # `countdown_s: 0` porque a preparação da T-049 corre no relógio de PAREDE, e ela está
        # parada aqui: com "3, 2, 1" a contagem nunca começaria. É preferência de quem treina,
        # aceita no corpo, e desligá-la não mexe em nada do que este teste verifica.
        {
            "exercise": "jumping_jack",
            "set_mode": "contado",
            "target_reps": 999,
            "countdown_s": 0,
        },
        autorizacao(client),
    )
    envelope = next(
        e for e in bus.published_in(Stream.POSE_FRAMES) if e.type is EventType.SESSION_STARTED
    )

    router = AnalysisRouter()
    router.handle(envelope, now_wall_ms=PAREDE_PARADA)
    saidas: list = []
    # Mais repetições do que a meta resolvida: se ela não valesse, a série seguiria até o teto.
    for frame in sequence(session_poses(jumping_jack_poses(35))):
        saidas.extend(
            router.handle(envelope_pose(frame, envelope.session_id), now_wall_ms=PAREDE_PARADA)
        )

    fins = [e for e in saidas if e.type is EventType.SESSION_COMPLETED]
    assert len(fins) == 1
    payload = SessionCompleted.from_data(fins[0].data)
    assert payload.reason is SessionEndReason.TARGET_REACHED
    assert payload.rep_count == 30


# --------------------------------------------------------------------------------------
# Critério 9 (metade da API) — cliente anterior à SPEC-023 continua treinando
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_corpo_sem_os_campos_da_serie_abre_nos_defaults(client, conta, monkeypatch) -> None:
    """O corpo que todo cliente manda hoje: nenhum campo da SPEC-023, nenhuma recusa."""
    resposta, bus = treinar(
        client,
        monkeypatch,
        {"exercise": "jumping_jack", "requested_mode": "edge"},
        autorizacao(client),
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["set_mode"] == SetMode.LIVRE.value
    assert corpo["target_reps"] == 0
    assert (corpo["set_index"], corpo["set_total"]) == (0, 0)
    assert corpo["duration_s"] == DEFAULT_DURATION_S

    dados = abertura(bus)
    assert dados.set_mode is SetMode.LIVRE
    assert dados.duration_s == DEFAULT_DURATION_S


def test_sessao_sem_serie_resolvida_continua_livre() -> None:
    """`create_session` sem `set_plan` — `evalctl`, teste, qualquer caminho sem admissão."""
    ticket = create_session(
        SessionRequest(exercise="jumping_jack", requested_mode=Mode.EDGE),
        now=AGORA,
        redis_client=FakeRedis(),
        event_bus=InMemoryBus(),
    )

    assert ticket.set_plan == SetPlan()
    assert ticket.duration_s == DEFAULT_DURATION_S


# --------------------------------------------------------------------------------------
# A vaga cloud precisa durar a série, não o ticket
# --------------------------------------------------------------------------------------


class SlotsEspiao:
    """Semáforo que só anota com que prazo a vaga foi pedida."""

    def __init__(self) -> None:
        self.ttl_ms: int | None = None

    def acquire(self, _session_id: str, *, ttl_ms: int, now_ms: int | None = None) -> bool:
        self.ttl_ms = ttl_ms
        return True


@pytest.mark.parametrize(
    ("serie", "esperado_ms"),
    [
        # Livre: o prazo do ticket (45 s), exatamente como antes desta task.
        (SetPlan(), 45_000),
        # Contado: o teto da série. Mantido o prazo do ticket, o semáforo devolveria a vaga aos
        # 60 s com a pessoa ainda treinando, e uma 4ª sessão cloud entraria — três `pose-worker`
        # virariam quatro, e o orçamento da VPS que a SPEC-009 protege viraria ficção.
        (SetPlan(set_mode=SetMode.CONTADO, target_reps=15, duration_s=180), 180_000),
    ],
)
def test_a_vaga_cloud_cobre_a_serie_inteira(serie: SetPlan, esperado_ms: int) -> None:
    espiao = SlotsEspiao()

    create_session(
        SessionRequest(exercise="jumping_jack", requested_mode=Mode.CLOUD),
        now=AGORA,
        redis_client=FakeRedis(),
        event_bus=InMemoryBus(),
        slots=espiao,
        set_plan=serie,
    )

    assert espiao.ttl_ms == esperado_ms
