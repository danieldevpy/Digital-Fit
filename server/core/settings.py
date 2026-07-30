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

#: Painel de operação (SPEC-018 / ADR-011). **Desligado por padrão**: a única coisa que a
#: variável decide é se a rota existe neste processo — os apps e as tabelas entram sempre (ver
#: nota logo abaixo). Ligar só no serviço `api`; o gateway tem uma trava própria em
#: `core/admin_gate.py` que vale mesmo se alguém ligar a variável para ele.
ADMIN_ENABLED = _env_bool("DJANGO_ENABLE_ADMIN", False)

#: Onde o painel responde. Fora de `/admin` de propósito: é a primeira URL que qualquer
#: scanner tenta. O default já não é `admin/`, e em produção vale trocar por algo só seu.
ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "painel/").strip("/") + "/"

INSTALLED_APPS = [
    # Sem `daphne`: o gateway sobe com uvicorn (`core.asgi:application`) e o `api` segue em
    # WSGI. Instalar daphne só para trocar o runserver não paga o peso.
    "django.contrib.contenttypes",
    # Entra na SPEC-011 pelos hashers de senha, pelo `ModelBackend` e pelas validações de
    # senha.
    "django.contrib.auth",
    # Os três do painel (SPEC-018). Entram INCONDICIONALMENTE, e não atrás de `ADMIN_ENABLED`:
    # apps condicionais dariam estado de migration diferente por processo e por ambiente, e o
    # sintoma seria um `django_session` que não existe justamente na máquina onde alguém acabou
    # de ligar o painel. Com a rota desmontada, esta máquina toda fica inerte — o cookie de
    # sessão não tem quem o emita, e a autenticação do produto continua sendo só JWT.
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
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
    # Serve o CSS do painel sem depender do nginx da frente, que nesta arquitetura é o do
    # Daniel e não é versionado aqui (docs/DEPLOY.md). Sem isto o painel sobe sem estilo
    # nenhum em produção — e um admin sem CSS parece quebrado, não austero.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Só afeta o painel: as views do DRF são `csrf_exempt` e a autenticação da API é JWT
    # (`settings.REST_FRAMEWORK`), então nada que o cliente faz passa por aqui.
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # O projeto passou a servir HTML com formulário; clickjacking deixou de ser hipotético.
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
        # Os dois processadores são exigência do painel (checks `admin.E402`/`admin.E403`):
        # sem eles o Django recusa subir, e a lista ficou vazia até a SPEC-018 porque não havia
        # template nenhum sendo renderizado.
        "OPTIONS": {
            "context_processors": [
                # `request` não é exigência de check, é o que liga a barra lateral de navegação
                # do painel (`admin.W411`) — sem ela o operador navega por URL.
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
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

# Estáticos do painel: o `collectstatic` roda no build da imagem (docker/server.Dockerfile) e o
# whitenoise serve o resultado. Sem `Manifest...Storage` de propósito — ele estoura em qualquer
# ambiente onde o `collectstatic` não tenha rodado, e isso inclui a suíte de testes.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
# Em desenvolvimento o `collectstatic` não roda; o whitenoise então procura os arquivos pelos
# mesmos finders do runserver, em vez de servir de um `staticfiles/` que não existe.
WHITENOISE_USE_FINDERS = DEBUG

# Cookie de sessão — existe só para o login do painel (SPEC-018). Fora de DEBUG ele é `Secure`
# porque o painel só é acessível por HTTPS; `Lax` porque nada legítimo posta nele de outro site.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
#: Origem do painel, com esquema (`https://painel.dominio`). Necessária para o POST do login
#: passar no CSRF quando o Django está atrás do proxy que termina TLS.
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS", "")

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
