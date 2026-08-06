"""Catálogo servido e admissão travada (SPEC-018 §B, T-074).

O que estes testes protegem é a promessa do `[A/T-051]`: **card na tela e sessão admitida saem
da mesma lista**. Por isso o teste central não olha um ou outro — ele percorre o que o
`GET /api/config` devolveu e abre sessão de cada um.
"""

from __future__ import annotations

import pytest
from api.config import PLAN_ANON, PLAN_SUBSCRIBER, SNAPSHOT_KEY, config_payload, exercises_for
from api.models import Exercise, Plan, User
from django.core.cache import cache
from django.core.exceptions import ValidationError

from tests.test_config import RedisFalso, admissao  # noqa: F401 — fixture reusada
from workers.analysis_worker.exercises import EXERCISES
from workers.shared.events import Code

SENHA = "segredo-de-teste-123"


@pytest.fixture(autouse=True)
def _limpa_snapshot():
    cache.delete(SNAPSHOT_KEY)
    yield
    cache.delete(SNAPSHOT_KEY)


# --------------------------------------------------------------------------------------
# A migration de dados — o catálogo de hoje, e nada além
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_migration_traz_os_dois_exercicios_com_os_dados_do_cliente() -> None:
    polichinelo = Exercise.objects.get(slug="jumping_jack")

    assert polichinelo.display_name == "Polichinelo"
    assert polichinelo.muscle_group == "Corpo inteiro"
    assert polichinelo.main_angle == "arm_abduction"
    assert polichinelo.dot_color == "#34d399"
    assert polichinelo.guide_steps.count() == 3
    assert Exercise.objects.get(slug="squat").main_angle == "none"


@pytest.mark.django_db
def test_categoria_virou_slug_e_nao_string_de_exibicao() -> None:
    """`'Cardio'` copiado do cliente quebraria conquistas (019) e mix por objetivo (022)."""
    assert Exercise.objects.get(slug="jumping_jack").category == "cardio"
    assert Exercise.objects.get(slug="squat").category == "forca"


@pytest.mark.django_db
def test_met_veio_da_tabela_da_spec() -> None:
    assert float(Exercise.objects.get(slug="jumping_jack").met) == 8.0
    assert float(Exercise.objects.get(slug="squat").met) == 5.0


@pytest.mark.django_db
def test_os_dois_primeiros_nascem_validado_por_decisao_declarada() -> None:
    """Grandfathering da SPEC-018: o critério de `validado` não foi medido para nenhum dos dois.

    Se este teste começar a falhar porque alguém rebaixou um deles, o Free fica sem exercício —
    leia a SPEC-018 §Grandfathering antes de "consertar" o teste.
    """
    maturidades = dict(Exercise.objects.values_list("slug", "maturity"))

    assert maturidades["jumping_jack"] == "validado"
    assert maturidades["squat"] == "validado"


@pytest.mark.django_db
def test_exercicio_de_chao_nasce_beta_e_nao_herda_o_grandfathering() -> None:
    """O oposto do teste acima, e é o que separa decisão declarada de decisão medida.

    A flexão e o abdominal (T-106/T-107) tiveram os limiares calibrados no gerador sintético,
    contra nenhum vídeo de gente treinando. `beta` é a afirmação verdadeira sobre isso, e o
    grandfathering da SPEC-018 valia para os dois que já estavam no ar — não é um selo que se
    herda por chegar depois.
    """
    maturidades = dict(Exercise.objects.values_list("slug", "maturity"))

    assert maturidades["flexao"] == "beta"
    assert maturidades["abdominal"] == "beta"


# --------------------------------------------------------------------------------------
# A trava de slug (critério 4 da SPEC-018)
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_slug_fora_do_registro_nao_salva() -> None:
    exercicio = Exercise(slug="levitacao", display_name="Levitação")

    with pytest.raises(ValidationError) as erro:
        exercicio.full_clean()

    assert "slug" in erro.value.message_dict
    # A mensagem diz o que fazer, não só o que aconteceu: quem está no painel achava que estava
    # cadastrando um exercício.
    assert "codigo" in str(erro.value).lower()


@pytest.mark.django_db
def test_slug_do_registro_salva() -> None:
    for slug in EXERCISES:
        Exercise.objects.get(slug=slug).full_clean()


# --------------------------------------------------------------------------------------
# O resolvedor único — o coração do [A/T-051]
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_catalogo_e_admissao_saem_da_mesma_lista(client, admissao) -> None:  # noqa: F811
    """Critério 11 da SPEC-018, por construção: tudo que o config devolve, a admissão aceita."""
    payload = client.get("/api/config").json()
    assert payload["exercises"], "config sem catálogo — o teste abaixo não provaria nada"

    for exercicio in payload["exercises"]:
        resposta = client.post(
            "/api/sessions",
            data={"exercise": exercicio["slug"], "requested_mode": "edge"},
            content_type="application/json",
        )
        assert resposta.status_code == 201, exercicio["slug"]


@pytest.mark.django_db
def test_exercicio_desligado_some_do_catalogo_e_a_admissao_recusa(client, admissao) -> None:  # noqa: F811
    """Critério 3 da SPEC-018 — e a metade que faltava: a UI nunca é a única trava."""
    Exercise.objects.filter(slug="squat").update(enabled=False)
    Exercise.objects.get(slug="squat").save()

    payload = client.get("/api/config").json()
    servidos = [e["slug"] for e in payload["exercises"]]
    assert "squat" not in servidos
    assert "jumping_jack" in servidos  # o resto do catálogo não foi junto

    resposta = client.post(
        "/api/sessions",
        data={"exercise": "squat", "requested_mode": "edge"},
        content_type="application/json",
    )

    assert resposta.status_code == 403
    assert resposta.json()["code"] == "exercise_unavailable"


@pytest.mark.django_db
def test_exclusivo_de_plano_nao_abre_para_quem_nao_tem(client, admissao) -> None:  # noqa: F811
    """`min_plan` é a trava comercial: o cadeado precisa valer na API, não só na tela."""
    assinatura = Plan.objects.get(slug=PLAN_SUBSCRIBER)
    Exercise.objects.filter(slug="squat").update(min_plan=assinatura)
    Exercise.objects.get(slug="squat").save()

    # Anônimo não vê nem abre.
    servidos = [e["slug"] for e in client.get("/api/config").json()["exercises"]]
    assert "squat" not in servidos
    assert "jumping_jack" in servidos
    recusa = client.post(
        "/api/sessions",
        data={"exercise": "squat", "requested_mode": "edge"},
        content_type="application/json",
    )
    assert recusa.status_code == 403

    # Assinante vê.
    assinante = User.objects.create_user(email="ass@x.com", password=SENHA, plan=assinatura)
    assert "squat" in exercises_for(assinante)


@pytest.mark.django_db
def test_exclusividade_falha_fechada_sem_catalogo_resolvido(monkeypatch) -> None:
    """Sem ordem de plano resolvível, o exclusivo some — o resto continua aparecendo.

    Os dois lados falham para o lado certo de cada um: esconder tudo esvaziaria a tela Escolha
    num soluço de banco; deixar o exclusivo aberto entregaria conteúdo pago de graça.
    """
    assinatura = Plan.objects.get(slug=PLAN_SUBSCRIBER)
    Exercise.objects.filter(slug="squat").update(min_plan=assinatura)
    Exercise.objects.get(slug="squat").save()

    original = __import__("api.config", fromlist=["_read_snapshot_from_db"])._read_snapshot_from_db

    def sem_ordens():
        dados = original()
        dados["plan_order"] = {}
        return dados

    monkeypatch.setattr("api.config._read_snapshot_from_db", sem_ordens)
    cache.delete(SNAPSHOT_KEY)

    visiveis = exercises_for(None)

    assert "jumping_jack" in visiveis
    assert "squat" not in visiveis


def test_sem_banco_a_admissao_ainda_conhece_o_registro() -> None:
    """P2: catálogo fora do ar não pode impedir alguém de treinar o que já existia."""
    assert set(exercises_for(None)) == set(EXERCISES)


def test_sem_banco_o_catalogo_servido_vem_vazio() -> None:
    """Vazio quer dizer "não sei, use o seu" — card em branco seria pior que card nenhum."""
    assert config_payload(None)["exercises"] == []


# --------------------------------------------------------------------------------------
# Cache e ETag — a resposta é privada
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_config_responde_privado_e_com_etag(client) -> None:
    resposta = client.get("/api/config")

    assert resposta.status_code == 200
    assert resposta["Cache-Control"] == "private, must-revalidate"
    # `Accept` é acrescentado pela negociação de conteúdo do DRF; o que esta task garante é o
    # `Authorization`, sem o qual um cache serviria a mesma entrada para dois usuários.
    assert "Authorization" in resposta["Vary"]
    assert resposta["ETag"]


@pytest.mark.django_db
def test_revalidar_com_o_mesmo_etag_custa_304(client) -> None:
    etag = client.get("/api/config")["ETag"]

    resposta = client.get("/api/config", headers={"If-None-Match": etag})

    assert resposta.status_code == 304


@pytest.mark.django_db
def test_planos_diferentes_recebem_etags_diferentes(client) -> None:
    """Critério 10: ETag só sobre `config_version` faria um proxy servir o catálogo do
    assinante para o próximo Free que revalidasse."""
    from api.config import config_etag

    assinatura = Plan.objects.get(slug=PLAN_SUBSCRIBER)
    assinante = User.objects.create_user(email="e@x.com", password=SENHA, plan=assinatura)

    assert config_etag(None) != config_etag(assinante)


@pytest.mark.django_db
def test_is_admin_muda_o_etag() -> None:
    """`beta` será visível só para `is_admin` (T-090); o ETag já precisa saber disso hoje."""
    from api.config import config_etag

    comum = User.objects.create_user(email="f@x.com", password=SENHA)
    dev = User.objects.create_user(email="g@x.com", password=SENHA, is_admin=True)

    assert config_etag(comum) != config_etag(dev)


@pytest.mark.django_db
def test_editar_exercicio_muda_o_etag(client) -> None:
    antes = client.get("/api/config")["ETag"]

    exercicio = Exercise.objects.get(slug="squat")
    exercicio.display_name = "Agachamento livre"
    exercicio.save()

    assert client.get("/api/config")["ETag"] != antes


@pytest.mark.django_db
def test_editar_passo_do_guia_invalida_o_catalogo(client) -> None:
    """Os passos viajam dentro do exercício: sem invalidar, o Guia serviria o texto antigo."""
    payload = client.get("/api/config").json()
    passo = next(e for e in payload["exercises"] if e["slug"] == "squat")["guide_steps"][0]

    alvo = Exercise.objects.get(slug="squat").guide_steps.first()
    alvo.texto = "Texto novo do primeiro passo."
    alvo.save()

    depois = client.get("/api/config").json()
    novo = next(e for e in depois["exercises"] if e["slug"] == "squat")["guide_steps"][0]
    assert novo["text"] == "Texto novo do primeiro passo."
    assert novo["text"] != passo["text"]


# --------------------------------------------------------------------------------------
# O payload
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_payload_nao_conta_a_regra_ao_cliente() -> None:
    """`enabled` e `min_plan` são decisão interna: quem chegou ao payload já passou por ela."""
    for exercicio in config_payload(None)["exercises"]:
        assert "enabled" not in exercicio
        assert "min_plan" not in exercicio


@pytest.mark.django_db
def test_payload_traz_capacidades_e_faixas(client) -> None:
    corpo = client.get("/api/config").json()

    assert corpo["plan"]["slug"] == PLAN_ANON
    assert corpo["session"]["duration_s"] == 30
    assert corpo["steppers"] == {
        "series_min": 1,
        "series_max": 9,
        "series_default": 1,
        "reps_min": 5,
        "reps_max": 30,
        "reps_default": 15,
    }
    assert corpo["config_version"] >= 0


@pytest.mark.django_db
def test_payload_traz_met_e_maturity_para_a_fase_5(client) -> None:
    """A T-090 e o kcal consomem estes dois; a T-074 só os carrega até aqui."""
    polichinelo = next(
        e for e in client.get("/api/config").json()["exercises"] if e["slug"] == "jumping_jack"
    )

    assert polichinelo["met"] == 8.0
    assert polichinelo["maturity"] == "validado"


# --------------------------------------------------------------------------------------
# Texto de feedback no payload (T-126) — o relatório precisa falar português
# --------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_payload_traz_o_texto_de_todo_codigo_do_contrato(client) -> None:
    """O cliente traduz `{código: contagem}` sozinho — e o relatório é onde isso aparece.

    Sem esta parte do payload ele dependia de um mapa próprio, escrito quando o polichinelo era
    o único exercício que contava. `SQUAT_TOO_SHALLOW` chegava à tela com nome de constante.
    """
    feedback = client.get("/api/config").json()["feedback"]

    for code in Code:
        assert code.value in feedback, f"codigo sem texto no payload: {code.value}"
        assert feedback[code.value]["message"]


@pytest.mark.django_db
def test_payload_e_motor_leem_o_mesmo_catalogo(client) -> None:
    """Duas cópias do mesmo texto divergem; esta é a mesma promessa do `[A/T-051]`."""
    from workers.analysis_worker.feedback import FeedbackCatalog

    feedback = client.get("/api/config").json()["feedback"]
    entradas = FeedbackCatalog.load().entries

    assert feedback["SQUAT_TOO_SHALLOW"]["message"] == entradas[Code.SQUAT_TOO_SHALLOW].message
    assert feedback["HIPS_PIKED"]["hint"] == entradas[Code.HIPS_PIKED].hint
