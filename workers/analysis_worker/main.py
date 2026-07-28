"""Processo do analysis-worker (T-009).

Loop: lê `pose.frames` pelo consumer group `analysis`, roda o roteador, publica em
`events.analysis`, dá ack. Nada além disso — a inteligência está em `router.py` e nos
`exercises/`, ambos testáveis sem Redis.

    python -m workers.analysis_worker.main
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import sys
from types import FrameType

from workers.analysis_worker.router import AnalysisRouter
from workers.shared.bus import EventBus, RedisBus
from workers.shared.events import Stream

__all__ = ["main", "run"]

logger = logging.getLogger("analysis-worker")

GROUP = "analysis"
BLOCK_MS = 1000
BATCH = 50


class Shutdown:
    """SIGTERM/SIGINT pedem parada limpa: termina o lote e sai (o compose reinicia)."""

    def __init__(self) -> None:
        self.requested = False

    def install(self) -> None:
        for sinal in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sinal, self._handle)

    def _handle(self, signum: int, frame: FrameType | None) -> None:
        del frame
        logger.info("sinal %s recebido, encerrando apos o lote atual", signum)
        self.requested = True


def run(
    bus: EventBus,
    *,
    consumer: str,
    router: AnalysisRouter | None = None,
    shutdown: Shutdown | None = None,
    max_batches: int | None = None,
) -> AnalysisRouter:
    """Roda o loop de consumo. `max_batches` existe para os testes rodarem um número finito."""
    router = router or AnalysisRouter()
    shutdown = shutdown or Shutdown()
    bus.ensure_group(Stream.POSE_FRAMES, GROUP)

    lotes = 0
    while not shutdown.requested and (max_batches is None or lotes < max_batches):
        lotes += 1
        for message_id, envelope in bus.consume(
            Stream.POSE_FRAMES, group=GROUP, consumer=consumer, block_ms=BLOCK_MS, count=BATCH
        ):
            try:
                for saida in router.handle(envelope):
                    bus.publish(saida)
            except Exception:
                # Um evento problemático não pode matar o worker nem ser reprocessado em loop.
                logger.exception(
                    "falha ao processar %s (%s)", message_id, getattr(envelope, "type", "?")
                )
            finally:
                bus.ack(Stream.POSE_FRAMES, GROUP, message_id)

    return router


def main(argv: list[str] | None = None) -> int:
    del argv
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    consumer = os.environ.get("CONSUMER_NAME") or f"analysis-{socket.gethostname()}-{os.getpid()}"

    bus = RedisBus.from_url(redis_url)
    shutdown = Shutdown()
    shutdown.install()
    logger.info("analysis-worker de pe (%s) lendo %s", consumer, Stream.POSE_FRAMES.value)
    try:
        run(bus, consumer=consumer, shutdown=shutdown)
    finally:
        bus.close()
    logger.info("analysis-worker encerrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
