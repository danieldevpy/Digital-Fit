from django.urls import path

from api import views

urlpatterns = [
    path("healthz", views.healthz, name="healthz"),
    path("readyz", views.readyz, name="readyz"),
    path("api/sessions", views.sessions, name="sessions"),
]
