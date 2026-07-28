"""Processo do pose-worker (T-016).

Loop: lê `frames.raw` pelo consumer group `pose-workers`, extrai a pose, publica `pose.frame`
em `pose.frames`, dá ack. A partir daí o modo cloud é indistinguível do edge — o
analysis-worker não sabe (nem pode saber) de onde vieram os landmarks.

    python -m workers.pose_worker.main
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import sys
from types import FrameType

from workers.pose_worker.extractor import MediaPipeImageExtractor, PoseExtractor
from workers.pose_worker.router import PoseRouter
from workers.shared.bus import EventBus, RedisBus
from workers.shared.events import Stream

__all__ = ["main", "run"]

logger = logging.getLogger("pose-worker")

GROUP = "pose-workers"
BLOCK_MS = 1000

#: Lote pequeno de propósito. Cada frame custa uma detecção completa (~80ms no orçamento da
#: SPEC-005), então puxar 50 de uma vez só encheria a memória com trabalho que vai vencer por
#: idade antes de ser feito — o descarte ficaria caro em vez de barato.
BATCH = 5

#: A cada quantos frames processados sair uma linha de estatística.
LOG_EVERY = 100


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
    extractor: PoseExtractor | None = None,
    router: PoseRouter | None = None,
    shutdown: Shutdown | None = None,
    max_batches: int | None = None,
) -> PoseRouter:
    """Roda o loop de consumo. `max_batches` existe para os testes rodarem um número finito."""
    if router is None:
        if extractor is None:
            raise ValueError("informe `router` ou `extractor`")
        router = PoseRouter(extractor=extractor)
    shutdown = shutdown or Shutdown()
    bus.ensure_group(Stream.FRAMES_RAW, GROUP)

    lotes = 0
    ultimo_log = 0
    while not shutdown.requested and (max_batches is None or lotes < max_batches):
        lotes += 1
        for message_id, envelope in bus.consume(
            Stream.FRAMES_RAW, group=GROUP, consumer=consumer, block_ms=BLOCK_MS, count=BATCH
        ):
            try:
                for saida in router.handle(envelope):
                    bus.publish(saida, stream=Stream.POSE_FRAMES)
            except Exception:
                # `handle` já trata o que sabe; isto cobre falha ao PUBLICAR, que não pode
                # matar o worker nem deixar a mensagem pendente para sempre.
                logger.exception("falha ao processar %s", message_id)
            finally:
                bus.ack(Stream.FRAMES_RAW, GROUP, message_id)

        if router.stats.processed - ultimo_log >= LOG_EVERY:
            ultimo_log = router.stats.processed
            logger.info("pose-worker %s", router.stats.as_dict())

    return router


def main(argv: list[str] | None = None) -> int:
    del argv
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    consumer = os.environ.get("CONSUMER_NAME") or f"pose-{socket.gethostname()}-{os.getpid()}"

    # Carregar o modelo antes do primeiro frame: são centenas de ms, e pagá-los no meio de uma
    # sessão de 30s significaria descartar os primeiros frames por idade.
    extractor = MediaPipeImageExtractor()
    logger.info("modelo de pose carregado: %s", extractor.version)

    bus = RedisBus.from_url(redis_url)
    shutdown = Shutdown()
    shutdown.install()
    router = PoseRouter(extractor=extractor)
    logger.info("pose-worker de pe (%s) lendo %s", consumer, Stream.FRAMES_RAW.value)
    try:
        run(bus, consumer=consumer, router=router, shutdown=shutdown)
    finally:
        extractor.close()
        bus.close()
    logger.info("pose-worker encerrado %s", router.stats.as_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
