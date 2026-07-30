"""Painel de operação (SPEC-018, Fase Inicial — T-072).

O que existe aqui é o mínimo que tira o suporte do shell da VPS: ver e editar contas, ler
sessões e conferir o que foi mudado por quem. **Configuração de produto (planos, exercícios,
textos) não entra nesta task** — entra nas T-073/T-074, e entra como modelo próprio.

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

from api.models import SessionClaim, SessionResult, User

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
        fields = ("email", "name", "is_active", "is_admin")

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

    list_display = ("email", "name", "is_active", "is_staff", "is_admin", "date_joined")
    list_filter = ("is_staff", "is_admin", "is_active")
    search_fields = ("email", "name")
    ordering = ("email",)
    filter_horizontal = ()

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("name",)}),
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
    """Relatórios consolidados — a resposta para "meu treino não apareceu"."""

    list_display = ("session_id", "exercise", "mode", "reason", "rep_count", "created_at")
    list_filter = ("exercise", "mode", "reason")
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
