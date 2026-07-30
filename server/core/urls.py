"""Rotas HTTP raiz."""

from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path


def build_urlpatterns(*, admin_enabled: bool, admin_path: str) -> list[URLPattern | URLResolver]:
    """Rotas do processo, com o painel montado só quando pedido (SPEC-018).

    Função, e não um `if` solto no módulo, para que a decisão tenha teste: a garantia que
    importa é a de que o painel **não** existe com a variável desligada, e ela não dá para
    verificar por requisição — rota já importada não se desmonta.

    O `import` local é só higiene de rota condicional e **não** é trava: o app do admin está
    instalado sempre, então `AdminConfig.ready()` já rodou o autodiscover de `api/admin.py`
    antes de qualquer URL ser montada. Quem impede o acesso é a rota não existir.
    """
    rotas: list[URLPattern | URLResolver] = [path("", include("api.urls"))]
    if admin_enabled:
        from django.contrib import admin

        rotas.append(path(admin_path, admin.site.urls))
    return rotas


urlpatterns = build_urlpatterns(
    admin_enabled=settings.ADMIN_ENABLED,
    admin_path=settings.ADMIN_PATH,
)
