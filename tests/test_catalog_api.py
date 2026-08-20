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
def test_orientacao_recomendada_repete_o_que_o_scene_tip_ja_dizia() -> None:
    """SPEC-027 §E: a coluna é a `scene_tip` em forma que a TELA consegue comparar.

    Os quatro valores não são chute — são a mesma informação que o texto de cena já dava. Os
    de chão pedem o celular deitado; os em pé precisam da altura do quadro (no polichinelo os
    braços ainda sobem acima da cabeça).

    O default da coluna é `qualquer`, e ele continua sendo o certo para exercício futuro que
    não tenha opinião: `qualquer` não é omissão, é a afirmação de que as duas servem.
    """
    esperado = {
        "jumping_jack": "retrato",
        "squat": "retrato",
        "flexao": "paisagem",
        "abdominal": "paisagem",
    }
    for slug, valor in esperado.items():
        assert Exercise.objects.get(slug=slug).orientacao_recomendada == valor

    por_slug = {ex["slug"]: ex for ex in config_payload()["exercises"]}
    for slug, valor in esperado.items():
        assert por_slug[slug]["orientacao_recomendada"] == valor


@pytest.mark.django_db
def test_orientacao_editada_no_painel_chega_ao_cliente_pelo_caminho_de_sempre() -> None:
    """Sem rota nova e sem segundo canal — é campo de apresentação como os outros."""
    Exercise.objects.filter(slug="squat").update(orientacao_recomendada="paisagem")
    cache.delete(SNAPSHOT_KEY)

    por_slug = {ex["slug"]: ex for ex in config_payload()["exercises"]}
    assert por_slug["squat"]["orientacao_recomendada"] == "paisagem"


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
def test_todo_exercicio_tem_cadencia_de_referencia() -> None:
    """MET sem cadência não vira caloria por repetição — vira `--` na tela (T-128).

    Cobra o catálogo INTEIRO e não dois slugs: exercício novo entra pela `df-exercise` com MET
    preenchido, e é exatamente aí que se esquece o par. O sintoma seria mudo: o card de
    calorias simplesmente não apareceria naquele exercício.
    """
    sem_cadencia = [e.slug for e in Exercise.objects.all() if e.met and not e.ref_cadence_rpm]

    assert sem_cadencia == [], f"MET sem cadência de referência: {sem_cadencia}"


@pytest.mark.django_db
def test_cadencia_de_referencia_veio_da_migration() -> None:
    assert Exercise.objects.get(slug="jumping_jack").ref_cadence_rpm == 50
    assert Exercise.objects.get(slug="squat").ref_cadence_rpm == 20


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
def test_os_exercicios_de_chao_estao_na_prateleira_de_todo_mundo() -> None:
    """Onde a flexão e o abdominal pararam, e com que lastro cada um chegou lá.

    Os dois nasceram `beta` (T-106/T-107), calibrados só contra o boneco sintético. Hoje os dois
    são `validado` (T-113, migration 0019) — **por decisão de produto, e não pelo mesmo
    caminho**, o que este teste existe para não deixar esquecer:

    - a **flexão** passou pela T-111: oito itens de corpus, cinco com rótulo contado a mão,
      MAE de 0,20 repetição nas duas vistas;
    - o **abdominal** não tem um único vídeo de gente real, e a dívida segue declarada em
      `SEM_MATERIAL_REAL` (`tests/test_corpus_regressao.py`).

    A migration 0019 documenta o risco; o caminho de volta é o campo Maturidade no painel.
    """
    maturidades = dict(Exercise.objects.values_list("slug", "maturity"))

    assert maturidades["flexao"] == "validado"
    assert maturidades["abdominal"] == "validado"


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
    # `Authorization` e, desde a SPEC-025, o `Accept-Language` — sem eles um cache serviria a
    # mesma entrada para dois usuários, ou para duas línguas diferentes do mesmo usuário.
    assert "Authorization" in resposta["Vary"]
    assert "Accept-Language" in resposta["Vary"]
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


# --------------------------------------------------------------------------------------
# O locale como quarta dimensão do ETag (SPEC-025, T-143)
#
# `config_payload` ainda não traduz nada (o catálogo é da T-144/T-146) — o que estes testes
# provam é o MECANISMO: sem o locale no ETag, trocar `Accept-Language` reaproveitaria o
# `If-None-Match` de uma visita anterior e a rota devolveria `304` (corpo nenhum) para uma
# língua que ela nunca serviu.
# --------------------------------------------------------------------------------------


def test_locale_diferente_muda_o_etag() -> None:
    from api.config import config_etag

    assert config_etag(None, locale="pt-BR") != config_etag(None, locale="en")


@pytest.mark.django_db
def test_trocar_de_locale_nao_devolve_304(client) -> None:
    """Critério de aceite 6 (SPEC-025), na rota de verdade: o `If-None-Match` obtido em pt-BR
    não pode custar `304` quando o próximo pedido chega em inglês — tem de vir um corpo novo."""
    em_pt = client.get("/api/config", HTTP_ACCEPT_LANGUAGE="pt-BR")
    assert em_pt.status_code == 200

    em_en = client.get(
        "/api/config", HTTP_ACCEPT_LANGUAGE="en", headers={"If-None-Match": em_pt["ETag"]}
    )

    assert em_en.status_code == 200
    assert em_en.content  # um corpo de verdade, não o vazio de um 304
    assert em_en["ETag"] != em_pt["ETag"]


@pytest.mark.django_db
def test_mesmo_locale_continua_custando_304(client) -> None:
    """O contrapositivo do teste acima: a revalidação normal não quebrou com a dimensão nova."""
    primeira = client.get("/api/config", HTTP_ACCEPT_LANGUAGE="pt-BR")

    segunda = client.get(
        "/api/config", HTTP_ACCEPT_LANGUAGE="pt-BR", headers={"If-None-Match": primeira["ETag"]}
    )

    assert segunda.status_code == 304


@pytest.mark.django_db
def test_normalizacao_do_accept_language_produz_o_mesmo_etag(client) -> None:
    """`pt`, `pt-br` e `pt-BR;q=0.9` são o mesmo locale (critério 1) — e por isso o mesmo ETag."""
    canonico = client.get("/api/config", HTTP_ACCEPT_LANGUAGE="pt-BR")["ETag"]

    for variante in ("pt", "pt-br", "pt_BR", "pt-BR;q=0.9"):
        resposta = client.get("/api/config", HTTP_ACCEPT_LANGUAGE=variante)
        assert resposta["ETag"] == canonico, f"variante {variante!r} divergiu do ETag canônico"


@pytest.mark.django_db
def test_locale_via_query_param_vence_o_cabecalho_tambem_na_rota(client) -> None:
    """O `?locale=` explícito da SPEC-025 §1 tem de valer na rota real, não só na função pura."""
    via_override = client.get("/api/config?locale=en", HTTP_ACCEPT_LANGUAGE="pt-BR")
    via_cabecalho = client.get("/api/config", HTTP_ACCEPT_LANGUAGE="en")

    assert via_override["ETag"] == via_cabecalho["ETag"]


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
    # O par do MET (T-128). Sem ele no payload o cliente tem o numerador e não o denominador.
    assert polichinelo["ref_cadence_rpm"] == 50


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


# ======================================================================================
# Eixo maturidade (T-090 / SPEC-020 §Maturidade).
# ======================================================================================


@pytest.fixture
def usuario_free(db) -> User:
    """Conta sem FK de plano — o caso normal, que cai no plano default."""
    return User.objects.create_user(email="free@exemplo.com", password=SENHA)


@pytest.fixture
def usuario_assinante(db) -> User:
    conta = User.objects.create_user(email="sub@exemplo.com", password=SENHA)
    conta.plan = Plan.objects.get(slug=PLAN_SUBSCRIBER)
    conta.save(update_fields=["plan"])
    return conta


@pytest.fixture
def usuario_admin(db) -> User:
    """Ferramentas de dev (T-048) — a única porta do `beta`."""
    return User.objects.create_user(email="dev@exemplo.com", password=SENHA, is_admin=True)


@pytest.mark.django_db
def test_free_nao_ve_exercicio_beta(client) -> None:
    """Critério de aceite 1 da SPEC-020, metade da visibilidade.

    Nenhum exercício do catálogo é `beta` desde a T-113 — os quatro são `validado` —, então o
    teste **põe um lá** para cobrar a regra. Cobrar a lista de slugs seria cobrar o catálogo de
    hoje; o que precisa não voltar nunca é `beta` na tela de quem não é dev.
    """
    Exercise.objects.filter(slug="abdominal").update(maturity="beta")
    cache.delete(SNAPSHOT_KEY)

    visiveis = sorted(exercises_for(None))

    assert "abdominal" not in visiveis
    assert visiveis == ["flexao", "jumping_jack", "squat"]


@pytest.mark.django_db
def test_is_admin_ve_beta_e_o_resto(usuario_admin) -> None:
    """A única porta do `beta`, e é ferramenta de dev — o mesmo direito da T-048."""
    Exercise.objects.filter(slug="abdominal").update(maturity="beta")
    cache.delete(SNAPSHOT_KEY)

    assert sorted(exercises_for(usuario_admin)) == [
        "abdominal",
        "flexao",
        "jumping_jack",
        "squat",
    ]


@pytest.mark.django_db
def test_beta_NUNCA_e_liberado_por_plano(usuario_free) -> None:
    """A ortogonalidade que a spec exige, testada pelo caminho que a validação não cobre.

    `Plan.min_maturity` só oferece `validado` e `calibrado` no formulário — mas um `.update()`
    por SQL passa por cima disso. Se a regra fosse só a comparação ordenada, este UPDATE abriria
    o laboratório inteiro para todo mundo. O `if` explícito é o que a torna uma regra.
    """
    Exercise.objects.filter(slug="abdominal").update(maturity="beta")
    Plan.objects.filter(slug="free").update(min_maturity="beta")
    cache.delete(SNAPSHOT_KEY)

    # O piso do plano desceu ao chão e mesmo assim o `beta` não passa — é só isso que este teste
    # guarda, e é por isso que ele planta um `beta` em vez de contar com o catálogo do dia.
    visiveis = sorted(exercises_for(usuario_free))
    assert "abdominal" not in visiveis
    assert visiveis == ["flexao", "jumping_jack", "squat"]


@pytest.mark.django_db
def test_maturidade_desconhecida_some_para_quem_nao_e_admin(usuario_free, usuario_admin) -> None:
    """Valor fora do vocabulário não é `validado`, e tratá-lo como tal liberaria justamente o
    caso em que ninguém sabe o que aquilo é."""
    Exercise.objects.filter(slug="squat").update(maturity="dourado")
    cache.delete(SNAPSHOT_KEY)

    visiveis = sorted(exercises_for(usuario_free))
    assert "squat" not in visiveis
    assert visiveis == ["abdominal", "flexao", "jumping_jack"]
    assert "squat" in exercises_for(usuario_admin)


@pytest.mark.django_db
def test_o_assinante_enxerga_o_laboratorio(usuario_assinante, usuario_free) -> None:
    """Critério de aceite 2, metade do servidor: `calibrado` é o degrau que a assinatura compra
    neste eixo. O selo 🧪 na pré-config é a T-091."""
    Exercise.objects.filter(slug="flexao").update(maturity="calibrado")
    cache.delete(SNAPSHOT_KEY)

    assert "flexao" in exercises_for(usuario_assinante)
    assert "flexao" not in exercises_for(usuario_free)


@pytest.mark.django_db
def test_rebaixar_maturidade_no_painel_some_do_free_sem_deploy(usuario_free) -> None:
    """Critério de aceite 3. O `post_save` do `Exercise` invalida o snapshot (T-073), então a
    edição vale na requisição seguinte."""
    cache.delete(SNAPSHOT_KEY)
    assert "squat" in exercises_for(usuario_free)

    exercicio = Exercise.objects.get(slug="squat")
    exercicio.maturity = "calibrado"
    exercicio.save()

    assert "squat" not in exercises_for(usuario_free)


@pytest.mark.django_db
def test_a_admissao_recusa_exercicio_abaixo_da_maturidade(client, monkeypatch) -> None:
    """A UI nunca é a única trava (SPEC-020 §Fase Inicial): forjar o cliente não abre `beta`.

    Planta o `beta` em vez de contar com o catálogo do dia — desde a T-113 os quatro exercícios
    são `validado`, e um teste que dependesse disso mediria o catálogo, não a trava.
    """
    from tests.test_sessions import FakeRedis, admissao_falsa

    Exercise.objects.filter(slug="flexao").update(maturity="beta")
    admissao_falsa(monkeypatch, FakeRedis())
    cache.delete(SNAPSHOT_KEY)

    resposta = client.post(
        "/api/sessions",
        data={"exercise": "flexao", "mode": "edge"},
        content_type="application/json",
    )

    assert resposta.status_code == 403
    assert resposta.json()["code"] == "exercise_unavailable"


@pytest.mark.django_db
def test_o_catalogo_servido_nao_conta_o_que_esta_escondido(client) -> None:
    """O payload do `GET /api/config` é o MESMO resolvedor da admissão — se divergissem, haveria
    card na tela que o `POST /sessions` recusa, que é o `[A/T-051]`."""
    cache.delete(SNAPSHOT_KEY)

    Exercise.objects.filter(slug="abdominal").update(maturity="beta")
    cache.delete(SNAPSHOT_KEY)

    corpo = client.get("/api/config").json()
    slugs = {ex["slug"] for ex in corpo["exercises"]}

    assert slugs == {"jumping_jack", "squat", "flexao"}
    # E a maturidade viaja junto, para o selo da T-091 ter de onde sair.
    assert all("maturity" in ex for ex in corpo["exercises"])
