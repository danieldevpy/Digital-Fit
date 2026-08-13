"""Painel de operação (T-072 / SPEC-018).

O que estes testes protegem é a fronteira do painel, não o CRUD que o Django dá pronto:

- quem entra (`is_staff`) e quem **não** entra — inclusive quem tem a outra flag privilegiada;
- que o painel não existe com a variável desligada, nem no processo do gateway;
- que dado derivado de evento (`SessionResult`) não se edita por formulário.

O contrário disso já custou caro no projeto: a T-048 descobriu a superfície de dev exposta em
produção porque "comentário não é gate". Painel é a mesma classe de problema, com mais dado
atrás.
"""

from __future__ import annotations

import pytest
from api.models import SessionResult, User
from core.admin_gate import belongs_to_admin, block_admin
from core.urls import build_urlpatterns
from django.conf import settings

from tests.test_auth import SENHA

PAINEL = "/" + settings.ADMIN_PATH


@pytest.fixture
def comum(db) -> User:
    return User.objects.create_user(email="ana@exemplo.com", password=SENHA, name="Ana")


@pytest.fixture
def operador(db) -> User:
    return User.objects.create_user(
        email="chefe@exemplo.com", password=SENHA, name="Chefe", is_staff=True
    )


# --- a rota existe? ---------------------------------------------------------------------


def test_variavel_desligada_nao_monta_a_rota() -> None:
    """A garantia que importa em produção, e a única que não dá para exercer por requisição.

    Rota já importada não se desmonta — por isso os testes de acesso montam a URLconf do
    painel por `@pytest.mark.urls`, e a decisão de montá-la ou não é verificada aqui, na
    função que `core/urls.py` usa de verdade.
    """
    desligado = build_urlpatterns(admin_enabled=False, admin_path="painel/")
    ligado = build_urlpatterns(admin_enabled=True, admin_path="painel/")

    assert len(desligado) == 1
    assert len(ligado) == len(desligado) + 1


@pytest.mark.parametrize(
    ("caminho", "esperado"),
    [
        ("/painel", True),
        ("/painel/", True),
        ("/painel/api/user/", True),
        ("/api/sessions", False),
        ("/painelzinho/", False),
        # O caso que um `in` ingênuo bloquearia: a palavra existe, o prefixo não.
        ("/api/sessions/painel/", False),
    ],
)
def test_reconhece_o_que_e_do_painel(caminho: str, esperado: bool) -> None:
    assert belongs_to_admin(caminho, "painel/") is esperado


@pytest.mark.asyncio
async def test_gateway_nao_serve_o_painel_nem_com_a_variavel_ligada() -> None:
    """Critério 5 da SPEC-018.

    A separação por variável de ambiente cairia no dia em que alguém movesse
    `DJANGO_ENABLE_ADMIN` para o bloco compartilhado do compose. Esta trava é do processo.
    """
    chamou_o_app = False

    async def app_de_baixo(scope, receive, send) -> None:
        nonlocal chamou_o_app
        chamou_o_app = True

    respostas: list[dict] = []

    async def send(mensagem: dict) -> None:
        respostas.append(mensagem)

    async def receive() -> dict:
        return {"type": "http.request"}

    protegido = block_admin(app_de_baixo, "painel/")
    await protegido({"type": "http", "path": "/painel/"}, receive, send)

    assert respostas[0]["status"] == 404
    assert chamou_o_app is False

    # O que NÃO é do painel continua passando — inclusive o WebSocket, que é o que este
    # processo existe para servir.
    await protegido({"type": "http", "path": "/api/sessions"}, receive, send)
    assert chamou_o_app is True


# --- quem entra -------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_anonimo_nao_entra(client) -> None:
    resposta = client.get(PAINEL)

    assert resposta.status_code == 302
    assert "login" in resposta["Location"]


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_conta_comum_nao_entra(client, comum) -> None:
    client.force_login(comum)

    assert client.get(PAINEL).status_code == 302


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_ferramentas_de_diagnostico_nao_abrem_o_painel(client, comum) -> None:
    """O motivo de `is_staff` ser campo novo, e não um apelido de `is_admin` (SPEC-018).

    As contas com `is_admin` foram concedidas sob a promessa escrita de que a flag "não dá
    acesso a dado de ninguém". Se este teste passar a falhar, alguém uniu as duas — e promoveu
    em silêncio todo mundo que já tinha a primeira.
    """
    comum.is_admin = True
    comum.save(update_fields=["is_admin"])
    client.force_login(comum)

    assert client.get(PAINEL).status_code == 302


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_operador_entra(client, operador) -> None:
    resposta = client.get(PAINEL)  # sem login ainda
    assert resposta.status_code == 302

    client.force_login(operador)
    resposta = client.get(PAINEL)

    assert resposta.status_code == 200
    assert b"Digital Fit" in resposta.content


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_conta_desativada_perde_o_painel(client, operador) -> None:
    """`is_active` é o botão de emergência — tem de valer para o painel também."""
    client.force_login(operador)
    assert client.get(PAINEL).status_code == 200

    operador.is_active = False
    operador.save(update_fields=["is_active"])

    assert client.get(PAINEL).status_code == 302


# --- o que o painel deixa fazer -----------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_relatorio_de_sessao_nao_se_edita(client, operador) -> None:
    """Editar à mão criaria uma linha que nenhum replay reproduz (SPEC-010)."""
    SessionResult.objects.create(
        session_id="s-1", exercise="jumping_jack", mode="edge", reason="timeout", rep_count=12
    )
    client.force_login(operador)

    assert client.get(f"{PAINEL}api/sessionresult/").status_code == 200
    assert client.get(f"{PAINEL}api/sessionresult/add/").status_code == 403


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_painel_nao_promove_operador(client, operador, comum) -> None:
    """Conceder painel exige shell (`admin_tools --panel-on`), e o formulário não é atalho."""
    client.force_login(operador)

    resposta = client.post(
        f"{PAINEL}api/user/{comum.pk}/change/",
        data={
            "email": comum.email,
            "name": comum.name,
            "is_active": "on",
            "is_admin": "on",
            "is_staff": "on",
        },
    )

    assert resposta.status_code == 302  # salvou
    comum.refresh_from_db()
    assert comum.is_admin is True  # este o painel concede
    assert comum.is_staff is False  # este não


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_criar_conta_pelo_painel(client, operador) -> None:
    """Pela requisição, e não pelo formulário: o `ContaCreateForm` sozinho passava enquanto a
    tela respondia 500 — os `add_fieldsets` pedem um campo (`usable_password`) que só existe na
    forma do admin, e nada disso aparece instanciando a classe à mão.

    De quebra, a normalização do e-mail: sem ela `Ana@X.com` criada aqui conviveria com a
    `ana@x.com` do cadastro — duas linhas para a mesma pessoa, e a segunda sem conseguir entrar.
    """
    client.force_login(operador)

    assert client.get(f"{PAINEL}api/user/add/").status_code == 200

    resposta = client.post(
        f"{PAINEL}api/user/add/",
        data={
            "email": "Ana@Exemplo.COM",
            "name": "Ana",
            "usable_password": "true",
            "password1": SENHA,
            "password2": SENHA,
        },
    )

    assert resposta.status_code == 302, resposta.context["adminform"].form.errors
    assert User.objects.filter(email="ana@exemplo.com").exists()


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_troca_de_senha_pelo_painel(client, operador, comum) -> None:
    """O pedido de suporte mais comum, e a única razão de herdar do `UserAdmin` do Django."""
    client.force_login(operador)

    assert client.get(f"{PAINEL}api/user/{comum.pk}/password/").status_code == 200


# --- configuração de produto (T-073) ----------------------------------------------------
#
# Todos por REQUISIÇÃO, e não instanciando `ModelAdmin`: a lição do `ContaCreateForm` acima é
# que fieldset errado responde 500 sem que nenhum teste de classe perceba. Aqui há dois
# fieldsets novos e um `get_readonly_fields` condicional — exatamente o tipo de código que
# quebra na tela e passa na unidade.


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_telas_de_plano_e_configuracao_abrem(client, operador) -> None:
    from api.models import Plan

    client.force_login(operador)
    free = Plan.objects.get(slug="free")

    assert client.get(f"{PAINEL}api/plan/").status_code == 200
    assert client.get(f"{PAINEL}api/plan/{free.pk}/change/").status_code == 200
    assert client.get(f"{PAINEL}api/siteconfig/").status_code == 200
    assert client.get(f"{PAINEL}api/siteconfig/1/change/").status_code == 200


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_editar_o_plano_no_painel_muda_a_admissao_sem_restart(client, operador) -> None:
    """Critério 1 da SPEC-018, pelo caminho real: formulário do painel → resolvedor."""
    from api.config import capabilities_for
    from api.models import Plan

    anon = Plan.objects.get(slug="anon")
    assert capabilities_for(None).daily_sessions == 3

    client.force_login(operador)
    campos = {
        campo: getattr(anon, campo)
        for campo in (
            "nome",
            "ordem",
            "daily_sessions",
            "session_min_s",
            "session_max_s",
            "countdown_max_s",
            "history_limit",
            "streak_protections_month",
            "min_maturity",
            "quota_message",
        )
    }
    campos["daily_sessions"] = 5
    campos["allow_cloud"] = "on"
    campos["flags"] = "{}"

    resposta = client.post(f"{PAINEL}api/plan/{anon.pk}/change/", data=campos)

    assert resposta.status_code == 302, resposta.context["adminform"].form.errors
    assert capabilities_for(None).daily_sessions == 5

    # Critério 7 da spec, agora sobre configuração: mudança de capacidade sem autor e data
    # registrados seria a pior espécie de mudança sem deploy.
    from django.contrib.admin.models import LogEntry

    registro = LogEntry.objects.latest("action_time")
    assert registro.user == operador
    assert "Daily sessions" in registro.change_message


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_plano_nao_se_apaga_pelo_painel(client, operador) -> None:
    """`User.plan` é `SET_NULL`: apagar o `free` esvaziaria contas em silêncio, sem erro."""
    from api.models import Plan

    client.force_login(operador)
    free = Plan.objects.get(slug="free")

    assert client.get(f"{PAINEL}api/plan/{free.pk}/delete/").status_code == 403
    assert Plan.objects.filter(slug="free").exists()


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_configuracao_do_site_e_singleton(client, operador) -> None:
    """Um segundo `SiteConfig` seria configuração que nunca é lida (o resolvedor busca `pk=1`)."""
    client.force_login(operador)

    assert client.get(f"{PAINEL}api/siteconfig/add/").status_code == 403
    assert client.get(f"{PAINEL}api/siteconfig/1/delete/").status_code == 403


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_painel_atribui_plano_e_validade_a_uma_conta(client, operador, comum) -> None:
    """SPEC-018 §E: atribuir plano e validade é o suporte que hoje passa por shell na VPS."""
    from api.config import capabilities_for
    from api.models import Plan

    assinatura = Plan.objects.get(slug="subscriber")
    client.force_login(operador)

    resposta = client.post(
        f"{PAINEL}api/user/{comum.pk}/change/",
        data={
            "email": comum.email,
            "name": comum.name,
            "is_active": "on",
            "plan": assinatura.pk,
            "plan_until_0": "2027-01-01",
            "plan_until_1": "00:00:00",
        },
    )

    assert resposta.status_code == 302, resposta.context["adminform"].form.errors
    comum.refresh_from_db()
    assert capabilities_for(comum).plan_slug == "subscriber"


@pytest.mark.django_db
def test_cadastro_pela_api_nao_concede_o_painel(client) -> None:
    """O caminho óbvio de ataque, agora para a flag que abre dado dos outros."""
    resposta = client.post(
        "/api/auth/register",
        data={"email": "esperta@exemplo.com", "password": SENHA, "is_staff": True},
        content_type="application/json",
    )

    assert resposta.status_code == 201
    assert User.objects.get(email="esperta@exemplo.com").is_staff is False


@pytest.mark.django_db
def test_me_nao_conta_ao_cliente_quem_e_operador(client, operador) -> None:
    """`GET /api/me` é payload de produto; o cliente não tem tela que dependa do painel."""
    assert "is_staff" not in operador.to_dict()


# --- o tema e o dashboard (T-130) ---------------------------------------------------------


def test_jazzmin_vem_antes_do_admin_nos_installed_apps() -> None:
    """A ordem É o tema (SPEC-018 / T-130).

    O loader de templates de app varre `INSTALLED_APPS` na ordem, então quem vier primeiro
    responde por `admin/base.html`. Invertido, o painel volta a ser o do Django com o jazzmin
    instalado, carregado e **invisível** — nenhum erro, nenhum aviso, só a tela antiga de
    volta. É a única forma de quebrar o tema inteiro sem nada aparecer no log.
    """
    apps = list(settings.INSTALLED_APPS)
    admin = next(i for i, nome in enumerate(apps) if nome.split(".")[-1].endswith("AdminConfig"))

    assert apps.index("jazzmin") < admin


def test_dashboard_proprio_vence_o_do_tema() -> None:
    """`server/templates/` na frente dos templates de app — senão o dashboard é o do jazzmin."""
    from django.template.loader import get_template

    origem = get_template("admin/index.html").origin.name

    assert origem.endswith("server/templates/admin/index.html")
    assert get_template("admin/includes/fieldset.html").origin.name.endswith(
        "server/templates/admin/includes/fieldset.html"
    )


@pytest.mark.django_db
def test_permissoes_respondem_o_mesmo_que_has_perm(operador, comum) -> None:
    """`get_all_permissions` é a versão em conjunto do `has_perm` — e tem de concordar.

    Quem chama é o tema, em toda página, para decidir quais atalhos de modelo desenhar. Se as
    duas respostas divergirem, um atalho configurado no menu some sem erro nenhum enquanto o
    `has_perm` continua dizendo "pode".
    """
    permissoes = operador.get_all_permissions()

    assert "api.view_user" in permissoes
    assert "api.change_plan" in permissoes
    assert all(operador.has_perm(perm) for perm in permissoes)

    # E o contrário: quem não entra no painel não tem nenhuma.
    assert comum.get_all_permissions() == set()
    operador.is_active = False
    assert operador.get_all_permissions() == set()


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_dashboard_mostra_os_numeros_da_operacao(client, operador) -> None:
    SessionResult.objects.create(
        session_id="s-dash", exercise="jumping_jack", mode="edge", reason="timeout", rep_count=7
    )
    client.force_login(operador)

    corpo = client.get(PAINEL).content.decode()

    assert "Sessões hoje" in corpo
    assert "7 repetições contadas" in corpo
    # A faixa não é enfeite: é ela que diz sob qual configuração as sessões de hoje nasceram.
    assert "Configuração" in corpo


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_dashboard_sobrevive_a_um_numero_que_nao_da_para_calcular(
    client, operador, monkeypatch
) -> None:
    """P2 da SPEC-018 na forma "nenhum número derruba o painel".

    O painel sem a faixa continua servindo para tudo que servia antes. Um painel que responde
    500 na home não serve nem para consertar o que quebrou.
    """
    from api.templatetags import painel as tags

    def explode() -> dict:
        raise RuntimeError("banco fora")

    monkeypatch.setattr(tags, "_resumo", explode)
    client.force_login(operador)

    resposta = client.get(PAINEL)

    assert resposta.status_code == 200
    assert "Sessões hoje" not in resposta.content.decode()


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_aviso_de_exercicio_sem_cadencia(client, operador) -> None:
    """Cadência 0 desliga o card de calorias sem erro nenhum (T-128). O painel avisa."""
    from api.models import Exercise

    Exercise.objects.filter(enabled=True).update(ref_cadence_rpm=0)
    client.force_login(operador)

    corpo = client.get(PAINEL).content.decode()

    assert "card de calorias mostra" in corpo


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_aviso_de_exercicio_no_ar_contando_zero(client, operador) -> None:
    """T-104: o exercício não quebra nada — devolve relatório vazio a quem treinou."""
    for i in range(4):
        SessionResult.objects.create(
            session_id=f"s-zero-{i}",
            exercise="squat",
            mode="edge",
            reason="completed",
            rep_count=0,
        )
    SessionResult.objects.create(
        session_id="s-conta", exercise="squat", mode="edge", reason="completed", rep_count=12
    )
    client.force_login(operador)

    corpo = client.get(PAINEL).content.decode()

    assert "contando zero repetição" in corpo


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_sessao_sem_frame_nao_vira_aviso_de_contagem(client, operador) -> None:
    """`no_data` é captura, não contagem (T-133). Um painel que grita errado ensina o
    operador a ignorar a faixa — que é o único lugar onde o grito certo vai aparecer."""
    for i in range(10):
        SessionResult.objects.create(
            session_id=f"s-nd-{i}", exercise="squat", mode="edge", reason="no_data", rep_count=0
        )
    client.force_login(operador)

    corpo = client.get(PAINEL).content.decode()

    assert "contando zero repetição" not in corpo


@pytest.mark.django_db
@pytest.mark.urls("tests.urls_painel")
def test_descricao_do_fieldset_chega_como_html(client, operador) -> None:
    """As descrições de `api/admin.py` usam `<b>` e `<code>`, e o admin do Django as trata
    como confiáveis. O template do tema as escapava: a tela mostrava a tag como texto, no
    lugar exato onde o operador lê o que quebra ao salvar errado."""
    client.force_login(operador)

    corpo = client.get(f"{PAINEL}api/user/{operador.pk}/change/").content.decode()

    assert "<b>Ferramentas de diagnóstico</b>" in corpo
    assert "&lt;b&gt;Ferramentas" not in corpo
