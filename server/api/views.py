"""Views da API.

Fase 0: saude + ciclo minimo de sessao (SPEC-009). Auth, quotas e historico sao a SPEC-011.
"""

import logging
from typing import Any

from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from api.sessions import SessionRequest, create_session

logger = logging.getLogger("api")


@api_view(["GET"])
def healthz(_request: Request) -> Response:
    """Liveness: o processo esta de pe. Nao toca em dependencias externas."""
    return Response({"status": "ok", "service": "api"})


@api_view(["GET"])
def readyz(_request: Request) -> Response:
    """Readiness: Postgres e Redis respondem."""
    checks: dict[str, Any] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["postgres"] = "ok"
    except Exception as exc:  # readiness reporta o erro, nao trata
        checks["postgres"] = f"error: {exc.__class__.__name__}"

    try:
        import redis

        redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    ready = all(value == "ok" for value in checks.values())
    return Response({"status": "ready" if ready else "degraded", "checks": checks})


@api_view(["POST"])
def sessions(request: Request) -> Response:
    """`POST /api/sessions` — admite a sessao e devolve o ticket do WebSocket (SPEC-009).

    A sessao de 30s e a unidade de carga: o token expira com o TTL (45s) e o timer autoritativo
    roda no analysis-worker, nao aqui.
    """
    try:
        pedido = SessionRequest.parse(request.data)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    try:
        ticket = create_session(pedido)
    except Exception as exc:  # Redis fora do ar: o cliente merece um erro claro
        logger.exception("falha ao criar sessao")
        return Response({"detail": f"nao foi possivel criar a sessao: {exc}"}, status=503)

    return Response(ticket.to_dict(), status=201)
