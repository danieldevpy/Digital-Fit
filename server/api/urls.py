from django.urls import path

from api import auth, views

urlpatterns = [
    path("healthz", views.healthz, name="healthz"),
    path("readyz", views.readyz, name="readyz"),
    # A SPEC-011 escreve as rotas sem prefixo (`POST /auth/login`, `GET /me`). Ficam sob
    # `/api/` como todo o resto: o prefixo separa a API do que o nginx serve como app, e
    # abrir uma segunda raiz só para auth seria a exceção mais cara de explicar do projeto.
    path("api/auth/register", auth.register, name="auth-register"),
    path("api/auth/login", auth.login, name="auth-login"),
    path("api/auth/refresh", auth.refresh, name="auth-refresh"),
    path("api/me", auth.me, name="me"),
    path("api/config", views.config, name="config"),
    # Separada do `/api/config` de proposito: aquela resposta e cacheada por ETag, e esta muda
    # a cada sessao (ver `views.quota`).
    path("api/quota", views.quota, name="quota"),
    path("api/sessions", views.sessions, name="sessions"),
    path("api/sessions/<str:session_id>/report", views.session_report, name="session-report"),
]
