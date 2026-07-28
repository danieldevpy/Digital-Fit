"""Processo do dataset-writer (T-021).

Loop: lê frames de `pose.frames` e o encerramento de `events.analysis`, bufferiza por sessão
e grava um Parquet por sessão. A inteligência está em `collector.py` (puro) e `parquet.py`
(schema); aqui é encanamento.

    python -m workers.dataset_writer.main

**Dois streams, e por quê.** Os frames vivem em `pose.frames`, mas o `session.completed`
autoritativo — o que sabe o total de reps e o motivo do fim — é emitido pelo analysis-worker
em `events.analysis`. Ler só o primeiro deixaria de fora toda sessão encerrada pelo timer dos
30 s, que é o caso normal; ler só o segundo não traria frame nenhum.

**Ack imediato, ao contrário do report-builder.** Lá as mensagens ficam pendentes até o
relatório estar no banco, porque a SPEC-010 promete que nenhuma sessão fica sem relatório.
Aqui isso seria teatro: `pose.frames` é aparado por `MAXLEN ~5000` (~11 sessões), e entrada
aparada some do stream mesmo continuando no PEL — o restart reencontraria pendências vazias.
O dataset é best-effort por construção, e a spec pede dele apenas que o arquivo seja legível.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType

from workers.dataset_writer.collector import FrameCollector, SessionFrames
from workers.shared.bus import EventBus, RedisBus
from workers.shared.events import Stream

__all__ = ["GROUP", "DatasetWriter", "main", "run"]

logger = logging.getLogger("dataset-writer")

GROUP = "dataset"
BLOCK_MS = 1000
#: Lote maior que o do analysis-worker: aqui cada mensagem só vira uma linha em memória, e a
#: 15 fps por sessão o volume é o dobro do de qualquer outro consumidor.
BATCH = 200

DEFAULT_ROOT = "dataset"


class Shutdown:
    """SIGTERM/SIGINT pedem parada limpa: termina o lote, grava o que está aberto e sai."""

    def __init__(self) -> None:
        self.requested = False

    def install(self) -> None:
        for sinal in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sinal, self._handle)

    def _handle(self, signum: int, frame: FrameType | None) -> None:
        del frame
        logger.info("sinal %s recebido, encerrando apos o lote atual", signum)
        self.requested = True


class DatasetWriter:
    """Loop de consumo. Separado de `main()` para ser testável com o barramento em memória."""

    def __init__(
        self,
        bus: EventBus,
        *,
        consumer: str,
        root: Path | str = DEFAULT_ROOT,
        sink=None,
    ) -> None:
        self.bus = bus
        self.consumer = consumer
        self.root = Path(root)
        self.collector = FrameCollector()
        #: Onde a sessão vira arquivo. Injetável para o teste do loop não precisar de disco
        #: quando o que está sob teste é o roteamento, e não o Parquet.
        self.sink = sink or self._gravar
        self.written = 0
        self.frames = 0

    def run(self, *, shutdown: Shutdown | None = None, max_batches: int | None = None) -> None:
        shutdown = shutdown or Shutdown()
        self.bus.ensure_group(Stream.POSE_FRAMES, GROUP)
        self.bus.ensure_group(Stream.EVENTS_ANALYSIS, GROUP)

        lotes = 0
        while not shutdown.requested and (max_batches is None or lotes < max_batches):
            lotes += 1
            self.run_once()

        # Sessão em andamento na hora do deploy não pode virar captura perdida.
        self._descarregar(self.collector.drain())

    def run_once(self) -> int:
        """Um lote dos dois streams + o fechamento do que venceu. Devolve eventos consumidos."""
        agora = _agora_ms()
        total = 0
        # `pose.frames` primeiro e bloqueante: é onde o volume está, e é o que dá o ritmo do
        # loop. `events.analysis` sai logo atrás sem bloquear, senão cada volta ociosa
        # esperaria dois segundos em vez de um.
        for stream, block_ms in ((Stream.POSE_FRAMES, BLOCK_MS), (Stream.EVENTS_ANALYSIS, 0)):
            for message_id, envelope in self.bus.consume(
                stream, group=GROUP, consumer=self.consumer, block_ms=block_ms, count=BATCH
            ):
                total += 1
                try:
                    self.collector.push(envelope, now_ms=agora)
                except Exception:
                    # Um evento problemático não pode matar o writer nem voltar em loop.
                    logger.exception("falha ao acumular %s (%s)", message_id, envelope.type)
                finally:
                    self.bus.ack(stream, GROUP, message_id)

        self._descarregar(self.collector.due(_agora_ms()))
        return total

    def _descarregar(self, prontas: list[SessionFrames]) -> None:
        for sessao in prontas:
            try:
                caminho = self.sink(sessao)
            except Exception:
                # Disco cheio ou permissão errada derruba esta sessão, não o processo: as
                # próximas continuam sendo gravadas e o erro aparece no log.
                logger.exception("falha ao gravar dataset de %s", sessao.session_id)
                continue
            if caminho is None:
                logger.info(
                    "sessao %s sem frames; nenhum arquivo gerado (SPEC-010, criterio 3)",
                    sessao.session_id,
                )
                continue
            self.written += 1
            self.frames += len(sessao)
            logger.info(
                "dataset de %s gravado: %s frames em %s", sessao.session_id, len(sessao), caminho
            )

    def _gravar(self, sessao: SessionFrames) -> Path | None:
        # Import tardio: pyarrow só é exigido de quem realmente grava, então o coletor e o
        # loop continuam importáveis (e testáveis) sem ele instalado.
        from workers.dataset_writer.parquet import write_session

        return write_session(sessao, root=self.root, day=_dia_utc())


def _agora_ms() -> int:
    """Relógio de parede do servidor — o único que decide carência e abandono aqui."""
    return int(time.time() * 1000)


def _dia_utc() -> str:
    """Pasta do dia, em UTC e pelo relógio do servidor.

    Não pelo `ts` do evento: ele é o relógio do cliente, e um celular com a data errada
    espalharia sessões por 1970 e 2038 dentro do corpus.
    """
    return datetime.now(UTC).strftime("%Y-%m-%d")


def run(
    bus: EventBus,
    *,
    consumer: str,
    root: Path | str = DEFAULT_ROOT,
    sink=None,
    shutdown: Shutdown | None = None,
    max_batches: int | None = None,
) -> DatasetWriter:
    """Roda o loop. `max_batches` existe para os testes rodarem um número finito de voltas."""
    writer = DatasetWriter(bus, consumer=consumer, root=root, sink=sink)
    writer.run(shutdown=shutdown, max_batches=max_batches)
    return writer


def main(argv: list[str] | None = None) -> int:
    del argv
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    root = os.environ.get("DATASET_DIR", DEFAULT_ROOT)
    # Nome com PID de propósito, ao contrário do report-builder: como o ack é imediato, não há
    # PEL a recuperar, e nomes distintos deixam duas réplicas dividirem o stream sem disputa.
    consumer = os.environ.get("CONSUMER_NAME") or f"dataset-{os.getpid()}"

    bus = RedisBus.from_url(redis_url)
    parada = Shutdown()
    parada.install()
    writer = DatasetWriter(bus, consumer=consumer, root=root)
    logger.info("dataset-writer de pe (%s) gravando em %s", consumer, Path(root).resolve())
    try:
        writer.run(shutdown=parada)
    finally:
        bus.close()
    logger.info(
        "dataset-writer encerrado: %s sessoes, %s frames gravados", writer.written, writer.frames
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
