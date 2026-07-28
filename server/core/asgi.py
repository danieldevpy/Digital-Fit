import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# O gateway WebSocket (Channels) entra aqui na T-005, envolvendo esta aplicacao
# em um ProtocolTypeRouter. Por ora, apenas HTTP.
application = get_asgi_application()
