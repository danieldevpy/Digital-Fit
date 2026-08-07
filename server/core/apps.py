"""Configuração de app do próprio projeto.

Existe por um motivo só, e ele é de rótulo: o `django.contrib.admin` se apresenta como
"Administration" no menu do painel, e o `USE_I18N = False` deste projeto (settings) faz esse
texto **não** ser traduzido. Num painel em português, sobrando um grupo em inglês só para
abrigar o registro de auditoria, o operador lê duas línguas na mesma barra lateral.

Subclasse do `AdminConfig` e não do `SimpleAdminConfig`: é o `AdminConfig` que roda o
autodiscover de `api/admin.py` no `ready()`. Trocar pela outra classe faria o painel subir
com zero modelos registrados — sem erro nenhum, que é o pior jeito de descobrir.
"""

from django.contrib.admin.apps import AdminConfig


class PainelAdminConfig(AdminConfig):
    verbose_name = "Auditoria"
