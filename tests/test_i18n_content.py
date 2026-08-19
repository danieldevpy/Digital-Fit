"""Tradução do conteúdo do banco (SPEC-025 §Tabela de tradução, T-146).

Três coisas para provar, na ordem dos critérios de aceite da spec:

1. As colunas de `Exercise`/`Plan`/`ExerciseGuideStep` continuam sendo o pt-BR — a migration
   `0022` não migra dado nenhum, só cria tabela nova.
2. `exercises_for()`/`config_payload()` resolvem por locale, com fallback honesto para a coluna
   base quando falta tradução (campo a campo, nunca em branco, nunca em chave crua).
3. `manage.py i18n_status` acusa um buraco de verdade — e só um buraco de verdade: campo vazio
   na própria fonte não é dívida de tradução, é ausência de conteúdo desde sempre.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from api.config import SNAPSHOT_KEY, config_payload, exercises_for
from api.i18n import SOURCE_LOCALE
from api.i18n_status import coletar
from api.models import (
    TRANSLATABLE_LOCALE_CHOICES,
    Exercise,
    ExerciseGuideStepTranslation,
    ExerciseTranslation,
    Plan,
    PlanTranslation,
)
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from tests.test_admin_panel import operador  # noqa: F401 — fixture reusada

pytestmark = pytest.mark.django_db

PAINEL = "/" + settings.ADMIN_PATH


@pytest.fixture(autouse=True)
def _limpa_snapshot():
    cache.delete(SNAPSHOT_KEY)
    yield
    cache.delete(SNAPSHOT_KEY)


# ------------------------------------------------------------------------------------------
# A forma da tabela — vocabulário de locale, FK exclusiva, campo tipado
# ------------------------------------------------------------------------------------------


def test_locale_traduzivel_e_so_o_que_nao_e_a_fonte() -> None:
    """Hoje só `en` — a fonte (`pt-BR`) não tem linha própria na tabela de tradução."""
    assert TRANSLATABLE_LOCALE_CHOICES == [("en", "en")]


def test_linha_de_traducao_na_fonte_e_recusada() -> None:
    """`clean()` recusa `locale="pt-BR"` mesmo que alguém contorne o `choices` do formulário."""
    exercicio = Exercise.objects.get(slug="squat")
    traducao = ExerciseTranslation(exercise=exercicio, locale=SOURCE_LOCALE, display_name="x")

    with pytest.raises(ValidationError):
        traducao.full_clean()


def test_fk_exclusiva_um_par_exercicio_locale_so() -> None:
    """Segunda linha para o mesmo (exercício, locale) é erro de banco, não sobrescrita
    silenciosa."""
    exercicio = Exercise.objects.get(slug="squat")
    ExerciseTranslation.objects.create(exercise=exercicio, locale="en", display_name="Squat")

    with pytest.raises(IntegrityError):
        ExerciseTranslation.objects.create(exercise=exercicio, locale="en", display_name="Squat 2")


def test_migration_nao_criou_traducao_nenhuma() -> None:
    """As colunas de `Exercise`/`Plan` continuam sendo o pt-BR — nada migrou para cá (§Tabela)."""
    assert ExerciseTranslation.objects.count() == 0
    assert PlanTranslation.objects.count() == 0
    assert ExerciseGuideStepTranslation.objects.count() == 0


# ------------------------------------------------------------------------------------------
# `exercises_for()` — resolução por locale, com fallback campo a campo
# ------------------------------------------------------------------------------------------


def test_locale_fonte_nao_dispara_overlay_nenhum() -> None:
    """`SOURCE_LOCALE` é o próprio caminho de ontem: nem uma consulta extra."""
    sem_locale = exercises_for(None)
    com_fonte_explicita = exercises_for(None, locale=SOURCE_LOCALE)

    assert sem_locale == com_fonte_explicita


def test_sem_traducao_nenhuma_cai_para_pt_br() -> None:
    """Critério 4: exercício cadastrado sem tradução aparece em português para o inglês."""
    base = exercises_for(None)["squat"]

    traduzido = exercises_for(None, locale="en")["squat"]

    assert traduzido["display_name"] == base["display_name"] == "Agachamento"
    assert traduzido["muscle_group"] == base["muscle_group"]
    assert traduzido["guide_steps"] == base["guide_steps"]


def test_traducao_completa_sobrepoe_todos_os_campos() -> None:
    exercicio = Exercise.objects.get(slug="squat")
    ExerciseTranslation.objects.create(
        exercise=exercicio,
        locale="en",
        display_name="Squat",
        muscle_group="Legs and glutes",
        default_tip="Sit back, chest up.",
        scene_tip="Stand, phone upright, 2 m away.",
    )

    traduzido = exercises_for(None, locale="en")["squat"]

    assert traduzido["display_name"] == "Squat"
    assert traduzido["muscle_group"] == "Legs and glutes"
    assert traduzido["default_tip"] == "Sit back, chest up."
    assert traduzido["scene_tip"] == "Stand, phone upright, 2 m away."


def test_traducao_parcial_cai_para_a_base_campo_a_campo() -> None:
    """Linha existe mas um campo ficou em branco (o `extra=1` do admin não foi preenchido
    inteiro) — o campo em branco cai para a base, os outros usam a tradução (critério 4)."""
    exercicio = Exercise.objects.get(slug="squat")
    base = exercises_for(None)["squat"]
    ExerciseTranslation.objects.create(
        exercise=exercicio, locale="en", display_name="Squat", muscle_group=""
    )

    traduzido = exercises_for(None, locale="en")["squat"]

    assert traduzido["display_name"] == "Squat"
    assert traduzido["muscle_group"] == base["muscle_group"]  # nunca em branco


def test_traducao_de_passo_do_guia_e_por_passo() -> None:
    """Um passo traduzido, os outros dois na base — nunca em branco, nunca misturado."""
    exercicio = Exercise.objects.get(slug="squat")
    base = exercises_for(None)["squat"]["guide_steps"]
    primeiro_passo = exercicio.guide_steps.order_by("ordem", "pk").first()
    ExerciseGuideStepTranslation.objects.create(
        guide_step=primeiro_passo, locale="en", texto="Feet shoulder-width apart."
    )

    traduzido = exercises_for(None, locale="en")["squat"]["guide_steps"]

    assert traduzido[0]["text"] == "Feet shoulder-width apart."
    assert traduzido[1:] == base[1:]


def test_traducao_de_passo_em_branco_cai_para_a_base() -> None:
    """`texto=""` na tradução é "sem tradução ainda", não "traduzido como vazio"."""
    exercicio = Exercise.objects.get(slug="squat")
    base = exercises_for(None)["squat"]["guide_steps"]
    primeiro_passo = exercicio.guide_steps.order_by("ordem", "pk").first()
    ExerciseGuideStepTranslation.objects.create(guide_step=primeiro_passo, locale="en", texto="")

    traduzido = exercises_for(None, locale="en")["squat"]["guide_steps"]

    assert traduzido == base


def test_traducao_de_um_exercicio_nao_vaza_para_outro() -> None:
    exercicio = Exercise.objects.get(slug="squat")
    ExerciseTranslation.objects.create(exercise=exercicio, locale="en", display_name="Squat")

    traduzido = exercises_for(None, locale="en")

    assert traduzido["jumping_jack"]["display_name"] == "Polichinelo"


def test_falha_de_banco_na_traducao_degrada_para_a_base(monkeypatch) -> None:
    """P2 aplicado à tradução: banco fora do ar não derruba o payload, só devolve a base."""
    base = exercises_for(None)

    def explode(*_a, **_kw):
        raise RuntimeError("postgres fora do ar")

    monkeypatch.setattr("api.models.ExerciseTranslation.objects.filter", explode)

    assert exercises_for(None, locale="en") == base


# ------------------------------------------------------------------------------------------
# `config_payload()` — o mesmo fallback, agora no nome/mensagem do plano
# ------------------------------------------------------------------------------------------


def test_config_payload_sem_traducao_de_plano_usa_o_nome_base() -> None:
    corpo = config_payload(None, locale="en")

    assert corpo["plan"]["name"] == "Visitante"


def test_config_payload_com_traducao_de_plano_usa_a_traducao() -> None:
    anon = Plan.objects.get(slug="anon")
    PlanTranslation.objects.create(
        plan=anon, locale="en", nome="Guest", quota_message="Create an account to keep training."
    )

    corpo = config_payload(None, locale="en")

    assert corpo["plan"]["name"] == "Guest"
    assert corpo["plan"]["quota_message"] == "Create an account to keep training."


def test_config_payload_com_traducao_parcial_do_plano_cai_para_a_base() -> None:
    """`quota_message` em branco na tradução cai para a mensagem base, `nome` usa a tradução."""
    anon = Plan.objects.get(slug="anon")
    base_message = config_payload(None)["plan"]["quota_message"]
    PlanTranslation.objects.create(plan=anon, locale="en", nome="Guest", quota_message="")

    corpo = config_payload(None, locale="en")

    assert corpo["plan"]["name"] == "Guest"
    assert corpo["plan"]["quota_message"] == base_message


def test_config_payload_exercicios_tambem_traduzidos() -> None:
    exercicio = Exercise.objects.get(slug="squat")
    ExerciseTranslation.objects.create(exercise=exercicio, locale="en", display_name="Squat")

    corpo = config_payload(None, locale="en")

    nomes = {e["slug"]: e["display_name"] for e in corpo["exercises"]}
    assert nomes["squat"] == "Squat"
    assert nomes["jumping_jack"] == "Polichinelo"  # sem tradução, cai na base


def test_config_payload_locale_padrao_e_a_fonte_sem_mudanca_de_comportamento() -> None:
    """Quem chama sem `locale` (código anterior à T-146) continua recebendo o payload de ontem."""
    exercicio = Exercise.objects.get(slug="squat")
    ExerciseTranslation.objects.create(exercise=exercicio, locale="en", display_name="Squat")

    corpo = config_payload(None)

    nomes = {e["slug"]: e["display_name"] for e in corpo["exercises"]}
    assert nomes["squat"] == "Agachamento"


# ------------------------------------------------------------------------------------------
# `manage.py i18n_status` — o buraco visível
# ------------------------------------------------------------------------------------------


def executar(*args: str) -> str:
    saida = StringIO()
    call_command("i18n_status", *args, stdout=saida)
    return saida.getvalue()


def test_sem_traducao_nenhuma_todo_exercicio_habilitado_aparece_no_relatorio() -> None:
    relatorio = coletar()

    assert relatorio.ok is False
    slugs = {gap.slug for gap in relatorio.exercicios}
    # Os quatro exercícios habilitados da migration (T-074/T-134) têm `display_name` e
    # `default_tip` preenchidos — logo, todos têm buraco de verdade para `en`.
    assert {"squat", "jumping_jack", "flexao", "abdominal"} <= slugs


def test_campo_vazio_na_propria_fonte_nao_e_reportado_como_buraco() -> None:
    """`scene_tip` do agachamento está em branco desde a migration — não há o que traduzir."""
    relatorio = coletar()

    gap = next(g for g in relatorio.exercicios if g.slug == "squat")
    assert "scene_tip" not in gap.campos_faltando


def test_traduzir_tudo_faz_o_exercicio_sumir_do_relatorio() -> None:
    exercicio = Exercise.objects.get(slug="squat")
    ExerciseTranslation.objects.create(
        exercise=exercicio,
        locale="en",
        display_name="Squat",
        muscle_group="Legs and glutes",
        default_tip="Sit back, chest up.",
        url_slug="squat",
        # scene_tip fica em branco na base e na tradução — não é buraco.
    )
    for passo in exercicio.guide_steps.all():
        ExerciseGuideStepTranslation.objects.create(guide_step=passo, locale="en", texto="step")

    relatorio = coletar()

    assert "squat" not in {gap.slug for gap in relatorio.exercicios}


def test_traduzir_so_os_campos_do_exercicio_ainda_deixa_os_passos_no_relatorio() -> None:
    exercicio = Exercise.objects.get(slug="squat")
    ExerciseTranslation.objects.create(
        exercise=exercicio,
        locale="en",
        url_slug="squat",
        display_name="Squat",
        muscle_group="Legs and glutes",
        default_tip="Sit back, chest up.",
    )

    relatorio = coletar()

    gap = next(g for g in relatorio.exercicios if g.slug == "squat")
    assert gap.campos_faltando == ()
    assert gap.passos_faltando == 3


def test_exercicio_desligado_fica_fora_do_relatorio_por_padrao() -> None:
    exercicio = Exercise.objects.get(slug="squat")
    exercicio.enabled = False
    exercicio.save()

    relatorio = coletar()

    assert "squat" not in {gap.slug for gap in relatorio.exercicios}


def test_todos_traz_o_exercicio_desligado_de_volta() -> None:
    exercicio = Exercise.objects.get(slug="squat")
    exercicio.enabled = False
    exercicio.save()

    relatorio = coletar(apenas_habilitados=False)

    assert "squat" in {gap.slug for gap in relatorio.exercicios}


def test_plano_com_mensagem_de_quota_em_branco_na_fonte_nao_e_buraco() -> None:
    """O assinante tem `quota_message=""` (sem limite, sem recusa) — nada para traduzir ali."""
    relatorio = coletar()

    gap_assinante = next((g for g in relatorio.planos if g.slug == "subscriber"), None)
    if gap_assinante is not None:
        assert "quota_message" not in gap_assinante.campos_faltando


def test_traduzir_o_plano_tira_ele_do_relatorio() -> None:
    anon = Plan.objects.get(slug="anon")
    PlanTranslation.objects.create(
        plan=anon, locale="en", nome="Guest", quota_message="Create an account to keep training."
    )

    relatorio = coletar()

    assert "anon" not in {gap.slug for gap in relatorio.planos}


def test_relatorio_vazio_quando_tudo_traduzido() -> None:
    for exercicio in Exercise.objects.filter(enabled=True):
        ExerciseTranslation.objects.create(
            exercise=exercicio,
            locale="en",
            display_name=f"{exercicio.display_name} EN",
            muscle_group=exercicio.muscle_group and f"{exercicio.muscle_group} EN",
            default_tip=exercicio.default_tip and f"{exercicio.default_tip} EN",
            scene_tip=exercicio.scene_tip and f"{exercicio.scene_tip} EN",
            # T-165: o endereço público da página também é campo traduzível — sem ele o
            # exercício continua (corretamente) no relatório, por faltar URL em inglês.
            url_slug=exercicio.url_slug and f"{exercicio.url_slug}-en",
        )
        for passo in exercicio.guide_steps.all():
            ExerciseGuideStepTranslation.objects.create(
                guide_step=passo, locale="en", texto=f"{passo.texto} EN"
            )
    for plano in Plan.objects.all():
        PlanTranslation.objects.create(
            plan=plano,
            locale="en",
            nome=f"{plano.nome} EN",
            quota_message=plano.quota_message and f"{plano.quota_message} EN",
        )

    relatorio = coletar()

    assert relatorio.ok is True
    assert relatorio.total == 0


# --------------------------------------------------------------------------------------
# O comando de verdade — o que o operador lê no terminal
# --------------------------------------------------------------------------------------


def test_comando_sem_buraco_imprime_sucesso() -> None:
    for exercicio in Exercise.objects.filter(enabled=True):
        ExerciseTranslation.objects.create(
            exercise=exercicio, locale="en", display_name=f"{exercicio.display_name} EN"
        )
        # Zera os outros campos traduzíveis na fonte para não sobrar buraco neste teste.
        exercicio.muscle_group = ""
        exercicio.default_tip = ""
        exercicio.scene_tip = ""
        # `url_slug` entrou na lista na T-165 (o endereço da página pública) e a migration o
        # semeou em pt-BR — zerar aqui mantém o teste falando do que ele quis falar.
        exercicio.url_slug = ""
        exercicio.save()
        for passo in exercicio.guide_steps.all():
            ExerciseGuideStepTranslation.objects.create(guide_step=passo, locale="en", texto="x")
    for plano in Plan.objects.all():
        PlanTranslation.objects.create(plan=plano, locale="en", nome="x", quota_message="x")

    saida = executar()

    assert "nada para traduzir" in saida


def test_comando_com_buraco_imprime_o_slug_e_o_locale() -> None:
    saida = executar()

    assert "squat" in saida
    assert "[en]" in saida


def test_comando_json_e_serializavel_e_bate_com_coletar() -> None:
    saida = executar("--json")
    corpo = json.loads(saida)

    relatorio = coletar()
    assert corpo["total"] == relatorio.total
    assert corpo["ok"] is False


# --------------------------------------------------------------------------------------
# Edição inline no painel — a UI de verdade, não só a função pura
#
# O admin não aninha `TabularInline` dentro de `TabularInline` (ver `ExerciseGuideStepAdmin`
# no `admin.py`): estes testes são a prova de que essa solução carrega de verdade, e não só
# no papel. Um `fk_name` errado, por exemplo, derrubaria a página com 500 aqui — nunca num
# teste unitário de `config.py`.
# --------------------------------------------------------------------------------------


@pytest.mark.urls("tests.urls_painel")
def test_tela_do_exercicio_carrega_com_o_inline_de_traducao(client, operador) -> None:  # noqa: F811
    client.force_login(operador)
    squat = Exercise.objects.get(slug="squat")

    resposta = client.get(f"{PAINEL}api/exercise/{squat.pk}/change/")

    assert resposta.status_code == 200
    assert b"translations-TOTAL_FORMS" in resposta.content


@pytest.mark.urls("tests.urls_painel")
def test_tela_do_plano_carrega_com_o_inline_de_traducao(client, operador) -> None:  # noqa: F811
    client.force_login(operador)
    anon = Plan.objects.get(slug="anon")

    resposta = client.get(f"{PAINEL}api/plan/{anon.pk}/change/")

    assert resposta.status_code == 200
    assert b"translations-TOTAL_FORMS" in resposta.content


@pytest.mark.urls("tests.urls_painel")
def test_tela_do_passo_do_guia_existe_e_carrega_com_o_inline_de_traducao(client, operador) -> None:  # noqa: F811
    """A tela própria que existe só para hospedar a tradução do passo (T-146)."""
    client.force_login(operador)
    squat = Exercise.objects.get(slug="squat")
    passo = squat.guide_steps.first()

    lista = client.get(f"{PAINEL}api/exerciseguidestep/")
    change = client.get(f"{PAINEL}api/exerciseguidestep/{passo.pk}/change/")

    assert lista.status_code == 200
    assert change.status_code == 200
    assert b"translations-TOTAL_FORMS" in change.content


@pytest.mark.urls("tests.urls_painel")
def test_salvar_traducao_de_exercicio_pelo_painel_reflete_no_resolvedor(client, operador) -> None:  # noqa: F811
    """O caminho ponta a ponta: formulário do painel → `exercises_for()` (critério 4 na prática)."""
    client.force_login(operador)
    squat = Exercise.objects.get(slug="squat")

    resposta = client.post(
        f"{PAINEL}api/exercise/{squat.pk}/change/",
        data={
            "slug": squat.slug,
            "display_name": squat.display_name,
            "category": squat.category,
            "muscle_group": squat.muscle_group,
            "ordem": squat.ordem,
            "enabled": "on",
            "default_tip": squat.default_tip,
            "main_angle": squat.main_angle,
            "demo_img": squat.demo_img,
            "dot_color": squat.dot_color,
            "scene_tip": squat.scene_tip,
            "met": squat.met,
            "ref_cadence_rpm": squat.ref_cadence_rpm,
            "maturity": squat.maturity,
            "guide_steps-TOTAL_FORMS": "0",
            "guide_steps-INITIAL_FORMS": "0",
            "guide_steps-MIN_NUM_FORMS": "0",
            "guide_steps-MAX_NUM_FORMS": "1000",
            "translations-TOTAL_FORMS": "1",
            "translations-INITIAL_FORMS": "0",
            "translations-MIN_NUM_FORMS": "0",
            "translations-MAX_NUM_FORMS": "1000",
            "translations-0-exercise": squat.pk,
            "translations-0-locale": "en",
            "translations-0-display_name": "Squat",
            "translations-0-muscle_group": "",
            "translations-0-default_tip": "",
            "translations-0-scene_tip": "",
        },
    )

    assert resposta.status_code == 302, resposta.context["adminform"].form.errors
    assert exercises_for(None, locale="en")["squat"]["display_name"] == "Squat"
