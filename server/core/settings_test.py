"""Settings da suite de testes (T-076).

Existe porque `tests/conftest.py` NAO roda antes do `django.setup()` do pytest-django neste
ambiente. As duas linhas de `os.environ.setdefault` que escolhiam SQLite e cache em memoria
chegavam tarde demais, e a suite inteira morria tentando Postgres e Redis de verdade — a
Descoberta `[A/T-072]` do BACKLOG. O contorno era passar as variaveis na linha de comando, e
gate que depende de alguem lembrar de uma variavel nao e gate.

Um modulo de settings resolve por construcao: ele E o que o Django importa, entao o ambiente
esta ajustado antes de qualquer leitura, em qualquer ordem de import.

O que muda em relacao a `core.settings`, e so isto:

- **Banco em SQLite** (em memoria). O schema vem das MESMAS migrations que rodam em producao,
  entao uma migration quebrada continua quebrando o teste.
- **Cache em memoria**: o rate limit das rotas de auth (SPEC-011) usa o cache do Django, e
  aponta-lo para Redis exigiria Redis no pytest. O contador continua sendo exercitado de
  verdade — so nao atravessa a rede.

Todo o resto vem de `core.settings` por import estrela, de proposito: o teste roda contra a
configuracao de verdade, e opcao nova nasce valendo aqui sem ninguem lembrar de copiar.

O painel (SPEC-018) continua **desligado** aqui. `DJANGO_ENABLE_ADMIN` decide se a rota existe,
e os testes que precisam dela montam a URLconf por `@pytest.mark.urls("tests.urls_painel")` —
explicito, e sem depender de ordem de import.
"""

import os

# Antes do import, e nao depois: `core.settings` le o ambiente no momento em que e importado.
# `setdefault` e nao atribuicao porque quem chamar o pytest com a variavel na mao (para rodar
# contra Postgres de verdade, por exemplo) continua mandando.
os.environ.setdefault("DJANGO_DB_SQLITE", "1")
os.environ.setdefault("DJANGO_CACHE_LOCMEM", "1")

# O import fica DEPOIS das duas linhas acima de proposito — e a razao de este modulo existir.
from core.settings import *  # noqa: F403
