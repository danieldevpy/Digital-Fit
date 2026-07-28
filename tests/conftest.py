"""Ajustes globais da suíte.

Carregado antes de o pytest-django chamar `django.setup()`, que é o que torna possível
escolher o banco aqui: depois do setup, `settings.DATABASES` já teria sido lido.
"""

import os

# Postgres não existe na máquina de teste nem na CI. Os testes que tocam o banco (SPEC-010)
# rodam em SQLite em memória; o schema vem das MESMAS migrations que rodam em produção, então
# uma migration quebrada continua quebrando o teste.
os.environ.setdefault("DJANGO_DB_SQLITE", "1")
