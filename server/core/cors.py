"""CORS para o cliente web (SPEC-009: o navegador chama `POST /api/sessions`).

O cliente Vite roda em `localhost:5173` e a API em `localhost:8000` — origens diferentes, então
sem estes cabeçalhos o navegador recusa a admissão antes de ela sair da máquina. `curl` não
mostra o problema: quem aplica a regra é o navegador.

Middleware próprio em vez de `django-cors-headers`: são 30 linhas e a Fase 0 precisa de uma
regra só (a origem do dev server). Quando houver domínio de produção e cookies, trocar pela
biblioteca é uma linha no `MIDDLEWARE`.
"""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

__all__ = ["CorsMiddleware", "origem_permitida"]

ALLOWED_METHODS = "GET, POST, OPTIONS"
#: `Authorization` (JWT) e `X-Device-Id` (trial anônimo) entram na SPEC-011. Sem eles no
#: preflight, o navegador não deixa a requisição sair — e o erro aparece como "sem conta" ou
#: "trial zerado", não como CORS.
#: `If-None-Match` entra na T-074: sem ele no preflight, a revalidação do `GET /api/config`
#: nem sai do navegador.
ALLOWED_HEADERS = "Content-Type, Authorization, X-Device-Id, If-None-Match"
#: Cabeçalhos de resposta que o JavaScript consegue **ler**. Sem esta lista o navegador entrega
#: a resposta e esconde o `ETag`: `resposta.headers.get('ETag')` devolve `null` cross-origin, e
#: o cliente nunca guarda o que precisaria para revalidar. O sintoma não é erro nenhum — é o
#: `GET /api/config` baixando o payload inteiro para sempre em vez de custar 304. Não aparece no
#: `curl` (que ignora CORS) nem em teste com `fetch` dublado; só no navegador de verdade.
EXPOSED_HEADERS = "ETag"
MAX_AGE = "600"


def origem_permitida(origem: str) -> bool:
    """Origem liberada?

    Em `DEBUG` vale qualquer uma: o celular do teste entra pelo IP da LAN
    (`http://192.168.0.104:5173`), que ninguém consegue listar de antemão. Fora de `DEBUG`,
    só o que estiver em `CORS_ALLOWED_ORIGINS` — o default é vazio, então produção não
    libera nada por acidente.
    """
    if not origem:
        return False
    if settings.DEBUG:
        return True
    return origem in getattr(settings, "CORS_ALLOWED_ORIGINS", [])


class CorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        origem = request.headers.get("Origin", "")

        # Preflight: responde sem chegar na view (a view nem precisa saber que existe CORS).
        if request.method == "OPTIONS" and "Access-Control-Request-Method" in request.headers:
            resposta: HttpResponse = HttpResponse(status=204)
        else:
            resposta = self.get_response(request)

        if origem_permitida(origem):
            resposta["Access-Control-Allow-Origin"] = origem
            resposta["Access-Control-Allow-Methods"] = ALLOWED_METHODS
            resposta["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
            resposta["Access-Control-Expose-Headers"] = EXPOSED_HEADERS
            resposta["Access-Control-Max-Age"] = MAX_AGE
            # A resposta muda conforme a origem: sem isso, cache/CDN serve a origem errada.
            resposta["Vary"] = (
                f"{resposta['Vary']}, Origin" if resposta.has_header("Vary") else "Origin"
            )
        return resposta
