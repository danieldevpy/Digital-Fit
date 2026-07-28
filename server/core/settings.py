"""Settings do projeto Django (api + gateway).

Configuracao dirigida por variaveis de ambiente, com defaults de desenvolvimento
que funcionam no docker-compose sem nenhum arquivo .env.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-nao-usar-em-producao")
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,api,[::1]")

INSTALLED_APPS = [
    # Sem `daphne`: o gateway sobe com uvicorn (`core.asgi:application`) e o `api` segue em
    # WSGI. Instalar daphne só para trocar o runserver não paga o peso.
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "api",
    "gateway",
]

MIDDLEWARE = [
    # CORS antes de tudo: o preflight tem de ser respondido mesmo que a view recuse depois.
    "core.cors.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

#: Origens do cliente web fora de DEBUG (em DEBUG qualquer origem passa — ver core/cors.py).
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS", "")

# Atrás de um proxy que termina TLS (o nginx da VPS), o Django enxerga a conexão interna em
# http e `request.is_secure()` mente. Nada na Fase 0 depende disso ainda; fica ligado por
# variável porque só é correto quando o proxy REESCREVE o header — confiar nele com a porta
# aberta ao mundo deixaria o cliente forjar `https`.
if _env_bool("DJANGO_BEHIND_PROXY", False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "digitalfit"),
        "USER": os.environ.get("POSTGRES_USER", "digitalfit"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "digitalfit"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Barramento de eventos (Redis Streams). Consumido pelo gateway e pelos workers.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Channel layer: fanout do relay para a conexao que tem cada sessao. Em teste, camada em
# memoria (`CHANNEL_LAYER_IN_MEMORY=1`) para nao exigir Redis no pytest.
if _env_bool("CHANNEL_LAYER_IN_MEMORY", False):
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }

# URL publica do gateway WebSocket, devolvida no ticket de sessao (SPEC-009).
GATEWAY_WS_URL = os.environ.get("GATEWAY_WS_URL", "ws://localhost:8001")

# Segredo de assinatura do token de sessao (SPEC-009). Separado do SECRET_KEY para poder
# rotacionar sem invalidar outras assinaturas do Django.
SESSION_TOKEN_SECRET = os.environ.get("SESSION_TOKEN_SECRET", "")

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}
