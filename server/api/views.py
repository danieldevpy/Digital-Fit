"""Views da API.

Fase 0: apenas checagens de saude. O ciclo de sessao (`POST /sessions`) entra na T-011.
"""

from typing import Any

from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


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
