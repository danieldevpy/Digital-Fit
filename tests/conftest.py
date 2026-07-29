"""Ajustes globais da suíte.

Carregado antes de o pytest-django chamar `django.setup()`, que é o que torna possível
escolher o banco aqui: depois do setup, `settings.DATABASES` já teria sido lido.
"""

import os

# Postgres não existe na máquina de teste nem na CI. Os testes que tocam o banco (SPEC-010)
# rodam em SQLite em memória; o schema vem das MESMAS migrations que rodam em produção, então
# uma migration quebrada continua quebrando o teste.
os.environ.setdefault("DJANGO_DB_SQLITE", "1")

# Cache em memória pelo mesmo motivo: o rate limit das rotas de auth (SPEC-011) usa o cache
# do Django, e apontá-lo para Redis exigiria Redis no pytest. O contador continua sendo
# exercitado de verdade — só não atravessa a rede.
os.environ.setdefault("DJANGO_CACHE_LOCMEM", "1")

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
