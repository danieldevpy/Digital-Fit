"""Relay `events.analysis` → clientes conectados (SPEC-002).

Um único consumidor por processo de gateway lê o stream de saída da análise (consumer group
`gateway`) e reenvia cada evento ao grupo da sessão no channel layer. Quem tem a conexão daquela
sessão — este processo ou outro — recebe e empurra pelo WebSocket.

É o que faz o feedback ser parte do event loop: o gateway não pergunta nada ao worker, só
escuta o stream.
"""

from __future__ import annotations

import logging
import os
import threading

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from gateway.consumers import envelope_to_group_message, session_group
from workers.shared.bus import RedisBus
from workers.shared.events import Envelope, Stream

__all__ = ["AnalysisRelay", "publish_envelope", "start_relay"]

logger = logging.getLogger("gateway")

GROUP = "gateway"
BLOCK_MS = 500
BATCH = 100

_bus: RedisBus | None = None
_bus_lock = threading.Lock()


def bus() -> RedisBus:
    """Barramento do processo (um cliente Redis, criado na primeira necessidade)."""
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = RedisBus.from_url(settings.REDIS_URL)
        return _bus


def publish_envelope(envelope: Envelope, stream: Stream | None = None) -> str:
    """Publica um envelope vindo do cliente. Chamado de thread (o consumer é async)."""
    return bus().publish(envelope, stream=stream)


class AnalysisRelay:
    """Loop de relay. Roda em thread própria: `XREADGROUP` é bloqueante."""

    def __init__(self, *, consumer: str | None = None, channel_layer=None) -> None:
        self.consumer = consumer or f"gateway-{os.getpid()}"
        self.channel_layer = channel_layer or get_channel_layer()
        self.stop = threading.Event()
        self.forwarded = 0

    def run_once(self, event_bus=None) -> int:
        """Processa um lote; devolve quantos eventos foram repassados. Usado nos testes."""
        event_bus = event_bus or bus()
        event_bus.ensure_group(Stream.EVENTS_ANALYSIS, GROUP)
        repassados = 0
        for message_id, envelope in event_bus.consume(
            Stream.EVENTS_ANALYSIS,
            group=GROUP,
            consumer=self.consumer,
            block_ms=BLOCK_MS,
            count=BATCH,
        ):
            try:
                self._forward(envelope)
                repassados += 1
            except Exception:
                logger.exception("falha ao repassar %s ao cliente", message_id)
            finally:
                event_bus.ack(Stream.EVENTS_ANALYSIS, GROUP, message_id)
        self.forwarded += repassados
        return repassados

    def run(self, event_bus=None) -> None:
        logger.info("relay de %s ativo (%s)", Stream.EVENTS_ANALYSIS.value, self.consumer)
        while not self.stop.is_set():
            try:
                self.run_once(event_bus)
            except Exception:
                # Redis fora do ar não pode matar o gateway: loga e tenta de novo.
                logger.exception("relay falhou; tentando novamente")
                self.stop.wait(1.0)

    def _forward(self, envelope: Envelope) -> None:
        async_to_sync(self.channel_layer.group_send)(
            session_group(envelope.session_id), envelope_to_group_message(envelope)
        )


def start_relay() -> AnalysisRelay:
    """Sobe o relay em background — chamado no start do ASGI."""
    relay = AnalysisRelay()
    thread = threading.Thread(target=relay.run, name="analysis-relay", daemon=True)
    thread.start()
    return relay
