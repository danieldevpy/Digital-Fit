"""Painel de operação (SPEC-018, Fase Inicial — T-072).

Duas camadas: suporte (contas e sessões, T-072) e **configuração de produto** — planos e
parâmetros globais, T-073. O catálogo de exercícios é a T-074 e os textos de feedback ficam para
a Evolução da SPEC-018.

Duas regras que valem para tudo que for registrado daqui em diante:

1. **Dado derivado de evento é somente leitura.** `SessionResult` é escrito pelo report-builder
   a partir do stream, e a SPEC-010 promete que ele é reproduzível por replay. Uma linha
   editada à mão é uma linha que nenhum replay reproduz — e o sintoma apareceria meses depois,
   num relatório que não bate com os eventos que o geraram.
2. **Quem entra no painel enxerga tudo que está registrado.** Não há permissão por modelo
   (`has_perm` em `api/models.py` responde pela conta inteira): registrar um modelo aqui é
   decidir que todo operador pode vê-lo.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group
from django.http import HttpRequest

from api.models import (
    Exercise,
    ExerciseGuideStep,
    Plan,
    SessionClaim,
    SessionResult,
    SiteConfig,
    User,
)

admin.site.site_header = "Digital Fit — operação"
admin.site.site_title = "Digital Fit"
admin.site.index_title = "Painel"

# "Grupos" vem de graça com `django.contrib.auth` e aqui não faz **nada**: sem
# `PermissionsMixin` no `User`, quem entra no painel enxerga tudo (`has_perm` responde pela
# conta inteira), e um grupo criado nesta tela não mudaria permissão de ninguém. Deixá-lo à
# vista seria oferecer um controle que não controla — a tabela vazia que a descoberta
# `[A/T-022]` já registrou, agora com botão. Volta no dia em que o mixin entrar.
with suppress(admin.sites.NotRegistered):  # a ordem do autodiscover é quem registra
    admin.site.unregister(Group)


def _normaliza_email(form: Any) -> str:
    """Mesma normalização do cadastro (`UserManager.create_user`, `Credentials.parse`).

    O painel não passa pelo manager, então sem isto uma conta criada aqui como `Ana@x.com`
    conviveria com a `ana@x.com` do cadastro — duas linhas para a mesma pessoa, e a segunda
    nunca conseguindo entrar.
    """
    return str(form.cleaned_data.get("email") or "").strip().lower()


class ContaChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("email", "name", "is_active", "is_admin", "plan", "plan_until")

    def clean_email(self) -> str:
        return _normaliza_email(self)


class ContaCreateForm(AdminUserCreationForm):
    """`AdminUserCreationForm` e não `UserCreationForm`: é ela que declara o campo
    `usable_password` que os `add_fieldsets` do painel usam. Com a outra, a tela de criar conta
    responde 500 — e o erro só aparece na requisição, não em teste de formulário."""

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email", "name")

    def clean_email(self) -> str:
        return _normaliza_email(self)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Contas.

    Herda de `DjangoUserAdmin` por causa da tela de troca de senha (`<id>/password/`), que é o
    pedido de suporte mais comum e a única coisa aqui que não daria para escrever em dez linhas.
    Todo o resto dela é sobrescrito: os fieldsets padrão falam de `username`, `is_superuser`,
    grupos e permissões — nada disso existe neste modelo (SPEC-011).
    """

    form = ContaChangeForm
    add_form = ContaCreateForm

    list_display = ("email", "name", "plan", "plan_until", "is_active", "is_staff", "is_admin")
    list_filter = ("is_staff", "is_admin", "is_active", "plan")
    search_fields = ("email", "name")
    ordering = ("email",)
    filter_horizontal = ()

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("name",)}),
        (
            "Plano",
            {
                "fields": ("plan", "plan_until"),
                "description": (
                    "Vazio = plano default. <b>Validade</b> vazia = sem prazo; vencida, a conta "
                    "cai no default na próxima leitura, sem job de expiração. O pagamento ainda "
                    "não escreve aqui (SPEC-018 Evolução) — a atribuição é manual."
                ),
            },
        ),
        (
            "Acesso",
            {
                "fields": ("is_active", "is_admin", "is_staff"),
                "description": (
                    "<b>Ferramentas de diagnóstico</b> liberam o chip de FPS e o gravador de "
                    "fixtures no cliente. <b>Painel</b> é o acesso a esta tela e só se concede "
                    "por shell: <code>manage.py admin_tools &lt;email&gt; --panel-on</code>."
                ),
            },
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "usable_password", "password1", "password2"),
            },
        ),
    )

    #: `is_staff` é exibido mas não editável **de propósito** (SPEC-018): conceder acesso ao
    #: painel é a única escalada que o painel não faz sozinho. Um operador comprometido não
    #: promove ninguém sem ter shell na máquina — e a T-048 já tinha estabelecido essa porta
    #: única para o `is_admin`. `last_login`/`date_joined` são fatos, não campos.
    readonly_fields = ("is_staff", "last_login", "date_joined")


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Planos — a razão de a SPEC-018 existir.

    Editar aqui muda a admissão **sem restart** (o snapshot é invalidado por signal). É também
    a tela mais perigosa do painel: `daily_sessions = 1` no plano default desliga o produto para
    todo mundo às 3 h da manhã. O que compra segurança contra isso é o `clean()` do modelo
    (faixas plausíveis) e o P2 — nunca a boa intenção de quem edita.
    """

    list_display = (
        "nome",
        "slug",
        "is_default",
        "daily_sessions",
        "session_max_s",
        "allow_cloud",
        "min_maturity",
        "daily_workout",
    )
    list_filter = ("is_default", "allow_cloud", "daily_workout", "min_maturity")
    search_fields = ("slug", "nome")
    ordering = ("ordem", "slug")

    fieldsets = (
        (None, {"fields": ("slug", "nome", "is_default", "ordem")}),
        (
            "Sessões",
            {
                "fields": ("daily_sessions", "session_min_s", "session_max_s", "countdown_max_s"),
                "description": (
                    "<b>Sessões por dia:</b> 0 significa ilimitado. O contador do visitante é "
                    "por aparelho; o da conta, por usuário."
                ),
            },
        ),
        (
            "Recursos",
            {"fields": ("allow_cloud", "history_limit", "kcal_accumulation", "effects_enabled")},
        ),
        (
            "Fase 5",
            {
                "fields": ("streak_protections_month", "min_maturity", "daily_workout"),
                "description": (
                    "Capacidades consumidas pelo engajamento (SPEC-019), pelo catálogo "
                    "(SPEC-020) e pelo treino do dia (SPEC-022). Sem consumidor ligado ainda: "
                    "mudar aqui hoje não tem efeito visível."
                ),
            },
        ),
        ("Textos", {"fields": ("quota_message", "flags")}),
    )

    #: O slug é contrato: `capabilities_for` resolve o anônimo por `anon` e o default por
    #: `is_default`, e uma renomeação silenciosa faria o resolvedor cair no piso do código sem
    #: ninguém ver — o produto continuaria de pé, com a configuração toda ignorada.
    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        return ("slug",) if obj else ()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Plano não se apaga pelo painel.

        Apagar o `free` deixaria toda conta sem capacidade resolvida e apagar o `anon` mataria o
        funil — e o `on_delete=SET_NULL` do `User.plan` faria isso em silêncio, sem erro na tela.
        Plano que não se usa mais se desativa por ordem e por limite, não por DELETE.
        """
        return False


class GuideStepInline(admin.TabularInline):
    """Passos do Guia (SPEC-015), inline e não tela própria: passo não existe sem exercício."""

    model = ExerciseGuideStep
    extra = 1
    fields = ("ordem", "img", "texto")


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    """Catálogo — a apresentação que virou dado (SPEC-018 §B).

    Desligar um exercício quebrado aqui tira ele da tela **e** faz a admissão recusá-lo, sem
    deploy. A FSM continua em código: esta tela não tem nem terá limiar (P3).
    """

    inlines = (GuideStepInline,)
    list_display = ("display_name", "slug", "category", "maturity", "met", "enabled", "ordem")
    list_filter = ("enabled", "category", "maturity")
    list_editable = ("enabled", "ordem")
    search_fields = ("slug", "display_name")
    ordering = ("ordem", "slug")

    fieldsets = (
        (
            None,
            {
                "fields": ("slug", "display_name", "category", "muscle_group", "ordem", "enabled"),
                "description": (
                    "O <b>slug</b> precisa existir no registro do servidor "
                    "(<code>EXERCISES</code>). Um exercício nasce em código — FSM e fixtures — e "
                    "só então ganha esta ficha; o formulário recusa o que a admissão recusaria."
                ),
            },
        ),
        (
            "Apresentação",
            {"fields": ("default_tip", "main_angle", "demo_img", "dot_color", "scene_tip")},
        ),
        (
            "Catálogo (SPEC-020)",
            {
                "fields": ("met", "ref_cadence_rpm", "maturity", "min_plan"),
                "description": (
                    "<b>MET</b> e <b>cadência de referência</b> alimentam o kcal, e andam "
                    "juntos: o MET de tabela vale a um ritmo, e é esse ritmo que o segundo "
                    "campo declara. Mexer só num dos dois desregula a caloria — dobrar a "
                    "cadência com o mesmo MET corta o gasto por repetição pela metade. "
                    "Cadência <b>0</b> desliga o card de calorias (mostra '--'). "
                    "<b>Maturidade</b> é o selo de qualidade: a regra de quem vê o quê entra "
                    "na T-090 — hoje o campo só viaja até o cliente. <b>Plano mínimo</b> "
                    "vazio = todo mundo vê."
                ),
            },
        ),
    )

    #: O slug é a chave que amarra ficha, registro de código e admissão. Renomear depois de
    #: criado deixaria a ficha órfã (a admissão recusaria) sem nenhum erro na tela — o
    #: `clean()` do modelo pegaria um slug inexistente, mas não pega um slug VÁLIDO trocado
    #: por outro slug VÁLIDO, que é como se perde a ficha de um exercício.
    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        return ("slug",) if obj else ()


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    """Parâmetros globais (singleton).

    Sem botão de adicionar e sem botão de apagar: a linha é uma só, criada pela migration. Um
    segundo `SiteConfig` seria uma configuração que nunca é lida (o resolvedor busca `pk=1`) —
    a pior espécie de bug de painel, o que parece ter funcionado.
    """

    list_display = ("__str__", "default_duration_s", "cloud_slots", "ticket_ttl_s", "updated_at")
    readonly_fields = ("version", "updated_at")

    fieldsets = (
        ("Sessão", {"fields": ("default_duration_s", "default_countdown_s", "ticket_ttl_s")}),
        ("Capacidade cloud", {"fields": ("cloud_slots", "cloud_grace_ms")}),
        (
            "Faixas da pré-configuração",
            {
                "fields": (
                    "series_min",
                    "series_max",
                    "series_default",
                    "reps_min",
                    "reps_max",
                    "reps_default",
                )
            },
        ),
        ("Versão", {"fields": ("version", "updated_at")}),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


class SomenteLeituraAdmin(admin.ModelAdmin):
    """Base do que só se consulta. Ver a regra 1 no topo do módulo."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(SessionResult)
class SessionResultAdmin(SomenteLeituraAdmin):
    """Relatórios consolidados — a resposta para "meu treino não apareceu".

    `config_version` na lista é o critério 8 da SPEC-018 virando resposta de suporte: quem
    mudou a duração no painel ontem consegue separar as sessões de antes das de depois sem
    cruzar horário de `LogEntry` com `created_at` no olho. `0` quer dizer "não registrada" —
    sessão anterior à T-075, ou admitida com a configuração fora do ar.
    """

    list_display = (
        "session_id",
        "exercise",
        "mode",
        "reason",
        "rep_count",
        "config_version",
        "created_at",
    )
    list_filter = ("exercise", "mode", "reason", "config_version")
    search_fields = ("session_id",)
    date_hierarchy = "created_at"


@admin.register(SessionClaim)
class SessionClaimAdmin(SomenteLeituraAdmin):
    """De quem é cada sessão. Escrito pela API na admissão (ADR-009)."""

    list_display = ("session_id", "user", "device_id", "created_at")
    list_filter = ("created_at",)
    search_fields = ("session_id", "device_id", "user__email")
    date_hierarchy = "created_at"
    raw_id_fields = ("user",)


@admin.register(LogEntry)
class LogEntryAdmin(SomenteLeituraAdmin):
    """Quem mudou o quê, e quando (SPEC-018, critério 7).

    O Django grava isto sozinho a cada salvamento no painel, mas não registra a tela — sem
    ela a auditoria existe no banco e não existe para quem precisa dela. Somente leitura pelo
    motivo óbvio: registro de auditoria editável não é registro de auditoria.
    """

    list_display = ("action_time", "user", "content_type", "object_repr", "change_message")
    list_filter = ("action_flag", "content_type")
    search_fields = ("object_repr", "change_message", "user__email")
    date_hierarchy = "action_time"
