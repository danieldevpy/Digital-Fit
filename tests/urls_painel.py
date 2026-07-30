"""URLconf com o painel montado, para `@pytest.mark.urls` (T-072 / SPEC-018).

Em produção quem monta a rota é `DJANGO_ENABLE_ADMIN`, lida na importação do settings — cedo
demais para a conftest da suíte alcançar (ver `[A/T-072]` no BACKLOG). Este módulo tira a
decisão do ambiente: o teste que quer o painel diz que quer, no próprio teste.

Passa pela MESMA função que o `core/urls.py` de produção usa, e não por uma lista escrita à
mão: um painel montado de um jeito diferente do real testaria outra coisa.
"""

from core.urls import build_urlpatterns
from django.conf import settings

urlpatterns = build_urlpatterns(admin_enabled=True, admin_path=settings.ADMIN_PATH)
