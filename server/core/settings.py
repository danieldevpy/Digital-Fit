"""Settings do projeto Django (api + gateway).

Configuracao dirigida por variaveis de ambiente, com defaults de desenvolvimento
que funcionam no docker-compose sem nenhum arquivo .env.
"""

import os
from datetime import timedelta
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
    # Entra na SPEC-011 pelos hashers de senha, pelo `ModelBackend` e pelas validações de
    # senha. NÃO entra `django.contrib.sessions`: a autenticação é JWT, e sessão de cookie
    # seria um segundo mecanismo de login para manter seguro sem ninguém usar.
    "django.contrib.auth",
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

# Os testes rodam sem Postgres (a CI instala so Python, e o pytest nao sobe container).
# `DJANGO_DB_SQLITE=1` troca o banco por SQLite em memoria; quem liga isso e o conftest do
# pytest. Fica atras de variavel, e nao de um settings_test paralelo, para que o arquivo de
# settings testado seja EXATAMENTE o que roda em producao.
if _env_bool("DJANGO_DB_SQLITE", False):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

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
    # JWT e só JWT (SPEC-011). Sem `SessionAuthentication`: ela viria com CSRF a reboque, e
    # um cliente que já manda `Authorization` não deve ter um segundo caminho de entrada.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # `AllowAny` continua sendo o default do projeto: o núcleo funciona anônimo por decisão
    # (SPEC-011, "o SaaS é adicionado por fora"). Quem exige conta declara na própria view.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    # Anônimo é `None`, não `AnonymousUser`: o projeto não tem `contrib.sessions`, e um objeto
    # que responde `is_authenticated=False` já é tudo que as views precisam distinguir.
    "UNAUTHENTICATED_USER": None,
    #: Rate limit das rotas de auth (SPEC-011). Só elas: limitar `POST /sessions` seria mexer
    #: na quota do trial, que é decisão de produto e vive em `api/trial.py`.
    "DEFAULT_THROTTLE_RATES": {"auth": os.environ.get("AUTH_THROTTLE_RATE", "10/min")},
}

AUTH_USER_MODEL = "api.User"

# Fora de DEBUG a senha passa pelos validadores padrão do Django. Em DEBUG ficam desligados:
# criar conta de teste com "1234" é rotina de desenvolvimento, e nada aqui protege produção.
AUTH_PASSWORD_VALIDATORS = (
    []
    if DEBUG
    else [
        {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    ]
)

SIMPLE_JWT = {
    # Access curto porque ele viaja em toda chamada; refresh longo porque o app é de celular e
    # ninguém quer logar de novo a cada semana. O treino em si NÃO depende disto: o WebSocket
    # é autenticado pelo token HMAC de 45 s do ticket (SPEC-009), então um access vencido no
    # meio da sessão não derruba nada — é o critério 3 da SPEC-011, e ele sai da arquitetura.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    # Sem rotação e sem blacklist na Fase Inicial: o blacklist é mais um app com migrations e
    # uma tabela que cresce, e não há o que revogar antes de existir pagamento ou logout
    # remoto. Trocar depois é ligar duas chaves.
    "ROTATE_REFRESH_TOKENS": False,
    "SIGNING_KEY": os.environ.get("JWT_SIGNING_KEY") or SECRET_KEY,
    "USER_ID_FIELD": "id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Cache — hoje serve ao contador de rate limit do DRF. Redis para que o limite valha para o
# serviço inteiro: com cache local de processo, 3 workers gunicorn dariam 3× o limite.
if _env_bool("DJANGO_CACHE_LOCMEM", False):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }

# Atrás do nginx, `REMOTE_ADDR` é o próprio proxy — sem isto o rate limit por IP contaria o
# mundo inteiro como um cliente só. Vale exatamente quando o proxy reescreve o header, que é
# a mesma condição do `SECURE_PROXY_SSL_HEADER` acima.
if _env_bool("DJANGO_BEHIND_PROXY", False):
    NUM_PROXIES = 1
