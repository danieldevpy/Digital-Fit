"""O painel não existe no processo do gateway (SPEC-018, critério 5).

`ROOT_URLCONF` é um só para os dois processos: o `api` sobe em WSGI (`core/wsgi.py`) e o
gateway em ASGI (`core/asgi.py`), mas ambos leem as mesmas rotas. Deixar a separação por conta
de variável de ambiente funcionaria enquanto ninguém movesse `DJANGO_ENABLE_ADMIN` para o bloco
compartilhado do compose — e o dia em que alguém movesse, o painel apareceria na porta do
WebSocket sem que nenhum teste reclamasse.

Por isso a trava é estrutural e mora aqui: o `application` do ASGI embrulha o app HTTP do Django
e responde 404 a qualquer caminho do painel, **valha o que valer a variável**. O gateway é
processo de ingestão de frames; não tem por que servir formulário de login.

Módulo puro (sem `django.setup()`), para o teste poder importá-lo sem subir o relay junto.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

__all__ = ["belongs_to_admin", "block_admin"]

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[Any]]
Send = Callable[[Any], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

_NAO_ENCONTRADO = b"404"


def belongs_to_admin(path: str, admin_path: str) -> bool:
    """O caminho pertence ao painel?

    Compara a partir da raiz e não por `in`: `/api/sessions/painel/x` não é o painel, e um
    casamento frouxo aqui derrubaria rota legítima — o oposto do que esta trava existe para
    fazer. O próprio prefixo, sem barra final (`/painel`), conta: é o que o navegador pede
    antes do redirect do Django.
    """
    prefixo = "/" + admin_path.strip("/")
    return path == prefixo or path.startswith(prefixo + "/")


def block_admin(app: ASGIApp, admin_path: str) -> ASGIApp:
    """Embrulha um app ASGI negando o painel. WebSocket passa intacto."""

    async def application(scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") == "http" and belongs_to_admin(scope.get("path", ""), admin_path):
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [
                        (b"content-type", b"text/plain; charset=utf-8"),
                        (b"content-length", str(len(_NAO_ENCONTRADO)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": _NAO_ENCONTRADO})
            return
        await app(scope, receive, send)

    return application
