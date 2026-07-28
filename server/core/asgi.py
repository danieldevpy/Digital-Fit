"""Aplicação ASGI: HTTP (DRF) + WebSocket (Channels).

O relay de `events.analysis` sobe junto com o processo do gateway — é ele que empurra os
eventos de análise ao cliente (SPEC-002).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# `get_asgi_application()` primeiro: carrega os apps antes de importar consumers.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from gateway.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(websocket_urlpatterns),
    }
)


if os.environ.get("GATEWAY_RELAY", "1") not in {"0", "false", "False"}:
    from gateway.relay import start_relay

    start_relay()
