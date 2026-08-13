"""Ajustes globais da suíte.

**Banco, cache e painel NÃO são escolhidos aqui** — quem faz isso é `core/settings_test.py`,
o `DJANGO_SETTINGS_MODULE` da suíte (`pyproject.toml`). Este arquivo já tentou fazê-lo com
`os.environ.setdefault`, contando ser lido antes do `django.setup()` do pytest-django; neste
ambiente ele não é, e a suíte inteira morria tentando Postgres e Redis. Ver a Descoberta
`[A/T-072]` do BACKLOG e a T-076.

O que sobra aqui é o que precisa de fixture: estado que muda ENTRE testes.
"""

import pytest


@pytest.fixture(autouse=True)
def _zera_rate_limit():
    """Limpa o cache entre testes.

    O contador do rate limit é global e por IP: sem isto, um arquivo de teste que faz vários
    logins deixaria o próximo teste tomando 429 — uma falha que aponta para o lugar errado e
    depende da ordem em que o pytest coleta.
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
