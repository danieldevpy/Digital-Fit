"""Rotas WebSocket do gateway (SPEC-002)."""

from django.urls import path

from gateway.consumers import SessionConsumer

websocket_urlpatterns = [
    path("ws/session/<str:session_id>", SessionConsumer.as_asgi()),
]
